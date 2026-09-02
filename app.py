import os
import math
import warnings
import pandas as pd
from flask import Flask, request, jsonify, send_from_directory
from werkzeug.middleware.proxy_fix import ProxyFix

warnings.filterwarnings("ignore")

app = Flask(__name__, static_folder=".")
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def process_csv(filepath):
    df = pd.read_csv(filepath, low_memory=False)
    
    # 1. Normalize boolean columns
    for col in ["is_soc_outbound_ontime", "is_soc_outbound_2nd_ontime", "is_in_sorting_center", "is_soc_missort"]:
        if col in df.columns:
            df[col] = (df[col].astype(str).str.strip().str.upper()
                       .map({"TRUE": True, "FALSE": False, "1": True, "0": False}))

    # 2. Parse timestamps
    ts_cols = [
        "first_soc_outbound_timestamp",
        "soc_outbound_based_received_cut_off_timestamp",
        "soc_outbound_based_received_2nd_cut_off_timestamp",
        "first_soc_received_timestamp",
        "first_soc_arrive_timestamp"
    ]
    for col in ts_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    # 3. Filter late shipments
    has_out = df["first_soc_outbound_timestamp"].notna()
    is_late = df["is_soc_outbound_ontime"] == False
    late_df = df[has_out & is_late].copy()
    total_late = int(len(late_df))
    dest_count = int(df["dest_station_name"].nunique())

    # 4. Calculate delay & D+2
    has_cut = late_df["soc_outbound_based_received_2nd_cut_off_timestamp"].notna()
    calc_df = late_df[has_cut & late_df["first_soc_outbound_timestamp"].notna()].copy()
    if len(calc_df) > 0:
        calc_df["delay_mins"] = (
            (calc_df["first_soc_outbound_timestamp"] - calc_df["soc_outbound_based_received_2nd_cut_off_timestamp"])
            .dt.total_seconds() / 60
        )
        median_late = round(float(calc_df["delay_mins"].median()), 1)
        d2_count = int((calc_df["delay_mins"] >= 2 * 24 * 60).sum())
    else:
        median_late = 0.0
        d2_count = 0

    THAI_STATION_MAP = {
        'APTNI': 'พัทลุง', 'HSNOI': 'สะเดาน้อย', 'APHIT': 'พิษณุโลก',
        'ABKEN': 'บางเขน', 'HNJOK': 'หนองจอก', 'AKSWA': 'คลองสามวา',
        'AMBRI': 'มีนบุรี', 'HTYBR': 'ธัญบุรี', 'HLDLK': 'ลาดหลุมแก้ว',
        'AKLNG': 'คลองหลวง', 'HKRET': 'ปากเกร็ด', 'HSAMP': 'สามพราน',
        'HPTUM': 'ปทุมธานี', 'HRCTW': 'ราชเทวี', 'ASMAI': 'สายไหม',
        'ADONM': 'ดอนเมือง', 'ALKSI': 'หลักสี่', 'ALUKA': 'ลำลูกกา',
        'HKYAO': 'ห้วยขวาง', 'APTUM': 'ปทุมวัน', 'AKRET': 'ปากเกร็ด',
        'HBKUM': 'บึงกุ่ม', 'ABKUM': 'บึงกุ่ม', 'ASRIN': 'ศรีนครินทร์',
        'HKSWA': 'คลองสามวา', 'HDONM': 'ดอนเมือง', 'ATYBR': 'ธัญบุรี',
        'HSKOK': 'สามโคก', 'AUBON': 'อุบลราชธานี', 'ALDLK': 'ลาดหลุมแก้ว',
        'HSMAI': 'สายไหม', 'APRAO': 'ลาดพร้าว', 'HLKSI': 'หลักสี่',
        'ANSUG': 'สุไหงโก-ลก', 'AYASO': 'ยโสธร', 'ACYPM': 'ชัยภูมิ',
        'ASKLA': 'สงขลา', 'ABRAM': 'บุรีรัมย์', 'AROET': 'ร้อยเอ็ด',
        'ABACH': 'บางบัวทอง', 'APBMS': 'พนมสารคาม', 'AHYAI': 'หาดใหญ่',
        'ARTBR': 'ราชบุรี', 'APHKT': 'ภูเก็ต', 'AWRIN': 'วารินชำราบ',
        'AJRAT': 'เจริญราษฎร์', 'AKLAK': 'คลองลาน', 'ARMAN': 'รามัน',
        'AMYOR': 'มายอ', 'ABUAY': 'บัวใหญ่', 'HNSUA': 'หนองเสือ',
        'HLUKA': 'ลำลูกกา', 'AYALA': 'ยะลา', 'ACRAI': 'เชียงราย',
        'AYLNG': 'ยะรัง', 'ABDNG': 'บางแค', 'APSAT': 'โพธิ์ทอง',
        'ATANG': 'ทุ่งยางแดง', 'ANKPN': 'นครพนม', 'AKMRT': 'เขมราฐ',
        'ALPMT': 'ลำปาง', 'APYPS': 'พยัคฆภูมิพิสัย', 'ASBRI': 'สระบุรี',
        'APIMY': 'พิมาย', 'ASTON': 'สตูล', 'ASKON': 'สกลนคร',
        'ASRGS': 'ศรีสะเกษ', 'AGUNT': 'กันทรลักษ์', 'ASSKT': 'ศรีสะเกษ',
        'ACPON': 'ชุมพร', 'AKATU': 'กะทู้', 'HCRNG': 'เชียงราย',
        'ANKAI': 'หนองคาย', 'AMSOD': 'แม่สอด', 'AHYOD': 'อยุธยา',
        'AKNAI': 'ขอนแก่น', 'AKKOI': 'เกาะคา', 'APATL': 'ปัตตานี',
        'ABAMO': 'บางมด', 'ATTKO': 'ท่าตะโก', 'HDSIT': 'ดุสิต',
        'HTPAR': 'ท่าแพ', 'AKPSN': 'กำแพงแสน', 'APTCI': 'พญาไท',
        'ASWAN': 'นครสวรรค์', 'CC-SORC': 'ศูนย์คัดแยก SOC', 'CC': 'ศูนย์คัดแยก SOC',
        'ASMEN': 'สามเสน', 'HPRAP': 'พระราม 9', 'HSWRW': 'สว่างแดนดิน', 'AHTPN': 'ห้วยพูล'
    }

    # Clean station names and attach Thai name (without English in parentheses)
    def clean_name(val):
        if pd.isna(val):
            return "Unknown"
        s = str(val).strip()
        import re
        s = re.sub(r"\s*\([^)]*\)$", "", s).strip()
        s = re.sub(r"\s*-\s*\?+.*$", "", s).strip()
        s = re.sub(r"\?+", "", s).strip()
        base_code = s.split("-")[0].strip()
        th_name = THAI_STATION_MAP.get(base_code, "")
        if th_name and " - " not in s:
            return f"{s} - {th_name}"
        return s

    df["dest_station_name_clean"] = df["dest_station_name"].apply(clean_name)
    late_df["dest_station_name_clean"] = late_df["dest_station_name"].apply(clean_name)
    dest_count = int(df["dest_station_name_clean"].nunique())

    # 5. Peak time per destination (Mode of HH:MM)
    def calc_peak_time(s):
        t = s.dropna()
        if t.empty:
            return "-"
        hhmm = t.dt.strftime("%H:%M")
        mode_res = hhmm.mode()
        return str(mode_res.iloc[0]) if not mode_res.empty else "-"

    # 6. Group ranking table
    grp = (
        late_df.groupby("dest_station_name_clean", dropna=False)
        .agg(
            late_count=("shipment_id", "count"),
            peak_time=("first_soc_outbound_timestamp", calc_peak_time)
        )
        .reset_index()
        .sort_values("late_count", ascending=False)
        .reset_index(drop=True)
    )
    
    ranking_list = []
    max_count = int(grp["late_count"].max()) if len(grp) > 0 else 1
    for idx, row in grp.iterrows():
        cnt = int(row["late_count"])
        pct = round((cnt / total_late * 100), 1) if total_late > 0 else 0
        ranking_list.append({
            "rank": idx + 1,
            "station": str(row["dest_station_name_clean"]),
            "count": cnt,
            "pct": pct,
            "peakTime": str(row["peak_time"])
        })

    report_date = "N/A"
    if "report_date" in df.columns:
        valid_dates = df["report_date"].dropna()
        if len(valid_dates) > 0:
            report_date = str(valid_dates.iloc[0])

    return {
        "reportDate": report_date,
        "totalLate": total_late,
        "destCount": dest_count,
        "medianLate": median_late,
        "d2Count": d2_count,
        "maxCount": max_count,
        "ranking": ranking_list,
        "top10": ranking_list[:10]
    }


