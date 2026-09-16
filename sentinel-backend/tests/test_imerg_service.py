"""Offline tests for NASA IMERG parsing, decoding, and point sampling."""

from datetime import datetime, timezone
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from PIL import Image

from app.services.imerg_service import (
    IMERG_HEIGHT,
    IMERG_MISSING_VALUE,
    IMERG_WIDTH,
    IMERGRainfallService,
)


EXAMPLE_FILENAME = (
    "3B-HHR-E.MS.MRG.3IMERG.20260915-"
    "S053000-E055959.0330.V07B.30min.zip"
)


def _product():
    product = IMERGRainfallService.parse_product_filename(
        EXAMPLE_FILENAME,
        "https://example.test/2026/09/",
    )
    assert product is not None
    return product


def _archive_with_pixel(
    latitude: float,
    longitude: float,
    pixel_value: int,
) -> bytes:
    row, column = IMERGRainfallService.coordinate_to_pixel(
        latitude,
        longitude,
    )
    image = Image.new(
        "I;16",
        (IMERG_WIDTH, IMERG_HEIGHT),
        color=0,
    )
    image.putpixel((column, row), pixel_value)

    tiff_buffer = BytesIO()
    image.save(tiff_buffer, format="TIFF")
    image.close()

    archive_buffer = BytesIO()

    with ZipFile(
        archive_buffer,
        mode="w",
        compression=ZIP_DEFLATED,
    ) as archive:
        archive.writestr(
            EXAMPLE_FILENAME.removesuffix(".zip") + ".tif",
            tiff_buffer.getvalue(),
        )

    return archive_buffer.getvalue()


def test_parse_official_product_filename():
    product = _product()

    assert product.version == "V07B"
    assert product.period_start == datetime(
        2026,
        9,
        15,
        5,
        30,
        tzinfo=timezone.utc,
    )
    assert product.period_end == datetime(
        2026,
        9,
        15,
        5,
        59,
        59,
        tzinfo=timezone.utc,
    )


def test_directory_parser_filters_and_orders_products():
    older = EXAMPLE_FILENAME.replace("S053000-E055959", "S050000-E052959")
    html = (
        f'<a href="{EXAMPLE_FILENAME}">latest</a>'
        f'<a href="{older}">older</a>'
        '<a href="unrelated.txt">ignore</a>'
    )

    products = IMERGRainfallService.products_from_directory_html(
        html,
        "https://example.test/2026/09/",
    )

    assert [item.filename for item in products] == [
        older,
        EXAMPLE_FILENAME,
    ]


def test_coordinate_to_pixel_matches_documented_global_grid():
    row, column = IMERGRainfallService.coordinate_to_pixel(
        latitude=26.1445,
        longitude=91.7362,
    )

    assert 0 <= row < IMERG_HEIGHT
    assert 0 <= column < IMERG_WIDTH
    assert (row, column) == (638, 2717)


def test_decode_and_sample_converts_accumulation_to_hourly_rate():
    latitude = 26.1445
    longitude = 91.7362
    service = IMERGRainfallService(
        enabled=True,
        pps_email="registered@example.com",
    )
    archive = _archive_with_pixel(
        latitude,
        longitude,
        pixel_value=123,
    )
    grid = service.decode_product(
        _product(),
        archive,
        downloaded_at=datetime.now(timezone.utc),
    )

    sample = service.sample_grid(
        grid,
        latitude=latitude,
        longitude=longitude,
    )

    assert sample.accumulation_mm == 12.3
    assert sample.rainfall_rate_mm_hr == 24.6
    assert sample.quality_status == "VALID"
    assert sample.is_missing is False
    grid.image.close()


def test_missing_value_is_not_sent_to_the_ml_model():
    latitude = 27.0844
    longitude = 93.6053
    service = IMERGRainfallService(
        enabled=True,
        pps_email="registered@example.com",
    )
    archive = _archive_with_pixel(
        latitude,
        longitude,
        pixel_value=IMERG_MISSING_VALUE,
    )
    grid = service.decode_product(
        _product(),
        archive,
    )

    sample = service.sample_grid(
        grid,
        latitude=latitude,
        longitude=longitude,
    )

    assert sample.accumulation_mm is None
    assert sample.rainfall_rate_mm_hr is None
    assert sample.quality_status == "MISSING_AT_GRID_CELL"
    assert sample.is_missing is True
    grid.image.close()


def test_service_starts_safely_without_credentials():
    service = IMERGRainfallService(
        enabled=True,
        pps_email="",
    )

    status = service.get_status()

    assert status["status"] == "not_configured"
    assert status["configured"] is False
    assert status["credentials_exposed"] is False
