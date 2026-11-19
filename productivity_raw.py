"""Rebuild the "Productivity Orders  ZONE" tab (Hourly Tracker source) from LH Trip raw data.

Mirrors [SPX-SOCN] Outbound Daily Report - 2026: raw data -> pivots -> Outbound Daily Report -> Productivity.
  * one record per LH Trip Number; vehicle type and Sealed time from the FIRST raw row of the trip
    (VLOOKUP exact match), Orders = SUM Outbound(order) of all its rows, destination = Station Name of the
    Station Number 2 row
  * hour bucket = time of day of Sealed time; a day runs 16:00 -> 16:00 (sheet column AW)
  * trucks counted per vehicle-type group below (other 6WH variants are not counted, as in the sheet)
  * zone A/B/C of the destination ('Outbound Email' B:C; Hub "OBD Zone" as fallback)
Sheet quirks kept on purpose so the numbers match: the 15:00 row is always 0 (its SUMIFS range is
[15:00, 13:00)), Total/Max/Avg use the same row ranges as the sheet formulas.

build_productivity_rows() returns rows shaped like the sheet CSV so app.sync_productivity_orders_sheet()
can parse and save them unchanged.
"""
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta

DAY_START_HOUR = 16
HOURS = [16, 17, 18, 19, 20, 21, 22, 23, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
KEEP_15_QUIRK = True   # sheet row 34 (15:00) is always 0

VEHICLE_GROUPS = {
    "4wh": ("4WH-4ล้อ", "4WH-4ล้อ[OF]"),
    "4wj": ("4WJ-4ล้อจัมโบ้", "4WJ-4ล้อจัมโบ้[OF]"),
    "6wh": ("6WH-6ล้อ[7.2m]", "6WH-6ล้อ[5.5m]", "6WH-6ล้อ[9.6m]"),
    "semi": ("Semi trailer-รถพ่วงแม่ลูก",),
}
ZONES = ("A", "B", "C", "D", "E", "OBC")

_DT_RE = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4})\s+(\d{1,2}):(\d{2})")


def parse_raw_dt(v):
    """'18/11/2026 23:38' (dd/mm/yyyy, display value of the raw tab) -> datetime."""
    m = _DT_RE.search(str(v or ""))
    if not m:
        return None
    d, mo, y, h, mi = (int(x) for x in m.groups())
    try:
        return datetime(y, mo, d, h, mi)
    except ValueError:
        return None


def ops_day_of(sealed):
    """Productivity day (sheet AW): sealed date, minus one day before 16:00."""
    return (sealed - timedelta(days=1 if sealed.hour < DAY_START_HOUR else 0)).strftime("%Y-%m-%d")


def build_trips(headers, rows):
    """One record per LH Trip Number, as the pivots + VLOOKUPs build it."""
    ix = {str(h).strip(): i for i, h in enumerate(headers)}
    need = ["LH Trip Number", "Station Number", "Station Name", "Vehicle Type", "Sealed time", "Outbound(order)"]
    missing = [h for h in need if h not in ix]
    if missing:
        raise ValueError("raw data ไม่มีคอลัมน์: " + ", ".join(missing))
    get = lambda r, h: r[ix[h]] if ix[h] < len(r) else ""
    trips = {}
    for r in rows:
        t = str(get(r, "LH Trip Number") or "").strip()
        if not t:
            continue
        rec = trips.get(t)
        if rec is None:
            rec = trips[t] = {
                "trip": t,
                "vehicleType": str(get(r, "Vehicle Type") or "").strip(),
                "sealed": parse_raw_dt(get(r, "Sealed time")),
                "orders": 0.0,
                "destination": "",
            }
        try:
            rec["orders"] += float(str(get(r, "Outbound(order)") or 0).replace(",", "") or 0)
        except ValueError:
            pass
        if not rec["destination"] and str(get(r, "Station Number")).strip() in ("2", "2.0"):
            rec["destination"] = str(get(r, "Station Name") or "").strip()
    return list(trips.values())


def available_days(trips):
    c = Counter(ops_day_of(t["sealed"]) for t in trips if t["sealed"])
    return dict(sorted(c.items()))