@app.route('/favicon.ico')
@app.route('/favicon.png')
@app.route('/logo-spx-express.webp')
def serve_favicon():
    if os.path.exists(os.path.join(BASE_DIR, 'logo-spx-express.webp')):
        return send_from_directory(BASE_DIR, 'logo-spx-express.webp')
    return send_from_directory(BASE_DIR, 'favicon.png')

@app.route("/")
def index():
    return send_from_directory(BASE_DIR, "index.html")

@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file uploaded"}), 400
    
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"success": False, "error": "Empty filename"}), 400

    if not file.filename.lower().endswith(".csv"):
        return jsonify({"success": False, "error": "Please upload a CSV file"}), 400

    save_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(save_path)

    try:
        data = process_csv(save_path)
        data["filename"] = file.filename
        data["savedPath"] = save_path
        data["success"] = True
        # Include raw rows needed for Skip Process dashboard (minimal columns only)
        try:
            skip_df = pd.read_csv(save_path, low_memory=False,
                usecols=lambda c: c in [
                    'shipment_id', 'soc_outbound_late_type_2nd_cutoff',
                    'dest_station_name', 'recieve_team'
                ])
            data["rawRows"] = skip_df.fillna('').to_dict(orient='records')
        except Exception:
            data["rawRows"] = []
        return jsonify(data)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/list-files", methods=["GET"])
