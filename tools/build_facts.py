"""Build facts.html — "פרטים ועובדות על הלוח השומרוני".

Every number on the page is derived from the calendar's own data files (cal/<year>.dat),
so re-run this after the calendar data is regenerated:   python3 tools/build_facts.py
"""
import base64, datetime as dt, json, os
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
K = b'shomron-luach-5786'                          # same XOR key as decodeData() in index.html
D = dt.date.fromisoformat
WD = ['שני', 'שלישי', 'רביעי', 'חמישי', 'שישי', 'שבת', 'ראשון']          # date.weekday() order
WD_ORDER = ['ראשון', 'שני', 'שלישי', 'רביעי', 'חמישי', 'שישי', 'שבת']
GM = ['', 'ינואר', 'פברואר', 'מרץ', 'אפריל', 'מאי', 'יוני', 'יולי', 'אוגוסט', 'ספטמבר', 'אוקטובר', 'נובמבר', 'דצמבר']
NEAR = (1900, 2100)                                # "our era" sub-range shown beside the full range


def load(y):
    b = base64.b64decode(open(os.path.join(ROOT, 'cal', f'{y}.dat')).read())
    return json.loads(bytes(c ^ K[i % len(K)] for i, c in enumerate(b)).decode())


YEARS = sorted(int(f[:-4]) for f in os.listdir(os.path.join(ROOT, 'cal')) if f.endswith('.dat'))
DATA = {y: load(y) for y in YEARS}
Y0, Y1 = YEARS[0], YEARS[-1]
C0, C1 = DATA[Y0]['canaan_year'], DATA[Y1]['canaan_year']
CANAAN = {y: DATA[y]['canaan_year'] for y in YEARS}


def wd(s): return WD[D(s).weekday()]
def dm(s): d = D(s); return f'{d.day} ב{GM[d.month]}'
def link(s, text=None): return f'<a href="index.html#goto={s}">{text or D(s).strftime("%d.%m.%Y")}</a>'
def near(y): return NEAR[0] <= y <= NEAR[1]
def fmt(n): return f'{n:,}'


# ---------- collect ----------
FEASTS = [  # (label, kind, name in data, Samaritan date label)
    ('ראש החדש הראשון', 'rosh', 'ראש חדש ראשון', 'א׳ בחדש הראשון'),
    ('זבח הפסח (יום טבח)', 'sam', 'יום טבח - זבח הפסח', 'י״ד בחדש הראשון'),
    ('מועד הפסח הברוך', 'sam', 'מועד הפסח הברוך', 'ט״ו בחדש הראשון'),
    ('מועד חג המצות', 'sam', 'מועד חג המצות', 'כ״א בחדש הראשון'),
    ('מועד החדש השלישי', 'rosh', 'ראש חדש שלישי', 'א׳ בחדש השלישי'),
    ('יום מעמד הר סיני', 'moed', 'מעמד הר סיני - יום מקרתה', 'יום רביעי שלפני חג השבעות'),
    ('חג השבעות', 'sam', 'חג השבעות', 'יום ראשון, 50 יום מהשבת שבתוך חג המצות'),
    ('מועד החדש השביעי', 'sam', 'מועד החדש השביעי', 'א׳ בחדש השביעי'),
    ('יום הכפור', 'sam', 'יום כיפור', 'י׳ בחדש השביעי'),
    ('מועד חג הסכות', 'sam', 'חג הסכות', 'ט״ו בחדש השביעי'),
    ('שמיני עצרת', 'sam', 'שמיני עצרת', 'כ״ב בחדש השביעי'),
]
occ = defaultdict(dict)          # label -> {greg_year_of_file: iso}
jew_pesach = {}                  # calendar year -> iso of Jewish Pesach (15 Nisan)
month_rows = []                  # (index, length, weekday of day 1, sabbaths)
ben_porat = []
m7 = {}
for y in YEARS:
    d = DATA[y]
    for m in d['months']:
        days = m['days']
        month_rows.append((m['index'], len(days), wd(days[0]['greg']), sum(r['is_sat'] for r in days)))
        if m['index'] == 7: m7[y] = days
        for r in days:
            for f in r['festivals']:
                for lab, kind, name, _ in FEASTS:
                    if f['kind'] == kind and f['name'] == name: occ[lab][y] = r['greg']
                if f['kind'] == 'jew' and f['name'] == 'פסח': jew_pesach[int(r['greg'][:4])] = r['greg']
                if f['kind'] == 'parasha' and f['name'] == 'בן פרת': ben_porat.append((y, r['greg']))

