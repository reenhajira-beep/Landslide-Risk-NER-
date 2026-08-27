from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "landslide_data.csv"
)


def generate_demo_data(number_of_rows: int = 1000):

    random_generator = np.random.default_rng(42)

    rainfall = random_generator.uniform(
        0,
        120,
        number_of_rows
    )

    soil_moisture = np.clip(
        25
        + rainfall * 0.45
        + random_generator.normal(
            0,
            12,
            number_of_rows
        ),
        0,
        100
    )

    tilt = random_generator.uniform(
        0,
        8,
        number_of_rows
    )

    vegetation_change = random_generator.uniform(
        0,
        35,
        number_of_rows
    )

    satellite_risk = np.clip(
        rainfall / 200
        + soil_moisture / 300
        + tilt / 25
        + random_generator.normal(
            0,
            0.12,
            number_of_rows
        ),
        0,
        1
    )

    simulated_score = (
        np.minimum(rainfall / 100, 1) * 30
        + soil_moisture / 100 * 25
        + np.minimum(tilt / 10, 1) * 20
        + vegetation_change / 100 * 10
        + satellite_risk * 15
    )

    probability = 1 / (
        1 + np.exp(-(simulated_score - 50) / 8)
    )

    landslide_next_6h = random_generator.binomial(
        1,
        probability
    )

    dataset = pd.DataFrame({
        "rainfall_mm_hr": rainfall.round(2),
        "soil_moisture_pct": soil_moisture.round(2),
        "tilt_deg": tilt.round(2),
        "vegetation_change_pct": (
            vegetation_change.round(2)
        ),
        "satellite_risk_index": (
            satellite_risk.round(3)
        ),
        "landslide_next_6h": landslide_next_6h
    })

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    dataset.to_csv(
        OUTPUT_PATH,
        index=False
    )

    print(f"Demo dataset saved: {OUTPUT_PATH}")
    print(f"Number of rows: {len(dataset)}")
    print(dataset["landslide_next_6h"].value_counts())


if __name__ == "__main__":
    generate_demo_data()