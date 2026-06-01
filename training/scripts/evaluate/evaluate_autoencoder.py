from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import joblib
import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

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


class Autoencoder(nn.Module):
    def __init__(self, input_dim: int, latent_dim: int) -> None:
        super().__init__()

        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 256),
            nn.ReLU(),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, latent_dim),
        )

        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, 128),
            nn.ReLU(),
            nn.Linear(128, 256),
            nn.ReLU(),
            nn.Linear(256, input_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        z = self.encoder(x)
        return self.decoder(z)


def reconstruction_errors(
    model: Autoencoder,
    x: np.ndarray,
    device: torch.device,
    batch_size: int,
) -> np.ndarray:
    model.eval()

    dataset = TensorDataset(torch.tensor(x, dtype=torch.float32))
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=False)

    errors = []

    with torch.no_grad():
        for (batch,) in loader:
            batch = batch.to(device)
            restored = model(batch)

            batch_errors = torch.mean((batch - restored) ** 2, dim=1)
            errors.extend(batch_errors.cpu().numpy())

    return np.asarray(errors)


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument('--source', choices=['alfa', 'px4'], required=True)
    parser.add_argument('--processed-root', required=True, type=Path)
    parser.add_argument('--model-dir', required=True, type=Path)
    parser.add_argument('--tolerance', type=float, default=1.0)
    parser.add_argument('--batch-size', type=int, default=256)

    args = parser.parse_args()

    preprocessing = get_preprocessing(args.source)

    metadata = json.loads(
        (args.model_dir / 'metadata.json').read_text(encoding='utf-8')
    )

    threshold = float(metadata['threshold'])
    window_size = int(metadata['window_size'])
    step_size = int(metadata['step_size'])
    input_dim = int(metadata['input_dim'])
    latent_dim = int(metadata['latent_dim'])

    scaler = joblib.load(args.model_dir / 'scaler.joblib')

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    model = Autoencoder(
        input_dim=input_dim,
        latent_dim=latent_dim,
    ).to(device)

    model.load_state_dict(
        torch.load(
            args.model_dir / 'model.pt',
            map_location=device,
        )
    )

    results = []

    for flight_dir in preprocessing.find_flight_dirs(args.processed_root):
        try:
            flight = preprocessing.load_flight_dataframe(
                flight_dir,
                tolerance=args.tolerance,
            )

            windows = preprocessing.build_sequence_windows(
                flight,
                window_size=window_size,
                step_size=step_size,
            )

            if len(windows) == 0:
                raise RuntimeError('Нет окон')

            windows = np.nan_to_num(
                windows,
                nan=0.0,
                posinf=0.0,
                neginf=0.0,
            )

            x = scaler.transform(windows).astype(np.float32)

            errors = reconstruction_errors(
                model=model,
                x=x,
                device=device,
                batch_size=args.batch_size,
            )

            predictions = errors > threshold

            anomaly_count = int(predictions.sum())
            total_windows = len(predictions)

            anomaly_ratio = (
                anomaly_count / total_windows
                if total_windows > 0
                else 0.0
            )

            print(
                f'{flight_dir.name}: '
                f'mean={errors.mean():.6f}, '
                f'min={errors.min():.6f}, '
                f'max={errors.max():.6f}'
            )

            results.append(
                {
                    'flight': flight_dir.name,
                    'windows': total_windows,
                    'anomalies': anomaly_count,
                    'anomaly_ratio': anomaly_ratio,
                    'error_mean': float(errors.mean()),
                    'error_min': float(errors.min()),
                    'error_max': float(errors.max()),
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

    total_windows = sum(result['windows'] for result in results)
    total_anomalies = sum(result['anomalies'] for result in results)
    global_ratio = total_anomalies / total_windows if total_windows else 0.0

    ratios = [result['anomaly_ratio'] for result in results]

    high_threshold = 0.10
    medium_threshold = 0.01

    high_count = sum(ratio >= high_threshold for ratio in ratios)
    medium_count = sum(
        medium_threshold <= ratio < high_threshold
        for ratio in ratios
    )
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
        '  The autoencoder detects windows with a reconstruction error higher '
        'than the threshold estimated on validation data. A high anomaly ratio '
        'means that a large part of the flight is reconstructed poorly and '
        'therefore differs from the normal PX4 flight patterns used during '
        'training.'
    )

    output_path = args.model_dir / 'evaluation_diagnostic.json'

    output_path.write_text(
        json.dumps(
            {
                'threshold': threshold,
                'results': results,
                'summary': {
                    'processed_flights': len(results),
                    'total_windows': total_windows,
                    'anomalous_windows': total_anomalies,
                    'global_anomaly_ratio': global_ratio,
                    'high_anomaly_ratio_flights': high_count,
                    'medium_anomaly_ratio_flights': medium_count,
                    'low_anomaly_ratio_flights': low_count,
                },
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