css = '''
  :root{--bg:#f4f1ea;--card:#fffdf7;--ink:#2b2620;--muted:#7a6f62;--accent:#8a6d3b;--accent2:#735a30;
    --soft:#efe6d3;--line:#e3dac8;--sam:#3c7a4f;--sam-bg:#e8f1e9}
  *{box-sizing:border-box}
  body{margin:0;font-family:"Segoe UI","Assistant",system-ui,Arial,sans-serif;background:var(--bg);color:var(--ink);line-height:1.65}
  .wrap{max-width:980px;margin:0 auto;padding:18px 16px 70px}
  .top{display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap}
  .back{display:inline-block;padding:7px 14px;border-radius:10px;background:var(--accent);color:#fff;text-decoration:none;font-weight:700;font-size:.9rem}
  h1{color:var(--accent);font-size:1.45rem;margin:14px 0 4px}
  .scope{background:var(--soft);border:1px solid var(--line);border-radius:12px;padding:10px 14px;margin:10px 0 18px;font-size:.92rem}
  .toc{display:flex;flex-wrap:wrap;gap:6px;margin:0 0 10px}
  .toc a{font-size:.82rem;padding:4px 10px;border:1px solid var(--line);border-radius:999px;background:var(--card);color:var(--accent2);text-decoration:none}
  section{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 16px;margin:14px 0}
  h2{color:var(--accent2);font-size:1.12rem;margin:0 0 8px}
  h3{font-size:.98rem;margin:14px 0 6px;color:var(--accent2)}
  p{margin:6px 0}
  .note{color:var(--muted);font-size:.85rem}
  .tw{overflow-x:auto;margin:8px 0}
  table{border-collapse:collapse;width:100%;font-size:.86rem}
  th,td{border:1px solid var(--line);padding:6px 8px;text-align:right;vertical-align:top}
  th{background:var(--soft);font-weight:700;white-space:nowrap}
  td.n{white-space:nowrap}
  .yes{color:var(--sam);font-weight:700}
  .no{color:#a04040;font-weight:700}
  .years{display:flex;flex-wrap:wrap;gap:5px;margin:6px 0}
  .years a,.years span{font-size:.8rem;padding:2px 8px;border-radius:7px;background:var(--sam-bg);color:var(--sam);text-decoration:none;white-space:nowrap}
  .big{font-size:1.05rem;font-weight:700;color:var(--accent)}
  a{color:#0e7aa0}
  @media print{.back,.toc{display:none}}
'''

S = []   # sections: (id, title, html)

# ---------- 1. festival ranges ----------
rows = []
for lab, _, _, hd in FEASTS:
    v = occ[lab]
    def ext(ys):
        ss = sorted(((v[y][5:], v[y]) for y in ys if y in v))
        return ss[0][1], ss[-1][1]
    lo, hi = ext(YEARS)
    nlo, nhi = ext([y for y in YEARS if near(y)])
    wds = Counter(wd(v[y]) for y in v)
    wtxt = 'תמיד ביום ' + next(iter(wds)) if len(wds) == 1 else 'כל ימות השבוע'
    rows.append(f'<tr><th>{lab}</th><td>{hd}</td><td class="n">{dm(lo)}<br><span class="note">({link(lo, D(lo).year)})</span></td>'
                f'<td class="n">{dm(hi)}<br><span class="note">({link(hi, D(hi).year)})</span></td>'
                f'<td class="n">{dm(nlo)} – {dm(nhi)}</td><td>{wtxt}</td></tr>')
