from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd


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

    # PX4 estimator status
    'pos_test_ratio',
    'vel_test_ratio',
    'hgt_test_ratio',
    'mag_test_ratio',
    'hdg_test_ratio',
    'filter_fault_flags',
    'innovation_check_flags',
    'gps_check_fail_flags',

    # PX4 failsafe flags
    'attitude_invalid',
    'angular_velocity_invalid',
    'local_position_invalid',
    'global_position_invalid',
    'local_velocity_invalid',
    'battery_warning',
    'fd_motor_failure',
    'fd_critical_failure',

    # PX4 failure detector
    'fd_roll',
    'fd_pitch',
    'fd_alt',
    'fd_motor',
    'fd_battery',
    'fd_imbalanced_prop',
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

    # estimator status
    'pos_test_ratio_mean',
    'pos_test_ratio_max',
    'vel_test_ratio_mean',
    'vel_test_ratio_max',
    'hgt_test_ratio_mean',
    'hgt_test_ratio_max',
    'mag_test_ratio_mean',
    'mag_test_ratio_max',
    'hdg_test_ratio_mean',
    'hdg_test_ratio_max',
    'filter_fault_flags_max',
    'innovation_check_flags_max',
    'gps_check_fail_flags_max',

    # failsafe flags
    'attitude_invalid_max',
    'angular_velocity_invalid_max',
    'local_position_invalid_max',
    'global_position_invalid_max',
    'local_velocity_invalid_max',
    'battery_warning_max',
    'fd_motor_failure_max',
    'fd_critical_failure_max',

    # failure detector
    'fd_roll_max',
    'fd_pitch_max',
    'fd_alt_max',
    'fd_motor_max',
    'fd_battery_max',
    'fd_imbalanced_prop_max',
]


def find_flight_dirs(csv_root: Path) -> list[Path]:
    return sorted(path for path in csv_root.iterdir() if path.is_dir())


def find_topic_file(folder: Path, topic: str) -> Path | None:
    matches = []

    for path in folder.rglob('*.csv'):
        name = path.name

        if name.endswith(f'_{topic}_0.csv') or name.endswith(f'_{topic}.csv'):
            matches.append(path)

    return matches[0] if matches else None


def read_px4_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path).copy()

    if 'timestamp' not in df.columns:
        raise ValueError(f'В файле {path} не найдена колонка timestamp')

    df['t'] = pd.to_numeric(df['timestamp'], errors='coerce') / 1_000_000
    return df.dropna(subset=['t']).sort_values('t')


def optional_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for column in candidates:
        if column in df.columns:
            return column
    return None


def prepare_global_position(path: Path) -> pd.DataFrame:
    df = read_px4_csv(path)

    lat = optional_column(df, ['lat', 'latitude', 'latitude_deg'])
    lon = optional_column(df, ['lon', 'longitude', 'longitude_deg'])
    alt = optional_column(df, ['alt', 'altitude', 'altitude_msl_m'])

    if lat is None or lon is None or alt is None:
        raise ValueError(f'В файле {path} не найдены lat/lon/alt')

    out = df[['t', lat, lon, alt]].rename(
        columns={lat: 'latitude', lon: 'longitude', alt: 'altitude'},
    )

    if out['latitude'].abs().max() > 1000:
        out['latitude'] = out['latitude'] / 1e7

    if out['longitude'].abs().max() > 1000:
        out['longitude'] = out['longitude'] / 1e7

    return out


def prepare_local_position(path: Path) -> pd.DataFrame:
    df = read_px4_csv(path)

    vx = optional_column(df, ['vx', 'vel_n'])
    vy = optional_column(df, ['vy', 'vel_e'])
    vz = optional_column(df, ['vz', 'vel_d'])

    if vx is None or vy is None or vz is None:
        raise ValueError(f'В файле {path} не найдены vx/vy/vz')

    out = df[['t', vx, vy, vz]].rename(
        columns={vx: 'vx', vy: 'vy', vz: 'vz'},
    )

    out['ground_speed'] = np.sqrt(out['vx'] ** 2 + out['vy'] ** 2)
    return out


