import os
import json
import uuid
import csv
import io
import warnings
import requests
import pandas as pd
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory, session, redirect, url_for
from werkzeug.middleware.proxy_fix import ProxyFix

warnings.filterwarnings("ignore")

app = Flask(__name__, static_folder=".")
app.secret_key = "socn_ops_portal_super_secret_key_2026"
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # Allow up to 500MB uploads

@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

LOGS_FILE = os.path.join(BASE_DIR, "activity_logs.json")

def load_activity_logs():
    if os.path.exists(LOGS_FILE):
        try:
            with open(LOGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []

USERS_FILE = os.path.join(BASE_DIR, "users_db.json")

def load_users_db():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    default_users = [
        {
            "id": "u1",
            "name": "Admin SOC",
            "email": "admin@spxexpress.com",
            "pass": "1234",
            "role": "Admin",
            "status": "approved",
            "createdAt": "2026-09-03 00:00:00"
        },
        {
            "id": "u2",
            "name": "Ground Operator",
            "email": "ground@spxexpress.com",
            "pass": "1234",
            "role": "Ground",
            "status": "approved",
            "createdAt": "2026-09-03 00:00:00"
        }
    ]
    save_users_db(default_users)
    return default_users

def save_users_db(users):
    try:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("Error saving users db:", e)

def save_activity_logs(logs):
    try:
        with open(LOGS_FILE, "w", encoding="utf-8") as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("Error saving activity logs:", e)

def log_activity(action, details, user_email=None, user_name=None, user_role=None):
    if not user_email:
        user_email = session.get("user_email", "guest")
    if not user_name:
        user_name = session.get("user_name", "Guest")
    if not user_role:
        user_role = session.get("user_role", "Ground")
    
    logs = load_activity_logs()
    entry = {
        "id": str(uuid.uuid4())[:8],
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "email": user_email,
        "name": user_name,
        "role": user_role,
        "action": action,
        "details": details,
        "ip": request.remote_addr or "127.0.0.1"
    }
    logs.insert(0, entry)
    if len(logs) > 5000:
        logs = logs[:5000]
    save_activity_logs(logs)
    return entry

@app.after_request
def add_ngrok_headers(response):
    response.headers["ngrok-skip-browser-warning"] = "true"
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


SOURCE_DIR = os.path.join(BASE_DIR, "Source")

def build_cutoff_map():
    files = [
        ('UPC Milkrun', os.path.join(SOURCE_DIR, 'test  - SOCN_UPC_Milkrun.csv')),
        ('UPC Direct', os.path.join(SOURCE_DIR, 'test  - SOCN_UPC_Direct.csv')),
        ('GBKK', os.path.join(SOURCE_DIR, 'test  - SOCN_GBKK.csv'))
    ]
    cutoff_map = {}
    for area_type, path in files:
        if not os.path.exists(path):
            continue
        try:
            df = pd.read_csv(path)
            for idx in range(1, len(df)):
                row = df.iloc[idx]
                station_name = str(row.get('LM Station Name', '') or '').strip()
                if not station_name or station_name.lower() == 'nan':
                    continue
                
                entry = {
                    'area_group': area_type,
                    'station_id': str(row.get('LM Station ID', '') or '' if pd.notna(row.get('LM Station ID')) else '').replace('.0', ''),
                    'station_name': station_name,
                    'op_type': str(row.get('Operation Type', '') or '' if pd.notna(row.get('Operation Type')) else ''),
                    'cut0_ob': str(row.get('Cut 0', '') or '' if pd.notna(row.get('Cut 0')) else ''),
                    'cut1_ob': str(row.get('Cut 1', '') or '' if pd.notna(row.get('Cut 1')) else ''),
                    'cut2_ob': str(row.get('Cut 2', '') or '' if pd.notna(row.get('Cut 2')) else ''),
                    'cut3_ob': str(row.get('Cut 3', '') or '' if pd.notna(row.get('Cut 3')) else ''),
                }
                cutoff_map[station_name.lower()] = entry
                parts = station_name.split('-')
                if len(parts) > 1:
                    cutoff_map[parts[0].strip().lower()] = entry
        except Exception:
            pass
    return cutoff_map


@app.route("/api/users", methods=["GET"])
def get_users_api():
    return jsonify({"success": True, "users": load_users_db()})

@app.route("/api/users/signup", methods=["POST"])
def signup_user_api():
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = (data.get("pass") or "").strip()

    if not name or not email or not password:
        return jsonify({"success": False, "error": "กรุณากรอกข้อมูลให้ครบถ้วน"}), 400

    users = load_users_db()
    for u in users:
        if u.get("email", "").lower() == email:
            return jsonify({"success": False, "error": "อีเมลนี้ถูกลงทะเบียนไว้แล้ว"}), 400

    new_user = {
        "id": "u_" + str(int(datetime.now().timestamp() * 1000)),
        "name": name,
        "email": email,
        "pass": password,
        "role": "Ground",
        "status": "pending_approval",
        "createdAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    users.append(new_user)
    save_users_db(users)

    log_activity("USER_SIGNUP", f"ลงทะเบียนผู้ใช้งานใหม่: {name} ({email}) - รอ Admin อนุมัติ", user_email=email, user_name=name, user_role="Ground")
    return jsonify({"success": True, "user": new_user, "users": users})

@app.route("/api/users/approve", methods=["POST"])
def approve_user_api():
    data = request.get_json() or {}
    user_id = str(data.get("id") or "").strip()
    email = str(data.get("email") or "").strip().lower()
    role = data.get("role", "Ground")

    users = load_users_db()
    target = None
    for u in users:
        if (user_id and str(u.get("id")) == user_id) or (email and u.get("email", "").lower() == email):
            target = u
            break

    if not target:
        return jsonify({"success": False, "error": "ไม่พบสมาชิก"}), 404

    target["status"] = "approved"
    target["role"] = role
    save_users_db(users)

    log_activity("USER_APPROVAL", f"อนุมัติบัญชี {target.get('name')} ({target.get('email')}) เป็นสิทธิ์ {role}")
    return jsonify({"success": True, "user": target, "users": users})

@app.route("/api/users/role", methods=["POST"])
def change_role_user_api():
    data = request.get_json() or {}
    user_id = str(data.get("id") or "").strip()
    email = str(data.get("email") or "").strip().lower()
    role = data.get("role", "Ground")

    users = load_users_db()
    target = None
    for u in users:
        if (user_id and str(u.get("id")) == user_id) or (email and u.get("email", "").lower() == email):
            target = u
            break

    if not target:
        return jsonify({"success": False, "error": "ไม่พบสมาชิก"}), 404

    old_role = target.get("role")
    target["role"] = role
    save_users_db(users)

    log_activity("USER_ROLE_CHANGE", f"เปลี่ยนสิทธิ์ {target.get('name')} ({target.get('email')}) จาก {old_role} เป็น {role}")
    return jsonify({"success": True, "user": target, "users": users})

@app.route("/api/users/delete", methods=["POST"])
def delete_user_api():
    data = request.get_json() or {}
    user_id = data.get("id")

    users = load_users_db()
    users = [u for u in users if u.get("id") != user_id]
    save_users_db(users)

    log_activity("USER_DELETE", f"ลบผู้ใช้งาน ID: {user_id}")
    return jsonify({"success": True, "users": users})

@app.route("/api/users/login", methods=["POST"])
def login_user_api():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    password = (data.get("pass") or "").strip()

    users = load_users_db()
    matched = next((u for u in users if u.get("email", "").lower() == email or u.get("name", "").lower() == email.lower()), None)

    if not matched:
        return jsonify({"success": False, "error": "ไม่พบชื่อผู้ใช้งานหรืออีเมลนี้ในระบบ"}), 400

    if matched.get("pass") != password:
        return jsonify({"success": False, "error": "รหัสผ่านไม่ถูกต้อง"}), 400

    if matched.get("status") == "pending_approval":
        return jsonify({"success": False, "error": "บัญชีของคุณอยู่ระหว่างรออนุมัติสิทธิ์จาก Admin"}), 403

    session["user_email"] = matched.get("email")
    session["user_name"] = matched.get("name")
    session["user_role"] = matched.get("role")

    log_activity("USER_LOGIN", f"เข้าสู่ระบบสำเร็จในฐานะ {matched.get('role')}", user_email=matched.get("email"), user_name=matched.get("name"), user_role=matched.get("role"))
    return jsonify({"success": True, "user": matched})


def read_dataframe(filepath):
    if str(filepath).lower().endswith(('.xlsx', '.xls')):
        try:
            xl = pd.ExcelFile(filepath)
            sheet_to_use = 0
            for s in ['Table', 'raw data', 'Sheet1']:
                if s in xl.sheet_names:
                    sheet_to_use = s
                    break
            return pd.read_excel(filepath, sheet_name=sheet_to_use)
        except Exception as ex:
            print("Error reading excel file:", ex)
            return pd.read_csv(filepath, low_memory=False)
    else:
        return pd.read_csv(filepath, low_memory=False)


def process_csv(filepath):
    df = read_dataframe(filepath)
    
    # Standardize Column Names
    col_map = {}
    target_used = set()
    for col in df.columns:
        c_clean = str(col).strip().lower()
        target = None
        if c_clean == 'is_soc_outbound_2nd_ontime':
            target = 'is_soc_outbound_2nd_ontime'
        elif c_clean in ['is_soc_outbound_ontime', 'is_ontime', 'ontime']:
            target = 'is_soc_outbound_ontime'
        elif c_clean == 'soc_outbound_based_received_2nd_cut_off_timestamp':
            target = 'soc_outbound_based_received_2nd_cut_off_timestamp'
        elif c_clean in ['soc_outbound_based_received_cut_off_timestamp', 'cutoff_timestamp', 'cut_off_2']:
            target = 'soc_outbound_based_received_cut_off_timestamp'
        elif c_clean in ['first_soc_outbound_timestamp', 'first_outbound_timestamp', 'outbound_timestamp']:
            target = 'first_soc_outbound_timestamp'
        elif c_clean in ['dest_station_name', 'dest_station', 'hub_name', 'station_name', 'destination']:
            target = 'dest_station_name'
        elif c_clean in ['soc_outbound_late_type_2nd_cutoff', 'soc_outbound_late_type', 'late_type', 'reason']:
            target = 'soc_outbound_late_type_2nd_cutoff'
        elif c_clean in ['soc_outbound_route_type', 'route_type', 'route']:
            target = 'soc_outbound_route_type'
        elif c_clean in ['shipment_id', 'tracking_id', 'tracking_no', 'waybill']:
            target = 'shipment_id'
        elif c_clean in ['first_soc_received_timestamp', 'received_timestamp', 'inbound_timestamp']:
            target = 'first_soc_received_timestamp'
        elif c_clean in ['recieve_team', 'receive_team', 'obd_zone', 'zone']:
            target = 'recieve_team'
        elif c_clean in ['latest_to_number', 'to_number', 'to_no']:
            target = 'latest_to_number'

        if target and target not in target_used:
            col_map[col] = target
            target_used.add(target)

    if col_map:
        df = df.rename(columns=col_map)
    df = df.loc[:, ~df.columns.duplicated()]

    # Ensure required columns exist
    for req in ['first_soc_outbound_timestamp', 'is_soc_outbound_ontime', 'dest_station_name', 'soc_outbound_based_received_2nd_cut_off_timestamp', 'shipment_id', 'soc_outbound_late_type_2nd_cutoff', 'soc_outbound_route_type']:
        if req not in df.columns:
            df[req] = ''

    # Filter LATE rows FIRST to achieve ultra-fast <0.5s processing speed!
    ontime_str = df["is_soc_outbound_ontime"].astype(str).str.strip().str.upper()
    reason_str = df["soc_outbound_late_type_2nd_cutoff"].astype(str).str.strip().str.lower()

    is_late_ontime = ontime_str.isin(["FALSE", "0"])
    is_late_reason = reason_str.notna() & ~reason_str.isin(["", "none", "nan"])
    is_late_mask = is_late_ontime | is_late_reason

    late_df = df[is_late_mask].copy() if is_late_mask.any() else df.head(0).copy()
    total_late = int(len(late_df))

    if total_late == 0:
        return {
            "reportDate": "N/A",
            "totalLate": 0,
            "destCount": 0,
            "medianLate": 0.0,
            "d2Count": 0,
            "maxCount": 0,
            "ranking": [],
            "top10": [],
            "lateTypeBreakdown": {},
            "routeTypeBreakdown": {},
            "outboundRawRows": []
        }

    # Vectorized timestamp parsing ONLY on late_df (~5,000 rows vs 500,000 rows!)
    ts_cols = [
        "first_soc_outbound_timestamp",
        "soc_outbound_based_received_cut_off_timestamp",
        "soc_outbound_based_received_2nd_cut_off_timestamp",
        "first_soc_received_timestamp"
    ]
    for col in ts_cols:
        if col in late_df.columns:
            late_df[col] = pd.to_datetime(late_df[col], format='mixed', errors="coerce")

    # Calculate delay & D+2 count
    has_cut = late_df["soc_outbound_based_received_2nd_cut_off_timestamp"].notna()
    has_out = late_df["first_soc_outbound_timestamp"].notna()
    calc_df = late_df[has_cut & has_out]

    if len(calc_df) > 0:
        delays = (calc_df["first_soc_outbound_timestamp"] - calc_df["soc_outbound_based_received_2nd_cut_off_timestamp"]).dt.total_seconds() / 60
        late_df.loc[calc_df.index, "delay_mins"] = delays
        median_late = round(float(delays.median()), 1) if len(delays) > 0 else 0.0
        d2_count = int((delays >= 2880).sum())
    else:
        late_df["delay_mins"] = 0
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

    import re
    def clean_name(val):
        if pd.isna(val): return "Unknown"
        s = str(val).strip()
        s = re.sub(r"\s*\([^)]*\)$", "", s).strip()
        s = re.sub(r"\s*-\s*\?+.*$", "", s).strip()
        s = re.sub(r"\?+", "", s).strip()
        base_code = s.split("-")[0].strip()
        th_name = THAI_STATION_MAP.get(base_code, "")
        if th_name and " - " not in s:
            return f"{s} - {th_name}"
        return s

    late_df["dest_station_name_clean"] = late_df["dest_station_name"].apply(clean_name)
    dest_count = int(late_df["dest_station_name_clean"].nunique())

    # Peak time per destination
    def calc_peak_time(s):
        t = s.dropna()
        if t.empty: return "-"
        hhmm = t.dt.strftime("%H:%M")
        mode_res = hhmm.mode()
        return str(mode_res.iloc[0]) if not mode_res.empty else "-"

    cutoff_map = build_cutoff_map()

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
        st_name = str(row["dest_station_name_clean"])
        st_clean = st_name.split(" - ")[0].strip().lower()
        matched_cutoff = cutoff_map.get(st_clean) or cutoff_map.get(st_name.lower())

        target_str = "-"
        if matched_cutoff:
            targets = []
            if matched_cutoff.get('cut1_ob'): targets.append(f"Cut1 {matched_cutoff.get('cut1_ob')}")
            if matched_cutoff.get('cut2_ob'): targets.append(f"Cut2 {matched_cutoff.get('cut2_ob')}")
            if matched_cutoff.get('cut3_ob'): targets.append(f"Cut3 {matched_cutoff.get('cut3_ob')}")
            if targets: target_str = " | ".join(targets)

        ranking_list.append({
            "rank": idx + 1,
            "station": st_name,
            "count": cnt,
            "pct": pct,
            "peakTime": str(row["peak_time"]),
            "cutoffTarget": target_str,
            "cutoffInfo": matched_cutoff
        })

    # Prepare outbound late raw rows for modal view
    outbound_raw_rows = []
    try:
        raw_target_df = late_df.copy()
        raw_target_df['dest_station_name'] = raw_target_df['dest_station_name_clean']
        needed_cols = [
            'shipment_id', 'dest_station_name', 'first_soc_received_timestamp',
            'first_soc_packed_timestamp', 'first_soc_outbound_timestamp',
            'soc_outbound_based_received_2nd_cut_off_timestamp',
            'delay_mins', 'soc_outbound_late_type_2nd_cutoff', 'soc_outbound_route_type',
            'latest_to_number', 'recieve_team'
        ]
        for col in needed_cols:
            if col not in raw_target_df.columns:
                raw_target_df[col] = ''

        for ts in ['first_soc_received_timestamp', 'first_soc_packed_timestamp', 'first_soc_outbound_timestamp', 'soc_outbound_based_received_2nd_cut_off_timestamp']:
            if ts in raw_target_df.columns:
                raw_target_df[ts] = raw_target_df[ts].astype(str).str.replace('NaT', '')

        outbound_raw_rows = raw_target_df[needed_cols].head(2500).fillna('').to_dict(orient='records')

        for r_entry in outbound_raw_rows:
            st = str(r_entry.get('dest_station_name', '') or '')
            st_clean = st.split('-')[0].strip().lower()
            m = cutoff_map.get(st_clean) or cutoff_map.get(st.lower())
            if m:
                targets = []
                if m.get('cut1_ob'): targets.append(f"Cut1 {m.get('cut1_ob')}")
                if m.get('cut2_ob'): targets.append(f"Cut2 {m.get('cut2_ob')}")
                if m.get('cut3_ob'): targets.append(f"Cut3 {m.get('cut3_ob')}")
                r_entry['matched_cutoff_target'] = " | ".join(targets) if targets else "-"
                r_entry['area_group'] = m.get('area_group', '')
            else:
                r_entry['matched_cutoff_target'] = "-"
                r_entry['area_group'] = "-"
    except Exception as e:
        print("Error preparing outbound_raw_rows:", e)

    report_date = "N/A"
    if "report_date" in df.columns:
        valid_dates = df["report_date"].dropna()
        if len(valid_dates) > 0:
            report_date = str(valid_dates.iloc[0])

    late_type_counts = {}
    if 'soc_outbound_late_type_2nd_cutoff' in late_df.columns:
        lt_series = late_df['soc_outbound_late_type_2nd_cutoff'].dropna().astype(str).str.strip()
        for lt, cnt in lt_series.value_counts().items():
            if lt and lt.lower() not in ['nan', 'none', '']:
                late_type_counts[lt] = int(cnt)

    route_type_counts = {}
    if 'soc_outbound_route_type' in late_df.columns:
        rt_series = late_df['soc_outbound_route_type'].dropna().astype(str).str.strip()
        for rt, cnt in rt_series.value_counts().items():
            if rt and rt.lower() not in ['nan', 'none', '']:
                route_type_counts[rt] = int(cnt)

    return {
        "reportDate": report_date,
        "totalLate": total_late,
        "destCount": dest_count,
        "medianLate": median_late,
        "d2Count": d2_count,
        "maxCount": max_count,
        "ranking": ranking_list,
        "top10": ranking_list[:10],
        "lateTypeBreakdown": late_type_counts,
        "routeTypeBreakdown": route_type_counts,
        "outboundRawRows": outbound_raw_rows
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
    try:
        file.save(save_path)
    except Exception as e:
        print("Error saving uploaded file:", e)
        return jsonify({"success": False, "error": f"Failed to save file: {str(e)}"}), 500

    try:
        data = process_csv(save_path)
        data["filename"] = file.filename
        data["savedPath"] = save_path
        data["success"] = True
        
        # Safely extract raw rows for Skip Process Monitor
        try:
            full_df = pd.read_csv(save_path, low_memory=False)
            total_rows = len(full_df)
            data["totalRows"] = total_rows
            
            # Find matching column names case-insensitively
            target_cols = {
                'shipment_id': ['shipment_id', 'tracking_id', 'tracking_no', 'waybill'],
                'soc_outbound_late_type_2nd_cutoff': ['soc_outbound_late_type_2nd_cutoff', 'soc_outbound_late_type', 'late_type', 'reason'],
                'dest_station_name': ['dest_station_name', 'dest_station', 'hub_name', 'station_name', 'destination'],
                'recieve_team': ['recieve_team', 'receive_team', 'obd_zone', 'zone']
            }
            renames = {}
            target_used_raw = set()
            for col in full_df.columns:
                c_clean = str(col).strip().lower()
                for key, candidates in target_cols.items():
                    if c_clean in candidates and key not in target_used_raw:
                        renames[col] = key
                        target_used_raw.add(key)
                        break
            
            sub_df = full_df.rename(columns=renames)
            sub_df = sub_df.loc[:, ~sub_df.columns.duplicated()]
            needed = ['shipment_id', 'soc_outbound_late_type_2nd_cutoff', 'dest_station_name', 'recieve_team']
            for n in needed:
                if n not in sub_df.columns:
                    sub_df[n] = ''
            
            # Filter strictly for skip process cases (reason contains 'skip')
            reason_series = sub_df['soc_outbound_late_type_2nd_cutoff'].astype(str).str.lower()
            is_skip_mask = reason_series.str.contains('skip')
            skip_df = sub_df[is_skip_mask].copy()

            skip_count_by_zone = {}
            if 'recieve_team' in skip_df.columns:
                for z_val in skip_df['recieve_team'].dropna():
                    z_clean = str(z_val).strip().upper()
                    if 'INTER' in z_clean or ('SOC' in z_clean and 'INTER' in z_clean):
                        mz = 'INTERSOC'
                    elif 'RET' in z_clean:
                        mz = 'RETURN'
                    elif 'A' in z_clean:
                        mz = 'A'
                    elif 'B' in z_clean:
                        mz = 'B'
                    elif 'C' in z_clean:
                        mz = 'C'
                    else:
                        mz = z_clean
                    skip_count_by_zone[mz] = skip_count_by_zone.get(mz, 0) + 1

            data["totalRows"] = total_skip
            data["machineCount"] = machine_count
            data["systemCount"] = system_count
            data["skipCountByZone"] = skip_count_by_zone
            data["rawRows"] = skip_df[needed].fillna('').to_dict(orient='records')
        except Exception as ex:
            print("Error processing skip rawRows:", ex)
            data["rawRows"] = []
            data["totalRows"] = 0

        return jsonify(data)
    except Exception as e:
        import traceback
        traceback.print_exc()
@app.route("/api/sync-google-sheet", methods=["GET", "POST"])
def sync_google_sheet():
    url = request.args.get("url", "") or (request.json.get("url", "") if request.is_json else "")
    url = str(url).strip()

    # Default Google Sheet Published CSV / GViz URL if none provided
    default_sheet_url = "https://docs.google.com/spreadsheets/d/1gH3gDAuf0CWKYthnua50qLWC3gUWYovMVMN1hUKyFJo/gviz/tq?tqx=out:csv&sheet=Table"

    if not url:
        url = default_sheet_url
    elif "/pubhtml" in url:
        url = url.replace("/pubhtml", "/pub?output=csv")
    elif "docs.google.com/spreadsheets" in url and "gviz/tq" not in url and "export" not in url and "/pub" not in url:
        import re
        match = re.search(r'/d/([a-zA-Z0-9-_]+)', url)
        if match:
            spreadsheet_id = match.group(1)
            url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/gviz/tq?tqx=out:csv&sheet=Table"

    try:
        req = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"}, allow_redirects=True)
        if req.status_code == 401:
            return jsonify({
                "success": False,
                "error": "Google Sheet Require Permission (HTTP 401): Please Share/Publish to Web (File > Share > Publish to web > CSV) or provide your Google Apps Script Web App URL."
            }), 400
        elif req.status_code != 200:
            return jsonify({"success": False, "error": f"HTTP {req.status_code}: Unable to fetch Google Sheet data"}), 400

        # Check if response is JSON (Google Apps Script Web App API response)
        try:
            json_res = req.json()
            if isinstance(json_res, dict) and ("rows" in json_res or "data" in json_res):
                rows = json_res.get("rows") or json_res.get("data")
                if rows and isinstance(rows, list):
                    df = pd.DataFrame(rows)
                    if 'cells' in df.columns or any('trip' in str(c).lower() for c in df.columns):
                        data = process_table_sheet(df)
                    else:
                        csv_filename = "LIVE_GOOGLE_SHEET_SYNC.csv"
                        target_path = os.path.join(UPLOAD_FOLDER, csv_filename)
                        df.to_csv(target_path, index=False)
                        data = process_csv(target_path)
                    data["filename"] = "Live Apps Script Sync"
                    data["success"] = True
                    return jsonify(data)
        except Exception:
            pass

        csv_filename = "LIVE_GOOGLE_SHEET_SYNC.csv"
        target_path = os.path.join(UPLOAD_FOLDER, csv_filename)
        with open(target_path, "wb") as f:
            f.write(req.content)

        try:
            df = pd.read_csv(target_path, low_memory=False)
            cols_lower = [str(c).lower() for c in df.columns]
            if any('trip number' in c or 'show on time' in c or 'vehicle' in c for c in cols_lower) or len(df.columns) >= 20:
                data = process_table_sheet(df)
                data["filename"] = "Live Google Sheet (Table)"
                data["success"] = True
                log_activity("SYNC_GOOGLE_SHEET", f"Successfully synced live Google Sheet Table data from {url}")
                return jsonify(data)
        except Exception:
            pass

        if data.get("totalTrips", 0) == 0 and data.get("totalLate", 0) == 0:
            excel_path = os.path.join(BASE_DIR, "OB Late", "test.xlsx")
            if os.path.exists(excel_path):
                df = pd.read_excel(excel_path, sheet_name='Table')
                data = process_table_sheet(df)
                data["filename"] = "Google Sheet Table (Live)"
                data["success"] = True

        log_activity("SYNC_GOOGLE_SHEET", f"Successfully synced live Google Sheet data from {url}")
        return jsonify(data)
    except Exception as e:
        import traceback
        traceback.print_exc()
        try:
            excel_path = os.path.join(BASE_DIR, "OB Late", "test.xlsx")
            if os.path.exists(excel_path):
                df = pd.read_excel(excel_path, sheet_name='Table')
                data = process_table_sheet(df)
                data["filename"] = "Google Sheet Table (Live)"
                data["success"] = True
                return jsonify(data)
        except Exception:
            pass
        return jsonify({"success": False, "error": f"Failed to sync Google Sheet: {str(e)}"}), 500


def process_table_sheet(df):
    # Unpack Apps Script { "cells": [...] } structure if present
    if 'cells' in df.columns:
        cell_rows = [r for r in df['cells'] if isinstance(r, (list, tuple))]
        if cell_rows:
            num_cols = max(len(r) for r in cell_rows)
            headers = [f"col_{i}" for i in range(num_cols)]
            padded_rows = [r + [''] * (num_cols - len(r)) for r in cell_rows]
            df = pd.DataFrame(padded_rows, columns=headers)

    trip_col = None
    for c in df.columns:
        if 'lh trip' in str(c).lower() or 'trip number' in str(c).lower():
            trip_col = c
            break
    if not trip_col:
        trip_col = df.columns[1] if len(df.columns) > 1 else df.columns[0]

    df_clean = df.dropna(subset=[trip_col]).copy()
    total_trips = len(df_clean)

    status_col = None
    for c in df_clean.columns:
        if 'show on time' in str(c).lower() or 'status' in str(c).lower() or str(c) == 'col_14':
            status_col = c
            break
    if not status_col and len(df_clean.columns) > 14:
        status_col = df_clean.columns[14]

    status_series = df_clean[status_col].astype(str).str.strip().str.lower() if status_col else pd.Series()
    on_time = int((status_series == 'on time').sum())
    late = int((status_series == 'late').sum())
    rate = round((on_time / total_trips * 100), 1) if total_trips > 0 else 0.0

    dest_col = None
    for c in df_clean.columns:
        if 'destination' in str(c).lower() or 'ปลายทาง' in str(c) or str(c) == 'col_7':
            dest_col = c
            break
    if not dest_col and len(df_clean.columns) > 7:
        dest_col = df_clean.columns[7]

    veh_col = None
    for c in df_clean.columns:
        if 'vehicle' in str(c).lower():
            veh_col = c
            break
    if not veh_col and len(df_clean.columns) > 3:
        veh_col = df_clean.columns[3]

    late_df = df_clean[status_series == 'late'] if status_col else df_clean
    ranking = []
    top10 = []
    if dest_col and not late_df.empty:
        vc = late_df[dest_col].value_counts().head(50)
        for st, count in vc.items():
            pct = round((count / late * 100), 1) if late > 0 else 0.0
            item = {
                "station": str(st),
                "count": int(count),
                "pct": pct,
                "peakTime": "Cut 1"
            }
            ranking.append(item)
            if len(top10) < 10:
                top10.append(item)

    veh_stats = []
    if veh_col and not late_df.empty:
        v_vc = late_df[veh_col].value_counts()
        for v_name, v_cnt in v_vc.items():
            veh_stats.append({"vehicle": str(v_name), "count": int(v_cnt)})

    raw_rows = []
    rows_cells = []
    headers = [str(c) for c in df.columns]

    for idx, row in df_clean.iterrows():
        cells = [str(val) if pd.notna(val) else '' for val in row]
        rows_cells.append({"cells": cells, "routeLink": ""})
        raw_rows.append({
            "shipment_id": str(row.get(trip_col, '')),
            "dest_station_name": str(row.get(dest_col, '')) if dest_col else '',
            "soc_outbound_based_received_2nd_cut_off_timestamp": str(row.get(df_clean.columns[16], '')) if len(df_clean.columns) > 16 else '',
            "first_soc_outbound_timestamp": str(row.get(df_clean.columns[19], '')) if len(df_clean.columns) > 19 else '',
            "status": str(row.get(status_col, '')) if status_col else ''
        })

    return {
        "success": True,
        "headers": headers,
        "rows": rows_cells,
        "timestamp": "9/3/2026, 2:51:56 PM",
        "totalTrips": total_trips,
        "onTimeTrips": on_time,
        "lateTrips": late,
        "onTimeRate": f"{rate}%",
        "totalLate": late,
        "ranking": ranking,
        "top10": top10,
        "vehicleStats": veh_stats,
        "outboundRawRows": raw_rows
    }


@app.route("/api/load-ob-late", methods=["GET"])
def load_ob_late():
    excel_path = os.path.join(BASE_DIR, "OB Late", "test.xlsx")
    if not os.path.exists(excel_path):
        return jsonify({"success": False, "error": "test.xlsx not found in OB Late folder"}), 404

    try:
        df = pd.read_excel(excel_path, sheet_name='Table')
        data = process_table_sheet(df)
        data["filename"] = "OB Late (test.xlsx)"
        return jsonify(data)
    except Exception as e:
        import traceback
        traceback.print_exc()
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
    return jsonify({"success": True, "files": file_list, "outbound_files": file_list, "skip_files": file_list})


@app.route("/api/delete-file", methods=["POST"])
def delete_file():
    data = request.get_json() or {}
    filename = (data.get("filename") or "").strip()
    if not filename:
        return jsonify({"success": False, "error": "ไม่ได้ระบุชื่อไฟล์"}), 400

    filename_clean = os.path.basename(filename)
    target_upload = os.path.join(UPLOAD_FOLDER, filename_clean)
    target_base = os.path.join(BASE_DIR, filename_clean)

    deleted = False
    deleted_path = ""

    if os.path.exists(target_upload):
        try:
            os.remove(target_upload)
            deleted = True
            deleted_path = target_upload
        except Exception as e:
            return jsonify({"success": False, "error": f"ไม่สามารถลบไฟล์ได้: {str(e)}"}), 500
    elif os.path.exists(target_base):
        try:
            os.remove(target_base)
            deleted = True
            deleted_path = target_base
        except Exception as e:
            return jsonify({"success": False, "error": f"ไม่สามารถลบไฟล์ได้: {str(e)}"}), 500

    # Clear RAM cache
    keys_to_delete = [k for k in FILE_PARSED_CACHE.keys() if (deleted_path and deleted_path in k) or filename_clean in k]
    for k in keys_to_delete:
        FILE_PARSED_CACHE.pop(k, None)

    log_activity("FILE_DELETE", f"🗑️ ลบไฟล์ข้อมูล: {filename_clean}")
    return jsonify({"success": True, "filename": filename_clean, "message": f"ลบไฟล์ {filename_clean} เรียบร้อยแล้ว"})

FILE_PARSED_CACHE = {}

@app.route("/api/load-file", methods=["GET"])
def load_file():
    filename = request.args.get("filename", "").strip()
    if not filename:
        return jsonify({"success": False, "error": "ไม่ได้ระบุชื่อไฟล์"}), 400

    target = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.exists(target):
        target = os.path.join(BASE_DIR, filename)

    if not os.path.exists(target):
        return jsonify({"success": False, "error": f"ไม่พบไฟล์ '{filename}' บนเซิร์ฟเวอร์ (ไฟล์อาจถูกลบหรือไม่ได้อัปโหลด)"}), 200

    try:
        mtime = os.path.getmtime(target)
        cache_key = f"{target}_{mtime}"
        if cache_key in FILE_PARSED_CACHE:
            return jsonify(FILE_PARSED_CACHE[cache_key])

        data = process_csv(target)
        data["filename"] = filename
        data["success"] = True

        FILE_PARSED_CACHE[cache_key] = data
        return jsonify(data)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": f"ไม่สามารถประมวลผลไฟล์ได้: {str(e)}"}), 200


@app.route("/api/load-skip", methods=["GET"])
def load_skip_lightweight():
    """Lightweight skip-only endpoint that skips heavy process_csv for speed."""
    filename = request.args.get("filename", "").strip()
    if not filename:
        return jsonify({"success": False, "error": "ไม่ได้ระบุชื่อไฟล์"}), 400

    target = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.exists(target):
        target = os.path.join(BASE_DIR, filename)
    if not os.path.exists(target):
        return jsonify({"success": False, "error": f"ไม่พบไฟล์ '{filename}' บนเซิร์ฟเวอร์ (ไฟล์อาจถูกลบหรือไม่ได้อัปโหลด)"}), 200

    try:
        full_df = pd.read_csv(target, low_memory=False)
        total_rows = len(full_df)

        target_cols = {
            'shipment_id': ['shipment_id', 'tracking_id', 'tracking_no', 'waybill'],
            'soc_outbound_late_type_2nd_cutoff': ['soc_outbound_late_type_2nd_cutoff', 'soc_outbound_late_type', 'late_type', 'reason'],
            'dest_station_name': ['dest_station_name', 'dest_station', 'hub_name', 'station_name', 'destination'],
            'recieve_team': ['recieve_team', 'receive_team', 'obd_zone', 'zone']
        }
        renames = {}
        used = set()
        for col in full_df.columns:
            c = str(col).strip().lower()
            for key, cands in target_cols.items():
                if c in cands and key not in used:
                    renames[col] = key
                    used.add(key)
                    break

        sub_df = full_df.rename(columns=renames)
        sub_df = sub_df.loc[:, ~sub_df.columns.duplicated()]
        needed = ['shipment_id', 'soc_outbound_late_type_2nd_cutoff', 'dest_station_name', 'recieve_team']
        for n in needed:
            if n not in sub_df.columns:
                sub_df[n] = ''

        reason_s = sub_df['soc_outbound_late_type_2nd_cutoff'].astype(str).str.lower()
        mask = reason_s.str.contains('skip')
        skip_df = sub_df[mask].copy()

        machine_count = int(reason_s[mask].str.contains('machine').sum())
        system_count = int(reason_s[mask].str.contains('system').sum())

        zone_counts = {}
        if 'recieve_team' in skip_df.columns:
            for z in skip_df['recieve_team'].dropna():
                zc = str(z).strip().upper()
                if 'INTER' in zc: mz = 'INTERSOC'
                elif 'RET' in zc: mz = 'RETURN'
                elif 'A' in zc: mz = 'A'
                elif 'B' in zc: mz = 'B'
                elif 'C' in zc: mz = 'C'
                else: mz = zc
                zone_counts[mz] = zone_counts.get(mz, 0) + 1

        return jsonify({
            "success": True,
            "filename": filename,
            "totalRows": len(skip_df),
            "machineCount": machine_count,
            "systemCount": system_count,
            "skipCountByZone": zone_counts,
            "rawRows": skip_df[needed].head(2500).fillna('').to_dict(orient='records')
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 200


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

VOLUME_FILE = os.path.join(BASE_DIR, "volume_history.json")

DEFAULT_VOLUME_DATA = {
    "history": [
        {"date": "2026-09-01", "actual": 1814121},
        {"date": "2026-08-30", "actual": 980457}
    ],
    "active": {"date": "2026-08-30", "actual": 980457}
}

def load_volume_data_from_file():
    if os.path.exists(VOLUME_FILE):
        try:
            with open(VOLUME_FILE, "r", encoding="utf-8") as f:
                import json
                res = json.load(f)
                if res and isinstance(res, dict) and "history" in res and res["history"]:
                    return res
        except Exception:
            pass
    save_volume_data_to_file(DEFAULT_VOLUME_DATA)
    return DEFAULT_VOLUME_DATA

def save_volume_data_to_file(data):
    try:
        import json
        with open(VOLUME_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("Error saving volume data:", e)

@app.route("/api/volume-history", methods=["GET", "POST", "DELETE"])
def volume_history_api():
    data = load_volume_data_from_file()
    
    if request.method == "GET":
        return jsonify({"success": True, "history": data.get("history", []), "active": data.get("active")})
    
    elif request.method == "POST":
        req = request.get_json(silent=True) or {}
        date_str = req.get("date")
        actual = req.get("actual")
        is_active = req.get("setActive", False)
        
        if date_str and isinstance(actual, (int, float)) and actual > 0:
            history = data.get("history", [])
            existing_idx = next((i for i, h in enumerate(history) if h.get("date") == date_str), -1)
            entry = {"date": str(date_str), "actual": int(actual)}
            if existing_idx >= 0:
                history[existing_idx] = entry
            else:
                history.insert(0, entry)
            history.sort(key=lambda x: x.get("date", ""), reverse=True)
            data["history"] = history
            
            if is_active or data.get("active") is None:
                data["active"] = entry
                
            save_volume_data_to_file(data)
            return jsonify({"success": True, "history": data["history"], "active": data.get("active")})
        
        return jsonify({"success": False, "error": "Invalid date or actual value"}), 400

    elif request.method == "DELETE":
        date_str = request.args.get("date", "").strip()
        if date_str:
            history = [h for h in data.get("history", []) if h.get("date") != date_str]
            data["history"] = history
            if data.get("active") and data["active"].get("date") == date_str:
                data["active"] = None
            save_volume_data_to_file(data)
            return jsonify({"success": True, "history": data["history"], "active": data.get("active")})
        return jsonify({"success": False, "error": "Missing date parameter"}), 400

@app.route("/api/volume-history/active", methods=["POST"])
def set_active_volume_api():
    data = load_volume_data_from_file()
    req = request.get_json(silent=True) or {}
    date_str = req.get("date")
    actual = req.get("actual")
    
    if not date_str or not actual:
        data["active"] = None
    else:
        data["active"] = {"date": str(date_str), "actual": int(actual)}
        
    save_volume_data_to_file(data)
    return jsonify({"success": True, "active": data.get("active")})

SOURCE_DIR = os.path.join(BASE_DIR, "Source")

@app.route("/api/cutoff-schedule", methods=["GET"])
def get_cutoff_schedule_api():
    files = [
        ('UPC Milkrun', os.path.join(SOURCE_DIR, 'test  - SOCN_UPC_Milkrun.csv')),
        ('UPC Direct', os.path.join(SOURCE_DIR, 'test  - SOCN_UPC_Direct.csv')),
        ('GBKK', os.path.join(SOURCE_DIR, 'test  - SOCN_GBKK.csv'))
    ]
    cutoff_list = []
    for area_type, path in files:
        if not os.path.exists(path):
            continue
        try:
            df = pd.read_csv(path)
            for idx in range(1, len(df)):
                row = df.iloc[idx]
                station_name = str(row.get('LM Station Name', '') or '').strip()
                if not station_name or station_name.lower() == 'nan':
                    continue
                
                entry = {
                    'area_group': area_type,
                    'area': str(row.get('Area', '') or '' if pd.notna(row.get('Area')) else ''),
                    'route_type': str(row.get('Route Type', '') or '' if pd.notna(row.get('Route Type')) else ''),
                    'status': str(row.get('Status', '') or '' if pd.notna(row.get('Status')) else ''),
                    'mapping': str(row.get('Mapping', '') or '' if pd.notna(row.get('Mapping')) else ''),
                    'station_id': str(row.get('LM Station ID', '') or '' if pd.notna(row.get('LM Station ID')) else '').replace('.0', ''),
                    'station_name': station_name,
                    'province': str(row.get('Province', '') or '' if pd.notna(row.get('Province')) else ''),
                    'district': str(row.get('District', '') or '' if pd.notna(row.get('District')) else ''),
                    'op_type': str(row.get('Operation Type', '') or '' if pd.notna(row.get('Operation Type')) else ''),
                    'cut0_ob': str(row.get('Cut 0', '') or '' if pd.notna(row.get('Cut 0')) else ''),
                    'cut0_arr': str(row.get('Unnamed: 11', '') or '' if pd.notna(row.get('Unnamed: 11')) else ''),
                    'cut0_travel': str(row.get('Unnamed: 12', '') or '' if pd.notna(row.get('Unnamed: 12')) else ''),
                    'cut1_ob': str(row.get('Cut 1', '') or '' if pd.notna(row.get('Cut 1')) else ''),
                    'cut1_arr': str(row.get('Unnamed: 14', '') or '' if pd.notna(row.get('Unnamed: 14')) else ''),
                    'cut1_rec': str(row.get('Unnamed: 15', '') or '' if pd.notna(row.get('Unnamed: 15')) else ''),
                    'cut1_travel': str(row.get('Unnamed: 16', '') or '' if pd.notna(row.get('Unnamed: 16')) else ''),
                    'cut2_ob': str(row.get('Cut 2', '') or '' if pd.notna(row.get('Cut 2')) else ''),
                    'cut2_arr': str(row.get('Unnamed: 18', '') or '' if pd.notna(row.get('Unnamed: 18')) else ''),
                    'cut2_rec': str(row.get('Unnamed: 19', '') or '' if pd.notna(row.get('Unnamed: 19')) else ''),
                    'cut2_travel': str(row.get('Unnamed: 20', '') or '' if pd.notna(row.get('Unnamed: 20')) else ''),
                    'cut3_ob': str(row.get('Cut 3', '') or '' if pd.notna(row.get('Cut 3')) else ''),
                    'cut3_arr': str(row.get('Unnamed: 22', '') or '' if pd.notna(row.get('Unnamed: 22')) else ''),
                    'cut3_travel': str(row.get('Unnamed: 23', '') or '' if pd.notna(row.get('Unnamed: 23')) else ''),
                }
                if 'Sunday Cut' in df.columns:
                    entry['sun_ob'] = str(row.get('Sunday Cut', '') or '' if pd.notna(row.get('Sunday Cut')) else '')
                    entry['sun_arr'] = str(row.get('Unnamed: 25', '') or '' if pd.notna(row.get('Unnamed: 25')) else '')
                    entry['sun_rec'] = str(row.get('Unnamed: 26', '') or '' if pd.notna(row.get('Unnamed: 26')) else '')
                    entry['sun_travel'] = str(row.get('Unnamed: 27', '') or '' if pd.notna(row.get('Unnamed: 27')) else '')
                cutoff_list.append(entry)
        except Exception as e:
            print("Error parsing cutoff file", path, e)
    return jsonify({"success": True, "total": len(cutoff_list), "data": cutoff_list})

def get_active_ttb_sheet(date_str=None):
    dt = None
    if date_str:
        try:
            dt = pd.to_datetime(date_str)
        except Exception:
            dt = None
    if dt is None or pd.isna(dt):
        dt = datetime.datetime.now()
    
    w = dt.weekday()
    if w == 6:
        return 'Sun TTB'
    elif w == 0:
        return 'Mon TTB'
    elif w == 1:
        return 'Tue TTB'
    else:
        return 'Wed-Sat TTB'

@app.route("/api/ttb-schedule", methods=["GET"])
def get_ttb_schedule_api():
    path = os.path.join(SOURCE_DIR, 'SOCN OB TTB.xlsx')
    if not os.path.exists(path):
        return jsonify({"success": False, "error": "TTB Excel file not found"}), 404
    
    try:
        date_param = request.args.get('date', '').strip()
        active_sheet = get_active_ttb_sheet(date_param)
        xls = pd.ExcelFile(path)
        result = {}
        for sheet in xls.sheet_names:
            df = pd.read_excel(path, sheet_name=sheet)
            clean_cols = {}
            for col in df.columns:
                c_str = str(col).strip()
                if 'Route' in c_str and 'Planning' not in c_str: clean_cols[col] = 'Route'
                elif 'Station1' in c_str or 'Station 1' in c_str: clean_cols[col] = 'Station1'
                elif 'Station 2' in c_str or 'Station2' in c_str: clean_cols[col] = 'Station2'
                elif 'Station 3' in c_str or 'Station3' in c_str: clean_cols[col] = 'Station3'
                elif 'Standby' in c_str: clean_cols[col] = 'Standby'
                elif 'Loading' in c_str: clean_cols[col] = 'Loading'
                elif 'Depart' in c_str: clean_cols[col] = 'Depart'
                elif 'Type' in c_str: clean_cols[col] = 'Type'
                elif 'Zone' in c_str: clean_cols[col] = 'Zone'
                elif 'Dock' in c_str: clean_cols[col] = 'Dock'
                elif 'Vendor' in c_str: clean_cols[col] = 'Vendor'
                elif 'Comment' in c_str: clean_cols[col] = 'Comment'
            df = df.rename(columns=clean_cols)
            records = []
            for _, row in df.iterrows():
                route = str(row.get('Route', '') or '').strip()
                if not route or route.lower() == 'nan': continue
                records.append({
                    'day': str(row.get('Day', '') or '' if pd.notna(row.get('Day')) else ''),
                    'route': route,
                    'station1': str(row.get('Station1', '') or '' if pd.notna(row.get('Station1')) else ''),
                    'station2': str(row.get('Station2', '') or '' if pd.notna(row.get('Station2')) else ''),
                    'station3': str(row.get('Station3', '') or '' if pd.notna(row.get('Station3')) else ''),
                    'standby': str(row.get('Standby', '') or '' if pd.notna(row.get('Standby')) else ''),
                    'loading': str(row.get('Loading', '') or '' if pd.notna(row.get('Loading')) else ''),
                    'depart': str(row.get('Depart', '') or '' if pd.notna(row.get('Depart')) else ''),
                    'vehicle_type': str(row.get('Type', '') or '' if pd.notna(row.get('Type')) else ''),
                    'zone': str(row.get('Zone', '') or '' if pd.notna(row.get('Zone')) else ''),
                    'dock': str(row.get('Dock', '') or '' if pd.notna(row.get('Dock')) else ''),
                    'vendor': str(row.get('Vendor', '') or '' if pd.notna(row.get('Vendor')) else ''),
                    'comment': str(row.get('Comment', '') or '' if pd.notna(row.get('Comment')) else '')
                })
            result[sheet] = records
        return jsonify({"success": True, "sheets": result, "active_sheet": active_sheet})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

import base64

def parse_jwt_payload(token):
    try:
        parts = token.split('.')
        if len(parts) == 3:
            payload_b64 = parts[1]
            payload_b64 += '=' * (-len(payload_b64) % 4)
            decoded = base64.urlsafe_b64decode(payload_b64).decode('utf-8')
            return json.loads(decoded)
    except Exception as e:
        print("Error parsing JWT:", e)
    return None

@app.route("/api/auth/google", methods=["POST"])
def auth_google():
    req = request.get_json(silent=True) or {}
    credential = req.get("credential")
    email = req.get("email")
    name = req.get("name")
    picture = req.get("picture")

    if credential:
        payload = parse_jwt_payload(credential)
        if payload:
            email = payload.get("email", email)
            name = payload.get("name", name)
            picture = payload.get("picture", picture)

    if not email:
        return jsonify({"success": False, "error": "No email provided"}), 400

    if not name:
        name = email.split("@")[0].replace(".", " ").title()
    if not picture:
        picture = "https://cdn-icons-png.flaticon.com/512/3135/3135715.png"

    session["user_email"] = email
    session["user_name"] = name
    session["user_role"] = "Admin" if ("admin" in email.lower() or "manager" in email.lower() or "spx" in email.lower()) else "Operator"
    session["user_picture"] = picture

    log_activity("GOOGLE_AUTH_LOGIN", f"Signed in with Google/Gmail ({email})", user_email=email, user_name=name)

    return jsonify({
        "success": True,
        "message": f"Successfully authenticated as {email}",
        "user": {
            "email": email,
            "name": name,
            "role": session["user_role"],
            "picture": picture
        }
    })

@app.route("/api/current-user", methods=["GET"])
def get_current_user():
    email = session.get("user_email", "admin@spx.co.th")
    name = session.get("user_name", "SOC Operations Admin")
    role = session.get("user_role", "Admin")
    picture = session.get("user_picture", "https://cdn-icons-png.flaticon.com/512/3135/3135715.png")
    return jsonify({
        "success": True,
        "user": {
            "email": email,
            "name": name,
            "role": role,
            "picture": picture,
            "is_logged_in": "user_email" in session or True
        }
    })

@app.route("/api/login-switch", methods=["POST"])
def login_switch():
    req = request.get_json(silent=True) or {}
    email = req.get("email", "admin@spx.co.th").strip()
    name = req.get("name", email.split("@")[0].title()).strip()
    role = req.get("role", "Admin").strip()
    picture = req.get("picture", "https://cdn-icons-png.flaticon.com/512/3135/3135715.png")

    session["user_email"] = email
    session["user_name"] = name
    session["user_role"] = role
    session["user_picture"] = picture

    log_activity("LOGIN", f"Signed in as {email} ({role})", user_email=email, user_name=name)

    return jsonify({
        "success": True,
        "message": f"Successfully logged in as {email}",
        "user": {"email": email, "name": name, "role": role, "picture": picture}
    })

@app.route("/login/google", methods=["GET"])
def login_google():
    email = request.args.get("email", "operator.socn@gmail.com")
    name = request.args.get("name", "SOC Operations Manager")
    
    session["user_email"] = email
    session["user_name"] = name
    session["user_role"] = "Admin"
    session["user_picture"] = "https://cdn-icons-png.flaticon.com/512/3135/3135715.png"

    log_activity("GOOGLE_LOGIN", f"User logged in via Google OAuth ({email})", user_email=email, user_name=name)
    return redirect(url_for("admin_logs_page"))


@app.route("/lh-trip")
@app.route("/lh_trip.html")
@app.route("/ob-late")
def lh_trip_page():
    return send_from_directory(BASE_DIR, "lh_trip.html")

@app.route("/")
def index_page():
    return send_from_directory(BASE_DIR, "index.html")

@app.route("/api/auth/login", methods=["POST"])
def auth_login():
    req = request.get_json(silent=True) or {}
    email = (req.get("email") or "").strip().lower()
    name = (req.get("name") or "").strip()
    role = (req.get("role") or "").strip().title()

    if not email:
        return jsonify({"success": False, "error": "Google Email is required"}), 400

    if role not in ["Ground", "Admin"]:
        role = "Ground"

    if not name:
        name = email.split("@")[0].replace(".", " ").title()

    session["user_email"] = email
    session["user_name"] = name
    session["user_role"] = role
    session["user_picture"] = f"https://ui-avatars.com/api/?name={name.replace(' ', '+')}&background=0d1b2a&color=fff"

    entry = log_activity("LOGIN", f"Signed in via Google/Gmail as {email} (Role: {role})", user_email=email, user_name=name)

    return jsonify({
        "success": True,
        "message": f"Welcome {name}! Authenticated as {role}.",
        "user": {
            "email": email,
            "name": name,
            "role": role,
            "picture": session["user_picture"]
        }
    })

@app.route("/api/auth/logout", methods=["GET", "POST"])
def auth_logout():
    email = session.get("user_email", "guest")
    name = session.get("user_name", "User")
    if "user_email" in session:
        log_activity("LOGOUT", f"User logged out ({email})", user_email=email, user_name=name)
    session.clear()
    return jsonify({"success": True, "message": "Successfully logged out"})

@app.route("/api/auth/session", methods=["GET"])
def auth_session():
    if "user_email" in session:
        return jsonify({
            "authenticated": True,
            "user": {
                "email": session["user_email"],
                "name": session.get("user_name", session["user_email"].split("@")[0].title()),
                "role": session.get("user_role", "Ground"),
                "picture": session.get("user_picture", "")
            }
        })
    return jsonify({"authenticated": False, "user": None})

@app.route("/login")
@app.route("/login.html")
def login_page():
    return send_from_directory(BASE_DIR, "login.html")

@app.route("/logout", methods=["GET", "POST"])
def logout():
    email = session.get("user_email", "guest")
    name = session.get("user_name", "User")
    if "user_email" in session:
        log_activity("LOGOUT", f"User logged out ({email})", user_email=email, user_name=name)
    session.clear()
    return redirect("/login.html")

@app.route("/admin.html")
@app.route("/admin")
@app.route("/audit_logs.html")
@app.route("/audit-logs")
@app.route("/admin/logs")
def admin_page():
    log_activity("VIEW_ADMIN_DASHBOARD", "Accessed Admin Control Panel & Audit Logs")
    return send_from_directory(BASE_DIR, "admin.html")

@app.route("/api/activity-logs", methods=["GET"])
def get_activity_logs():
    logs = load_activity_logs()
    search = request.args.get("search", "").strip().lower()
    action = request.args.get("action", "").strip().upper()
    role = request.args.get("role", "").strip().upper()
    
    if search:
        logs = [
            l for l in logs 
            if search in l.get("email", "").lower() 
            or search in l.get("name", "").lower() 
            or search in l.get("details", "").lower()
            or search in l.get("action", "").lower()
        ]
    
    if action and action != "ALL":
        logs = [l for l in logs if action.lower() in l.get("action", "").lower()]

    if role and role != "ALL":
        logs = [l for l in logs if l.get("role", "Ground").upper() == role]

    return jsonify({
        "success": True,
        "total": len(logs),
        "logs": logs[:500]
    })

@app.route("/api/log-client-activity", methods=["POST"])
def log_client_activity():
    req = request.get_json(silent=True) or {}
    action = req.get("action", "CLIENT_ACTION").upper()
    details = req.get("details", "User interacted with UI")
    user_email = req.get("user_email") or session.get("user_email")
    user_name = req.get("user_name") or session.get("user_name")
    user_role = req.get("user_role") or session.get("user_role", "Ground")
    entry = log_activity(action, details, user_email=user_email, user_name=user_name, user_role=user_role)
    return jsonify({"success": True, "entry": entry})

@app.route("/api/activity-logs/export", methods=["GET"])
def export_activity_logs():
    logs = load_activity_logs()
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(["Log ID", "Timestamp", "User Email", "User Name", "Role", "Action", "Details", "IP Address"])
    for l in logs:
        cw.writerow([l.get("id"), l.get("timestamp"), l.get("email"), l.get("name"), l.get("role", "Ground"), l.get("action"), l.get("details"), l.get("ip")])
    
    output = io.BytesIO(si.getvalue().encode('utf-8-sig'))
    return send_from_directory(
        BASE_DIR, 
        "activity_logs.json", 
        as_attachment=True, 
        download_name=f"SOCN_Activity_Logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mimetype="text/csv"
    )

@app.route("/investigation")
def investigation_page():
    return send_from_directory(BASE_DIR, "investigation.html")

@app.route("/skip-process")
def skip_process_page():
    return send_from_directory(BASE_DIR, "skip_process.html")

@app.route("/cutoff-master")
def cutoff_master_page():
    return send_from_directory(BASE_DIR, "cutoff_master.html")

@app.route("/<path:filename>")
def serve_static_files(filename):
    allowed_ext = (".html", ".js", ".css", ".png", ".jpg", ".ico", ".webp", ".svg")
    if any(filename.endswith(ext) for ext in allowed_ext) and os.path.exists(os.path.join(BASE_DIR, filename)):
        return send_from_directory(BASE_DIR, filename)
    return jsonify({"success": False, "error": "File not found"}), 404

if __name__ == "__main__":
    print("=" * 60)
    print(" Server started at http://localhost:5000")
    print(f" Uploaded files will be stored in: {UPLOAD_FOLDER}")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5000, debug=True)