"""Build the LH Trip "Table" tab from a "raw data" export, without Google Sheets.

Mirrors the formulas of the Table tab in the LH Trip spreadsheet:
  Cut 0-3      <- SOCN_GBKK / SOCN_UPC_Direct / SOCN_UPC_Milkrun (SOC OB times)
  Standby      <- "Tue TTB" route that contains the destination
  On time/Late <- TTB departure of that weekday (+30 min) or, if no TTB route, the cut windows
  RMK          <- LH Late when Assign time is after Standby, else OB Late
  Region/Zone/Intentional <- Hub tab
The output rows use the Table headers, so process_table_sheet() handles them unchanged.

refs = {
  "hub":  [[station_name, region, intentional, zone], ...],
  "cuts": {"gbkk": [[name, c0, c1, c2, c3], ...], "upcDirect": [...], "upcMilkrun": [...]},
  "ttb":  {"Mon TTB": [[route, standby, depart], ...], "Tue TTB": ..., "Sun TTB": ..., "Wed-Sat TTB": ...},
}
"""
import re
from datetime import datetime, timedelta

TABLE_HEADERS = [
    "No.", "LH Trip Number", "Trip Category", "Vehicle Type", "Vehicle Plate Number", "Driver",
    "ต้นทาง (Origin)", "ปลายทาง (Destination)", "", "Trip No. (ref)", "Trip Category", "First Occurrence",
    "Unique Rank", "Trip+Station Key", "Actual ops date", "Cut 0", "Cut 1", "Cut 2", "Cut 3",
    "Standby Time", "Assign Time", "Actual Dep cut", "Date", "show on time/late", "RMK",
    "Non Intentional", "Intentional", "Region", "Zone", "", "Order", "", "Day", "Month",
    "Year/Time", "Year", "Com Time", "MM/DD/YYYY", "Trip Occurrence Key",
]

_TOD_RE = re.compile(r"(\d{1,2}):(\d{2})(?::(\d{2}))?\s*([AaPp][Mm])?")
_DT_RE = re.compile(r"^\s*(\d{1,2})/(\d{1,2})/(\d{4})\s+(\d{1,2}):(\d{2})(?::(\d{2}))?")
_H = 1 / 24.0
_DAYS = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
USE_TTB_DEPART = False   # see build_table_rows: matches what the Table tab actually computes


def parse_tod(v):
    """'7:00' / '06:45:00' / '6:45 AM' -> fraction of a day; None when not a time."""
    m = _TOD_RE.search(str(v or ""))
    if not m:
        return None
    h, mi, se = int(m.group(1)), int(m.group(2)), int(m.group(3) or 0)
    ap = (m.group(4) or "").upper()
    if ap == "PM" and h < 12:
        h += 12
    elif ap == "AM" and h == 12:
        h = 0
    return ((h * 3600 + mi * 60 + se) / 86400.0) % 1.0


def parse_dt(v):
    """'16/11/2026 10:31' (DD/MM/YYYY HH:MM[:SS]) -> datetime; None otherwise."""
    m = _DT_RE.match(str(v or ""))
    if not m:
        return None
    d, mo, y, h, mi, se = (int(x or 0) for x in m.groups())
    try:
        return datetime(y, mo, d, h, mi, se)
    except ValueError:
        return None


def _tod_of(dt):
    return (dt.hour * 3600 + dt.minute * 60 + dt.second) / 86400.0


def _norm(s):
    return str(s or "").strip().lower()


def _first_map(rows, key_idx=0):
    """exact, case-insensitive lookup that keeps the first match (VLOOKUP / XLOOKUP)."""
    out = {}
    for r in rows or []:
        k = _norm(r[key_idx] if len(r) > key_idx else "")
        if k and k not in out:
            out[k] = r
    return out


def _cell(r, i):
    return str(r[i]).strip() if r is not None and len(r) > i and r[i] is not None else ""


