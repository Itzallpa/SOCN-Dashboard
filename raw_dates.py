"""Date format of LH Trip raw data: the export is sometimes DD/MM/YYYY ('18/11/2026 23:38') and sometimes
MM/DD/YYYY ('11/19/2026 18:11:00'). lh_raw_table and productivity_raw read DD/MM, so rows in MM/DD are
rewritten to DD/MM (time part kept as is) before they are processed.

Detection: a part > 12 can only be the day (decides it); when every value is ambiguous (day <= 12), the date in
the trip name ("20261119Timetable ...") decides which reading lands within a few days of it.
"""
import re
from datetime import date

_DATE_RE = re.compile(r"^(\s*)(\d{1,2})/(\d{1,2})/(\d{4})(.*)$", re.S)
_NAME_DATE_RE = re.compile(r"(20\d{2})(\d{2})(\d{2})")


def _name_date(name):
    m = _NAME_DATE_RE.search(str(name or ""))
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def detect_order(headers, rows, sample=4000):
    """-> 'DMY' or 'MDY'."""
    hdr = [str(h or "").strip() for h in headers]
    name_i = hdr.index("LH Trip Name") if "LH Trip Name" in hdr else None
    dmy = mdy = 0
    near = {"DMY": 0, "MDY": 0}
    for r in (rows or [])[:sample]:
        ref = _name_date(r[name_i]) if name_i is not None and name_i < len(r) else None
        for v in r:
            m = _DATE_RE.match(str(v)) if isinstance(v, str) else None
            if not m:
                continue
            a, b, y = int(m.group(2)), int(m.group(3)), int(m.group(4))
            if a > 12 >= b:
                dmy += 1
            elif b > 12 >= a:
                mdy += 1
            elif ref:
                for order, (d, mo) in (("DMY", (a, b)), ("MDY", (b, a))):
                    try:
                        if abs((date(y, mo, d) - ref).days) <= 3:
                            near[order] += 1
                    except ValueError:
                        pass
    if dmy or mdy:
        return "MDY" if mdy > dmy else "DMY"
    return "MDY" if near["MDY"] > near["DMY"] else "DMY"


def normalize_rows(headers, rows):
    """-> (rows in DD/MM/YYYY, detected order). Rows are returned unchanged when they already are DD/MM."""
    order = detect_order(headers, rows)
    if order == "DMY":
        return rows, order

    def fix(v):
        if not isinstance(v, str):
            return v
        m = _DATE_RE.match(v)
        if not m:
            return v
        lead, mo, d, y, rest = m.group(1), int(m.group(2)), int(m.group(3)), m.group(4), m.group(5)
        return f"{lead}{d:02d}/{mo:02d}/{y}{rest}"

    return [[fix(v) for v in r] for r in rows], order
