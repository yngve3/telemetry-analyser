# training/scripts/train_correlation_profile.py

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(SCRIPTS_ROOT))

from preprocessing.alfa_preprocessing import (  # noqa: E402
    find_flight_dirs,
    load_flight_dataframe,
)


METRICS = (
    'position_speed_error',
    'altitude_velocity_error',
    'heading_yaw_error',
)


def build_profile(
    all_errors: dict[str, list[float]],
    max_size: int,
    min_samples: int,
    percentile: float,
    threshold_multiplier: float,
) -> dict:
    errors: dict[str, list[float]] = {}

    for metric in METRICS:
        values = np.array(all_errors.get(metric, []), dtype=float)
        values = values[np.isfinite(values)]

        if len(values) > max_size:
            values = values[-max_size:]

        errors[metric] = values.tolist()

    return {
        'max_size': max_size,
        'min_samples': min_samples,
        'percentile': percentile,
        'threshold_multiplier': threshold_multiplier,
        'errors': errors,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--processed-root', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--max-size', type=int, default=1000)
    parser.add_argument('--min-samples', type=int, default=100)
    parser.add_argument('--percentile', type=float, default=0.99)
    parser.add_argument('--threshold-multiplier', type=float, default=1.2)
    parser.add_argument('--tolerance', type=float, default=1.0)

    args = parser.parse_args()

    all_errors: dict[str, list[float]] = defaultdict(list)
    used_flights: list[str] = []
    skipped_flights: list[dict[str, str]] = []

    for folder in find_flight_dirs(args.processed_root, no_failure_only=True):
        try:
            flight = load_flight_dataframe(folder, tolerance=args.tolerance)

            for metric in METRICS:
                values = flight[metric].to_numpy(dtype=float)
                values = values[np.isfinite(values)]
                all_errors[metric].extend(values.tolist())

            used_flights.append(folder.name)

            counts = ', '.join(
                f'{metric}={len(all_errors[metric])}'
                for metric in METRICS
            )
            print(f'OK {folder.name}: rows={len(flight)}, total {counts}')

        except Exception as error:
            skipped_flights.append({'flight': folder.name, 'reason': str(error)})
            print(f'SKIP {folder.name}: {error}')

    profile = build_profile(
        all_errors=all_errors,
        max_size=args.max_size,
        min_samples=args.min_samples,
        percentile=args.percentile,
        threshold_multiplier=args.threshold_multiplier,
    )

    profile['metadata'] = {
        'source_dataset': 'ALFA',
        'used_flights': used_flights,
        'skipped_flights': skipped_flights,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)

    with args.out.open('w', encoding='utf-8') as file:
        json.dump(profile, file, ensure_ascii=False, indent=2)

    print(f'Профиль сохранён: {args.out}')

    for metric in METRICS:
        values = profile['errors'][metric]
        print(f'{metric}: {len(values)} samples')


if __name__ == '__main__':
    main()