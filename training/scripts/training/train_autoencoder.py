from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

import joblib
import numpy as np
import torch
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
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


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


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


def sequence_feature_statistics(
    windows: np.ndarray,
    feature_names: list[str],
) -> dict[str, dict[str, float]]:
    values = windows.reshape(-1, len(feature_names))
    statistics = {}
    for index, feature_name in enumerate(feature_names):
        column = values[:, index]
        statistics[feature_name] = {
            'mean': float(np.mean(column)),
            'std': float(np.std(column)),
            'min': float(np.min(column)),
            'max': float(np.max(column)),
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

    parser.add_argument('--latent-dim', type=int, default=32)
    parser.add_argument('--epochs', type=int, default=50)
    parser.add_argument('--batch-size', type=int, default=32)
    parser.add_argument('--learning-rate', type=float, default=0.001)
    parser.add_argument('--threshold-percentile', type=float, default=99.0)
    parser.add_argument('--validation-size', type=float, default=0.2)
    parser.add_argument('--random-state', type=int, default=42)

    args = parser.parse_args()

    set_seed(args.random_state)

    preprocessing = get_preprocessing(args.source)

    all_windows: list[np.ndarray] = []
    used_flights: list[str] = []
    skipped_flights: list[dict[str, str]] = []

    for flight_dir in preprocessing.find_flight_dirs(args.dataset_root):
        try:
            flight = preprocessing.load_flight_dataframe(
                flight_dir,
                tolerance=args.tolerance,
            )

            windows = preprocessing.build_sequence_windows(
                flight,
                window_size=args.window_size,
                step_size=args.step_size,
            )

            if len(windows) == 0:
                raise RuntimeError('Не удалось сформировать окна')

            all_windows.append(windows)
            used_flights.append(flight_dir.name)

            print(f'OK {flight_dir.name}: rows={len(flight)}, windows={len(windows)}')

        except Exception as error:
            skipped_flights.append(
                {
                    'flight': flight_dir.name,
                    'reason': str(error),
                }
            )
            print(f'SKIP {flight_dir.name}: {error}')

    if not all_windows:
        raise RuntimeError('Нет данных для обучения автоэнкодера')

    dataset = np.concatenate(all_windows, axis=0)
    dataset = np.nan_to_num(dataset, nan=0.0, posinf=0.0, neginf=0.0)

    scaler = StandardScaler()
    dataset_scaled = scaler.fit_transform(dataset).astype(np.float32)

    train_x, validation_x = train_test_split(
        dataset_scaled,
        test_size=args.validation_size,
        random_state=args.random_state,
        shuffle=True,
    )

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    input_dim = train_x.shape[1]

    model = Autoencoder(
        input_dim=input_dim,
        latent_dim=args.latent_dim,
    ).to(device)

    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=args.learning_rate,
    )

    criterion = nn.MSELoss()

    train_loader = DataLoader(
        TensorDataset(torch.tensor(train_x, dtype=torch.float32)),
        batch_size=args.batch_size,
        shuffle=True,
    )

    for epoch in range(1, args.epochs + 1):
        model.train()

        losses = []

        for (batch,) in train_loader:
            batch = batch.to(device)

            optimizer.zero_grad()

            restored = model(batch)
            loss = criterion(restored, batch)

            loss.backward()
            optimizer.step()

            losses.append(float(loss.item()))

        if epoch == 1 or epoch % 10 == 0 or epoch == args.epochs:
            print(f'epoch={epoch}, loss={np.mean(losses):.6f}')

    validation_errors = reconstruction_errors(
        model=model,
        x=validation_x,
        device=device,
        batch_size=args.batch_size,
    )

    threshold = float(
        np.percentile(validation_errors, args.threshold_percentile)
    )

    args.out_dir.mkdir(parents=True, exist_ok=True)

    torch.save(
        model.state_dict(),
        args.out_dir / 'model.pt',
    )

    joblib.dump(
        scaler,
        args.out_dir / 'scaler.joblib',
    )

    metadata = {
        'model_type': 'mlp_autoencoder',
        'source': args.source,
        'feature_names': preprocessing.SEQUENCE_FEATURE_NAMES,
        'window_size': args.window_size,
        'step_size': args.step_size,
        'input_dim': int(input_dim),
        'latent_dim': args.latent_dim,
        'epochs': args.epochs,
        'batch_size': args.batch_size,
        'learning_rate': args.learning_rate,
        'threshold_percentile': args.threshold_percentile,
        'threshold': threshold,
        'feature_statistics': sequence_feature_statistics(
            dataset,
            preprocessing.SEQUENCE_FEATURE_NAMES,
        ),
        'train_samples': int(len(train_x)),
        'validation_samples': int(len(validation_x)),
        'reconstruction_error_percentiles': {
            'p50': float(np.percentile(validation_errors, 50)),
            'p95': float(np.percentile(validation_errors, 95)),
            'p99': float(np.percentile(validation_errors, 99)),
        },
        'used_flights': used_flights,
        'skipped_flights': skipped_flights,
    }

    with (args.out_dir / 'metadata.json').open('w', encoding='utf-8') as file:
        json.dump(
            metadata,
            file,
            ensure_ascii=False,
            indent=2,
        )

    print(f'Артефакт сохранен: {args.out_dir}')
    print(f'train={len(train_x)}, validation={len(validation_x)}')
    print(f'threshold={threshold}')


if __name__ == '__main__':
    main()