class RefTables:
    def __init__(self, refs):
        refs = refs or {}
        self.hub = _first_map(refs.get("hub"))
        cuts = refs.get("cuts") or {}
        self.gbkk = _first_map(cuts.get("gbkk"))
        self.upc_direct = _first_map(cuts.get("upcDirect"))
        self.upc_milkrun = _first_map(cuts.get("upcMilkrun"))
        ttb = refs.get("ttb") or {}
        self.ttb = {name: [[_cell(r, 0), _cell(r, 1), _cell(r, 2)] for r in (rows or [])] for name, rows in ttb.items()}
        self.has_ttb = bool(self.ttb)

    def cuts_for(self, dest):
        k = _norm(dest)
        c = ["", "", "", ""]
        for m in (self.gbkk, self.upc_direct, self.upc_milkrun):   # Cut 0-2: GBKK -> UPC Direct -> UPC Milkrun
            if k in m:
                r = m[k]
                c[0], c[1], c[2] = _cell(r, 1), _cell(r, 2), _cell(r, 3)
                break
        for m in (self.upc_direct, self.upc_milkrun):              # Cut 3: UPC sheets only
            if k in m:
                c[3] = _cell(m[k], 4)
                break
        return c

    def standby_for(self, dest):
        d = str(dest or "").strip()
        if not d or re.match(r"^(SORC|NORC|NERC)", d):
            return ""
        k = d.lower()
        for route, standby, _dep in self.ttb.get("Tue TTB", []):
            if k in route.lower():
                t = parse_tod(standby)
                if t is None:
                    return standby
                secs = int(round(t * 86400))
                return f"{secs // 3600:02d}:{secs % 3600 // 60:02d}:{secs % 60:02d}"
        return ""

    def ttb_depart(self, dest, weekday, actual_tod):
        sheet = {"SUN": "Sun TTB", "MON": "Mon TTB", "TUE": "Tue TTB"}.get(weekday, "Wed-Sat TTB")
        k = _norm(dest)
        best, best_diff = None, None
        for route, _sb, dep in self.ttb.get(sheet, []):
            if _norm(route) != k:
                continue
            t = parse_tod(dep)
            if t is None:
                t = 0.0 if not dep else None   # blank Depart counts as 00:00 in the sheet
            if t is None:
                continue
            diff = abs(t - actual_tod)
            if best_diff is None or diff < best_diff:
                best, best_diff = t, diff
        return best

    def hub_row(self, dest):
        return self.hub.get(_norm(dest))


def _minutes(t):
    return int(round(t * 1440)) % 1440


def cut_status(actual_tod, cuts):
    """The cut-window part of the 'show on time/late' formula (times shifted to an 18:00 day start).
    Works in whole minutes so a departure exactly on a window edge is not lost to float rounding."""
    sh = lambda m: (m - 18 * 60) % 1440
    c = [parse_tod(x) for x in cuts]
    c = [sh(_minutes(x)) if x is not None else None for x in c]
    a = sh(_minutes(actual_tod))
    present = [x for x in c if x is not None]
    if not present:
        return "On Time"
    if a <= min(present):
        return "On Time"
    c0, c1, c2, c3 = c

    def lower(*prev_then_self):
        *prev, own = prev_then_self
        for p in prev:
            if p is not None:
                return p + 60
        return own - 60

    if c3 is not None and a <= c3 and a >= lower(c2, c1, c0, c3):
        return "On Time"
    if c2 is not None and a <= c2 and a >= lower(c1, c0, c2):
        return "On Time"
    if c1 is not None and a <= c1 and a >= lower(c0, c1):
        return "On Time"
    if c0 is not None and a <= c0:
        return "On Time"
    return "Late"


def rmk_for(status, standby, assign):
    if status != "Late":
        return ""
    if not assign or not standby or standby == "-":
        return "OB Late"
    a = parse_dt(assign)
    if a is None:
        return "OB Late"
    sb = parse_tod(standby) or 0.0
    # Same arithmetic as the sheet: serial = DATE(...) + TIMEVALUE(...), time = MOD(serial, 1).
    # In floating point MOD(serial, 1) of exactly 13:00 comes out just under TIME(13,0,0),
    # so an assign at 13:00 sharp counts as "before 13:00" there; replicate that.
    serial = (datetime(a.year, a.month, a.day) - datetime(1899, 12, 30)).days + _tod_of(a)
    a_tod = serial - int(serial)
    full = datetime(a.year, a.month, a.day) + timedelta(days=(1 if (a_tod >= 13 * _H and sb < 13 * _H) else 0) + sb)
    return "LH Late" if a > full else "OB Late"


def _category(trip_name):
    n = str(trip_name or "").lower()
    if "timetable" in n:
        return "Timetable FULL"
    if "adhoc" in n:
        return "Adhoc"
    if "รถหลัก" in n:
        return "รถหลัก"
    if "รายเดือน" in n:
        return "รายเดือน"
    if "mix" in n:
        return "MIX SORT"
    return "Unknown"