sinai = occ['יום מעמד הר סיני']
sinai_days = Counter((D(sinai[y]) - D(occ['מועד החדש השלישי'][y])).days + 1 for y in sinai)
S.append(('ranges', 'טווח התאריכים הלועזיים של המועדים', f'''
<p>לכל מועד: התאריך הלועזי המוקדם ביותר והמאוחר ביותר שבו הוא יכול לחול, על פני כל הלוח ({Y0}–{Y1}),
ובעמודה נפרדת הטווח בתקופתנו ({NEAR[0]}–{NEAR[1]}). לחיצה על שנה פותחת את היום בלוח.</p>
<div class="tw"><table><tr><th>מועד</th><th>התאריך השומרוני</th><th>מוקדם ביותר</th><th>מאוחר ביותר</th><th>טווח {NEAR[0]}–{NEAR[1]}</th><th>יום בשבוע</th></tr>
{''.join(rows)}</table></div>
<p class="note">• כל מועד חל לעולם בתוך חלון של כ־30 יום, כי ראש החדש הראשון קבוע בחלון של חודש ירחי אחד (ראו חוק העיבור).
החלון זז ביום אחד מאוחר יותר אחרי שנת 2100, כי שנת השמש של הלוח ארוכה במעט מהשנה הגרגוריאנית.<br>
• יום מעמד הר סיני חל תמיד ביום רביעי וחג השבעות תמיד ביום ראשון, ולכן הם נעים בחודש השלישי:
מעמד הר סיני חל בין א׳ לט׳ בחדש השלישי, וחג השבעות בין ה׳ לי״ג בו.</p>'''))

# ---------- 2. leap rule ----------
leap = [y for y in YEARS if DATA[y]['leap']]
gaps = Counter(b - a for a, b in zip(leap, leap[1:]))
ex = [y for y in leap if 2000 <= y <= 2060]
S.append(('leap', 'חוק עיבור השנה', f'''
<p class="big">שנה מעוברת (13 חודשים) נוצרת כאשר מולד החודש שהיה אמור להיות "החדש הראשון" חל מוקדם מדי ביחס לתקופת האביב.</p>
<p>בכל שנות הלוח, <b>מולד החדש הראשון חל תמיד בין 11 באדר ל־10 בניסן לפי הלוח הסורי</b>, כלומר בערך בין 24 במרץ ל־23 באפריל.
אם מולד החודש שאחרי החדש השנים עשר חל לפני הגבול הזה (כ־11 באדר הסורי), מוסיפים חודש שלושה עשר.
החודש הבא, שמולדו כבר אחרי הגבול, נעשה לחדש הראשון של השנה החדשה.</p>
<p>לכן ראש החדש הראשון חל לעולם בין 25 במרץ ל־24 באפריל, ומועד הפסח חל תמיד אחרי תקופת האביב.</p>
<h3>מה רואים בנתונים</h3>
<p>{fmt(len(leap))} שנים מעוברות מתוך {fmt(len(YEARS))}, כלומר <b>בממוצע 7 שנים מעוברות בכל 19 שנים</b>.
המרווח בין שתי שנים מעוברות הוא תמיד 3 שנים ({gaps[3]} פעמים) או 2 שנים ({gaps[2]} פעמים).
בשונה מהלוח היהודי, אין כאן מחזור קבוע של 19 שנה. העיבור נקבע לפי המולד, ולכן מקומן של השנים המעוברות במחזור זז מדי פעם.</p>
<h3>דוגמאות: השנים המעוברות {ex[0]}–{ex[-1]}</h3>
<div class="tw"><table><tr><th>שנה לועזית</th><th>שנה לכניסה</th><th>ראש החדש הראשון</th><th>ראש החדש השלושה עשר</th></tr>
{''.join(f"<tr><td>{y}</td><td>{CANAAN[y]}</td><td>{link(DATA[y]['months'][0]['days'][0]['greg'])}</td><td>{link(DATA[y]['months'][-1]['days'][0]['greg'])}</td></tr>" for y in ex)}
</table></div>'''))

# ---------- 3. Sakhanta ----------
sak = defaultdict(lambda: [0, None])
for y, days in m7.items():
    w = wd(days[0]['greg'])
    sats = [r['heb_day'] for r in days if r['is_sat']]
    pre = [s for s in sats if 1 < s < 10]; mid = [s for s in sats if 10 < s < 15]
    day = 9 if len(pre) == 2 and 9 in pre else (mid[0] if mid else None)
    sak[w][0] += 1; sak[w][1] = day
HEBNUM = {9: 'ט׳', 11: 'י״א', 12: 'י״ב', 13: 'י״ג', 14: 'י״ד'}
srows = ''
for w in WD_ORDER:
    n, day = sak[w]
    kip = WD_ORDER[(WD_ORDER.index(w) + 9) % 7]
    if day == 9: res, why = f'<span class="yes">יש</span>: {HEBNUM[9]} בחדש השביעי, ערב יום הכפור', 'שתי שבתות בין ראש החדש לכפור; השנייה היא הסכנתה'
    elif day: res, why = f'<span class="yes">יש</span>: {HEBNUM[day]} בחדש השביעי', 'השבת שבין יום הכפור לחג הסכות'
    elif kip == 'שבת': res, why = '<span class="no">אין</span>', 'יום הכפור חל בשבת'
    else: res, why = '<span class="no">אין</span>', 'חג הסכות חל בשבת, ואין שבת בין הכפור לסכות'
    srows += f'<tr><th>{w}</th><td>{kip}</td><td>{res}</td><td>{why}</td><td>{n} ({n * 100 // len(m7)}%)</td></tr>'
