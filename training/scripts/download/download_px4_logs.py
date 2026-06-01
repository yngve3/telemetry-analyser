# training/scripts/download/download_px4_logs.py

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import requests


DBINFO_URL = 'https://review.px4.io/dbinfo'
DOWNLOAD_URL = 'https://review.px4.io/download'


def load_logs() -> list[dict[str, Any]]:
    response = requests.get(DBINFO_URL, timeout=60)
    response.raise_for_status()

    payload = response.json()

    if isinstance(payload, list):
        return payload

    if isinstance(payload, dict):
        for key in ('logs', 'data', 'items'):
            if key in payload and isinstance(payload[key], list):
                return payload[key]

    raise RuntimeError('Не удалось определить структуру ответа dbinfo')


def get_value(log: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in log:
            return log[key]
    return None


def matches_filter(log: dict[str, Any], args: argparse.Namespace) -> bool:
    if args.mav_type:
        mav_type = str(get_value(log, 'mav_type', 'MAV_TYPE', 'vehicle_type', 'type') or '')
        if args.mav_type.lower() not in mav_type.lower():
            return False

    if args.ratings:
        rating = str(log.get('rating') or '').lower()
        allowed_ratings = {value.lower() for value in args.ratings}
        if rating not in allowed_ratings:
            return False

    if args.flight_mode:
        modes = str(get_value(log, 'flight_modes', 'modes', 'flight_mode') or '')
        if args.flight_mode.lower() not in modes.lower():
            return False

    if args.min_duration is not None:
        duration = get_value(log, 'duration_s', 'duration', 'flight_time')
        try:
            if float(duration) < args.min_duration:
                return False
        except (TypeError, ValueError):
            return False

    return True


def get_log_id(log: dict[str, Any]) -> str | None:
    value = get_value(log, 'log_id', 'id', '_id')
    return str(value) if value else None


def get_date_key(log: dict[str, Any]) -> str:
    return str(get_value(log, 'date', 'upload_date', 'timestamp', 'time') or '')


def download_log(log_id: str, out_path: Path) -> None:
    response = requests.get(
        DOWNLOAD_URL,
        params={'log': log_id},
        timeout=120,
    )
    response.raise_for_status()

    out_path.write_bytes(response.content)


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '--out-dir',
        required=True,
        type=Path,
        help='Каталог для сохранения .ulg файлов',
    )
    parser.add_argument(
        '--max-num',
        type=int,
        default=30,
        help='Максимальное количество логов для скачивания',
    )
    parser.add_argument(
        '--delay',
        type=float,
        default=6.0,
        help='Пауза между скачиваниями',
    )
    parser.add_argument('--mav-type', type=str, default='Quadrotor')
    parser.add_argument(
        '--ratings',
        nargs='+',
    )
    parser.add_argument('--flight-mode', type=str, default=None)
    parser.add_argument('--min-duration', type=float, default=60.0)
    parser.add_argument(
        '--save-index',
        action='store_true',
        help='Сохранить список выбранных логов в index.json',
    )

    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)

    logs = load_logs()
    print(f'Всего логов в dbinfo: {len(logs)}')

    filtered = [log for log in logs if matches_filter(log, args)]
    filtered.sort(key=get_date_key, reverse=True)

    selected = filtered[:args.max_num]

    print(f'Подходит под фильтры: {len(filtered)}')
    print(f'Будет скачано: {len(selected)}')

    index = []

    for number, log in enumerate(selected, start=1):
        log_id = get_log_id(log)

        if not log_id:
            print(f'SKIP #{number}: нет log_id')
            continue

        out_path = args.out_dir / f'{log_id}.ulg'

        index.append(log)

        if out_path.exists():
            print(f'[{number}/{len(selected)}] EXISTS {out_path.name}')
            continue

        try:
            print(f'[{number}/{len(selected)}] DOWNLOAD {log_id}')
            download_log(log_id, out_path)
            print(f'  saved: {out_path}')

            time.sleep(args.delay)

        except Exception as error:
            print(f'  ERROR {log_id}: {error}')

    if args.save_index:
        index_path = args.out_dir / 'index.json'
        index_path.write_text(
            json.dumps(index, ensure_ascii=False, indent=2),
            encoding='utf-8',
        )
        print(f'Index saved: {index_path}')


if __name__ == '__main__':
    main()