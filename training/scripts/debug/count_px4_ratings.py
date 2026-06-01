# training/scripts/debug/count_px4_ratings.py

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path('training/datasets/px4/csv')

counter = Counter()

for flight_dir in ROOT.iterdir():
    if not flight_dir.is_dir():
        continue

    metadata_path = flight_dir / 'metadata.json'

    if not metadata_path.exists():
        counter['missing_metadata'] += 1
        continue

    try:
        metadata = json.loads(
            metadata_path.read_text(encoding='utf-8')
        )

        flight_review = (
            metadata.get('flight_review_metadata')
            or {}
        )

        rating = str(
            flight_review.get('rating', 'unknown')
        ).lower()

        counter[rating] += 1

    except Exception:
        counter['invalid_metadata'] += 1

print()
print('========== RATINGS ==========')

total = sum(counter.values())

for rating, count in sorted(
    counter.items(),
    key=lambda item: item[1],
    reverse=True,
):
    percent = count / total * 100 if total else 0

    print(
        f'{rating:<20} '
        f'{count:>6} '
        f'({percent:>5.1f}%)'
    )

print()
print(f'Total: {total}')