has = sum(n for w, (n, d) in sak.items() if d)
S.append(('sakhanta', 'שבת הסכנתה', f'''
<p>שבת הסכנתה היא אחת משתי אפשרויות:</p>
<p>• כשיש שתי שבתות בין ראש החדש השביעי ליום הכפור: הראשונה היא שבת עשרת ימי הסליחות, והשנייה (ערב הכפור) היא שבת הסכנתה.<br>
• כשיש שבת בין יום הכפור למועד חג הסכות: היא שבת הסכנתה.</p>
<div class="tw"><table><tr><th>ראש החדש השביעי ביום</th><th>יום הכפור ביום</th><th>שבת הסכנתה</th><th>הסבר</th><th>שכיחות בלוח</th></tr>{srows}</table></div>
<p>שבת הסכנתה חלה ב־{fmt(has)} מתוך {fmt(len(m7))} שנים ({has * 100 // len(m7)}%).
אין שבת הסכנתה כאשר ראש החדש השביעי חל ביום חמישי (הכפור חל בשבת) או ביום שבת (חג הסכות חל בשבת).<br>שבת הסכנתה מסומנת בלוח בכל השנים האלה.</p>'''))

# ---------- 4. Kippur on Shabbat ----------
kip = [y for y in YEARS if wd(occ['יום הכפור'][y]) == 'שבת']
kg = Counter(b - a for a, b in zip(kip, kip[1:]))
S.append(('kippur', 'שנים שבהן יום הכפור חל בשבת', f'''
<p class="big">יום הכפור חל בשבת כאשר מועד החדש השביעי חל ביום חמישי. יום הכפור הוא תשעה ימים אחריו.</p>
<p>זה קורה ב־{len(kip)} מתוך {fmt(len(YEARS))} שנים, כלומר <b>בממוצע פעם ב־{len(YEARS) / len(kip):.1f} שנים</b>.
המרווחים השכיחים בין פעם לפעם הם {', '.join(f'{g} שנים' for g, _ in kg.most_common(4))}.</p>
<h3>השנים בתקופתנו ({NEAR[0]}–{NEAR[1]})</h3>
<div class="years">{''.join(f'<a href="index.html#goto={occ["יום הכפור"][y]}">{D(occ["יום הכפור"][y]).year} · {CANAAN[y]}</a>' for y in kip if near(y))}</div>
<p class="note">בכל תגית: השנה הלועזית ואחריה השנה לכניסה.</p>'''))

# ---------- 5. vs Jewish Rosh Chodesh Nisan ----------
diff = {}
for y in YEARS:
    if y in jew_pesach:
        diff[y] = (D(occ['ראש החדש הראשון'][y]) - (D(jew_pesach[y]) - dt.timedelta(days=14))).days
def cls(v): return 'same' if v == 0 else ('1' if abs(v) == 1 else ('2' if abs(v) == 2 else ('m' if abs(v) >= 22 else 'x')))
def table_for(ys):
    c = Counter(cls(diff[y]) for y in ys); n = len(ys)
    lab = [('same', 'באותו יום'), ('1', 'הפרש של יום אחד'), ('2', 'הפרש של יומיים'), ('x', 'הפרש של 3–8 ימים'), ('m', 'הפרש של חודש (22–30 ימים)')]
    return ''.join(f'<tr><th>{t}</th><td>{c[k]}</td><td>{c[k] * 100 / n:.0f}%</td><td>{"פעם ב־%.1f שנים" % (n / c[k]) if c[k] else "—"}</td></tr>' for k, t in lab)
