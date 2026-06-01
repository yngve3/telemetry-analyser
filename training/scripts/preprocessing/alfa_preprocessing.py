from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd


FILES = {
    'global_position': 'mavros-global_position-global.csv',
    'velocity': 'mavros-local_position-velocity.csv',
    'yaw': 'mavros-nav_info-yaw.csv',
    'roll': 'mavros-nav_info-roll.csv',
    'pitch': 'mavros-nav_info-pitch.csv',
    'battery': 'mavros-battery.csv',
    'gps_fix': 'mavros-global_position-raw-fix.csv',
}

SEQUENCE_FEATURE_NAMES = [
    'altitude',
    'vx',
    'vy',
    'vz',
    'ground_speed',
    'roll',
    'pitch',
    'yaw',
    'battery_voltage',
    'battery_remaining',
    'gps_fix_status',
    'satellites_visible',
    'eph',
    'epv',
    'position_speed_error',
    'altitude_velocity_error',
    'heading_yaw_error',
]

WINDOW_FEATURE_NAMES = [
    'position_speed_error_mean',
    'position_speed_error_max',
    'altitude_velocity_error_mean',
    'altitude_velocity_error_max',
    'heading_yaw_error_mean',
    'heading_yaw_error_max',
    'ground_speed_mean',
    'ground_speed_std',
    'vertical_speed_mean',
    'vertical_speed_std',
    'altitude_delta',
    'roll_mean',
    'roll_std',
    'pitch_mean',
    'pitch_std',
    'yaw_mean',
    'yaw_std',
    'yaw_delta',
    'battery_voltage_mean',
    'battery_remaining_mean',
    'gps_fix_status_mean',
    'satellites_visible_mean',
    'eph_mean',
    'epv_mean',
]


def find_flight_dirs(processed_root: Path, *, no_failure_only: bool) -> list[Path]:
    dirs = [p for p in processed_root.iterdir() if p.is_dir()]

    if no_failure_only:
        return sorted(p for p in dirs if p.name.endswith('no_failure'))

    return sorted(dirs)


def is_failure_flight(folder: Path) -> bool:
    return not folder.name.endswith('no_failure') and 'no_ground_truth' not in folder.name


def find_file(folder: Path, suffix: str) -> Path | None:
    matches = [p for p in folder.rglob('*.csv') if p.name.endswith(suffix)]
    return matches[0] if matches else None


def read_csv_with_time(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)

    if '%time' not in df.columns:
        raise ValueError(f'В файле {path} не найдена колонка %time')

    df = df.copy()
    df['t'] = pd.to_numeric(df['%time'], errors='coerce') / 1_000_000_000
    return df.dropna(subset=['t']).sort_values('t')


def optional_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for column in candidates:
        if column in df.columns:
            return column
    return None


def prepare_global_position(path: Path) -> pd.DataFrame:
    df = read_csv_with_time(path)

    return df[
        ['t', 'field.latitude', 'field.longitude', 'field.altitude']
    ].rename(
        columns={
            'field.latitude': 'latitude',
            'field.longitude': 'longitude',
            'field.altitude': 'altitude',
        }
    )


def prepare_velocity(path: Path) -> pd.DataFrame:
    df = read_csv_with_time(path)

    out = df[
        [
            't',
            'field.twist.linear.x',
            'field.twist.linear.y',
            'field.twist.linear.z',
        ]
    ].rename(
        columns={
            'field.twist.linear.x': 'vx',
            'field.twist.linear.y': 'vy',
            'field.twist.linear.z': 'vz',
        }
    )

    out['ground_speed'] = np.sqrt(out['vx'] ** 2 + out['vy'] ** 2)
    return out


def prepare_nav_scalar(path: Path, output_name: str) -> pd.DataFrame:
    df = read_csv_with_time(path)

    column = optional_column(df, ['field.measured', 'field.data', 'data'])

    if column is None:
        raise ValueError(f'В файле {path} не найдена колонка измерения')

    return df[['t', column]].rename(columns={column: output_name})


