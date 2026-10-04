"""Mark שבת הסכנתה in the calendar data (cal/<year>.dat).

The rule, by the weekday of ראש החדש השביעי:
  • Friday — two Sabbaths fall before יום הכפור: the first (ב׳) stays
    "שבת עשרת ימי הסליחות", the second (ט׳, ערב הכפור) becomes "שבת הסכנתה".
  • Sunday–Wednesday — the Sabbath between יום הכפור and חג הסכות
    (י״ד / י״ג / י״ב / י״א) is "שבת הסכנתה".
  • Thursday (הכפור falls on Shabbat) and Saturday (הסכות falls on Shabbat) — none.

Idempotent: safe to re-run after the calendar data is regenerated.
    python3 tools/apply_sakhanta.py
"""
import base64, datetime as dt, json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
K = b'shomron-luach-5786'                      # same XOR key as decodeData() in index.html
TEN = 'שבת עשרת ימי הסליחות'
SAKH = 'שבת הסכנתה'


def xor(b): return bytes(c ^ K[i % len(K)] for i, c in enumerate(b))


def sakhanta_day(days):
    """The day-of-month of שבת הסכנתה in this seventh month, or None."""
    sats = [r['heb_day'] for r in days if r['is_sat']]
    if [s for s in sats if 1 < s < 10] == [2, 9]: return 9
    mid = [s for s in sats if 10 < s < 15]
    return mid[0] if mid else None


changed = 0
for f in sorted(os.listdir(os.path.join(ROOT, 'cal'))):
    if not f.endswith('.dat'): continue
    path = os.path.join(ROOT, 'cal', f)
    raw = open(path).read()
    data = json.loads(xor(base64.b64decode(raw)).decode())
    days = next(m for m in data['months'] if m['index'] == 7)['days']
    day = sakhanta_day(days)
    if not day: continue
    fest = days[day - 1]['festivals']
    assert days[day - 1]['heb_day'] == day and days[day - 1]['is_sat']
    if any(x['kind'] == 'sabbath' and x['name'] == SAKH for x in fest): continue
    fest[:] = [x for x in fest if not (x['kind'] == 'sabbath' and x['name'] == TEN)]
    at = next((i for i, x in enumerate(fest) if x['kind'] == 'parasha'), len(fest))   # Sabbath name before the portion
    fest.insert(at, {'kind': 'sabbath', 'name': SAKH})
    txt = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    open(path, 'w').write(base64.b64encode(xor(txt.encode())).decode())
    changed += 1
print('years updated:', changed)
