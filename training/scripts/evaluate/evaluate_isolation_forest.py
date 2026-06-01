# training/scripts/evaluate/evaluate_isolation_forest.py

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import joblib
import numpy as np

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


def print_results_table(results: list[dict]) -> None:
    results.sort(key=lambda item: item['anomaly_ratio'], reverse=True)

    print()
    print('=' * 150)
    print(
        f'{"Flight":60} '
        f'{"Label":8} '
        f'{"Windows":8} '
        f'{"Anom":8} '
        f'{"Ratio":8} '
        f'{"Mean":10} '
        f'{"Min":10} '
        f'{"Max":10}'
    )
    print('=' * 150)

    for item in results:
        print(
            f'{item["flight"][:60]:60} '
            f'{item["label"]:8} '
            f'{item["windows"]:8} '
            f'{item["anomaly_windows"]:8} '
            f'{item["anomaly_ratio"] * 100:7.2f}% '
            f'{item["score_mean"]:10.4f} '
            f'{item["score_min"]:10.4f} '
            f'{item["score_max"]:10.4f}'
        )


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '--source',
        choices=['alfa', 'px4'],
        required=True,
    )

    parser.add_argument(
        '--processed-root',
        required=True,
        type=Path,
    )

    parser.add_argument(
        '--model-dir',
        required=True,
        type=Path,
    )

    parser.add_argument(
        '--tolerance',
        type=float,
        default=1.0,
    )

    args = parser.parse_args()

    preprocessing = get_preprocessing(args.source)

    model = joblib.load(args.model_dir / 'model.joblib')
    scaler = joblib.load(args.model_dir / 'scaler.joblib')

    metadata = json.loads(
        (args.model_dir / 'metadata.json').read_text(
            encoding='utf-8',
        )
    )

    threshold = metadata['threshold']
    window_size = metadata['window_size']
    step_size = metadata['step_size']

    results = []

    for flight_dir in preprocessing.find_flight_dirs(args.processed_root):
        try:
            flight = preprocessing.load_flight_dataframe(
                flight_dir,
                tolerance=args.tolerance,
            )

            windows = preprocessing.build_feature_windows(
                flight,
                window_size=window_size,
                step_size=step_size,
            )

            if len(windows) == 0:
                raise RuntimeError('Нет окон')

            x = scaler.transform(windows)

            scores = model.decision_function(x)
            predictions = scores < threshold

            anomaly_count = int(predictions.sum())
            total_windows = len(predictions)

            anomaly_ratio = (
                anomaly_count / total_windows
                if total_windows > 0
                else 0.0
            )

            print(
                f'{flight_dir.name}: '
                f'mean={scores.mean():.4f}, '
                f'min={scores.min():.4f}, '
                f'max={scores.max():.4f}'
            )

            results.append(
                {
                    'flight': flight_dir.name,
                    'windows': total_windows,
                    'anomalies': anomaly_count,
                    'anomaly_ratio': anomaly_ratio,
                    'score_mean': float(scores.mean()),
                    'score_min': float(scores.min()),
                    'score_max': float(scores.max()),
                }
            )

        except Exception as error:
            print(f'SKIP {flight_dir.name}: {error}')

    if not results:
        raise RuntimeError('Не удалось получить результаты оценки')

    results.sort(
        key=lambda item: item['anomaly_ratio'],
        reverse=True,
    )

    print()
    print('========== RESULTS ==========')

    for result in results:
        print(
            f'{result["flight"]:<60} '
            f'{result["anomalies"]:>5}/{result["windows"]:<5} '
            f'{result["anomaly_ratio"] * 100:>6.2f}%'
        )

    mean_ratio = np.mean(
        [result['anomaly_ratio'] for result in results]
    )

    total_windows = sum(result['windows'] for result in results)
    total_anomalies = sum(result['anomalies'] for result in results)
    global_ratio = total_anomalies / total_windows if total_windows else 0.0

    ratios = [result['anomaly_ratio'] for result in results]

    high_threshold = 0.10
    medium_threshold = 0.01

    high_count = sum(ratio >= high_threshold for ratio in ratios)
    medium_count = sum(medium_threshold <= ratio < high_threshold for ratio in ratios)
    low_count = sum(ratio < medium_threshold for ratio in ratios)

    print()
    print('========== SUMMARY ==========')
    print(f'Model threshold              : {threshold:.6g}')
    print(f'Processed flights            : {len(results)}')
    print(f'Total windows                : {total_windows}')
    print(f'Anomalous windows            : {total_anomalies}')
    print(f'Global anomaly ratio         : {global_ratio * 100:.2f}%')
    print()
    print('Flight anomaly distribution:')
    print(f'  High anomaly ratio  (>= 10%) : {high_count}')
    print(f'  Medium anomaly ratio (1-10%) : {medium_count}')
    print(f'  Low anomaly ratio    (< 1%)  : {low_count}')
    print()
    print('Interpretation:')
    print(
        '  The model detects windows that differ from the normal PX4 flight '
        'patterns used during training. A high anomaly ratio means that a large '
        'part of the flight differs from the learned normal behavior. A low '
        'ratio means that the flight is mostly similar to the training data or '
        'contains deviations that are not represented by the selected features.'
    )

    output_path = args.model_dir / 'evaluation_diagnostic.json'

    output_path.write_text(
        json.dumps(
            {
                'threshold': threshold,
                'results': results,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding='utf-8',
    )

    print()
    print(f'Saved: {output_path}')


if __name__ == '__main__':
    main()