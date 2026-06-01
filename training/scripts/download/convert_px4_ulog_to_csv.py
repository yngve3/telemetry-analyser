from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

from pyulog import ULog


def read_index(raw_dir: Path) -> dict[str, dict[str, Any]]:
    index_path = raw_dir / 'index.json'

    if not index_path.exists():
        return {}

    payload = json.loads(index_path.read_text(encoding='utf-8'))

    result = {}

    if isinstance(payload, list):
        for item in payload:
            log_id = str(
                item.get('log_id')
                or item.get('id')
                or item.get('_id')
                or ''
            )

            if log_id:
                result[log_id] = item

    return result


def extract_dataset_names(ulog: ULog) -> list[str]:
    return sorted(dataset.name for dataset in ulog.data_list)


def count_messages_by_level(ulog: ULog) -> dict[str, int]:
    counts = {
        'error': 0,
        'warning': 0,
        'info': 0,
        'other': 0,
    }

    for message in ulog.logged_messages:
        level = str(getattr(message, 'log_level_str', '') or '').lower()

        if 'error' in level:
            counts['error'] += 1
        elif 'warn' in level:
            counts['warning'] += 1
        elif 'info' in level:
            counts['info'] += 1
        else:
            counts['other'] += 1

    return counts


def extract_logged_messages(ulog: ULog, limit: int = 100) -> list[dict[str, Any]]:
    result = []

    for message in ulog.logged_messages[:limit]:
        result.append(
            {
                'timestamp': str(getattr(message, 'timestamp', '')),
                'level': str(getattr(message, 'log_level_str', '')),
                'message': str(getattr(message, 'message', '')),
            }
        )

    return result


def dataset_summary(ulog: ULog, name: str) -> dict[str, Any] | None:
    try:
        data = ulog.get_dataset(name).data
    except Exception:
        return None

    result: dict[str, Any] = {
        'rows': 0,
        'columns': sorted(data.keys()),
    }

    if 'timestamp' in data:
        timestamps = data['timestamp']
        result['rows'] = int(len(timestamps))

        if len(timestamps) > 0:
            result['timestamp_start'] = int(timestamps[0])
            result['timestamp_end'] = int(timestamps[-1])
            result['duration_s'] = float((timestamps[-1] - timestamps[0]) / 1_000_000)

    return result


def extract_quality_flags(ulog: ULog) -> dict[str, Any]:
    flags: dict[str, Any] = {}

    for topic in (
        'vehicle_status',
        'failsafe_flags',
        'failure_detector_status',
        'estimator_status',
        'vehicle_gps_position',
        'battery_status',
    ):
        summary = dataset_summary(ulog, topic)
        if summary is not None:
            flags[topic] = summary

    return flags


def extract_ulog_metadata(ulg_path: Path, index: dict[str, dict[str, Any]]) -> dict[str, Any]:
    ulog = ULog(str(ulg_path))

    log_id = ulg_path.stem
    flight_review_metadata = index.get(log_id)

    metadata = {
        'log_id': log_id,
        'source_file': ulg_path.name,
        'flight_review_metadata': flight_review_metadata,
        'topics': extract_dataset_names(ulog),
        'message_counts': count_messages_by_level(ulog),
        'logged_messages': extract_logged_messages(ulog),
        'quality_topics': extract_quality_flags(ulog),
    }

    return metadata


def convert_ulog_to_csv(ulg_path: Path, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    subprocess.run(
        [
            'ulog2csv',
            str(ulg_path),
            '-o',
            str(out_dir),
        ],
        check=True,
    )


def to_jsonable(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, dict):
        return {
            str(key): to_jsonable(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple, set)):
        return [to_jsonable(item) for item in value]

    if callable(value):
        return str(value)

    return str(value)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--raw-dir', required=True, type=Path)
    parser.add_argument('--out-dir', required=True, type=Path)
    parser.add_argument('--skip-existing', action='store_true')
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)

    index = read_index(args.raw_dir)

    for ulg_path in sorted(args.raw_dir.glob('*.ulg')):
        flight_out_dir = args.out_dir / ulg_path.stem
        metadata_path = flight_out_dir / 'metadata.json'

        if args.skip_existing and metadata_path.exists():
            print(f'SKIP existing {ulg_path.name}')
            continue

        try:
            print(f'Convert {ulg_path.name}')
            convert_ulog_to_csv(ulg_path, flight_out_dir)

            metadata = extract_ulog_metadata(ulg_path, index)

            metadata_path.write_text(

                json.dumps(to_jsonable(metadata), ensure_ascii=False, indent=2),

                encoding='utf-8',

            )

            print(f'  saved: {flight_out_dir}')

        except Exception as error:
            print(f'ERROR {ulg_path.name}: {error}')


if __name__ == '__main__':
    main()