def list_files():
    file_list = []
    seen = set()

    # Search in uploads folder first
    if os.path.exists(UPLOAD_FOLDER):
        for f in os.listdir(UPLOAD_FOLDER):
            if f.endswith(".csv"):
                p = os.path.join(UPLOAD_FOLDER, f)
                file_list.append({
                    "filename": f,
                    "location": "uploads",
                    "mtime": os.path.getmtime(p),
                    "size": os.path.getsize(p)
                })
                seen.add(f)

    # Search in root folder
    for f in os.listdir(BASE_DIR):
        if f.endswith(".csv") and f not in seen:
            p = os.path.join(BASE_DIR, f)
            file_list.append({
                "filename": f,
                "location": "root",
                "mtime": os.path.getmtime(p),
                "size": os.path.getsize(p)
            })
            seen.add(f)

    # Sort by modification time (newest first)
    file_list.sort(key=lambda x: x["mtime"], reverse=True)
    return jsonify({"success": True, "files": file_list})

@app.route("/api/load-file", methods=["GET"])
def load_file():
    filename = request.args.get("filename", "").strip()
    if not filename:
        return jsonify({"success": False, "error": "No filename specified"}), 400

    target = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.exists(target):
        target = os.path.join(BASE_DIR, filename)

    if not os.path.exists(target):
        return jsonify({"success": False, "error": f"File '{filename}' not found"}), 404

    try:
        data = process_csv(target)
        data["filename"] = filename
        data["success"] = True
        # Include raw rows needed for Skip Process dashboard
        try:
            skip_df = pd.read_csv(target, low_memory=False,
                usecols=lambda c: c in [
                    'shipment_id', 'soc_outbound_late_type_2nd_cutoff',
                    'dest_station_name', 'recieve_team'
                ])
            data["rawRows"] = skip_df.fillna('').to_dict(orient='records')
        except Exception:
            data["rawRows"] = []
        return jsonify(data)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/raw-data", methods=["GET"])