def prepare_battery(path: Path) -> pd.DataFrame:
    df = read_csv_with_time(path)

    voltage = optional_column(df, ['field.voltage', 'field.voltage_v', 'voltage'])
    remaining = optional_column(df, ['field.percentage', 'field.remaining', 'remaining'])

    out = pd.DataFrame({'t': df['t']})
    out['battery_voltage'] = pd.to_numeric(df[voltage], errors='coerce') if voltage else np.nan
    out['battery_remaining'] = pd.to_numeric(df[remaining], errors='coerce') if remaining else np.nan

    return out


def prepare_gps_fix(path: Path) -> pd.DataFrame:
    df = read_csv_with_time(path)

    status = optional_column(df, ['field.status.status'])
    satellites = optional_column(df, ['field.satellites_visible', 'field.satellites'])
    eph = optional_column(df, ['field.eph', 'field.position_covariance0'])
    epv = optional_column(df, ['field.epv', 'field.position_covariance8'])

    out = pd.DataFrame({'t': df['t']})
    out['gps_fix_status'] = pd.to_numeric(df[status], errors='coerce') if status else np.nan
    out['satellites_visible'] = pd.to_numeric(df[satellites], errors='coerce') if satellites else np.nan
    out['eph'] = pd.to_numeric(df[eph], errors='coerce') if eph else np.nan
    out['epv'] = pd.to_numeric(df[epv], errors='coerce') if epv else np.nan

    return out


def merge_asof_all(frames: list[pd.DataFrame], tolerance: float) -> pd.DataFrame:
    merged = frames[0].sort_values('t')

    for frame in frames[1:]:
        merged = pd.merge_asof(
            merged,
            frame.sort_values('t'),
            on='t',
            direction='nearest',
            tolerance=tolerance,
        )

    return merged.sort_values('t')


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6_371_000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )

    return 2 * radius * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_lambda = math.radians(lon2 - lon1)

    y = math.sin(d_lambda) * math.cos(phi2)
    x = (
        math.cos(phi1) * math.sin(phi2)
        - math.sin(phi1) * math.cos(phi2) * math.cos(d_lambda)
    )

    return (math.degrees(math.atan2(y, x)) + 360) % 360


def angle_error_deg(a: float, b: float) -> float:
    return abs((a - b + 180) % 360 - 180)


def angle_delta_deg(a: float, b: float) -> float:
    return (b - a + 180) % 360 - 180


