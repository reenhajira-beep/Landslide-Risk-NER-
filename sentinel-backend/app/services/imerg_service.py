"""NASA GPM IMERG Early Run downloader and point-sampling service.

The service downloads one official 30-minute IMERG GIS ZIP, opens the
total-precipitation GeoTIFF in memory, and samples the 0.1-degree grid at
each configured monitoring location. No large raster is stored in PostgreSQL.
"""

from __future__ import annotations

import asyncio
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from io import BytesIO
from pathlib import PurePosixPath
from urllib.parse import unquote, urljoin, urlsplit
from zipfile import BadZipFile, ZipFile

import httpx
from PIL import Image, UnidentifiedImageError


IMERG_WIDTH = 3600
IMERG_HEIGHT = 1800
IMERG_RESOLUTION_DEGREES = 0.1
IMERG_MISSING_VALUE = 29999
IMERG_ACCUMULATION_SCALE = 10.0
IMERG_PERIOD_HOURS = 0.5

DEFAULT_BASE_URL = (
    "https://jsimpsonhttps.pps.eosdis.nasa.gov/imerg/gis/early"
)

PRODUCT_PATTERN = re.compile(
    r"^3B-HHR-E\..*?\."
    r"(?P<date>\d{8})-S(?P<start>\d{6})-E(?P<end>\d{6})\."
    r"\d{4}\.(?P<version>V\d{2}[A-Z]?)\.30min\.zip$",
    re.IGNORECASE,
)


class IMERGError(RuntimeError):
    """Base class for clear satellite-provider failures."""


class IMERGNotConfiguredError(IMERGError):
    """Raised when the provider is disabled or credentials are absent."""


class IMERGAuthenticationError(IMERGError):
    """Raised when NASA PPS rejects the configured account."""


class IMERGProviderError(IMERGError):
    """Raised when the NASA server or downloaded product is unavailable."""


class IMERGProductError(IMERGError):
    """Raised when an IMERG archive or GeoTIFF is invalid."""


class _LinkCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        if tag.lower() != "a":
            return

        for name, value in attrs:
            if name.lower() == "href" and value:
                self.links.append(value)
                return


@dataclass(frozen=True)
class IMERGProduct:
    filename: str
    url: str
    version: str
    period_start: datetime
    period_end: datetime


@dataclass
class IMERGGrid:
    product: IMERGProduct
    image: Image.Image
    downloaded_at: datetime


@dataclass(frozen=True)
class IMERGPointSample:
    raw_pixel_value: int
    grid_row: int
    grid_column: int
    accumulation_mm: float | None
    rainfall_rate_mm_hr: float | None
    quality_status: str
    is_missing: bool


def _read_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)

    if value is None:
        return default

    return value.strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _read_positive_int(name: str, default: int) -> int:
    raw_value = os.getenv(name)

    if raw_value is None:
        return default

    try:
        value = int(raw_value)
    except ValueError:
        return default

    return value if value > 0 else default


def _read_positive_float(name: str, default: float) -> float:
    raw_value = os.getenv(name)

    if raw_value is None:
        return default

    try:
        value = float(raw_value)
    except ValueError:
        return default

    return value if value > 0 else default