def get_raw_data():
    filename = request.args.get("filename", "").strip()
    target = ""
    if filename:
        target = os.path.join(UPLOAD_FOLDER, filename)
        if not os.path.exists(target):
            target = os.path.join(BASE_DIR, filename)
    
    if not target or not os.path.exists(target):
        target = os.path.join(BASE_DIR, "SOC-BISOCinvestigateshipment_DownloadTable_20260901_201309.csv")
        if os.path.exists(UPLOAD_FOLDER):
            upload_files = [os.path.join(UPLOAD_FOLDER, f) for f in os.listdir(UPLOAD_FOLDER) if f.endswith(".csv")]
            if upload_files:
                upload_files.sort(key=os.path.getmtime, reverse=True)
                target = upload_files[0]

    if not os.path.exists(target):
        return jsonify({"success": False, "error": "No file found"}), 404

    df = pd.read_csv(target, low_memory=False)
    has_out = df["first_soc_outbound_timestamp"].notna()
    is_late = df["is_soc_outbound_ontime"].astype(str).str.strip().str.upper().isin(["FALSE", "0"])
    late_df = df[has_out & is_late].copy()

    # Filters
    search = request.args.get("search", "").strip().lower()
    station = request.args.get("station", "").strip()

    if search:
        mask = (
            late_df["shipment_id"].astype(str).str.lower().str.contains(search) |
            late_df["dest_station_name"].astype(str).str.lower().str.contains(search) |
            late_df["latest_to_number"].astype(str).str.lower().str.contains(search)
        )
        late_df = late_df[mask]

    if station:
        late_df = late_df[late_df["dest_station_name"].astype(str).str.contains(station)]

    page = int(request.args.get("page", 1))
    limit = int(request.args.get("limit", 100))
    total_count = len(late_df)

    # Delay calculation
    late_df["out_dt"] = pd.to_datetime(late_df["first_soc_outbound_timestamp"], errors="coerce")
    late_df["cut_dt"] = pd.to_datetime(late_df["soc_outbound_based_received_2nd_cut_off_timestamp"], errors="coerce")
    late_df["delay_mins"] = ((late_df["out_dt"] - late_df["cut_dt"]).dt.total_seconds() / 60).round(1).fillna(0)

    start_idx = (page - 1) * limit
    page_df = late_df.iloc[start_idx:start_idx + limit]

    cols = [
        "shipment_id", "dest_station_name", "first_soc_received_timestamp",
        "first_soc_outbound_timestamp", "soc_outbound_based_received_2nd_cut_off_timestamp",
        "delay_mins", "soc_outbound_late_type_2nd_cutoff", "soc_outbound_route_type", "latest_to_number", "recieve_team"
    ]
    rows = page_df[cols].fillna("").to_dict(orient="records")

    return jsonify({
        "success": True,
        "total": total_count,
        "page": page,
        "limit": limit,
        "totalPages": (total_count + limit - 1) // limit,
        "rows": rows
    })

@app.route("/api/current-data", methods=["GET"])
def get_current_data():
    candidates = [
        os.path.join(BASE_DIR, "SOC-BISOCinvestigateshipment_DownloadTable_20260901_201309.csv"),
    ]
    if os.path.exists(UPLOAD_FOLDER):
        upload_files = [os.path.join(UPLOAD_FOLDER, f) for f in os.listdir(UPLOAD_FOLDER) if f.endswith(".csv")]
        if upload_files:
            upload_files.sort(key=os.path.getmtime, reverse=True)
            candidates.insert(0, upload_files[0])

    for target in candidates:
        if os.path.exists(target):
            try:
                data = process_csv(target)
                data["filename"] = os.path.basename(target)
                data["success"] = True
                try:
                    skip_df = pd.read_csv(target, low_memory=False,
                        usecols=lambda c: c in [
                            'shipment_id', 'soc_outbound_late_type_2nd_cutoff',
                            'dest_station_name', 'recieve_team'
                        ])
                    data["rawRows"] = skip_df.fillna('').to_dict(orient='records')
                except Exception:
                    data["rawRows"] = []
                return jsonify(data)
            except Exception:
                pass

    return jsonify({"success": False, "message": "No CSV loaded yet"})

import json

VOLUME_FILE = os.path.join(BASE_DIR, "volume_history.json")

@app.route("/api/get-volume", methods=["GET"])
def get_volume():
    if os.path.exists(VOLUME_FILE):
        try:
            with open(VOLUME_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return jsonify({"success": True, "history": data})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500
    return jsonify({"success": True, "history": []})

@app.route("/api/save-volume", methods=["POST"])
def save_volume():
    try:
        req_data = request.get_json(force=True)
        if isinstance(req_data, list):
            with open(VOLUME_FILE, "w", encoding="utf-8") as f:
                json.dump(req_data, f, ensure_ascii=False, indent=2)
            return jsonify({"success": True})
        return jsonify({"success": False, "error": "Invalid payload"}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    print("=" * 60)
    print(" Server started at http://localhost:5000")
    print(f" Uploaded files will be stored in: {UPLOAD_FOLDER}")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5000, debug=True)