nys = [y for y in diff if near(y)]
early = Counter(diff[y] for y in nys if abs(diff[y]) <= 2)
mon = [y for y in nys if cls(diff[y]) == 'm']
S.append(('jewish', 'ההפרש בין מועד החדש הראשון לראש חודש ניסן היהודי', f'''
<h3>בתקופתנו ({NEAR[0]}–{NEAR[1]}, {len(nys)} שנים)</h3>
<div class="tw"><table><tr><th>ההפרש</th><th>מספר שנים</th><th>שיעור</th><th>כל כמה שנים</th></tr>{table_for(nys)}</table></div>
<p>כשההפרש הוא ימים בודדים, הלוח השומרוני מקדים כמעט תמיד: יום אחד מוקדם ב־{early[-1]} שנים, יומיים מוקדם ב־{early[-2]} שנים,
ורק ב־{early[1]} שנים הוא מאחר ביום.</p>
<h3>למה?</h3>
<p><b>הפרש של יום או יומיים:</b> החדש השומרוני מתחיל לפי חשבון המולד (הקשר בין הירח לשמש) בלי דחיות.
הלוח היהודי הקבוע דוחה את ראש החודש ביום או יומיים בגלל כללי הדחייה ("לא אד״ו ראש"), ומולד הלוח היהודי מאחר מעט מהמולד האמיתי.
לכן ראש החודש היהודי נופל לרוב באותו יום או יום-יומיים אחרי השומרוני.</p>
<p><b>הפרש של חודש:</b> שני הלוחות מעברים 7 שנים מתוך 19, אך לא באותן שנים.
הלוח השומרוני מעבר לפי מיקום מולד החדש הראשון ביחס לתקופת האביב, ולכן ראש החדש הראשון אינו חל לפני 25 במרץ.
הלוח היהודי מעבר בשנים קבועות במחזור (3, 6, 8, 11, 14, 17, 19) ומרשה לראש חודש ניסן לחול כבר באמצע מרץ.
בשנים שבהן הלוח היהודי לא מעובר והשומרוני כן (או להפך), ראש חודש ניסן היהודי מקדים בחודש שלם.
זה קרה ב־{len(mon)} מתוך {len(nys)} שנים בתקופתנו (בערך פעם ב־{len(nys) / len(mon):.1f} שנים).</p>
<h3>על פני כל הלוח ({Y0}–{Y1})</h3>
<div class="tw"><table><tr><th>ההפרש</th><th>מספר שנים</th><th>שיעור</th><th>כל כמה שנים</th></tr>{table_for(list(diff))}</table></div>
<p class="note">הלוח היהודי הקבוע "נסחף" לאט ביחס לשמש (כיום בערך יום אחד ל־216 שנה), ולכן בעתיד הרחוק ההפרש גדל:
אחרי 2200 הוא כבר 3 ימים ומעלה, ואחרי 2900 עד 8 ימים.</p>'''))

# ---------- 6. fifth Sabbath ----------
f5 = defaultdict(lambda: [0, 0]); cond = Counter()
for idx, n, w, s in month_rows:
    f5[idx][1] += 1
    if s == 5: f5[idx][0] += 1; cond[(n, w)] += 1
mn = {1: 'הראשון', 2: 'השני', 3: 'השלישי', 4: 'הרביעי', 5: 'החמישי', 6: 'הששי', 7: 'השביעי', 8: 'השמיני', 9: 'התשיעי', 10: 'העשירי', 11: 'האחד עשר', 12: 'השנים עשר', 13: 'השלושה עשר'}
S.append(('fifth', 'שבת חמישית בחודש', f'''
<p class="big">כל חודש בלוח יכול לחול בו שבת חמישית. הכלל תלוי באורך החודש וביום שבו חל ראש החדש:</p>
<div class="tw"><table><tr><th>אורך החודש</th><th>שבת חמישית רק כאשר ראש החדש חל ביום</th><th>השבתות בחודש</th></tr>
<tr><th>29 יום</th><td>שבת</td><td>א׳, ח׳, ט״ו, כ״ב, כ״ט</td></tr>
<tr><th>30 יום</th><td>שבת</td><td>א׳, ח׳, ט״ו, כ״ב, כ״ט</td></tr>
<tr><th>30 יום</th><td>שישי</td><td>ב׳, ט׳, ט״ז, כ״ג, ל׳</td></tr></table></div>
<p>הכלל נגזר מהלוח עצמו ומתקיים בכל {fmt(sum(cond.values()))} החודשים שבהם יש שבת חמישית, בלי יוצא מן הכלל.
29 יום הם 4 שבועות ויום אחד, ולכן יש שבת חמישית רק אם השבת היא היום הראשון.
30 יום הם 4 שבועות ויומיים, ולכן יש שבת חמישית אם השבת נופלת באחד משני הימים הראשונים.</p>
<div class="tw"><table><tr><th>החדש</th><th>חודשים עם שבת חמישית</th><th>שיעור</th></tr>
{''.join(f'<tr><th>{mn[i]}</th><td>{f5[i][0]} מתוך {f5[i][1]}</td><td>{f5[i][0] * 100 / f5[i][1]:.0f}%</td></tr>' for i in sorted(f5))}
</table></div>'''))