def quaternion_to_euler(
    w: np.ndarray,
    x: np.ndarray,
    y: np.ndarray,
    z: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    roll = np.arctan2(
        2.0 * (w * x + y * z),
        1.0 - 2.0 * (x * x + y * y),
    )

    sin_pitch = 2.0 * (w * y - z * x)
    sin_pitch = np.clip(sin_pitch, -1.0, 1.0)
    pitch = np.arcsin(sin_pitch)

    yaw = np.arctan2(
        2.0 * (w * z + x * y),
        1.0 - 2.0 * (y * y + z * z),
    )

    return np.degrees(roll), np.degrees(pitch), np.degrees(yaw)


def prepare_attitude(path: Path) -> pd.DataFrame:
    df = read_px4_csv(path)

    q0 = optional_column(df, ['q[0]', 'q_0', 'q0'])
    q1 = optional_column(df, ['q[1]', 'q_1', 'q1'])
    q2 = optional_column(df, ['q[2]', 'q_2', 'q2'])
    q3 = optional_column(df, ['q[3]', 'q_3', 'q3'])

    if None in (q0, q1, q2, q3):
        roll = optional_column(df, ['roll'])
        pitch = optional_column(df, ['pitch'])
        yaw = optional_column(df, ['yaw'])

        if roll is None or pitch is None or yaw is None:
            raise ValueError(f'В файле {path} не найдены quaternion или roll/pitch/yaw')

        out = df[['t', roll, pitch, yaw]].rename(
            columns={roll: 'roll', pitch: 'pitch', yaw: 'yaw'},
        )

        if out[['roll', 'pitch', 'yaw']].abs().max().max() <= 2 * math.pi + 0.1:
            out[['roll', 'pitch', 'yaw']] = np.degrees(out[['roll', 'pitch', 'yaw']])

        return out

    roll, pitch, yaw = quaternion_to_euler(
        pd.to_numeric(df[q0], errors='coerce').to_numpy(),
        pd.to_numeric(df[q1], errors='coerce').to_numpy(),
        pd.to_numeric(df[q2], errors='coerce').to_numpy(),
        pd.to_numeric(df[q3], errors='coerce').to_numpy(),
    )

    return pd.DataFrame(
        {
            't': df['t'].to_numpy(),
            'roll': roll,
            'pitch': pitch,
            'yaw': yaw,
        },
    )


def prepare_battery(path: Path) -> pd.DataFrame:
    df = read_px4_csv(path)

    voltage = optional_column(df, ['voltage_v', 'voltage_filtered_v', 'voltage'])
    remaining = optional_column(df, ['remaining', 'remaining_capacity_wh'])

    out = pd.DataFrame({'t': df['t']})
    out['battery_voltage'] = pd.to_numeric(df[voltage], errors='coerce') if voltage else np.nan
    out['battery_remaining'] = pd.to_numeric(df[remaining], errors='coerce') if remaining else np.nan

    return out


def prepare_gps(path: Path) -> pd.DataFrame:
    df = read_px4_csv(path)

    fix_type = optional_column(df, ['fix_type'])
    satellites = optional_column(df, ['satellites_used', 'satellites_visible'])
    eph = optional_column(df, ['eph'])
    epv = optional_column(df, ['epv'])

    out = pd.DataFrame({'t': df['t']})
    out['gps_fix_status'] = pd.to_numeric(df[fix_type], errors='coerce') if fix_type else np.nan
    out['satellites_visible'] = pd.to_numeric(df[satellites], errors='coerce') if satellites else np.nan
    out['eph'] = pd.to_numeric(df[eph], errors='coerce') if eph else np.nan
    out['epv'] = pd.to_numeric(df[epv], errors='coerce') if epv else np.nan

    return out


def prepare_estimator_status(path: Path) -> pd.DataFrame:
    df = read_px4_csv(path)

    columns = {
        'pos_test_ratio': ['pos_test_ratio'],
        'vel_test_ratio': ['vel_test_ratio'],
        'hgt_test_ratio': ['hgt_test_ratio'],
        'mag_test_ratio': ['mag_test_ratio'],
        'hdg_test_ratio': ['hdg_test_ratio'],
        'filter_fault_flags': ['filter_fault_flags'],
        'innovation_check_flags': ['innovation_check_flags'],
        'gps_check_fail_flags': ['gps_check_fail_flags'],
    }

    out = pd.DataFrame({'t': df['t']})

    for output, candidates in columns.items():
        column = optional_column(df, candidates)
        out[output] = pd.to_numeric(df[column], errors='coerce') if column else np.nan

    return out


def prepare_failsafe_flags(path: Path) -> pd.DataFrame:
    df = read_px4_csv(path)

    columns = [
        'attitude_invalid',
        'angular_velocity_invalid',
        'local_position_invalid',
        'global_position_invalid',
        'local_velocity_invalid',
        'battery_warning',
        'fd_motor_failure',
        'fd_critical_failure',
    ]

    out = pd.DataFrame({'t': df['t']})

    for column in columns:
        out[column] = (
            pd.to_numeric(df[column], errors='coerce')
            if column in df.columns
            else np.nan
        )

    return out


def prepare_failure_detector_status(path: Path) -> pd.DataFrame:
    df = read_px4_csv(path)

    columns = [
        'fd_roll',
        'fd_pitch',
        'fd_alt',
        'fd_motor',
        'fd_battery',
        'fd_imbalanced_prop',
    ]

    out = pd.DataFrame({'t': df['t']})

    for column in columns:
        out[column] = (
            pd.to_numeric(df[column], errors='coerce')
            if column in df.columns
            else np.nan
        )

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
    global_position = find_topic_file(folder, 'vehicle_global_position')
    local_position = find_topic_file(folder, 'vehicle_local_position')
    attitude = find_topic_file(folder, 'vehicle_attitude')
    battery = find_topic_file(folder, 'battery_status')
    gps = find_topic_file(folder, 'vehicle_gps_position')
    estimator_status = find_topic_file(folder, 'estimator_status')
    failsafe_flags = find_topic_file(folder, 'failsafe_flags')
    failure_detector_status = find_topic_file(folder, 'failure_detector_status')

    required = {
        'vehicle_global_position': global_position,
        'vehicle_local_position': local_position,
        'vehicle_attitude': attitude,
    }

    missing = [name for name, path in required.items() if path is None]
    if missing:
        raise FileNotFoundError(f'Не найдены обязательные PX4 CSV: {missing}')

    frames = [
        prepare_global_position(global_position),
        prepare_local_position(local_position),
        prepare_attitude(attitude),
    ]

    if battery is not None:
        frames.append(prepare_battery(battery))

    if gps is not None:
        frames.append(prepare_gps(gps))

    if estimator_status is not None:
        frames.append(prepare_estimator_status(estimator_status))

    if failsafe_flags is not None:
        frames.append(prepare_failsafe_flags(failsafe_flags))

    if failure_detector_status is not None:
        frames.append(prepare_failure_detector_status(failure_detector_status))

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

        'pos_test_ratio_mean': mean('pos_test_ratio'),
        'pos_test_ratio_max': max_value('pos_test_ratio'),
        'vel_test_ratio_mean': mean('vel_test_ratio'),
        'vel_test_ratio_max': max_value('vel_test_ratio'),
        'hgt_test_ratio_mean': mean('hgt_test_ratio'),
        'hgt_test_ratio_max': max_value('hgt_test_ratio'),
        'mag_test_ratio_mean': mean('mag_test_ratio'),
        'mag_test_ratio_max': max_value('mag_test_ratio'),
        'hdg_test_ratio_mean': mean('hdg_test_ratio'),
        'hdg_test_ratio_max': max_value('hdg_test_ratio'),
        'filter_fault_flags_max': max_value('filter_fault_flags'),
        'innovation_check_flags_max': max_value('innovation_check_flags'),
        'gps_check_fail_flags_max': max_value('gps_check_fail_flags'),

        'attitude_invalid_max': max_value('attitude_invalid'),
        'angular_velocity_invalid_max': max_value('angular_velocity_invalid'),
        'local_position_invalid_max': max_value('local_position_invalid'),
        'global_position_invalid_max': max_value('global_position_invalid'),
        'local_velocity_invalid_max': max_value('local_velocity_invalid'),
        'battery_warning_max': max_value('battery_warning'),
        'fd_motor_failure_max': max_value('fd_motor_failure'),
        'fd_critical_failure_max': max_value('fd_critical_failure'),

        'fd_roll_max': max_value('fd_roll'),
        'fd_pitch_max': max_value('fd_pitch'),
        'fd_alt_max': max_value('fd_alt'),
        'fd_motor_max': max_value('fd_motor'),
        'fd_battery_max': max_value('fd_battery'),
        'fd_imbalanced_prop_max': max_value('fd_imbalanced_prop'),
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