def add_consistency_errors(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    position_speed_errors = [np.nan]
    altitude_velocity_errors = [np.nan]
    heading_yaw_errors = [np.nan]

    rows = df.to_dict('records')

    for previous, current in zip(rows, rows[1:]):
        dt = current['t'] - previous['t']

        if not np.isfinite(dt) or dt <= 0.02 or dt > 2.0:
            position_speed_errors.append(np.nan)
            altitude_velocity_errors.append(np.nan)
            heading_yaw_errors.append(np.nan)
            continue

        distance = haversine_m(
            previous['latitude'],
            previous['longitude'],
            current['latitude'],
            current['longitude'],
        )

        speed_from_position = distance / dt
        position_speed_errors.append(abs(speed_from_position - current['ground_speed']))

        vertical_speed_from_altitude = (current['altitude'] - previous['altitude']) / dt
        altitude_velocity_errors.append(abs(vertical_speed_from_altitude - current['vz']))

        if distance > 0.5 and np.isfinite(current.get('yaw', np.nan)):
            heading = bearing_deg(
                previous['latitude'],
                previous['longitude'],
                current['latitude'],
                current['longitude'],
            )
            heading_yaw_errors.append(angle_error_deg(heading, current['yaw'] % 360))
        else:
            heading_yaw_errors.append(np.nan)

    df['position_speed_error'] = position_speed_errors
    df['altitude_velocity_error'] = altitude_velocity_errors
    df['heading_yaw_error'] = heading_yaw_errors

    return df


def load_flight_dataframe(folder: Path, tolerance: float = 1.0) -> pd.DataFrame:
    paths = {key: find_file(folder, suffix) for key, suffix in FILES.items()}

    required = ['global_position', 'velocity', 'yaw', 'roll', 'pitch']
    missing = [key for key in required if paths[key] is None]

    if missing:
        raise FileNotFoundError(f'Не найдены обязательные файлы: {missing}')

    frames = [
        prepare_global_position(paths['global_position']),
        prepare_velocity(paths['velocity']),
        prepare_nav_scalar(paths['yaw'], 'yaw'),
        prepare_nav_scalar(paths['roll'], 'roll'),
        prepare_nav_scalar(paths['pitch'], 'pitch'),
    ]

    if paths['battery'] is not None:
        frames.append(prepare_battery(paths['battery']))

    if paths['gps_fix'] is not None:
        frames.append(prepare_gps_fix(paths['gps_fix']))

    merged = merge_asof_all(frames, tolerance=tolerance)
    merged = add_consistency_errors(merged)

    for column in SEQUENCE_FEATURE_NAMES:
        if column not in merged.columns:
            merged[column] = np.nan

    merged = merged.replace([np.inf, -np.inf], np.nan)
    merged = merged.interpolate(limit_direction='both').fillna(0.0)

    return merged


def build_sequence_windows(
    df: pd.DataFrame,
    window_size: int,
    step_size: int,
) -> np.ndarray:
    values = df[SEQUENCE_FEATURE_NAMES].to_numpy(dtype=np.float32)
    windows = []

    for start in range(0, len(values) - window_size + 1, step_size):
        windows.append(values[start:start + window_size].reshape(-1))

    if not windows:
        return np.empty((0, window_size * len(SEQUENCE_FEATURE_NAMES)), dtype=np.float32)

    return np.stack(windows).astype(np.float32)


def extract_window_features(window: pd.DataFrame) -> dict[str, float]:
    def mean(column: str) -> float:
        return float(window[column].mean(skipna=True))

    def std(column: str) -> float:
        value = window[column].std(skipna=True)
        return 0.0 if pd.isna(value) else float(value)

    def max_value(column: str) -> float:
        return float(window[column].max(skipna=True))

    def delta(column: str) -> float:
        values = window[column].dropna()
        if len(values) < 2:
            return 0.0
        return float(values.iloc[-1] - values.iloc[0])

    def angle_delta(column: str) -> float:
        values = window[column].dropna()
        if len(values) < 2:
            return 0.0
        return float(angle_delta_deg(values.iloc[0], values.iloc[-1]))

    result = {
        'position_speed_error_mean': mean('position_speed_error'),
        'position_speed_error_max': max_value('position_speed_error'),
        'altitude_velocity_error_mean': mean('altitude_velocity_error'),
        'altitude_velocity_error_max': max_value('altitude_velocity_error'),
        'heading_yaw_error_mean': mean('heading_yaw_error'),
        'heading_yaw_error_max': max_value('heading_yaw_error'),
        'ground_speed_mean': mean('ground_speed'),
        'ground_speed_std': std('ground_speed'),
        'vertical_speed_mean': mean('vz'),
        'vertical_speed_std': std('vz'),
        'altitude_delta': delta('altitude'),
        'roll_mean': mean('roll'),
        'roll_std': std('roll'),
        'pitch_mean': mean('pitch'),
        'pitch_std': std('pitch'),
        'yaw_mean': mean('yaw'),
        'yaw_std': std('yaw'),
        'yaw_delta': angle_delta('yaw'),
        'battery_voltage_mean': mean('battery_voltage'),
        'battery_remaining_mean': mean('battery_remaining'),
        'gps_fix_status_mean': mean('gps_fix_status'),
        'satellites_visible_mean': mean('satellites_visible'),
        'eph_mean': mean('eph'),
        'epv_mean': mean('epv'),
    }

    return {key: 0.0 if not np.isfinite(value) else value for key, value in result.items()}


def build_feature_windows(
    df: pd.DataFrame,
    window_size: int,
    step_size: int,
) -> pd.DataFrame:
    features = []

    for start in range(0, len(df) - window_size + 1, step_size):
        window = df.iloc[start:start + window_size]
        features.append(extract_window_features(window))

    return pd.DataFrame(features, columns=WINDOW_FEATURE_NAMES)