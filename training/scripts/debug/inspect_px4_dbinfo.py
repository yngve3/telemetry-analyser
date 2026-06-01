# training/scripts/debug/inspect_px4_dbinfo.py

from collections import Counter
import requests

logs = requests.get('https://review.px4.io/dbinfo', timeout=60).json()

ratings = Counter()
error_labels = Counter()
warnings = Counter()

for log in logs:
    ratings[str(log.get('rating', 'missing')).lower()] += 1

    for label in log.get('error_labels') or []:
        error_labels[str(label).lower()] += 1

    warnings[int(log.get('num_logged_warnings') or 0)] += 1

print('RATINGS:')
print(ratings)

print('\nERROR LABELS:')
print(error_labels.most_common(50))

print('\nWARNINGS:')
print(warnings.most_common(20))