class IMERGRainfallService:
    """Fetch and decode the newest NASA IMERG Early Run GIS product."""

    def __init__(
        self,
        *,
        enabled: bool | None = None,
        pps_email: str | None = None,
        pps_password: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self.enabled = (
            enabled
            if enabled is not None
            else _read_bool("NASA_GPM_ENABLED", False)
        )

        self.pps_email = (
            pps_email
            if pps_email is not None
            else os.getenv("NASA_GPM_PPS_EMAIL", "").strip()
        )

        configured_password = (
            pps_password
            if pps_password is not None
            else os.getenv("NASA_GPM_PPS_PASSWORD", "").strip()
        )

        # NASA PPS documentation currently uses the registered email as
        # both username and password. A separate password remains supported
        # in case the provider changes this behavior later.
        self.pps_password = configured_password or self.pps_email

        self.base_url = (
            base_url
            or os.getenv("NASA_GPM_BASE_URL", DEFAULT_BASE_URL)
        ).rstrip("/")

        self.timeout_seconds = _read_positive_float(
            "NASA_GPM_TIMEOUT_SECONDS",
            45.0,
        )
        self.cache_ttl_seconds = _read_positive_int(
            "NASA_GPM_CACHE_TTL_SECONDS",
            900,
        )
        self.max_download_bytes = _read_positive_int(
            "NASA_GPM_MAX_DOWNLOAD_MB",
            64,
        ) * 1024 * 1024
        self.max_uncompressed_bytes = _read_positive_int(
            "NASA_GPM_MAX_UNCOMPRESSED_MB",
            64,
        ) * 1024 * 1024
        self.collection_interval_seconds = _read_positive_int(
            "NASA_GPM_COLLECTION_INTERVAL_SECONDS",
            1800,
        )
        self.auto_collection_enabled = _read_bool(
            "NASA_GPM_AUTO_COLLECTION",
            True,
        )
        self.max_data_age_hours = _read_positive_float(
            "NASA_GPM_MAX_DATA_AGE_HOURS",
            12.0,
        )

        self._cache: IMERGGrid | None = None
        self._cache_lock = asyncio.Lock()
        self.last_success_at: datetime | None = None
        self.last_error: str | None = None

    @property
    def configured(self) -> bool:
        return bool(self.enabled and self.pps_email)

    @property
    def should_auto_collect(self) -> bool:
        return bool(
            self.configured
            and self.auto_collection_enabled
        )

    @staticmethod
    def parse_product_filename(
        filename: str,
        directory_url: str = "",
    ) -> IMERGProduct | None:
        match = PRODUCT_PATTERN.match(filename)

        if match is None:
            return None

        date_value = match.group("date")
        start_value = match.group("start")
        end_value = match.group("end")

        period_start = datetime.strptime(
            f"{date_value}{start_value}",
            "%Y%m%d%H%M%S",
        ).replace(tzinfo=timezone.utc)

        period_end = datetime.strptime(
            f"{date_value}{end_value}",
            "%Y%m%d%H%M%S",
        ).replace(tzinfo=timezone.utc)

        if period_end < period_start:
            period_end += timedelta(days=1)

        return IMERGProduct(
            filename=filename,
            url=urljoin(
                directory_url.rstrip("/") + "/",
                filename,
            ),
            version=match.group("version").upper(),
            period_start=period_start,
            period_end=period_end,
        )

    @classmethod
    def products_from_directory_html(
        cls,
        html: str,
        directory_url: str,
    ) -> list[IMERGProduct]:
        parser = _LinkCollector()
        parser.feed(html)

        products: dict[str, IMERGProduct] = {}

        for href in parser.links:
            decoded_path = unquote(urlsplit(href).path)
            filename = PurePosixPath(
                decoded_path.replace("\\", "/")
            ).name

            product = cls.parse_product_filename(
                filename,
                directory_url,
            )

            if product is not None:
                products[filename] = product

        return sorted(
            products.values(),
            key=lambda item: (
                item.period_start,
                item.version,
                item.filename,
            ),
        )

    @staticmethod
    def month_directories(
        now: datetime | None = None,
    ) -> list[str]:
        reference = now or datetime.now(timezone.utc)

        if reference.tzinfo is None:
            reference = reference.replace(tzinfo=timezone.utc)

        current_month = reference.astimezone(timezone.utc).replace(
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
        previous_month = current_month - timedelta(days=1)

        return [
            f"{current_month.year:04d}/{current_month.month:02d}",
            f"{previous_month.year:04d}/{previous_month.month:02d}",
        ]

    @staticmethod
    def coordinate_to_pixel(
        latitude: float,
        longitude: float,
    ) -> tuple[int, int]:
        if not -90.0 <= latitude <= 90.0:
            raise ValueError("latitude must be between -90 and 90")

        if not -180.0 <= longitude <= 180.0:
            raise ValueError("longitude must be between -180 and 180")

        column = int(
            (longitude + 180.0)
            // IMERG_RESOLUTION_DEGREES
        )
        row = int(
            (90.0 - latitude)
            // IMERG_RESOLUTION_DEGREES
        )

        # Coordinates exactly on the eastern or southern outer boundary
        # belong to the final valid grid cell.
        column = min(max(column, 0), IMERG_WIDTH - 1)
        row = min(max(row, 0), IMERG_HEIGHT - 1)

        return row, column

    @classmethod
    def sample_grid(
        cls,
        grid: IMERGGrid,
        *,
        latitude: float,
        longitude: float,
    ) -> IMERGPointSample:
        if grid.image.size != (IMERG_WIDTH, IMERG_HEIGHT):
            raise IMERGProductError(
                "Unexpected IMERG raster size: "
                f"{grid.image.size}; expected "
                f"{(IMERG_WIDTH, IMERG_HEIGHT)}."
            )

        row, column = cls.coordinate_to_pixel(
            latitude,
            longitude,
        )

        pixel = grid.image.getpixel((column, row))

        if isinstance(pixel, tuple):
            pixel = pixel[0]

        raw_value = int(pixel)

        if raw_value == IMERG_MISSING_VALUE:
            return IMERGPointSample(
                raw_pixel_value=raw_value,
                grid_row=row,
                grid_column=column,
                accumulation_mm=None,
                rainfall_rate_mm_hr=None,
                quality_status="MISSING_AT_GRID_CELL",
                is_missing=True,
            )

        if raw_value < 0 or raw_value > IMERG_MISSING_VALUE:
            raise IMERGProductError(
                f"Invalid IMERG precipitation value: {raw_value}."
            )

        accumulation_mm = raw_value / IMERG_ACCUMULATION_SCALE
        rainfall_rate_mm_hr = accumulation_mm / IMERG_PERIOD_HOURS

        return IMERGPointSample(
            raw_pixel_value=raw_value,
            grid_row=row,
            grid_column=column,
            accumulation_mm=round(accumulation_mm, 3),
            rainfall_rate_mm_hr=round(rainfall_rate_mm_hr, 3),
            quality_status="VALID",
            is_missing=False,
        )

    def _ensure_configured(self) -> None:
        if not self.enabled:
            raise IMERGNotConfiguredError(
                "NASA GPM collection is disabled. Set "
                "NASA_GPM_ENABLED=true in .env."
            )

        if not self.pps_email:
            raise IMERGNotConfiguredError(
                "NASA_GPM_PPS_EMAIL is missing. Register the email "
                "with NASA PPS and add it to .env."
            )

    def _auth(self) -> httpx.BasicAuth:
        return httpx.BasicAuth(
            self.pps_email,
            self.pps_password,
        )

    async def _read_response_with_limit(
        self,
        response: httpx.Response,
        maximum_bytes: int,
    ) -> bytes:
        chunks: list[bytes] = []
        total_bytes = 0

        async for chunk in response.aiter_bytes():
            total_bytes += len(chunk)

            if total_bytes > maximum_bytes:
                raise IMERGProviderError(
                    "NASA IMERG response exceeded the configured "
                    "download-size limit."
                )

            chunks.append(chunk)

        return b"".join(chunks)

    async def _list_products(
        self,
        client: httpx.AsyncClient,
        now: datetime,
    ) -> list[IMERGProduct]:
        products: list[IMERGProduct] = []

        for month_path in self.month_directories(now):
            directory_url = f"{self.base_url}/{month_path}/"

            async with client.stream(
                "GET",
                directory_url,
            ) as response:
                if response.status_code in {401, 403}:
                    raise IMERGAuthenticationError(
                        "NASA PPS rejected the registered email. "
                        "Check NASA_GPM_PPS_EMAIL and PPS registration."
                    )

                if response.status_code == 404:
                    continue

                response.raise_for_status()
                payload = await self._read_response_with_limit(
                    response,
                    5 * 1024 * 1024,
                )

            products.extend(
                self.products_from_directory_html(
                    payload.decode("utf-8", errors="replace"),
                    directory_url,
                )
            )

        return products

    async def _download_product(
        self,
        client: httpx.AsyncClient,
        product: IMERGProduct,
    ) -> bytes:
        async with client.stream(
            "GET",
            product.url,
        ) as response:
            if response.status_code in {401, 403}:
                raise IMERGAuthenticationError(
                    "NASA PPS rejected the registered email while "
                    "downloading the IMERG product."
                )

            response.raise_for_status()

            return await self._read_response_with_limit(
                response,
                self.max_download_bytes,
            )

    def decode_product(
        self,
        product: IMERGProduct,
        archive_bytes: bytes,
        *,
        downloaded_at: datetime | None = None,
    ) -> IMERGGrid:
        try:
            with ZipFile(BytesIO(archive_bytes)) as archive:
                candidates = []

                for member in archive.infolist():
                    if member.is_dir():
                        continue

                    name = PurePosixPath(
                        member.filename.replace("\\", "/")
                    ).name
                    lower_name = name.lower()

                    if not lower_name.endswith(".tif"):
                        continue

                    if any(
                        excluded in lower_name
                        for excluded in (
                            "liquid",
                            "ice",
                            "percent",
                            "numvalid",
                            "numprecip",
                            ".rate.",
                        )
                    ):
                        continue

                    rank = 2

                    if lower_name.endswith(".30min.tif"):
                        rank = 0
                    elif "total.accum" in lower_name:
                        rank = 1

                    candidates.append((rank, name, member))

                if not candidates:
                    raise IMERGProductError(
                        "The NASA IMERG archive contains no total "
                        "precipitation GeoTIFF."
                    )

                _, _, selected = min(
                    candidates,
                    key=lambda item: (item[0], item[1]),
                )

                if selected.file_size > self.max_uncompressed_bytes:
                    raise IMERGProductError(
                        "The IMERG GeoTIFF exceeded the configured "
                        "uncompressed-size limit."
                    )

                image_bytes = archive.read(selected)

        except BadZipFile as error:
            raise IMERGProductError(
                "NASA returned an invalid IMERG ZIP archive."
            ) from error

        try:
            with Image.open(BytesIO(image_bytes)) as opened_image:
                opened_image.load()
                image = opened_image.copy()
        except (UnidentifiedImageError, OSError) as error:
            raise IMERGProductError(
                "Unable to decode the IMERG GeoTIFF."
            ) from error

        if image.size != (IMERG_WIDTH, IMERG_HEIGHT):
            image.close()
            raise IMERGProductError(
                "NASA IMERG GeoTIFF has an unexpected raster size: "
                f"{image.size}."
            )

        return IMERGGrid(
            product=product,
            image=image,
            downloaded_at=(
                downloaded_at
                or datetime.now(timezone.utc)
            ),
        )

    def _cache_is_fresh(self, now: datetime) -> bool:
        if self._cache is None:
            return False

        age_seconds = (
            now - self._cache.downloaded_at
        ).total_seconds()

        return age_seconds < self.cache_ttl_seconds

    async def fetch_latest_grid(
        self,
        *,
        force_refresh: bool = False,
        now: datetime | None = None,
    ) -> IMERGGrid:
        self._ensure_configured()

        reference = now or datetime.now(timezone.utc)

        if reference.tzinfo is None:
            reference = reference.replace(tzinfo=timezone.utc)

        reference = reference.astimezone(timezone.utc)

        async with self._cache_lock:
            if (
                not force_refresh
                and self._cache_is_fresh(reference)
            ):
                return self._cache  # type: ignore[return-value]

            try:
                timeout = httpx.Timeout(self.timeout_seconds)

                async with httpx.AsyncClient(
                    auth=self._auth(),
                    follow_redirects=True,
                    timeout=timeout,
                    headers={
                        "User-Agent": "SENTINEL-NER/3.2 NASA-IMERG",
                    },
                ) as client:
                    products = await self._list_products(
                        client,
                        reference,
                    )

                    if not products:
                        raise IMERGProviderError(
                            "No 30-minute IMERG Early Run product was "
                            "found in the current or previous month."
                        )

                    latest_product = products[-1]
                    archive_bytes = await self._download_product(
                        client,
                        latest_product,
                    )

                grid = self.decode_product(
                    latest_product,
                    archive_bytes,
                    downloaded_at=reference,
                )
                self._cache = grid
                self.last_success_at = reference
                self.last_error = None

                return grid

            except IMERGError as error:
                self.last_error = str(error)
                raise

            except httpx.HTTPStatusError as error:
                message = (
                    "NASA PPS returned HTTP "
                    f"{error.response.status_code}."
                )
                self.last_error = message
                raise IMERGProviderError(message) from error

            except httpx.HTTPError as error:
                message = (
                    "Unable to contact the NASA PPS IMERG server: "
                    f"{error.__class__.__name__}."
                )
                self.last_error = message
                raise IMERGProviderError(message) from error

            except (ValueError, OSError) as error:
                message = f"Unable to process NASA IMERG data: {error}."
                self.last_error = message
                raise IMERGProductError(message) from error

    def get_status(self) -> dict:
        if not self.enabled:
            status = "disabled"
        elif not self.pps_email:
            status = "not_configured"
        elif self.last_error:
            status = "degraded"
        else:
            status = "ready"

        return {
            "status": status,
            "enabled": self.enabled,
            "configured": self.configured,
            "auto_collection_enabled": self.auto_collection_enabled,
            "provider": "NASA GPM PPS",
            "product": "IMERG Early Run GIS 30-minute",
            "base_url": self.base_url,
            "temporal_resolution_minutes": 30,
            "spatial_resolution_degrees": IMERG_RESOLUTION_DEGREES,
            "approximate_spatial_resolution_km": 10,
            "expected_latency_hours": "4-5",
            "collection_interval_seconds": (
                self.collection_interval_seconds
            ),
            "maximum_prediction_age_hours": self.max_data_age_hours,
            "last_success_at": self.last_success_at,
            "last_error": self.last_error,
            "credentials_exposed": False,
        }


imerg_service = IMERGRainfallService()
