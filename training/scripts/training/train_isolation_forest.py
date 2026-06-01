# training/scripts/training/train_isolation_forest.py

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(SCRIPTS_ROOT))


def get_preprocessing(source: str):
    if source == 'alfa':
        from preprocessing import alfa_preprocessing as preprocessing
    elif source == 'px4':
        from preprocessing import px4_preprocessing as preprocessing
    else:
        raise ValueError(f'Unknown source: {source}')

    return preprocessing


def train_model(
    features: pd.DataFrame,
    contamination: float,
    random_state: int,
) -> tuple[IsolationForest, StandardScaler, float, np.ndarray]:
    scaler = StandardScaler()
    x_scaled = scaler.fit_transform(features)

    model = IsolationForest(
        n_estimators=200,
        contamination=contamination,
        random_state=random_state,
        n_jobs=-1,
    )

    model.fit(x_scaled)

    scores = model.decision_function(x_scaled)
    threshold = float(np.percentile(scores, contamination * 100))

    return model, scaler, threshold, scores


def feature_statistics(features: pd.DataFrame) -> dict[str, dict[str, float]]:
    statistics = {}
    for column in features.columns:
        series = pd.to_numeric(features[column], errors='coerce')
        series = series.replace([np.inf, -np.inf], np.nan).fillna(0.0)
        statistics[column] = {
            'mean': float(series.mean()),
            'std': float(series.std(ddof=0)),
            'min': float(series.min()),
            'max': float(series.max()),
        }
    return statistics


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', choices=['alfa', 'px4'], required=True)
    parser.add_argument('--dataset-root', required=True, type=Path)
    parser.add_argument('--out-dir', required=True, type=Path)
    parser.add_argument('--window-size', type=int, default=20)
    parser.add_argument('--step-size', type=int, default=3)
    parser.add_argument('--tolerance', type=float, default=1.0)
    parser.add_argument('--contamination', type=float, default=0.01)
    parser.add_argument('--random-state', type=int, default=42)

    args = parser.parse_args()

    preprocessing = get_preprocessing(args.source)

    all_features: list[pd.DataFrame] = []
    used_flights: list[str] = []
    skipped_flights: list[dict[str, str]] = []

    for flight_dir in preprocessing.find_flight_dirs(args.dataset_root):
        try:
            flight = preprocessing.load_flight_dataframe(
                flight_dir,
                tolerance=args.tolerance,
            )

            windows = preprocessing.build_feature_windows(
                flight,
                window_size=args.window_size,
                step_size=args.step_size,
            )

            if windows.empty:
                raise RuntimeError('Не удалось сформировать окна')

            all_features.append(windows)
            used_flights.append(flight_dir.name)

            print(f'OK {flight_dir.name}: rows={len(flight)}, windows={len(windows)}')

        except Exception as error:
            skipped_flights.append({'flight': flight_dir.name, 'reason': str(error)})
            print(f'SKIP {flight_dir.name}: {error}')

    if not all_features:
        raise RuntimeError('Нет данных для обучения Isolation Forest')

    dataset = pd.concat(all_features, ignore_index=True)
    dataset = dataset.replace([np.inf, -np.inf], np.nan).fillna(0.0)

    print()
    print('========== TRAIN DATASET STATS ==========')

    stats = dataset.describe().T[
        ['mean', 'std', 'min', '25%', '50%', '75%', 'max']
    ]

    with pd.option_context(
        'display.max_rows', None,
        'display.max_columns', None,
        'display.width', 200,
    ):
        print(stats)

    model, scaler, threshold, scores = train_model(
        features=dataset,
        contamination=args.contamination,
        random_state=args.random_state,
    )

    args.out_dir.mkdir(parents=True, exist_ok=True)

    joblib.dump(model, args.out_dir / 'model.joblib')
    joblib.dump(scaler, args.out_dir / 'scaler.joblib')

    metadata = {
        'model_type': 'isolation_forest',
        'source': args.source,
        'feature_names': preprocessing.WINDOW_FEATURE_NAMES,
        'window_size': args.window_size,
        'step_size': args.step_size,
        'contamination': args.contamination,
        'threshold': threshold,
        'feature_statistics': feature_statistics(dataset),
        'score_percentiles': {
            'p01': float(np.percentile(scores, 1)),
            'p05': float(np.percentile(scores, 5)),
            'p50': float(np.percentile(scores, 50)),
            'p95': float(np.percentile(scores, 95)),
        },
        'used_flights': used_flights,
        'skipped_flights': skipped_flights,
        'samples': int(len(dataset)),
    }

    with (args.out_dir / 'metadata.json').open('w', encoding='utf-8') as file:
        json.dump(metadata, file, ensure_ascii=False, indent=2)

    print(f'Артефакт сохранён: {args.out_dir}')
    print(f'windows={len(dataset)}')
    print(f'threshold={threshold}')


if __name__ == '__main__':
    main()