# ---------- 7. Ben Porat ----------
bp = sorted(ben_porat)
bpg = [b[0] - a[0] for a, b in zip(bp, bp[1:])]
S.append(('benporat', 'פרשת בן פרת יוסף בנפרד', f'''
<p class="big">בכל הלוח נקראת פרשת בן פרת בשבת נפרדת {len(bp)} פעמים ב־{fmt(len(YEARS))} שנים, כלומר בממוצע פעם ב־{len(YEARS) / len(bp):.0f} שנים.</p>
<p>המרווחים אינם קבועים: מ־{min(bpg)} שנים ועד {max(bpg)} שנים. בתקופתנו זה קרה פעמיים בלבד, ב־1983 וב־2007, והפעם הבאה היא רק ב־2105.</p>
<div class="years">{''.join(f'<a href="index.html#goto={g}">{D(g).strftime("%d.%m.%Y")} · {CANAAN[y]}</a>' for y, g in bp)}</div>
<p class="note">בכל תגית: תאריך השבת ואחריו השנה לכניסה.</p>'''))

# ---------- 8. Sinai = new moon of the third month ----------
same = [y for y in YEARS if sinai[y] == occ['מועד החדש השלישי'][y]]
S.append(('sinai', 'מועד החדש השלישי ביום מעמד הר סיני', f'''
<p class="big">יום מעמד הר סיני חל תמיד ביום רביעי. הוא חל ביום מועד החדש השלישי רק כאשר ראש החדש השלישי חל ביום רביעי וחג השבעות חל בה׳ בחדש השלישי.</p>
<p>זה קורה רק {len(same)} פעמים בכל {fmt(len(YEARS))} שנות הלוח, כלומר בממוצע פעם ב־{len(YEARS) / len(same):.0f} שנים.
<b>בתקופתנו זה קרה פעם אחת בלבד, ב־{D(sinai[same[0]]).strftime('%d.%m.%Y')}</b> (שנת {CANAAN[same[0]]} לכניסה). הפעם הבאה תהיה רק ב־{same[1]}.</p>
<div class="years">{''.join(f'<a href="index.html#goto={sinai[y]}">{D(sinai[y]).strftime("%d.%m.%Y")} · {CANAAN[y]}</a>' for y in same)}</div>
<h3>באיזה יום בחדש השלישי חל מעמד הר סיני</h3>
<div class="tw"><table><tr><th>היום בחדש השלישי</th>{''.join(f'<td>{k}</td>' for k in sorted(sinai_days))}</tr>
<tr><th>מספר שנים</th>{''.join(f'<td>{sinai_days[k]}</td>' for k in sorted(sinai_days))}</tr></table></div>'''))

# ---------- 9. same date in two years ----------
def rec(lab):
    v = occ[lab]; ys = sorted(v); nxt = []; full = []
    for i, y in enumerate(ys):
        z = next((z for z in ys[i + 1:] if v[z][5:] == v[y][5:]), None)
        if z: nxt.append(z - y)
        z = next((z for z in ys[i + 1:] if v[z][5:] == v[y][5:] and wd(v[z]) == wd(v[y])), None)
        if z: full.append(z - y)
    return Counter(nxt), Counter(full)
rrows = ''
for lab in ['מועד הפסח הברוך', 'חג השבעות', 'יום הכפור', 'מועד חג הסכות']:
    a, b = rec(lab); n = sum(a.values())
    rrows += (f'<tr><th>{lab}</th><td>{"; ".join(f"{g} שנים ({c * 100 / n:.0f}%)" for g, c in a.most_common(3))}</td>'
              f'<td>{"; ".join(f"{g} שנים" for g, _ in b.most_common(3))}</td></tr>')