def _ops_date_of(rows, g):
    """'Actual ops date' = MAXIFS of raw AW per trip; AW = departure date, minus 1 day before 13:00."""
    best = None
    for r in rows:
        dt = parse_dt(g(r, "dep"))
        if not dt:
            continue
        d = datetime(dt.year, dt.month, dt.day) - timedelta(days=1 if dt.hour < 13 else 0)
        best = d if best is None or d > best else best
    return best.strftime("%d/%m/%y") if best else ""


def build_table_rows(raw_headers, raw_rows, refs):
    """raw data (headers + rows) -> (TABLE_HEADERS, rows) like the Table tab."""
    hdr = [str(h or "").strip() for h in raw_headers]

    def col(name):
        try:
            return hdr.index(name)
        except ValueError:
            return None

    ix = {k: col(n) for k, n in {
        "trip": "LH Trip Number", "name": "LH Trip Name", "stno": "Station Number", "stname": "Station Name",
        "veh": "Vehicle Type", "plate": "Vehicle Plate Number", "driver": "Driver", "assign": "Assign time",
        "dep": "Actual Departure Time", "order": "Outbound(order)", "ops": "_opsDate",
    }.items()}
    if ix["trip"] is None:
        raise ValueError('ไม่พบคอลัมน์ "LH Trip Number" ในไฟล์ raw data')

    g = lambda r, k: _cell(r, ix[k]) if ix[k] is not None else ""
    ref = RefTables(refs)

    trips, order = {}, []
    for r in raw_rows or []:
        t = g(r, "trip")
        if not t:
            continue
        if t not in trips:
            trips[t] = []
            order.append(t)
        trips[t].append(r)

    out = []
    for n, t in enumerate(order, start=1):
        rows = trips[t]
        first = rows[0]
        origin = next((g(r, "stname") for r in rows if g(r, "stno") == "1"), "")
        dest = next((g(r, "stname") for r in rows if g(r, "stno") == "2"), "")
        cuts = ref.cuts_for(dest)
        standby = ref.standby_for(dest)
        assign = g(first, "assign")
        dep_dt = parse_dt(g(first, "dep"))
        dep_txt = dep_dt.strftime("%d/%m/%Y %H:%M") if dep_dt else ""

        weekday, status = "", ""
        if dep_dt:
            weekday = _DAYS[(dep_dt - timedelta(hours=13)).weekday()]
            actual = (dep_dt.hour * 60 + dep_dt.minute) / 1440.0
            # The sheet formula also has a TTB-departure rule, but its Route comparison sits inside a
            # LAMBDA (no array evaluation) and never matches, so the sheet decides by Cut only.
            # USE_TTB_DEPART=True turns the intended TTB rule on.
            ttb_t = ref.ttb_depart(dest, weekday, actual) if USE_TTB_DEPART else None
            if ttb_t is not None:
                status = "On Time" if _minutes(actual) <= _minutes(ttb_t) + 30 else "Late"
            else:
                status = cut_status(actual, cuts)

        hub = ref.hub_row(dest)
        intent = _cell(hub, 2) if hub else ""
        region = _cell(hub, 1) if hub else ""
        region = "UPC" if region == "RC" else region
        zone = _cell(hub, 3) if hub else ""

        day = month = yt = year = ctime = mdy = ""
        if dep_dt:
            day, month = str(dep_dt.day), str(dep_dt.month)
            year, ctime = str(dep_dt.year), dep_dt.strftime("%H:%M")
            yt, mdy = f"{year} {ctime}", f"{month}/{day}/{year}"

        out.append([
            n, t, _category(g(first, "name")), g(first, "veh"), g(first, "plate"), g(first, "driver"),
            origin, dest, "", t, _category(g(first, "name")), 1, n, f"{t}|1",
            _ops_date_of(rows, g),
            cuts[0], cuts[1], cuts[2], cuts[3], standby, assign, dep_txt, weekday, status,
            rmk_for(status, standby, assign),
            "Non-intentional" if intent == "Non-intentional" else "",
            "Intentional" if intent == "Intentional" else "",
            region, zone, "", g(first, "order"), "", day, month, yt, year, ctime, mdy, f"{t}_1",
        ])
    return TABLE_HEADERS, out