def build_productivity_rows(headers, rows, zone_map, day=None):
    """-> (day, csv_like_rows, info). day defaults to the day with the most sealed trips."""
    trips = build_trips(headers, rows)
    days = available_days(trips)
    if not days:
        raise ValueError("raw data ไม่มี Sealed time เลย")
    if not day:
        day = max(days, key=days.get)

    per_hour = defaultdict(Counter)
    unknown_zone = Counter()
    for t in trips:
        s = t["sealed"]
        if not s or ops_day_of(s) != day:
            continue
        h = s.hour
        if KEEP_15_QUIRK and h == 15:
            continue
        c = per_hour[h]
        for g, names in VEHICLE_GROUPS.items():
            if t["vehicleType"] in names:
                c[g] += 1
        c["orders"] += t["orders"]
        z = zone_map.get(t["destination"], "")
        if z in ZONES:
            c["zone" + z] += t["orders"]
        elif t["destination"]:
            unknown_zone[t["destination"]] += 1

    def trucks(c):
        return sum(c[g] for g in VEHICLE_GROUPS)

    # sheet ranges: hour rows 10..34 = HOURS[0..23] ; rows 10:31 = 16:00..12:00 ; rows 12:31 = 18:00..12:00
    h_10_31 = HOURS[:21]
    h_12_31 = HOURS[2:21]
    tot_trucks = sum(trucks(per_hour[h]) for h in HOURS)
    tot_orders = sum(per_hour[h]["orders"] for h in HOURS)
    pct = lambda a, b: f"{a / b * 100:.2f}%" if b else "-"

    def line(label, c_trucks, c_pct, groups, orders, o_pct, zones):
        return ["", label, str(c_trucks), c_pct] + [str(groups[g]) for g in VEHICLE_GROUPS] + \
               [str(int(round(orders))), o_pct] + [str(int(round(zones[z]))) for z in ZONES]

    out = []
    # Total: C7/I7 = rows 10:34, E..H / K..P = rows 10:31, D7/J7 = sum of % rows 10:31
    sum_g = {g: sum(per_hour[h][g] for h in h_10_31) for g in VEHICLE_GROUPS}
    sum_z = {z: sum(per_hour[h]["zone" + z] for h in h_10_31) for z in ZONES}
    d7 = sum(trucks(per_hour[h]) for h in h_10_31)
    j7 = sum(per_hour[h]["orders"] for h in h_10_31)
    out.append(line("Total", tot_trucks, pct(d7, tot_trucks), sum_g, tot_orders, pct(j7, tot_orders), sum_z))
    # Max/hr: trucks rows 12:31, orders/zones rows 10:31
    max_g = {g: max(per_hour[h][g] for h in h_12_31) for g in VEHICLE_GROUPS}
    max_z = {z: max(per_hour[h]["zone" + z] for h in h_10_31) for z in ZONES}
    max_c = max(trucks(per_hour[h]) for h in h_12_31)
    max_i = max(per_hour[h]["orders"] for h in h_10_31)
    out.append(line("Max/hr", max_c, pct(max_c, tot_trucks), max_g, max_i, pct(max_i, tot_orders), max_z))

    # Avg/hr: AVERAGEIF(range, ">0")
    def avg(vals):
        v = [x for x in vals if x > 0]
        return sum(v) / len(v) if v else 0
    avg_g = {g: int(round(avg([per_hour[h][g] for h in h_12_31]))) for g in VEHICLE_GROUPS}
    avg_z = {z: avg([per_hour[h]["zone" + z] for h in h_10_31]) for z in ZONES}
    avg_c = avg([trucks(per_hour[h]) for h in h_12_31])
    avg_i = avg([per_hour[h]["orders"] for h in h_10_31])
    out.append(line("Avg/hr", int(round(avg_c)), pct(avg_c, tot_trucks), avg_g, avg_i, pct(avg_i, tot_orders), avg_z))

    for h in HOURS:
        c = per_hour[h]
        out.append(line(f"{h:02d}:00", trucks(c), pct(trucks(c), tot_trucks), {g: c[g] for g in VEHICLE_GROUPS},
                        c["orders"], pct(c["orders"], tot_orders), {z: c["zone" + z] for z in ZONES}))

    info = {
        "day": day,
        "days": days,
        "trips": sum(1 for t in trips if t["sealed"] and ops_day_of(t["sealed"]) == day),
        "rawTrips": len(trips),
        "notSealed": sum(1 for t in trips if not t["sealed"]),
        "unknownZone": dict(unknown_zone.most_common(20)),
    }
    return day, out, info