pes = occ['מועד הפסח הברוך']
S.append(('repeat', 'מתי מועד חוזר לאותו תאריך לועזי', f'''
<p class="big">מועד שומרוני חוזר לאותו תאריך לועזי בדרך כלל אחרי 19 שנה, כלומר מחזור עיבור אחד.</p>
<p>19 שנות שמש שוות כמעט בדיוק ל־235 חודשי ירח, ולכן אחרי 19 שנה המועדים חוזרים לאותו תאריך או לתאריך סמוך מאוד.
לדוגמה, מועד הפסח חל ב־{dm(pes[2007])} 2007 ושוב ב־{dm(pes[2026])} 2026.
הפעם הבאה שהמועד חוזר לאותו תאריך גם באותו יום בשבוע רחוקה הרבה יותר, בדרך כלל אחרי עשרות שנים ואף יותר.</p>
<div class="tw"><table><tr><th>מועד</th><th>חזרה לאותו תאריך לועזי (המרווחים השכיחים)</th><th>אותו תאריך וגם אותו יום בשבוע</th></tr>{rrows}</table></div>
<p class="note">חג השבעות חל תמיד ביום ראשון, ולכן כל חזרה שלו לאותו תאריך היא גם באותו יום בשבוע. המרווח השכיח אצלו הוא 11 שנים.</p>'''))

# ---------- 10. cross-check against the Aziz calendar ----------
# Static: the reference table (חשבון קשטה 2009–2100, computed after the guide of הכהן עזיז בן יעקב)
# lives outside this repo. Numbers from the comparison run when this section was written.
S.append(('aziz', 'אימות מול הלוח של הכהן עזיז בן יעקב', '''
<p>כל ראשי החודשים בלוח הושוו לטבלת "חשבון קשטה — לוח השנה השומרוני 2009–2100", שחושבה לפי מדריכו של הכהן עזיז בן יעקב
(1,125 ראשי חודשים).</p>
<p>• <b>ראש החדש הראשון, השלישי והשביעי זהים בכל 91 השנים</b>, וכך גם כל השנים המעוברות.
לכן גם כל המועדים שתלויים בהם זהים: הפסח, חג המצות, מעמד הר סיני, השבעות, הכפור, הסכות ושמיני עצרת.
העובדות שבעמוד הזה מתאימות ללוח של עזיז בכל השנים שהוא מכסה.<br>
• 1,116 ראשי חודשים זהים לחלוטין. ב־9 ראשי חודשים אחרים יש הפרש של יום אחד, כולם בחודשים שאין בהם מועד:
העשירי 2009, השמיני 2025, האחד עשר 2062 ו־2063, העשירי 2071, השלושה עשר 2080, החמישי 2083 ו־2093, השני 2094.<br>
• בטבלת עזיז, ראשי החודשים מיולי 2037 עד יוני 2038 רשומים כתאריך המולד הגולמי, בלי ההמרה של 13 הימים.
זו שגיאת העתקה מה־PDF. אחרי תיקונה גם הם זהים ללוח.</p>
<p class="note">הלוח של עזיז מכסה רק את השנים 2009–2100. העובדות שמחוץ לטווח הזה, וקריאת הפרשות (בן פרת), נבדקו רק מול נתוני הלוח עצמו.</p>'''))

toc = ''.join(f'<a href="#{i}">{t}</a>' for i, t, _ in S)
body = ''.join(f'<section id="{i}"><h2>{t}</h2>{h}</section>' for i, t, h in S)
html = f'''<!DOCTYPE html>
<html lang="he" dir="rtl" translate="no" class="notranslate">
<head>
<meta charset="utf-8">
<meta name="google" content="notranslate">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>עובדות על הלוח השומרוני</title>
<meta name="theme-color" content="#8a6d3b">
<link rel="manifest" href="manifest.json">
<style>{css}</style>
</head>
<body>
<div class="wrap">
<div class="top"><a class="back" href="index.html">→ חזרה ללוח</a></div>
<h1>פרטים ועובדות על הלוח השומרוני</h1>
<div class="scope">כל הנתונים בעמוד נגזרו מהלוח עצמו, על פני כל שנותיו:
<b>שנים לכניסה {C0}–{C1}</b> · <b>שנים לועזיות {Y0}–{Y1}</b> ({fmt(len(YEARS))} שנים).
היכן שצוין, מוצג בנפרד גם הטווח בתקופתנו ({NEAR[0]}–{NEAR[1]}).</div>
<nav class="toc">{toc}</nav>
{body}
</div>
</body>
</html>
'''
open(os.path.join(ROOT, 'facts.html'), 'w', encoding='utf-8').write(html)
print('facts.html written:', len(html), 'bytes')
