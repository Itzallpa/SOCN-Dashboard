# -*- coding: utf-8 -*-
import os
import sys
import re
import json
import uuid
import time
import random
import urllib.parse
import csv
import io
import warnings
import requests
import pandas as pd
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory, session, redirect, url_for
from werkzeug.middleware.proxy_fix import ProxyFix

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

warnings.filterwarnings("ignore")

app = Flask(__name__, static_folder=".")
app.secret_key = "socn_ops_portal_super_secret_key_2026"
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # Allow up to 500MB uploads

@app.before_request
def handle_options_preflight():
    if request.method == "OPTIONS":
        res = app.make_default_options_response()
        res.headers['Access-Control-Allow-Origin'] = '*'
        res.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
        res.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        return res

@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    return response

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

BACKLOG_COMPARE_FOLDER = os.path.join(BASE_DIR, "Backlog Shipment")
os.makedirs(BACKLOG_COMPARE_FOLDER, exist_ok=True)

LOGS_FILE = os.path.join(DATA_DIR, "activity_logs.json")
if not os.path.exists(LOGS_FILE) and os.path.exists(os.path.join(BASE_DIR, "activity_logs.json")):
    LOGS_FILE = os.path.join(BASE_DIR, "activity_logs.json")

def load_activity_logs():
    if os.path.exists(LOGS_FILE):
        try:
            with open(LOGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []

USERS_FILE = os.path.join(DATA_DIR, "users_db.json")
if not os.path.exists(USERS_FILE) and os.path.exists(os.path.join(BASE_DIR, "users_db.json")):
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


SKIP_DIR = os.path.join(BASE_DIR, "Skip")
_CACHED_HUB_ZONE_MAP = None

def build_hub_zone_map():
    global _CACHED_HUB_ZONE_MAP
    if _CACHED_HUB_ZONE_MAP is not None:
        return _CACHED_HUB_ZONE_MAP

    json_cache = os.path.join(DATA_DIR, "hub_zone_map.json")
    if os.path.exists(json_cache):
        try:
            with open(json_cache, "r", encoding="utf-8") as f:
                _CACHED_HUB_ZONE_MAP = json.load(f)
                return _CACHED_HUB_ZONE_MAP
        except Exception:
            pass

    hub_map = {}
    hub_files = [
        os.path.join(SKIP_DIR, "Copy of [SOCN] Outbound On-time Investigation - Hub.csv"),
        os.path.join(SOURCE_DIR, "Copy of [SOCN] Outbound On-time Investigation - Hub.csv"),
        os.path.join(BASE_DIR, "Hub.csv"),
    ]
    
    hub_path = None
    for p in hub_files:
        if os.path.exists(p):
            hub_path = p
            break
            
    if hub_path and os.path.exists(hub_path):
        try:
            with open(hub_path, 'r', encoding='utf-8-sig', errors='ignore') as f:
                reader = csv.reader(f)
                header = next(reader, None)
                for row in reader:
                    if len(row) > 11:
                        st_id = row[0].strip()
                        st_name = row[1].strip()
                        st_short = row[2].strip()
                        zone = row[11].strip().upper()
                        
                        if not zone:
                            sup = row[5].strip().upper() if len(row) > 5 else ''
                            sub = row[8].strip().upper() if len(row) > 8 else ''
                            if 'NORC' in sup or 'NORC' in sub: zone = 'A'
                            elif 'NERC' in sup or 'NERC' in sub: zone = 'B'
                            elif 'SORC' in sup or 'SORC' in sub: zone = 'C'
                            elif 'SOCE' in sup or 'SOCW' in sup or 'SOCE' in sub or 'SOCW' in sub: zone = 'INTERSOC'
                            elif 'RET' in sup or 'RET' in sub: zone = 'RETURN'

                        if 'INTER' in zone: zone = 'INTERSOC'
                        elif 'RET' in zone: zone = 'RETURN'
                        
                        if zone in ['A', 'B', 'C', 'INTERSOC', 'RETURN']:
                            if st_name: hub_map[st_name.lower()] = zone
                            if st_short: hub_map[st_short.lower()] = zone
                            if st_id: hub_map[st_id.lower()] = zone
                            if '-' in st_name:
                                hub_map[st_name.split('-')[0].strip().lower()] = zone
            try:
                with open(json_cache, "w", encoding="utf-8") as f:
                    json.dump(hub_map, f, ensure_ascii=False, indent=2)
            except Exception:
                pass
        except Exception as e:
            print("Error loading Hub.csv:", e)

    _CACHED_HUB_ZONE_MAP = hub_map
    return hub_map

def lookup_obd_zone(station_name, hub_map=None):
    if hub_map is None:
        hub_map = build_hub_zone_map()
    if not station_name:
        return 'A'
    st = str(station_name).strip()
    st_lower = st.lower()
    if st_lower in hub_map:
        return hub_map[st_lower]
    if '-' in st_lower:
        prefix = st_lower.split('-')[0].strip()
        if prefix in hub_map:
            return hub_map[prefix]
    st_upper = st.upper()
    if 'INTER' in st_upper or 'SOCW' in st_upper or 'SOCE' in st_upper:
        return 'INTERSOC'
    if 'RET' in st_upper:
        return 'RETURN'
    return 'A'



def sanitize_user(u):
    if not u or not isinstance(u, dict):
        return u
    clean = dict(u)
    clean.pop("pass", None)
    clean.pop("password", None)
    return clean

def sanitize_users(users):
    if not isinstance(users, list):
        return []
    return [sanitize_user(u) for u in users]


@app.route("/api/users", methods=["GET"])
def get_users_api():
    return jsonify({"success": True, "users": sanitize_users(load_users_db())})

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
    return jsonify({"success": True, "user": sanitize_user(new_user), "users": sanitize_users(users)})

@app.route("/api/users/add", methods=["POST"])
def direct_add_user_api():
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = (data.get("pass") or "").strip()
    role = data.get("role", "Ground")
    requester_role = session.get("user_role") or data.get("requesterRole") or ""

    if not name or not email or not password:
        return jsonify({"success": False, "error": "กรุณากรอกข้อมูลให้ครบถ้วน"}), 400

    if requester_role == "Supervisor" and role == "Admin":
        return jsonify({"success": False, "error": "Supervisor ไม่มีสิทธิ์แต่งตั้งหรือเพิ่มผู้ใช้ในระดับ Admin"}), 403

    users = load_users_db()
    for u in users:
        if u.get("email", "").lower() == email:
            return jsonify({"success": False, "error": "อีเมลนี้ถูกลงทะเบียนไว้แล้ว"}), 400

    new_user = {
        "id": "u_" + str(int(datetime.now().timestamp() * 1000)),
        "name": name,
        "email": email,
        "pass": password,
        "role": role,
        "status": "approved",
        "createdAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    users.append(new_user)
    save_users_db(users)

    log_activity("USER_DIRECT_ADD", f"เพิ่มสมาชิกใหม่โดยตรง: {name} ({email}) สิทธิ์ {role}")
    return jsonify({"success": True, "user": sanitize_user(new_user), "users": sanitize_users(users)})

@app.route("/api/users/approve", methods=["POST"])
def approve_user_api():
    data = request.get_json() or {}
    user_id = str(data.get("id") or "").strip()
    email = str(data.get("email") or "").strip().lower()
    role = data.get("role", "Ground")
    requester_role = session.get("user_role") or data.get("requesterRole") or ""

    if requester_role == "Supervisor" and role == "Admin":
        return jsonify({"success": False, "error": "Supervisor ไม่มีสิทธิ์อนุมัติผู้ใช้ในระดับ Admin"}), 403

    users = load_users_db()
    target = None
    for u in users:
        if (user_id and str(u.get("id")) == user_id) or (email and u.get("email", "").lower() == email):
            target = u
            break

    if not target:
        return jsonify({"success": False, "error": "ไม่พบสมาชิก"}), 404

    if requester_role == "Supervisor" and target.get("role") == "Admin":
        return jsonify({"success": False, "error": "Supervisor ไม่สามารถแก้ไขบัญชีระดับ Admin ได้"}), 403

    target["status"] = "approved"
    target["role"] = role
    save_users_db(users)

    log_activity("USER_APPROVAL", f"อนุมัติบัญชี {target.get('name')} ({target.get('email')}) เป็นสิทธิ์ {role}")
    return jsonify({"success": True, "user": sanitize_user(target), "users": sanitize_users(users)})

@app.route("/api/users/role", methods=["POST"])
def change_role_user_api():
    data = request.get_json() or {}
    user_id = str(data.get("id") or "").strip()
    email = str(data.get("email") or "").strip().lower()
    role = data.get("role", "Ground")
    requester_role = session.get("user_role") or data.get("requesterRole") or ""

    if requester_role == "Supervisor" and role == "Admin":
        return jsonify({"success": False, "error": "Supervisor ไม่มีสิทธิ์แต่งตั้งผู้ใช้เป็นระดับ Admin"}), 403

    users = load_users_db()
    target = None
    for u in users:
        if (user_id and str(u.get("id")) == user_id) or (email and u.get("email", "").lower() == email):
            target = u
            break

    if not target:
        return jsonify({"success": False, "error": "ไม่พบสมาชิก"}), 404

    if requester_role == "Supervisor" and target.get("role") == "Admin":
        return jsonify({"success": False, "error": "Supervisor ไม่สามารถเปลี่ยนระดับสิทธิ์ของ Admin ได้"}), 403

    old_role = target.get("role")
    target["role"] = role
    save_users_db(users)

    log_activity("USER_ROLE_CHANGE", f"เปลี่ยนสิทธิ์ {target.get('name')} ({target.get('email')}) จาก {old_role} เป็น {role}")
    return jsonify({"success": True, "user": sanitize_user(target), "users": sanitize_users(users)})

@app.route("/api/users/delete", methods=["POST"])
def delete_user_api():
    data = request.get_json() or {}
    user_id = str(data.get("id") or "").strip()
    email = str(data.get("email") or "").strip().lower()
    requester_role = session.get("user_role") or data.get("requesterRole") or ""

    users = load_users_db()
    target = next((u for u in users if (user_id and str(u.get("id")) == user_id) or (email and u.get("email", "").lower() == email)), None)
    
    if target and requester_role == "Supervisor" and target.get("role") == "Admin":
        return jsonify({"success": False, "error": "Supervisor ไม่สามารถลบบัญชีระดับ Admin ได้"}), 403

    users = [u for u in users if str(u.get("id")) != user_id and (not email or u.get("email", "").lower() != email)]
    save_users_db(users)

    log_activity("USER_DELETE", f"ลบผู้ใช้งาน ID: {user_id}")
    return jsonify({"success": True, "users": sanitize_users(users)})

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
    return jsonify({"success": True, "user": sanitize_user(matched)})


@app.route("/api/users/change-password", methods=["POST"])
def change_user_password_api():
    data = request.get_json() or {}
    email = (data.get("email") or session.get("user_email") or "").strip().lower()
    current_pass = (data.get("currentPass") or "").strip()
    new_pass = (data.get("newPass") or "").strip()
    confirm_pass = (data.get("confirmPass") or "").strip()

    if not email:
        return jsonify({"success": False, "error": "ไม่พบข้อมูลผู้ใช้งาน กรุณาเข้าสู่ระบบใหม่"}), 401
    if not current_pass or not new_pass or not confirm_pass:
        return jsonify({"success": False, "error": "กรุณากรอกรหัสผ่านให้ครบทุกช่อง"}), 400
    if new_pass != confirm_pass:
        return jsonify({"success": False, "error": "รหัสผ่านใหม่และการยืนยันรหัสผ่านไม่ตรงกัน"}), 400
    if len(new_pass) < 4:
        return jsonify({"success": False, "error": "รหัสผ่านใหม่ต้องมีความยาวอย่างน้อย 4 ตัวอักษร"}), 400

    users = load_users_db()
    target = next((u for u in users if u.get("email", "").lower() == email or u.get("name", "").lower() == email), None)
    if not target:
        return jsonify({"success": False, "error": "ไม่พบบัญชีผู้ใช้งานในระบบ"}), 404

    if target.get("pass") != current_pass:
        return jsonify({"success": False, "error": "รหัสผ่านปัจจุบันไม่ถูกต้อง"}), 400

    target["pass"] = new_pass
    target["updatedAt"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    save_users_db(users)

    log_activity("USER_PASSWORD_CHANGE", f"เปลี่ยนรหัสผ่านสำเร็จ: {target.get('name')} ({target.get('email')})", user_email=target.get("email"), user_name=target.get("name"), user_role=target.get("role"))
    return jsonify({"success": True, "message": "เปลี่ยนรหัสผ่านสำเร็จเรียบร้อยแล้ว!"})


@app.route("/api/users/reset-password", methods=["POST"])
def reset_user_password_api():
    data = request.get_json() or {}
    user_id = str(data.get("id") or "").strip()
    email = str(data.get("email") or "").strip().lower()
    new_pass = (data.get("newPass") or "1234").strip()
    requester_role = session.get("user_role") or data.get("requesterRole") or ""

    users = load_users_db()
    target = next((u for u in users if (user_id and str(u.get("id")) == user_id) or (email and u.get("email", "").lower() == email)), None)
    if not target:
        return jsonify({"success": False, "error": "ไม่พบสมาชิก"}), 404

    if requester_role == "Supervisor" and target.get("role") == "Admin":
        return jsonify({"success": False, "error": "Supervisor ไม่สามารถรีเซ็ตรหัสผ่านของ Admin ได้"}), 403

    target["pass"] = new_pass
    target["updatedAt"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    save_users_db(users)

    log_activity("USER_RESET_PASSWORD", f"รีเซ็ตรหัสผ่านสมาชิก: {target.get('name')} ({target.get('email')})")
    return jsonify({"success": True, "message": "รีเซ็ตรหัสผ่านเรียบร้อยแล้ว", "users": sanitize_users(users)})

@app.route("/api/users/update-profile", methods=["POST"])
def update_user_profile_api():
    data = request.get_json() or {}
    email = (data.get("email") or session.get("user_email") or "").strip().lower()
    new_name = (data.get("name") or "").strip()
    current_pass = (data.get("currentPass") or "").strip()
    new_pass = (data.get("newPass") or "").strip()
    confirm_pass = (data.get("confirmPass") or "").strip()

    if not email:
        return jsonify({"success": False, "error": "ไม่พบข้อมูลผู้ใช้งาน กรุณาเข้าสู่ระบบใหม่"}), 401
    if not new_name:
        return jsonify({"success": False, "error": "กรุณากรอกชื่อผู้ใช้งาน (Username)"}), 400

    users = load_users_db()
    target = next((u for u in users if u.get("email", "").lower() == email or u.get("name", "").lower() == email), None)
    if not target:
        return jsonify({"success": False, "error": "ไม่พบบัญชีผู้ใช้งานในระบบ"}), 404

    # If updating name, check duplicate
    for u in users:
        if u.get("id") != target.get("id") and u.get("name", "").lower() == new_name.lower():
            return jsonify({"success": False, "error": "ชื่อผู้ใช้งานนี้ถูกใช้งานแล้ว กรุณาเลือกชื่ออื่น"}), 400

    old_name = target.get("name")
    target["name"] = new_name
    session["user_name"] = new_name

    # If password change is also requested
    if new_pass or current_pass:
        if not current_pass:
            return jsonify({"success": False, "error": "กรุณากรอกรหัสผ่านปัจจุบันเพื่อยืนยันการเปลี่ยนรหัส"}), 400
        if target.get("pass") != current_pass:
            return jsonify({"success": False, "error": "รหัสผ่านปัจจุบันไม่ถูกต้อง"}), 400
        if new_pass != confirm_pass:
            return jsonify({"success": False, "error": "รหัสผ่านใหม่และการยืนยันรหัสผ่านไม่ตรงกัน"}), 400
        if len(new_pass) < 4:
            return jsonify({"success": False, "error": "รหัสผ่านใหม่ต้องมีความยาวอย่างน้อย 4 ตัวอักษร"}), 400
        target["pass"] = new_pass

    target["updatedAt"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    save_users_db(users)

    log_activity("USER_PROFILE_UPDATE", f"อัปเดตโปรไฟล์: {old_name} -> {new_name} ({target.get('email')})", user_email=target.get("email"), user_name=new_name, user_role=target.get("role"))
    return jsonify({
        "success": True,
        "message": "อัปเดตข้อมูลผู้ใช้งานเรียบร้อยแล้ว!",
        "user": sanitize_user(target),
        "users": sanitize_users(users)
    })


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
            return pd.read_csv(filepath, low_memory=False, on_bad_lines='skip')
    else:
        return pd.read_csv(filepath, low_memory=False, on_bad_lines='skip')


def process_csv(filepath):
    df = read_dataframe(filepath)
    return process_dataframe(df, filename=os.path.basename(filepath))


def process_dataframe(df, filename=""):
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

    # Vectorized timestamp parsing ONLY on late_df with fast exact format fallback
    ts_cols = [
        "first_soc_outbound_timestamp",
        "soc_outbound_based_received_cut_off_timestamp",
        "soc_outbound_based_received_2nd_cut_off_timestamp",
        "first_soc_received_timestamp"
    ]
    for col in ts_cols:
        if col in late_df.columns:
            parsed = pd.to_datetime(late_df[col], format='%Y-%m-%d %H:%M:%S', errors='coerce')
            if parsed.isna().sum() > 0:
                parsed2 = pd.to_datetime(late_df[col], format='mixed', errors='coerce')
                late_df[col] = parsed.fillna(parsed2)
            else:
                late_df[col] = parsed

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

    # Fast Vectorized Peak Time
    if "first_soc_outbound_timestamp" in late_df.columns and pd.api.types.is_datetime64_any_dtype(late_df["first_soc_outbound_timestamp"]):
        late_df["_hhmm"] = late_df["first_soc_outbound_timestamp"].dt.strftime("%H:%M").fillna("-")
    else:
        late_df["_hhmm"] = "-"

    valid_hhmm = late_df[late_df["_hhmm"] != "-"]
    if not valid_hhmm.empty:
        st_counts = valid_hhmm.groupby(["dest_station_name_clean", "_hhmm"], observed=True).size().reset_index(name="cnt")
        idx_max = st_counts.groupby("dest_station_name_clean")["cnt"].idxmax()
        peak_map = dict(zip(st_counts.loc[idx_max, "dest_station_name_clean"], st_counts.loc[idx_max, "_hhmm"]))
    else:
        peak_map = {}

    cutoff_map = build_cutoff_map()
    grp_counts = late_df["dest_station_name_clean"].value_counts()

    ranking_list = []
    max_count = int(grp_counts.iloc[0]) if len(grp_counts) > 0 else 1
    for idx, (st_name, cnt) in enumerate(grp_counts.items()):
        cnt_int = int(cnt)
        pct = round((cnt_int / total_late * 100), 1) if total_late > 0 else 0
        st_clean = str(st_name).split(" - ")[0].strip().lower()
        matched_cutoff = cutoff_map.get(st_clean) or cutoff_map.get(str(st_name).lower())

        target_str = "-"
        if matched_cutoff:
            targets = []
            if matched_cutoff.get('cut1_ob'): targets.append(f"Cut1 {matched_cutoff.get('cut1_ob')}")
            if matched_cutoff.get('cut2_ob'): targets.append(f"Cut2 {matched_cutoff.get('cut2_ob')}")
            if matched_cutoff.get('cut3_ob'): targets.append(f"Cut3 {matched_cutoff.get('cut3_ob')}")
            if targets: target_str = " | ".join(targets)

        ranking_list.append({
            "rank": idx + 1,
            "station": str(st_name),
            "count": cnt_int,
            "pct": pct,
            "peakTime": str(peak_map.get(st_name, "-")),
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


def process_folder(folder_path, folder_name=None):
    if not folder_name:
        folder_name = os.path.basename(folder_path)
    
    files = []
    if os.path.exists(folder_path):
        for root, dirs, filenames in os.walk(folder_path):
            for f in filenames:
                if f.lower().endswith(('.csv', '.xlsx', '.xls')) and not f.startswith('.'):
                    files.append(os.path.join(root, f))
                    
    if not files:
        return {
            "success": False,
            "error": f"ไม่พบไฟล์ CSV/Excel ในโฟลเดอร์ '{folder_name}'"
        }
        
    dfs = []
    report_dates = []
    needed_patterns = ['ontime', 'cutoff', 'outbound', 'station', 'dest', 'late', 'route', 'shipment', 'tracking', 'received', 'pack', 'team', 'zone', 'to_number', 'report_date']
    
    for f in sorted(files):
        try:
            if f.lower().endswith('.csv'):
                h = pd.read_csv(f, nrows=0)
                usecols = [c for c in h.columns if any(p in str(c).lower() for p in needed_patterns)]
                sub_df = pd.read_csv(f, usecols=usecols if usecols else None, low_memory=False, on_bad_lines='skip')
            else:
                sub_df = read_dataframe(f)

            if sub_df is not None and not sub_df.empty:
                col_map = {}
                target_used = set()
                for col in sub_df.columns:
                    c_clean = str(col).strip().lower()
                    target = None
                    if c_clean in ['is_soc_outbound_ontime', 'is_ontime', 'ontime', 'is_soc_outbound_2nd_ontime']:
                        target = 'is_soc_outbound_ontime'
                    elif c_clean in ['soc_outbound_based_received_2nd_cut_off_timestamp', 'soc_outbound_based_received_cut_off_timestamp', 'cutoff_timestamp', 'cut_off_2']:
                        target = 'soc_outbound_based_received_2nd_cut_off_timestamp'
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
                    elif c_clean in ['report_date', 'date']:
                        target = 'report_date'

                    if target and target not in target_used:
                        col_map[col] = target
                        target_used.add(target)

                if col_map:
                    sub_df = sub_df.rename(columns=col_map)
                sub_df = sub_df.loc[:, ~sub_df.columns.duplicated()]

                if 'report_date' in sub_df.columns:
                    vds = sub_df['report_date'].dropna()
                    if len(vds) > 0:
                        report_dates.append(str(vds.iloc[0]))

                for req in ['is_soc_outbound_ontime', 'soc_outbound_late_type_2nd_cutoff', 'shipment_id', 'dest_station_name', 'first_soc_outbound_timestamp', 'soc_outbound_based_received_2nd_cut_off_timestamp']:
                    if req not in sub_df.columns:
                        sub_df[req] = ''

                ontime_str = sub_df["is_soc_outbound_ontime"].astype(str).str.strip().str.upper() if 'is_soc_outbound_ontime' in sub_df.columns else pd.Series([''] * len(sub_df))
                reason_str = sub_df["soc_outbound_late_type_2nd_cutoff"].astype(str).str.strip().str.lower() if 'soc_outbound_late_type_2nd_cutoff' in sub_df.columns else pd.Series([''] * len(sub_df))
                is_late_mask = ontime_str.isin(["FALSE", "0"]) | (reason_str.notna() & ~reason_str.isin(["", "none", "nan"]))
                
                late_sub_df = sub_df[is_late_mask].copy() if is_late_mask.any() else sub_df.head(0).copy()
                late_sub_df['source_file'] = os.path.basename(f)
                dfs.append(late_sub_df)
        except Exception as e:
            print(f"Error reading file {f} in folder {folder_name}:", e)
            
    if not dfs:
        return {
            "success": False,
            "error": f"ไม่สามารถอ่านข้อมูลจากไฟล์ในโฟลเดอร์ '{folder_name}' ได้"
        }
        
    combined_late_df = pd.concat(dfs, ignore_index=True)
    if 'shipment_id' in combined_late_df.columns:
        combined_late_df = combined_late_df.drop_duplicates(subset=['shipment_id'])
        
    data = process_dataframe(combined_late_df, filename=f"folder:{folder_name}")
    data["isFolder"] = True
    data["folderName"] = folder_name
    data["fileCount"] = len(files)
    data["fileList"] = [os.path.basename(f) for f in files]
    data["filename"] = f"folder:{folder_name}"
    if report_dates:
        data["reportDate"] = " - ".join(sorted(list(set(report_dates))))
    data["success"] = True
    return data


def process_folder_skip(folder_path, folder_name=None):
    if not folder_name:
        folder_name = os.path.basename(folder_path)
        
    files = []
    if os.path.exists(folder_path):
        for root, dirs, filenames in os.walk(folder_path):
            for f in filenames:
                if f.lower().endswith(('.csv', '.xlsx', '.xls')) and not f.startswith('.'):
                    files.append(os.path.join(root, f))
                    
    if not files:
        return {"success": False, "error": f"ไม่พบไฟล์ในโฟลเดอร์ '{folder_name}'"}
        
    dfs = []
    needed_patterns = ['shipment', 'tracking', 'waybill', 'late', 'reason', 'station', 'dest', 'hub', 'zone', 'team']
    
    for f in sorted(files):
        try:
            if f.lower().endswith('.csv'):
                h = pd.read_csv(f, nrows=0)
                usecols = [c for c in h.columns if any(p in str(c).lower() for p in needed_patterns)]
                sub_df = pd.read_csv(f, usecols=usecols if usecols else None, low_memory=False, on_bad_lines='skip')
            else:
                sub_df = read_dataframe(f)

            if sub_df is not None and not sub_df.empty:
                target_cols = {
                    'shipment_id': ['shipment_id', 'tracking_id', 'tracking_no', 'waybill'],
                    'soc_outbound_late_type_2nd_cutoff': ['soc_outbound_late_type_2nd_cutoff', 'soc_outbound_late_type', 'late_type', 'reason'],
                    'dest_station_name': ['dest_station_name', 'dest_station', 'hub_name', 'station_name', 'destination'],
                    'obd_zone': ['obd zone', 'obd_zone', 'zone', 'recieve_team', 'receive_team']
                }
                renames = {}
                used = set()
                for col in sub_df.columns:
                    c = str(col).strip().lower()
                    for key, cands in target_cols.items():
                        if c in cands and key not in used:
                            renames[col] = key
                            used.add(key)
                            break

                sub_df = sub_df.rename(columns=renames)
                sub_df = sub_df.loc[:, ~sub_df.columns.duplicated()]
                
                for n in ['shipment_id', 'soc_outbound_late_type_2nd_cutoff', 'dest_station_name', 'obd_zone']:
                    if n not in sub_df.columns:
                        sub_df[n] = ''

                reason_s = sub_df['soc_outbound_late_type_2nd_cutoff'].astype(str).str.lower()
                skip_mask = reason_s.str.contains('skip')
                skip_sub = sub_df[skip_mask].copy()
                skip_sub['source_file'] = os.path.basename(f)
                dfs.append(skip_sub)
        except Exception as e:
            print(f"Error reading skip file {f}:", e)
            
    if not dfs:
        return {"success": False, "error": f"ไม่สามารถอ่านไฟล์ในโฟลเดอร์ '{folder_name}'"}
        
    combined_skip = pd.concat(dfs, ignore_index=True)
    if 'shipment_id' in combined_skip.columns:
        combined_skip = combined_skip.drop_duplicates(subset=['shipment_id'])

    reason_s = combined_skip['soc_outbound_late_type_2nd_cutoff'].astype(str).str.lower()
    machine_count = int(reason_s.str.contains('machine').sum())
    system_count = int(reason_s.str.contains('system').sum())

    hub_map = build_hub_zone_map()

    def resolve_row_zone(ez, hub):
        ez_s = str(ez or '').strip().upper()
        if ez_s in ['A', 'B', 'C', 'INTERSOC', 'RETURN']:
            return ez_s
        if 'INTER' in ez_s:
            return 'INTERSOC'
        if 'RET' in ez_s:
            return 'RETURN'
        return lookup_obd_zone(hub, hub_map)

    obd_zones = combined_skip['obd_zone'].fillna('').astype(str).tolist()
    dest_stations = [str(s).strip() if pd.notna(s) and str(s).strip().lower() != 'nan' and str(s).strip() else '-' for s in combined_skip['dest_station_name'].tolist()]
    resolved_zones = [resolve_row_zone(z, h) for z, h in zip(obd_zones, dest_stations)]

    combined_skip['zone'] = resolved_zones

    zone_counts = {'A': 0, 'B': 0, 'C': 0, 'INTERSOC': 0, 'RETURN': 0}
    for z in resolved_zones:
        zone_counts[z] = zone_counts.get(z, 0) + 1

    shipment_ids = [str(s).strip() if pd.notna(s) and str(s).strip().lower() != 'nan' else '-' for s in combined_skip['shipment_id'].tolist()]
    reasons = [str(s).strip() if pd.notna(s) and str(s).strip().lower() != 'nan' else 'skip_outbound' for s in combined_skip['soc_outbound_late_type_2nd_cutoff'].tolist()]
    sources = [str(s).strip() if pd.notna(s) and str(s).strip().lower() != 'nan' else '-' for s in combined_skip['source_file'].tolist()]

    limit_preview = 2500
    raw_export_list = [
        {
            'shipment_id': sid,
            'shipmentId': sid,
            'soc_outbound_late_type_2nd_cutoff': rsn,
            'reason': rsn,
            'dest_station_name': dst,
            'hub': dst,
            'zone': zn,
            'source_file': src
        }
        for sid, rsn, dst, zn, src in zip(shipment_ids[:limit_preview], reasons[:limit_preview], dest_stations[:limit_preview], resolved_zones[:limit_preview], sources[:limit_preview])
    ]

    return {
        "success": True,
        "isFolder": True,
        "folderName": folder_name,
        "fileCount": len(files),
        "fileList": [os.path.basename(f) for f in files],
        "filename": f"folder:{folder_name}",
        "totalRows": len(combined_skip),
        "totalSkipCases": len(combined_skip),
        "machineCount": machine_count,
        "systemCount": system_count,
        "skipCountByZone": zone_counts,
        "rawRows": raw_export_list
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

@app.route("/upload", methods=["POST", "OPTIONS"])
@app.route("/api/upload", methods=["POST", "OPTIONS"])
def upload_file():
    if request.method == "OPTIONS":
        return jsonify({"success": True}), 200

    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file uploaded"}), 400
    
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"success": False, "error": "Empty filename"}), 400

    if not file.filename.lower().endswith((".csv", ".xlsx", ".xls")):
        return jsonify({"success": False, "error": "กรุณาอัปโหลดไฟล์ประเภท CSV หรือ Excel (.xlsx, .xls) เท่านั้น"}), 400

    scope = (request.form.get("scope") or "").strip().lower()
    fn_lower = file.filename.lower()
    if scope in ["compare", "backlog", "ob_bl_compare", "ob_bl"] or "backlog" in fn_lower or "compare" in fn_lower:
        target_folder = BACKLOG_COMPARE_FOLDER
    else:
        target_folder = UPLOAD_FOLDER

    os.makedirs(target_folder, exist_ok=True)
    save_path = os.path.join(target_folder, file.filename)
    try:
        file.save(save_path)
        print(f"✅ Saved file to folder ({target_folder}): {save_path}")
    except Exception as e:
        print("Error saving uploaded file:", e)
        return jsonify({"success": False, "error": f"Failed to save file: {str(e)}"}), 500

    if target_folder == BACKLOG_COMPARE_FOLDER:
        log_activity("UPLOAD_COMPARE_FILE", f"อัปโหลดไฟล์เปรียบเทียบเข้า Backlog Shipment: {file.filename}")
        return jsonify({
            "success": True,
            "filename": file.filename,
            "savedPath": save_path,
            "message": f"บันทึกไฟล์ {file.filename} เข้าโฟลเดอร์ Backlog Shipment เรียบร้อย"
        })

    try:
        data = process_csv(save_path)
        data["filename"] = file.filename
        data["savedPath"] = save_path
        data["success"] = True
        
        # Safely extract raw rows for Skip Process Monitor
        try:
            full_df = read_dataframe(save_path)
            
            # Find matching column names case-insensitively
            target_cols = {
                'shipment_id': ['shipment_id', 'tracking_id', 'tracking_no', 'waybill'],
                'soc_outbound_late_type_2nd_cutoff': ['soc_outbound_late_type_2nd_cutoff', 'soc_outbound_late_type', 'late_type', 'reason'],
                'dest_station_name': ['dest_station_name', 'dest_station', 'hub_name', 'station_name', 'destination'],
                'obd_zone': ['obd zone', 'obd_zone', 'zone', 'recieve_team', 'receive_team']
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
            needed = ['shipment_id', 'soc_outbound_late_type_2nd_cutoff', 'dest_station_name']
            for n in needed:
                if n not in sub_df.columns:
                    sub_df[n] = ''
            
            # Filter strictly for skip process cases (reason contains 'skip')
            reason_series = sub_df['soc_outbound_late_type_2nd_cutoff'].astype(str).str.lower()
            is_skip_mask = reason_series.str.contains('skip')
            skip_df = sub_df[is_skip_mask].copy()

            total_skip = len(skip_df)
            machine_count = int(reason_series[is_skip_mask].str.contains('machine').sum())
            system_count = int(reason_series[is_skip_mask].str.contains('system').sum())

            hub_map = build_hub_zone_map()
            
            # Resolve Zone accurately using Hub master lookup
            resolved_zones = []
            for _, r in skip_df.iterrows():
                explicit_zone = str(r.get('obd_zone', '') or '').strip().upper()
                if explicit_zone in ['A', 'B', 'C', 'INTERSOC', 'RETURN']:
                    resolved_zones.append(explicit_zone)
                elif 'INTER' in explicit_zone:
                    resolved_zones.append('INTERSOC')
                elif 'RET' in explicit_zone:
                    resolved_zones.append('RETURN')
                else:
                    hub = r.get('dest_station_name', '')
                    resolved_zones.append(lookup_obd_zone(hub, hub_map))
            
            skip_df['zone'] = resolved_zones

            skip_count_by_zone = {'A': 0, 'B': 0, 'C': 0, 'INTERSOC': 0, 'RETURN': 0}
            for z in resolved_zones:
                skip_count_by_zone[z] = skip_count_by_zone.get(z, 0) + 1

            raw_export_list = []
            for _, r in skip_df.iterrows():
                raw_export_list.append({
                    'shipment_id': str(r.get('shipment_id', '-')),
                    'shipmentId': str(r.get('shipment_id', '-')),
                    'soc_outbound_late_type_2nd_cutoff': str(r.get('soc_outbound_late_type_2nd_cutoff', 'skip_outbound')),
                    'reason': str(r.get('soc_outbound_late_type_2nd_cutoff', 'skip_outbound')),
                    'dest_station_name': str(r.get('dest_station_name', '-')),
                    'hub': str(r.get('dest_station_name', '-')),
                    'zone': str(r.get('zone', 'A'))
                })

            data["totalRows"] = total_skip
            data["totalSkipCases"] = total_skip
            data["machineCount"] = machine_count
            data["systemCount"] = system_count
            data["skipCountByZone"] = skip_count_by_zone
            data["rawRows"] = raw_export_list
        except Exception as ex:
            print("Error processing skip rawRows in upload_file:", ex)
            import traceback
            traceback.print_exc()
            data["rawRows"] = []
            data["totalRows"] = 0
            data["totalSkipCases"] = 0
            data["machineCount"] = 0
            data["systemCount"] = 0
            data["skipCountByZone"] = {}

        return jsonify(data)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": f"Failed to upload: {str(e)}"}), 500


@app.route("/api/upload-chunk", methods=["POST", "OPTIONS"])
@app.route("/upload-chunk", methods=["POST", "OPTIONS"])
@app.route("/api/upload-compare-chunk", methods=["POST", "OPTIONS"])
@app.route("/upload-compare-chunk", methods=["POST", "OPTIONS"])
def upload_chunk():
    if request.method == "OPTIONS":
        return jsonify({"success": True}), 200

    file_chunk = request.files.get("chunk")
    filename = (request.form.get("filename") or "").strip()
    chunk_index = int(request.form.get("chunk_index", 0))
    total_chunks = int(request.form.get("total_chunks", 1))
    scope = (request.form.get("scope") or "").strip().lower()
    folder_name = (request.form.get("folder_name") or request.form.get("folderName") or "").strip()

    if not file_chunk or not filename:
        return jsonify({"success": False, "error": "ไม่พบข้อมูล chunk หรือชื่อไฟล์"}), 400

    filename = os.path.basename(filename)
    if not filename.lower().endswith((".csv", ".xlsx", ".xls")):
        return jsonify({"success": False, "error": "กรุณาอัปโหลดไฟล์ประเภท CSV หรือ Excel (.xlsx, .xls) เท่านั้น"}), 400

    fn_lower = filename.lower()
    if scope in ["compare", "backlog", "ob_bl_compare"] or "backlog" in fn_lower or "compare" in fn_lower:
        target_dir = BACKLOG_COMPARE_FOLDER
    elif folder_name:
        folder_clean = re.sub(r'[\\/:*?"<>|]', '_', folder_name).strip()
        target_dir = os.path.join(UPLOAD_FOLDER, folder_clean)
    else:
        target_dir = UPLOAD_FOLDER

    os.makedirs(target_dir, exist_ok=True)
    save_path = os.path.join(target_dir, filename)

    try:
        mode = "wb" if chunk_index == 0 else "ab"
        with open(save_path, mode) as f:
            f.write(file_chunk.read())

        if chunk_index == total_chunks - 1:
            log_activity("UPLOAD_FILE", f"Uploaded file (chunked): {filename} -> {os.path.basename(target_dir)}")
            return jsonify({
                "success": True,
                "completed": True,
                "filename": filename,
                "savedPath": save_path,
                "message": f"บันทึกไฟล์ {filename} เรียบร้อยแล้ว"
            })
        else:
            return jsonify({
                "success": True,
                "completed": False,
                "chunk_index": chunk_index,
                "total_chunks": total_chunks
            })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": f"เกิดข้อผิดพลาดในการเขียนไฟล์: {str(e)}"}), 500


# ===== GAS PUSH endpoint: GAS ยิง POST มาหาเรา (แก้ปัญหา Workspace restriction) =====
GAS_PUSH_CACHE = {
    "lhtrip": None,
    "obbl": None
}

RECEIVE_API_KEY = "SOCN_OBBL_2026_SECRET_KEY_XK9M3"

@app.route("/api/receive-gas-data", methods=["POST", "GET"])
def receive_gas_data():
    """
    GAS ยิง POST มาที่นี่พร้อมข้อมูล headers+rows
    แก้ปัญหา 'Anyone within Shopee Mobile' — GAS รันใน account ที่มีสิทธิ์ แล้ว push มาให้เรา
    """
    # รองรับ GET เพื่อ health check
    if request.method == "GET":
        status = {}
        for k, v in GAS_PUSH_CACHE.items():
            if v:
                status[k] = {"rows": len(v.get("rows", [])), "updatedAt": v.get("updatedAt", "?")}
            else:
                status[k] = None
        return jsonify({"success": True, "cache": status})

    try:
        data = request.get_json(silent=True) or {}
        key = (data.get("key") or "").strip()
        page = (data.get("page") or "").strip().lower()

        # ตรวจ API Key
        if key != RECEIVE_API_KEY:
            return jsonify({"success": False, "error": "Unauthorized"}), 403

        if not page:
            return jsonify({"success": False, "error": "Missing page parameter"}), 400

        headers = data.get("headers", [])
        rows = data.get("rows", [])

        if not headers:
            return jsonify({"success": False, "error": "No headers in payload"}), 400

        cache_entry = {
            "success": True,
            "headers": headers,
            "rows": rows,
            "total": len(rows),
            "updatedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "pushedBy": data.get("pushedBy", "GAS"),
            "sheet": data.get("sheet", ""),
            "filename": f"Live {page.upper()} (GAS Push)"
        }

        GAS_PUSH_CACHE[page] = cache_entry

        # บันทึก disk cache ด้วย
        cache_path = os.path.join(UPLOAD_FOLDER, f"GAS_PUSH_{page.upper()}.json")
        try:
            import json as json_lib
            with open(cache_path, "w", encoding="utf-8") as f:
                json_lib.dump(cache_entry, f, ensure_ascii=False)
        except Exception:
            pass

        # ถ้าเป็น obbl ให้บันทึก CSV ด้วย
        if page == "obbl" and headers and rows:
            try:
                import csv as csv_lib
                csv_path = os.path.join(UPLOAD_FOLDER, "LIVE_OB_BL_SYNC.csv")
                with open(csv_path, "w", newline="", encoding="utf-8") as f:
                    writer = csv_lib.writer(f)
                    writer.writerow(headers)
                    writer.writerows(rows)
            except Exception:
                pass

        log_activity("GAS_PUSH", f"GAS pushed {page} data — {len(rows)} rows")
        return jsonify({"success": True, "received": len(rows), "page": page})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/get-gas-cache", methods=["GET"])
def get_gas_cache():
    """ให้ dashboard ดึงข้อมูลที่ GAS push มาแล้ว"""
    page = request.args.get("page", "lhtrip").strip().lower()

    # ลอง memory cache ก่อน
    cached = GAS_PUSH_CACHE.get(page)
    if cached and cached.get("rows"):
        return jsonify(cached)

    # ลอง disk cache
    cache_path = os.path.join(UPLOAD_FOLDER, f"GAS_PUSH_{page.upper()}.json")
    if os.path.exists(cache_path):
        try:
            import json as json_lib
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json_lib.load(f)
            GAS_PUSH_CACHE[page] = data
            return jsonify(data)
        except Exception:
            pass

    return jsonify({
        "success": False,
        "error": f"ยังไม่มีข้อมูล {page} ที่ GAS push มา — กรุณากด 'Push to Dashboard' ใน Apps Script ก่อนครับ"
    }), 200


@app.route("/api/sync-google-sheet", methods=["GET", "POST"])
def sync_google_sheet():
    url = request.args.get("url", "") or (request.json.get("url", "") if request.is_json else "")
    url = str(url).strip()

    # Default Google Sheet Published CSV / GViz URL if none provided
    default_sheet_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTTO9c6WUEftB0bua-dyM9XiQV74qVhQm7v6as6Pz6IP9h-p0XOmK2XL1uDFvOvJx1cMypb9cML2ExI/pub?output=csv"

    import re
    gid_match = re.search(r'gid=([0-9]+)', url)
    gid_param = f"&gid={gid_match.group(1)}" if gid_match else ""

    # ======= Apps Script URL → relay ผ่าน POST + API Key (แก้ domain restriction) =======
    if url and "script.google.com" in url:
        try:
            # ใช้ API Key เดียวกับที่กำหนดใน GAS_API_KEY
            payload = {"key": GAS_API_KEY, "page": "lhtrip"}
            resp = requests.post(
                url,
                json=payload,
                timeout=60,
                headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
                allow_redirects=True
            )

            # ถ้า response เป็น HTML (ติด login) ให้แจ้ง error ชัดเจน
            if (resp.content.strip().startswith(b"<!DOCTYPE html") or
                    b"Sign in - Google Accounts" in resp.content or
                    b"accounts.google.com" in resp.content):
                return jsonify({
                    "success": False,
                    "error": "Apps Script ยังติด Login Google ❌\n\nวิธีแก้:\n1. เปิด Apps Script > Deploy > Manage Deployments\n2. กด Edit (✏️) ตรง Deployment ที่ใช้งาน\n3. เปลี่ยน 'Who has access' → 'Anyone'\n4. กด Deploy ใหม่"
                }), 200

            if resp.status_code == 200:
                try:
                    json_res = resp.json()
                    if isinstance(json_res, dict):
                        # ถ้า GAS ตอบ error (key ผิด หรือ page ผิด) → ลอง GET format แบบเดิม
                        if json_res.get("success") == False and "Unauthorized" in str(json_res.get("error", "")):
                            pass  # fall through to old GET method below
                        else:
                            if "rows" in json_res or "data" in json_res or "headers" in json_res:
                                json_res["success"] = True
                                log_activity("SYNC_GOOGLE_SHEET", f"Synced LH Trip via GAS API Key from {url}")
                                return jsonify(json_res)
                except Exception:
                    pass  # fall through to old method
        except requests.Timeout:
            return jsonify({"success": False, "error": "Apps Script ใช้เวลานานเกินไป (Timeout 60s) กรุณาลองใหม่"}), 200
        except Exception:
            pass  # fall through to old GET method

    if not url:
        url = default_sheet_url
    elif "/pubhtml" in url:
        url = url.replace("/pubhtml", "/pub?output=csv")
        if gid_match and "gid=" not in url:
            url += gid_param
    elif "docs.google.com/spreadsheets" in url and "gviz/tq" not in url and "export" not in url and "/pub" not in url:
        match = re.search(r'/d/e/([a-zA-Z0-9-_]+)', url) or re.search(r'/d/([a-zA-Z0-9-_]+)', url)
        if match:
            spreadsheet_id = match.group(1)
            url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/gviz/tq?tqx=out:csv{gid_param}"
    elif "script.google.com" in url and "format=" not in url and "raw=" not in url and "page=" not in url:
        url += "&format=json" if "?" in url else "?format=json"

    try:
        # Fast check first without following endless Google SSO redirects (0.4s response)
        init_req = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"}, allow_redirects=False)
        loc = init_req.headers.get("Location", "")

        # Check if redirected to Google Account Sign-in
        if init_req.status_code in [301, 302, 303, 307] and ("ServiceLogin" in loc or "accounts.google.com" in loc or "google.com/a/" in loc):
            return jsonify({
                "success": False,
                "error": "URL นี้ติดสิทธิ์ล็อกอินองค์กร Google (Google Accounts Required)\n\n👉 วิธีแก้เปิดสิทธิ์ให้ดึงข้อมูลได้:\n1. หากใช้ Apps Script: ไปที่ 'Deploy' > 'Manage deployments' > เปลี่ยน 'Who has access' เป็น 'Anyone'\n2. หากใช้ Google Sheet: ไปที่ 'ไฟล์' > 'แชร์' > เปลี่ยนเป็น 'ทุกคนที่มีลิงก์' (Anyone with the link)"
            }), 200

        if init_req.status_code in [301, 302, 303, 307] and loc:
            req = requests.get(loc, timeout=15, headers={"User-Agent": "Mozilla/5.0"}, allow_redirects=True)
        else:
            req = init_req

        if req.status_code == 401:
            return jsonify({
                "success": False,
                "error": "URL นี้ติดสิทธิ์เข้าถึงของ Google (HTTP 401 / Permission Required)"
            }), 200
        elif req.status_code != 200:
            return jsonify({"success": False, "error": f"HTTP {req.status_code}: ไม่สามารถดึงข้อมูลจาก Google Sheet / Apps Script ได้"}), 200

        # Check if Google returned an HTML login redirect page instead of CSV/JSON
        if req.content.strip().startswith(b"<!DOCTYPE html") or req.content.strip().startswith(b"<html") or b"Sign in - Google Accounts" in req.content or b"accounts.google.com" in req.content:
            return jsonify({
                "success": False,
                "error": "URL นี้ติดสิทธิ์ล็อกอินองค์กร Google (Google Accounts Required)\n\n👉 วิธีแก้เปิดสิทธิ์ให้ดึงข้อมูลได้:\n1. หากใช้ Apps Script: ไปที่ 'Deploy' > 'Manage deployments' > เปลี่ยน 'Who has access' เป็น 'Anyone'\n2. หากใช้ Google Sheet: ไปที่ 'ไฟล์' > 'แชร์' > เปลี่ยนเป็น 'ทุกคนที่มีลิงก์' (Anyone with the link)"
            }), 200

        # Check if response is JSON (Google Apps Script Web App API response)
        try:
            json_res = req.json()
            if isinstance(json_res, dict) and ("rows" in json_res or "data" in json_res or "headers" in json_res):
                json_res["success"] = True
                log_activity("SYNC_GOOGLE_SHEET", f"Successfully synced live Apps Script JSON from {url}")
                return jsonify(json_res)
        except Exception:
            pass

        csv_filename = "LIVE_GOOGLE_SHEET_SYNC.csv"
        target_path = os.path.join(UPLOAD_FOLDER, csv_filename)
        with open(target_path, "wb") as f:
            f.write(req.content)

        try:
            df = pd.read_csv(target_path, low_memory=False, on_bad_lines='skip')
            cols_lower = [str(c).lower() for c in df.columns]
            if any('trip number' in c or 'show on time' in c or 'vehicle' in c for c in cols_lower) or len(df.columns) >= 20:
                data = process_table_sheet(df)
                data["filename"] = "Live Google Sheet (Table)"
                data["success"] = True
                log_activity("SYNC_GOOGLE_SHEET", f"Successfully synced live Google Sheet Table data from {url}")
                return jsonify(data)
        except Exception:
            pass

        log_activity("SYNC_GOOGLE_SHEET", f"Synced Google Sheet data from {url}")
        return jsonify(data)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": f"ไม่สามารถดึงข้อมูลจาก Google Sheet ได้: {str(e)}"}), 500


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
            "trip_category": str(row.get(df_clean.columns[2], '')) if len(df_clean.columns) > 2 else '',
            "vehicle_type": str(row.get(veh_col, '')) if veh_col else '',
            "vehicle_plate": str(row.get(df_clean.columns[4], '')) if len(df_clean.columns) > 4 else '',
            "driver": str(row.get(df_clean.columns[5], '')) if len(df_clean.columns) > 5 else '',
            "origin": str(row.get(df_clean.columns[6], '')) if len(df_clean.columns) > 6 else '',
            "dest_station_name": str(row.get(dest_col, '')) if dest_col else '',
            "cut0": str(row.get(df_clean.columns[15], '')) if len(df_clean.columns) > 15 else '',
            "cut1": str(row.get(df_clean.columns[16], '')) if len(df_clean.columns) > 16 else '',
            "cut2": str(row.get(df_clean.columns[17], '')) if len(df_clean.columns) > 17 else '',
            "actual_dep_cut": str(row.get(df_clean.columns[19], '')) if len(df_clean.columns) > 19 else '',
            "status": str(row.get(status_col, '')) if status_col else '',
            "region": str(row.get(df_clean.columns[25], '')) if len(df_clean.columns) > 25 else '',
            "zone": str(row.get(df_clean.columns[26], '')) if len(df_clean.columns) > 26 else ''
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
@app.route("/api/load-lh", methods=["GET"])
def load_ob_late():
    excel_path = os.path.join(BASE_DIR, "OB Late", "test.xlsx")
    if os.path.exists(UPLOAD_FOLDER):
        upload_files = [os.path.join(UPLOAD_FOLDER, f) for f in os.listdir(UPLOAD_FOLDER) if f.endswith(".csv") or f.endswith(".xlsx")]
        if upload_files:
            upload_files.sort(key=os.path.getmtime, reverse=True)
            excel_path = upload_files[0]

    if not os.path.exists(excel_path):
        return jsonify({"success": False, "error": "test.xlsx not found in OB Late folder"}), 404

    try:
        if excel_path.endswith('.xlsx') or excel_path.endswith('.xls'):
            df = pd.read_excel(excel_path, sheet_name='Table')
        else:
            df = pd.read_csv(excel_path, low_memory=False)
        data = process_table_sheet(df)
        data["filename"] = os.path.basename(excel_path)
        data["success"] = True
        return jsonify(data)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/list-files", methods=["GET"])
def list_files():
    file_list = []
    folder_list = []
    seen = set()

    # Search in uploads folder
    if os.path.exists(UPLOAD_FOLDER):
        for item in os.listdir(UPLOAD_FOLDER):
            item_path = os.path.join(UPLOAD_FOLDER, item)
            if os.path.isdir(item_path):
                child_files = [f for f in os.listdir(item_path) if f.lower().endswith(('.csv', '.xlsx', '.xls'))]
                if child_files:
                    folder_list.append({
                        "folderName": item,
                        "filename": f"folder:{item}",
                        "displayName": f"📁 ทั้งโฟลเดอร์: {item} ({len(child_files)} ไฟล์)",
                        "fileCount": len(child_files),
                        "mtime": os.path.getmtime(item_path),
                        "files": child_files
                    })
            elif item.lower().endswith(('.csv', '.xlsx', '.xls')):
                file_list.append({
                    "filename": item,
                    "location": "uploads",
                    "mtime": os.path.getmtime(item_path),
                    "size": os.path.getsize(item_path)
                })
                seen.add(item)

    # Search in root folder
    for f in os.listdir(BASE_DIR):
        if f.lower().endswith(".csv") and f not in seen:
            p = os.path.join(BASE_DIR, f)
            file_list.append({
                "filename": f,
                "location": "root",
                "mtime": os.path.getmtime(p),
                "size": os.path.getsize(p)
            })
            seen.add(f)

    folder_list.sort(key=lambda x: x["mtime"], reverse=True)
    file_list.sort(key=lambda x: x["mtime"], reverse=True)

    return jsonify({
        "success": True,
        "files": file_list,
        "folders": folder_list,
        "outbound_files": file_list,
        "outbound_folders": folder_list,
        "skip_files": file_list,
        "skip_folders": folder_list
    })


@app.route("/api/delete-file", methods=["POST"])
def delete_file():
    data = request.get_json() or {}
    filename = (data.get("filename") or "").strip()
    if not filename:
        return jsonify({"success": False, "error": "ไม่ได้ระบุชื่อไฟล์หรือโฟลเดอร์"}), 400

    if filename.startswith("folder:"):
        folder_name = filename.replace("folder:", "").strip()
        folder_clean = os.path.basename(folder_name)
        target_dir = os.path.join(UPLOAD_FOLDER, folder_clean)
        if os.path.exists(target_dir) and os.path.isdir(target_dir):
            import shutil
            try:
                shutil.rmtree(target_dir)
                log_activity("FOLDER_DELETE", f"🗑️ ลบโฟลเดอร์ข้อมูล: {folder_clean}")
                return jsonify({"success": True, "filename": filename, "message": f"ลบโฟลเดอร์ {folder_clean} เรียบร้อยแล้ว"})
            except Exception as e:
                return jsonify({"success": False, "error": f"ไม่สามารถลบโฟลเดอร์ได้: {str(e)}"}), 500
        else:
            return jsonify({"success": False, "error": f"ไม่พบโฟลเดอร์ '{folder_clean}' บนเซิร์ฟเวอร์"}), 404

    filename_clean = os.path.basename(filename)
    target_upload = os.path.join(UPLOAD_FOLDER, filename_clean)
    target_compare = os.path.join(BACKLOG_COMPARE_FOLDER, filename_clean)
    target_base = os.path.join(BASE_DIR, filename_clean)

    deleted = False
    deleted_path = ""

    if os.path.exists(target_compare):
        try:
            os.remove(target_compare)
            deleted = True
            deleted_path = target_compare
        except Exception as e:
            return jsonify({"success": False, "error": f"ไม่สามารถลบไฟล์ได้: {str(e)}"}), 500
    elif os.path.exists(target_upload):
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
    folder_param = request.args.get("folder", "").strip()
    if folder_param:
        filename = f"folder:{folder_param}"

    if not filename:
        return jsonify({"success": False, "error": "ไม่ได้ระบุชื่อไฟล์หรือโฟลเดอร์"}), 400

    if filename.startswith("folder:"):
        folder_name = filename.replace("folder:", "").strip()
        folder_path = os.path.join(UPLOAD_FOLDER, os.path.basename(folder_name))
        if not os.path.exists(folder_path):
            folder_path = os.path.join(BASE_DIR, os.path.basename(folder_name))
        if not os.path.exists(folder_path):
            return jsonify({"success": False, "error": f"ไม่พบโฟลเดอร์ '{folder_name}' บนเซิร์ฟเวอร์"}), 200
        
        folder_mtime = os.path.getmtime(folder_path)
        cache_key = f"folder_ob_{folder_path}_{folder_mtime}"
        if cache_key in FILE_PARSED_CACHE:
            return jsonify(FILE_PARSED_CACHE[cache_key])
            
        res = process_folder(folder_path, folder_name)
        if res.get("success"):
            FILE_PARSED_CACHE[cache_key] = res
        return jsonify(res)

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


@app.route("/api/hub-zone-map", methods=["GET"])
def get_hub_zone_map_api():
    return jsonify({"success": True, "hubMap": build_hub_zone_map()})


@app.route("/api/load-skip", methods=["GET"])
def load_skip_lightweight():
    """Lightweight skip-only endpoint that accurately processes skip cases and zone assignments."""
    filename = request.args.get("filename", "").strip()
    folder_param = request.args.get("folder", "").strip()
    if folder_param:
        filename = f"folder:{folder_param}"

    if not filename:
        return jsonify({"success": False, "error": "ไม่ได้ระบุชื่อไฟล์หรือโฟลเดอร์"}), 400

    if filename.startswith("folder:"):
        folder_name = filename.replace("folder:", "").strip()
        folder_path = os.path.join(UPLOAD_FOLDER, os.path.basename(folder_name))
        if not os.path.exists(folder_path):
            folder_path = os.path.join(BASE_DIR, os.path.basename(folder_name))
        if not os.path.exists(folder_path):
            return jsonify({"success": False, "error": f"ไม่พบโฟลเดอร์ '{folder_name}' บนเซิร์ฟเวอร์"}), 200
            
        folder_mtime = os.path.getmtime(folder_path)
        cache_key = f"folder_skip_{folder_path}_{folder_mtime}"
        if cache_key in FILE_PARSED_CACHE:
            return jsonify(FILE_PARSED_CACHE[cache_key])
            
        res = process_folder_skip(folder_path, folder_name)
        if res.get("success"):
            FILE_PARSED_CACHE[cache_key] = res
        return jsonify(res)

    target = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.exists(target):
        target = os.path.join(BASE_DIR, filename)
    if not os.path.exists(target):
        return jsonify({"success": False, "error": f"ไม่พบไฟล์ '{filename}' บนเซิร์ฟเวอร์ (ไฟล์อาจถูกลบหรือไม่ได้อัปโหลด)"}), 200

    try:
        full_df = pd.read_csv(target, low_memory=False)

        target_cols = {
            'shipment_id': ['shipment_id', 'tracking_id', 'tracking_no', 'waybill'],
            'soc_outbound_late_type_2nd_cutoff': ['soc_outbound_late_type_2nd_cutoff', 'soc_outbound_late_type', 'late_type', 'reason'],
            'dest_station_name': ['dest_station_name', 'dest_station', 'hub_name', 'station_name', 'destination'],
            'obd_zone': ['obd zone', 'obd_zone', 'zone', 'recieve_team', 'receive_team']
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
        needed = ['shipment_id', 'soc_outbound_late_type_2nd_cutoff', 'dest_station_name']
        for n in needed:
            if n not in sub_df.columns:
                sub_df[n] = ''

        reason_s = sub_df['soc_outbound_late_type_2nd_cutoff'].astype(str).str.lower()
        mask = reason_s.str.contains('skip')
        skip_df = sub_df[mask].copy()

        machine_count = int(reason_s[mask].str.contains('machine').sum())
        system_count = int(reason_s[mask].str.contains('system').sum())

        hub_map = build_hub_zone_map()

        resolved_zones = []
        for _, r in skip_df.iterrows():
            explicit_zone = str(r.get('obd_zone', '') or '').strip().upper()
            if explicit_zone in ['A', 'B', 'C', 'INTERSOC', 'RETURN']:
                resolved_zones.append(explicit_zone)
            elif 'INTER' in explicit_zone:
                resolved_zones.append('INTERSOC')
            elif 'RET' in explicit_zone:
                resolved_zones.append('RETURN')
            else:
                hub = r.get('dest_station_name', '')
                resolved_zones.append(lookup_obd_zone(hub, hub_map))

        skip_df['zone'] = resolved_zones

        zone_counts = {'A': 0, 'B': 0, 'C': 0, 'INTERSOC': 0, 'RETURN': 0}
        for z in resolved_zones:
            zone_counts[z] = zone_counts.get(z, 0) + 1

        raw_export_list = []
        for _, r in skip_df.iterrows():
            raw_export_list.append({
                'shipment_id': str(r.get('shipment_id', '-')),
                'shipmentId': str(r.get('shipment_id', '-')),
                'soc_outbound_late_type_2nd_cutoff': str(r.get('soc_outbound_late_type_2nd_cutoff', 'skip_outbound')),
                'reason': str(r.get('soc_outbound_late_type_2nd_cutoff', 'skip_outbound')),
                'dest_station_name': str(r.get('dest_station_name', '-')),
                'hub': str(r.get('dest_station_name', '-')),
                'zone': str(r.get('zone', 'A'))
            })

        return jsonify({
            "success": True,
            "filename": filename,
            "totalRows": len(skip_df),
            "totalSkipCases": len(skip_df),
            "machineCount": machine_count,
            "systemCount": system_count,
            "skipCountByZone": zone_counts,
            "rawRows": raw_export_list
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

VOLUME_FILE = os.path.join(DATA_DIR, "volume_history.json")
if not os.path.exists(VOLUME_FILE) and os.path.exists(os.path.join(BASE_DIR, "volume_history.json")):
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
        entry_type = req.get("type", "daily")
        label = req.get("label") or str(date_str)
        
        if date_str and isinstance(actual, (int, float)) and actual > 0:
            history = data.get("history", [])
            existing_idx = next((i for i, h in enumerate(history) if h.get("date") == date_str), -1)
            entry = {
                "date": str(date_str),
                "actual": int(actual),
                "type": entry_type,
                "label": str(label)
            }
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
    entry_type = req.get("type", "daily")
    label = req.get("label") or str(date_str)
    
    if not date_str or not actual:
        data["active"] = None
    else:
        data["active"] = {
            "date": str(date_str),
            "actual": int(actual),
            "type": entry_type,
            "label": str(label)
        }
        
    save_volume_data_to_file(data)
    return jsonify({"success": True, "active": data.get("active")})


# ===== STAFF ROSTER MANAGEMENT SYSTEM =====
STAFF_ROSTER_FILE = os.path.join(DATA_DIR, "staff_roster.json")

def load_staff_roster_data():
    if os.path.exists(STAFF_ROSTER_FILE):
        try:
            with open(STAFF_ROSTER_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print("Error loading staff roster file:", e)
    return {
        "updatedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "rosterByZone": {
            "ALL": ["Chain", "Big", "NULACK"],
            "A": ["Kwang", "Nut", "Mick", "Wave", "Porn"],
            "B": ["SKY", "Dum", "Korya", "Tang", "Oat"],
            "C": ["LY", "Tak", "Keng", "Nam", "Earth"],
            "TBS": ["Air", "Tarn", "Meiji"],
            "MS": ["Champ", "Tong"],
            "INTERSOC": [],
            "RETURN": []
        },
        "staffList": []
    }

def save_staff_roster_data(data):
    try:
        data["updatedAt"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(STAFF_ROSTER_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print("Error saving staff roster data:", e)
        return False

def parse_staff_roster_file(filepath):
    rows = []
    if filepath.lower().endswith(('.xlsx', '.xls')):
        try:
            df = pd.read_excel(filepath, sheet_name=0, header=None)
            rows = df.fillna('').astype(str).values.tolist()
        except Exception as e:
            print("Error reading excel roster:", e)
            return None
    else:
        # Try multiple encodings for CSV
        for enc in ['utf-8-sig', 'utf-8', 'cp874', 'tis-620', 'cp1252', 'latin-1']:
            try:
                with open(filepath, 'r', encoding=enc, errors='ignore') as f:
                    content = f.read()
                    if content:
                        # Auto detect delimiter
                        delim = ','
                        if content.count(';') > content.count(',') and content.count(';') > 5:
                            delim = ';'
                        elif content.count('\t') > content.count(',') and content.count('\t') > 5:
                            delim = '\t'
                        reader = csv.reader(content.splitlines(), delimiter=delim)
                        rows = list(reader)
                        if rows:
                            break
            except Exception as e:
                continue

    if not rows:
        return None

    # Step 1: Detect if there is a header row
    header_idx = -1
    for idx, r in enumerate(rows[:6]):
        row_str = ' '.join(str(x) for x in r).lower()
        has_header_word = any(k in row_str for k in ['รหัสพนักงาน', 'รหัส', 'staff id', 'emp id', 'opsid', 'ชื่อเล่น', 'nickname', 'position', 'ตำแหน่ง', 'zone', 'โซน'])
        has_data_pattern = any(bool(re.search(r'spxth\d+|ops\d+', str(x).lower())) for x in r)
        if has_header_word and not has_data_pattern:
            header_idx = idx
            break

    data_rows = rows[header_idx + 1:] if header_idx >= 0 else rows

    # Step 2: Determine column mapping
    col_map = {}
    if header_idx >= 0:
        header = [str(c).strip().lower() for c in rows[header_idx]]
        for i, h in enumerate(header):
            if 'รหัส' in h or 'emp' in h or 'staff' in h:
                col_map['empId'] = i
            elif 'ops' in h:
                col_map['opsId'] = i
            elif 'ชื่อเล่น' in h or 'nick' in h:
                col_map['nickname'] = i
            elif 'นามสกุล' in h or 'last' in h or 'surname' in h:
                col_map['lastName'] = i
            elif 'ชื่อ' in h or 'first' in h or 'name' in h:
                if 'nickname' not in col_map and 'firstName' not in col_map:
                    col_map['firstName'] = i
            elif 'position' in h or 'ตำแหน่ง' in h or 'role' in h:
                col_map['position'] = i
            elif 'zone' in h or 'โซน' in h:
                col_map['zone'] = i

    # If no header row or missing critical columns, use smart pattern detection
    if not col_map or 'nickname' not in col_map or ('empId' not in col_map and 'opsId' not in col_map):
        sample = [r for r in data_rows if any(str(x).strip() for x in r)][:15]
        max_cols = max(len(r) for r in sample) if sample else 0
        detected = {}
        for c in range(max_cols):
            vals = [str(r[c]).strip() for r in sample if c < len(r) and str(r[c]).strip() and str(r[c]).strip().lower() != 'nan']
            if not vals:
                continue

            # Check for empId (SPXTH... or 6-10 digit numbers)
            if 'empId' not in detected and all(re.match(r'^(spxth)?\d+$', v, re.I) for v in vals if v):
                if not all(re.match(r'^\d{1,3}$', v) for v in vals):  # exclude sequence 1, 2, 3
                    detected['empId'] = c
                    continue

            # Check for opsId (Ops... or ops_...)
            if 'opsId' not in detected and all(re.match(r'^ops_?\d+$', v, re.I) for v in vals if v):
                detected['opsId'] = c
                continue

            # Check for Zone (A, B, C, ALL, TBS, MS, INTERSOC, RETURN, Supervisor)
            zone_keywords = {'a', 'b', 'c', 'all', 'tbs', 'ms', 'intersoc', 'return', 'supervisor', 'sup'}
            if 'zone' not in detected and sum(1 for v in vals if v.lower() in zone_keywords) >= len(vals) * 0.6:
                detected['zone'] = c
                continue

            # Check for Position (Supervisor, Agent, Support, SOC, Lead, etc.)
            pos_keywords = ['supervisor', 'agent', 'support', 'soc', 'lead', 'manager', 'associate', 'act.', 'senior']
            if 'position' not in detected and any(any(pk in v.lower() for pk in pos_keywords) for v in vals):
                detected['position'] = c
                continue

        # Remaining columns mapping for Names
        remaining_cols = [c for c in range(max_cols) if c not in detected.values()]
        # Check if first col is just row index (1, 2, 3...)
        if 0 in remaining_cols:
            first_vals = [str(r[0]).strip() for r in sample if len(r) > 0 and str(r[0]).strip()]
            if all(v.isdigit() and len(v) <= 4 for v in first_vals if v):
                remaining_cols.remove(0)

        thai_cols = []
        nick_col = None
        for c in remaining_cols:
            vals = [str(r[c]).strip() for r in sample if c < len(r) and str(r[c]).strip() and str(r[c]).strip().lower() != 'nan']
            # English letters / short string -> Nickname
            if nick_col is None and any(re.search(r'[a-zA-Z]', v) for v in vals):
                nick_col = c
            else:
                thai_cols.append(c)

        if nick_col is not None and 'nickname' not in detected:
            detected['nickname'] = nick_col
        if 'firstName' not in detected and len(thai_cols) >= 1:
            detected['firstName'] = thai_cols[0]
        if 'lastName' not in detected and len(thai_cols) >= 2:
            detected['lastName'] = thai_cols[1]

        col_map = detected

    staff_list = []
    roster_by_zone = {
        'ALL': [], 'A': [], 'B': [], 'C': [], 'TBS': [], 'MS': [], 'INTERSOC': [], 'RETURN': []
    }

    for r in data_rows:
        if not any(str(c).strip() and str(c).strip().lower() != 'nan' for c in r):
            continue
        get_val = lambda k: str(r[col_map[k]]).strip() if k in col_map and col_map[k] < len(r) and str(r[col_map[k]]).strip().lower() != 'nan' else ''
        emp_id = get_val('empId')
        nick = get_val('nickname') or get_val('firstName')
        zone_raw = get_val('zone').upper().strip() or 'ALL'

        if not nick and not emp_id:
            continue

        zone = zone_raw
        if 'INTER' in zone:
            zone = 'INTERSOC'
        elif 'RET' in zone:
            zone = 'RETURN'
        elif zone in ['SUPERVISOR', 'SUP', 'HEAD', 'ALL', 'ALL_SOC']:
            zone = 'ALL'

        pos = get_val('position')
        if not zone or zone == 'NAN':
            if 'supervisor' in pos.lower():
                zone = 'ALL'
            else:
                zone = 'A'

        staff_entry = {
            'empId': emp_id,
            'opsId': get_val('opsId'),
            'firstName': get_val('firstName'),
            'lastName': get_val('lastName'),
            'nickname': nick,
            'position': pos,
            'zone': zone
        }
        staff_list.append(staff_entry)

        if zone not in roster_by_zone:
            roster_by_zone[zone] = []
        if nick and nick not in roster_by_zone[zone]:
            roster_by_zone[zone].append(nick)

    return {
        "updatedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "rosterByZone": roster_by_zone,
        "staffList": staff_list
    }


@app.route("/api/staff-roster", methods=["GET"])
def get_staff_roster_api():
    data = load_staff_roster_data()
    return jsonify({
        "success": True,
        "updatedAt": data.get("updatedAt", ""),
        "rosterByZone": data.get("rosterByZone", {}),
        "staffList": data.get("staffList", [])
    })


@app.route("/api/staff-roster/upload", methods=["POST"])
def upload_staff_roster_api():
    if "file" not in request.files:
        return jsonify({"success": False, "error": "ไม่พบไฟล์ที่อัปโหลด"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"success": False, "error": "ไม่ได้เลือกไฟล์"}), 400

    filename = os.path.basename(file.filename)
    if not filename.lower().endswith(('.xlsx', '.xls', '.csv')):
        return jsonify({"success": False, "error": "กรุณาอัปโหลดไฟล์ประเภท Excel (.xlsx, .xls) หรือ CSV เท่านั้น"}), 400

    temp_path = os.path.join(UPLOAD_FOLDER, f"temp_roster_{filename}")
    try:
        file.save(temp_path)
        parsed = parse_staff_roster_file(temp_path)
        if not parsed or not parsed.get("staffList"):
            return jsonify({"success": False, "error": "ไม่สามารถอ่านโครงสร้างรายชื่อพนักงานจากไฟล์ได้ กรุณาตรวจสอบหัวตาราง"}), 400

        save_staff_roster_data(parsed)
        log_activity("STAFF_ROSTER_UPLOAD", f"👷 อัปโหลดและอัปเดต Staff Roster ({len(parsed['staffList'])} คน) จากไฟล์: {filename}")
        
        try:
            os.remove(temp_path)
        except Exception:
            pass

        return jsonify({
            "success": True,
            "message": f"อัปเดต Staff Roster เรียบร้อยแล้ว ({len(parsed['staffList'])} รายการ)",
            "updatedAt": parsed["updatedAt"],
            "rosterByZone": parsed["rosterByZone"],
            "staffList": parsed["staffList"]
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": f"เกิดข้อผิดพลาดในการประมวลผลไฟล์: {str(e)}"}), 500


@app.route("/api/staff-roster/member", methods=["POST", "DELETE"])
def manage_staff_member_api():
    data = load_staff_roster_data()
    staff_list = data.get("staffList", [])
    roster_by_zone = data.get("rosterByZone", {})

    if request.method == "POST":
        req = request.get_json(silent=True) or {}
        emp_id = (req.get("empId") or "").strip()
        nickname = (req.get("nickname") or req.get("firstName") or "").strip()
        zone = (req.get("zone") or "ALL").strip().upper()
        ops_id = (req.get("opsId") or "").strip()
        first_name = (req.get("firstName") or "").strip()
        last_name = (req.get("lastName") or "").strip()
        position = (req.get("position") or "").strip()

        if not nickname and not emp_id:
            return jsonify({"success": False, "error": "กรุณาระบุรหัสพนักงานหรือชื่อเล่น"}), 400

        # Update or Insert
        existing_idx = -1
        for idx, s in enumerate(staff_list):
            if (emp_id and s.get("empId") == emp_id) or (nickname and s.get("nickname") == nickname and s.get("zone") == zone):
                existing_idx = idx
                break

        new_entry = {
            "empId": emp_id,
            "opsId": ops_id,
            "firstName": first_name,
            "lastName": last_name,
            "nickname": nickname,
            "position": position,
            "zone": zone
        }

        if existing_idx >= 0:
            staff_list[existing_idx] = new_entry
        else:
            staff_list.append(new_entry)

        # Re-sync rosterByZone
        new_roster_by_zone = {'ALL': [], 'A': [], 'B': [], 'C': [], 'TBS': [], 'MS': [], 'INTERSOC': [], 'RETURN': []}
        for s in staff_list:
            z = s.get("zone", "ALL").upper()
            nk = s.get("nickname")
            if z not in new_roster_by_zone:
                new_roster_by_zone[z] = []
            if nk and nk not in new_roster_by_zone[z]:
                new_roster_by_zone[z].append(nk)

        data["staffList"] = staff_list
        data["rosterByZone"] = new_roster_by_zone
        save_staff_roster_data(data)
        log_activity("STAFF_MEMBER_SAVE", f"บันทึกข้อมูลพนักงาน: {nickname} (Zone {zone})")

        return jsonify({
            "success": True,
            "message": f"บันทึกข้อมูล {nickname} เรียบร้อย",
            "staffList": staff_list,
            "rosterByZone": new_roster_by_zone
        })

    elif request.method == "DELETE":
        req = request.get_json(silent=True) or {}
        emp_id = (req.get("empId") or "").strip()
        nickname = (req.get("nickname") or "").strip()

        if not emp_id and not nickname:
            return jsonify({"success": False, "error": "ไม่ได้ระบุพนักงานที่ต้องการลบ"}), 400

        staff_list = [s for s in staff_list if not ((emp_id and s.get("empId") == emp_id) or (nickname and s.get("nickname") == nickname))]

        new_roster_by_zone = {'ALL': [], 'A': [], 'B': [], 'C': [], 'TBS': [], 'MS': [], 'INTERSOC': [], 'RETURN': []}
        for s in staff_list:
            z = s.get("zone", "ALL").upper()
            nk = s.get("nickname")
            if z not in new_roster_by_zone:
                new_roster_by_zone[z] = []
            if nk and nk not in new_roster_by_zone[z]:
                new_roster_by_zone[z].append(nk)

        data["staffList"] = staff_list
        data["rosterByZone"] = new_roster_by_zone
        save_staff_roster_data(data)
        log_activity("STAFF_MEMBER_DELETE", f"ลบพนักงานออกจาก Roster: {emp_id or nickname}")

        return jsonify({
            "success": True,
            "message": "ลบพนักงานเรียบร้อย",
            "staffList": staff_list,
            "rosterByZone": new_roster_by_zone
        })

CUSTOM_CUTOFF_FILE = os.path.join(DATA_DIR, "custom_cutoff_schedule.json")

def infer_cutoff_zone(row_data, area_group=""):
    # 1. Check explicit zone columns from uploaded or row data
    for k in ["Zone", "zone", "OBD ZONE", "OBD Zone", "obd_zone", "Zone Group", "zone_group"]:
        if k in row_data and row_data[k] and str(row_data[k]).strip().lower() not in ["", "nan", "none"]:
            val = str(row_data[k]).strip().upper()
            if val in ["A", "ZONE A", "ZONE_A"]: return "Zone A"
            if val in ["B", "ZONE B", "ZONE_B"]: return "Zone B"
            if val in ["C", "ZONE C", "ZONE_C"]: return "Zone C"
            if "INTER" in val: return "Zone InterSOC"
            if "RET" in val: return "Zone Return"
            if not val.startswith("Zone ") and len(val) <= 4:
                return f"Zone {val}"
            return str(row_data[k]).strip()
    
    # 2. Look up from Hub Master database (where both GBKK and UPC stations are mapped to OBD Zone)
    station_name = str(row_data.get("station_name") or row_data.get("LM Station Name") or "").strip()
    station_id = str(row_data.get("station_id") or row_data.get("LM Station ID") or "").replace(".0", "").strip()
    
    hub_map = build_hub_zone_map()
    resolved_z = None
    if station_id and station_id.lower() in hub_map:
        resolved_z = hub_map[station_id.lower()]
    elif station_name:
        resolved_z = lookup_obd_zone(station_name, hub_map)
        
    if resolved_z:
        if resolved_z == 'A': return "Zone A"
        if resolved_z == 'B': return "Zone B"
        if resolved_z == 'C': return "Zone C"
        if resolved_z == 'INTERSOC': return "Zone InterSOC"
        if resolved_z == 'RETURN': return "Zone Return"
        return f"Zone {resolved_z}"

    return "Zone A"


@app.route("/api/cutoff-schedule", methods=["GET"])
def get_cutoff_schedule_api():
    # If custom uploaded cutoff file exists, load it
    if os.path.exists(CUSTOM_CUTOFF_FILE):
        try:
            with open(CUSTOM_CUTOFF_FILE, "r", encoding="utf-8") as f:
                custom_data = json.load(f)
                if isinstance(custom_data, list) and len(custom_data) > 0:
                    return jsonify({
                        "success": True,
                        "is_custom": True,
                        "total": len(custom_data),
                        "data": custom_data,
                        "updatedAt": datetime.fromtimestamp(os.path.getmtime(CUSTOM_CUTOFF_FILE)).strftime("%Y-%m-%d %H:%M:%S")
                    })
        except Exception as e:
            print("Error loading custom cutoff file:", e)

    # Fallback to source files
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
                entry['zone'] = infer_cutoff_zone(entry, area_type)
                if 'Sunday Cut' in df.columns:
                    entry['sun_ob'] = str(row.get('Sunday Cut', '') or '' if pd.notna(row.get('Sunday Cut')) else '')
                    entry['sun_arr'] = str(row.get('Unnamed: 25', '') or '' if pd.notna(row.get('Unnamed: 25')) else '')
                    entry['sun_rec'] = str(row.get('Unnamed: 26', '') or '' if pd.notna(row.get('Unnamed: 26')) else '')
                    entry['sun_travel'] = str(row.get('Unnamed: 27', '') or '' if pd.notna(row.get('Unnamed: 27')) else '')
                cutoff_list.append(entry)
        except Exception as e:
            print("Error parsing cutoff file", path, e)
    return jsonify({"success": True, "is_custom": False, "total": len(cutoff_list), "data": cutoff_list})


@app.route("/api/cutoff-schedule/upload", methods=["POST"])
def upload_cutoff_schedule_api():
    if "file" not in request.files:
        return jsonify({"success": False, "error": "ไม่พบไฟล์ที่อัปโหลด"}), 400
    
    file = request.files["file"]
    if not file or not file.filename:
        return jsonify({"success": False, "error": "ชื่อไฟล์ไม่ถูกต้อง"}), 400
        
    filename = file.filename.lower()
    if not (filename.endswith('.xlsx') or filename.endswith('.xls') or filename.endswith('.csv')):
        return jsonify({"success": False, "error": "รองรับเฉพาะไฟล์ Excel (.xlsx, .xls) หรือ CSV (.csv) เท่านั้น"}), 400

    try:
        temp_path = os.path.join(UPLOAD_FOLDER, f"cutoff_upload_{int(time.time())}_{file.filename}")
        file.save(temp_path)
        
        parsed_list = []
        if filename.endswith('.csv'):
            df = pd.read_csv(temp_path, on_bad_lines='skip')
            dfs = [("Cutoff Master", df)]
        else:
            xl = pd.ExcelFile(temp_path)
            dfs = []
            for sheet in xl.sheet_names:
                dfs.append((sheet, xl.parse(sheet)))

        for sheet_name, df in dfs:
            if df.empty: continue
            
            # Map column names flexibly
            col_map = {}
            for col in df.columns:
                c_clean = str(col).strip().lower().replace("_", " ").replace("-", " ")
                if any(k in c_clean for k in ["station name", "station_name", "สถานี", "ชื่อสถานี"]):
                    col_map["station_name"] = col
                elif any(k in c_clean for k in ["station id", "station_id", "รหัสสถานี", "lm station id"]):
                    col_map["station_id"] = col
                elif any(k in c_clean for k in ["zone", "โซน", "obd zone"]):
                    col_map["zone"] = col
                elif any(k in c_clean for k in ["area group", "สายงาน", "กลุ่มสายงาน"]):
                    col_map["area_group"] = col
                elif any(k in c_clean for k in ["province", "จังหวัด"]):
                    col_map["province"] = col
                elif any(k in c_clean for k in ["district", "อำเภอ"]):
                    col_map["district"] = col
                elif any(k in c_clean for k in ["cut 0", "cut0", "รอบ 0", "c0"]):
                    col_map["cut0_ob"] = col
                elif any(k in c_clean for k in ["cut 1", "cut1", "รอบ 1", "c1"]):
                    col_map["cut1_ob"] = col
                elif any(k in c_clean for k in ["cut 2", "cut2", "รอบ 2", "c2"]):
                    col_map["cut2_ob"] = col
                elif any(k in c_clean for k in ["cut 3", "cut3", "รอบ 3", "c3"]):
                    col_map["cut3_ob"] = col
                elif any(k in c_clean for k in ["sunday", "sun cut", "รอบวันอาทิตย์"]):
                    col_map["sun_ob"] = col
                elif any(k in c_clean for k in ["op type", "operation type", "ประเภท"]):
                    col_map["op_type"] = col
            
            # If standard station_name not matched, try finding first string column with 'Station'
            if "station_name" not in col_map:
                for col in df.columns:
                    if "station" in str(col).lower():
                        col_map["station_name"] = col
                        break

            for _, row in df.iterrows():
                st_name = str(row.get(col_map.get("station_name", "LM Station Name"), "") or "").strip()
                if not st_name or st_name.lower() in ["nan", "none", "lm station name"]:
                    continue

                area_grp = str(row.get(col_map.get("area_group", "Area Group"), sheet_name) or sheet_name).strip()
                item_zone = str(row.get(col_map.get("zone", "Zone"), "") or "").strip()
                if not item_zone or item_zone.lower() in ["nan", "none"]:
                    item_zone = infer_cutoff_zone(row.to_dict(), area_grp)

                entry = {
                    "station_name": st_name,
                    "station_id": str(row.get(col_map.get("station_id", "LM Station ID"), "") or "").replace(".0", "").strip(),
                    "zone": item_zone,
                    "area_group": area_grp,
                    "area": str(row.get("Area", "") or "").strip(),
                    "province": str(row.get(col_map.get("province", "Province"), "") or "").strip(),
                    "district": str(row.get(col_map.get("district", "District"), "") or "").strip(),
                    "op_type": str(row.get(col_map.get("op_type", "Operation Type"), "") or "").strip(),
                    "cut0_ob": str(row.get(col_map.get("cut0_ob", "Cut 0"), "") or "").strip(),
                    "cut0_arr": str(row.get("Cut 0 Arrival", "") or "").strip(),
                    "cut0_travel": str(row.get("Cut 0 Travel", "") or "").strip(),
                    "cut1_ob": str(row.get(col_map.get("cut1_ob", "Cut 1"), "") or "").strip(),
                    "cut1_arr": str(row.get("Cut 1 Arrival", "") or "").strip(),
                    "cut1_rec": str(row.get("Cut 1 Received", "") or "").strip(),
                    "cut1_travel": str(row.get("Cut 1 Travel", "") or "").strip(),
                    "cut2_ob": str(row.get(col_map.get("cut2_ob", "Cut 2"), "") or "").strip(),
                    "cut2_arr": str(row.get("Cut 2 Arrival", "") or "").strip(),
                    "cut2_rec": str(row.get("Cut 2 Received", "") or "").strip(),
                    "cut2_travel": str(row.get("Cut 2 Travel", "") or "").strip(),
                    "cut3_ob": str(row.get(col_map.get("cut3_ob", "Cut 3"), "") or "").strip(),
                    "cut3_arr": str(row.get("Cut 3 Arrival", "") or "").strip(),
                    "cut3_travel": str(row.get("Cut 3 Travel", "") or "").strip(),
                    "sun_ob": str(row.get(col_map.get("sun_ob", "Sunday Cut"), "") or "").strip()
                }
                parsed_list.append(entry)

        if not parsed_list:
            return jsonify({"success": False, "error": "ไม่พบข้อมูลสถานีในไฟล์ที่อัปโหลด กรุณาตรวจสอบหัวตาราง"}), 400

        with open(CUSTOM_CUTOFF_FILE, "w", encoding="utf-8") as f:
            json.dump(parsed_list, f, ensure_ascii=False, indent=2)

        log_activity("CUTOFF_MASTER_UPLOAD", f"อัปโหลดและอัปเดตไฟล์ Cut-off Master ({len(parsed_list)} สถานี): {file.filename}")

        return jsonify({
            "success": True,
            "message": f"อัปโหลดและอัปเดตข้อมูล Cut-off Master สำเร็จ ({len(parsed_list):,} สถานี)",
            "total": len(parsed_list),
            "data": parsed_list
        })
    except Exception as e:
        return jsonify({"success": False, "error": f"เกิดข้อผิดพลาดในการประมวลผลไฟล์: {str(e)}"}), 500


TTB_REGISTRATION_FILE = os.path.join(DATA_DIR, "ttb_registration_live.json")

def load_ttb_registration_live():
    if os.path.exists(TTB_REGISTRATION_FILE):
        try:
            with open(TTB_REGISTRATION_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print("Error loading TTB live registration file:", e)
    return {"updatedAt": "", "total": 0, "rows": []}

def save_ttb_registration_live(data):
    try:
        with open(TTB_REGISTRATION_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print("Error saving TTB live registration file:", e)
        return False

@app.route("/api/ttb-registration/config", methods=["GET", "POST"])
def ttb_registration_config_api():
    settings = load_system_settings()
    if request.method == "POST":
        data = request.get_json() or {}
        url = (data.get("url") or "").strip()
        apps_script_url = (data.get("appsScriptUrl") or "").strip()
        write_target_url = (data.get("writeTargetUrl") or "").strip()
        auto_sync = bool(data.get("autoSync", True))
        interval = int(data.get("intervalMinutes", 10))
        
        current_cfg = settings.get("ttbSync", {})
        settings["ttbSync"] = {
            "url": url or current_cfg.get("url", ""),
            "appsScriptUrl": apps_script_url or current_cfg.get("appsScriptUrl", ""),
            "writeTargetUrl": write_target_url or current_cfg.get("writeTargetUrl", "https://docs.google.com/spreadsheets/d/1fcW2_deyDFDN9Dp9JfOv1NOinS1de6KMDcNZp2EOL9w/edit?gid=719250654#gid=719250654"),
            "autoSync": auto_sync,
            "intervalMinutes": interval,
            "updatedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        save_system_settings(settings)
        log_activity("TTB_SYNC_CONFIG", f"ตั้งค่าการเชื่อมต่อ TTB Google Sheet: Read URL={url[:30]}..., Apps Script={apps_script_url[:30]}...")
        return jsonify({"success": True, "message": "บันทึกการตั้งค่า TTB Google Sheet Sync เรียบร้อยแล้ว", "config": settings["ttbSync"]})

    return jsonify({"success": True, "config": settings.get("ttbSync", {
        "url": "",
        "appsScriptUrl": "",
        "writeTargetUrl": "https://docs.google.com/spreadsheets/d/1fcW2_deyDFDN9Dp9JfOv1NOinS1de6KMDcNZp2EOL9w/edit?gid=719250654#gid=719250654",
        "autoSync": True,
        "intervalMinutes": 10,
        "updatedAt": ""
    })})

def process_and_save_ttb_rows(raw_rows, source_sheet_name="TTB - Registration"):
    cutoff_master_entries = []
    zone_a_count = 0
    zone_b_count = 0
    zone_c_count = 0
    on_time_count = 0
    late_count = 0
    new_trips_count = 0

    for r in raw_rows:
        dest = str(r.get("destination") or "").strip()
        if not dest or dest.lower() in ["nan", "none", "#n/a"]:
            continue
            
        zone = str(r.get("obZone") or "").strip().upper()
        if not zone.startswith("ZONE"):
            if zone in ["A", "B", "C"]: zone = f"Zone {zone}"
            elif not zone: zone = infer_cutoff_zone({"station_name": dest}, "TTB")
            
        if "Zone A" in zone: zone_a_count += 1
        elif "Zone B" in zone: zone_b_count += 1
        elif "Zone C" in zone: zone_c_count += 1

        arr_status = str(r.get("arrivalStatus") or "").strip().lower()
        if "late" in arr_status: late_count += 1
        elif "on-time" in arr_status or "on time" in arr_status: on_time_count += 1

        if r.get("newTrip") or r.get("remarkLh"):
            new_trips_count += 1

        # Extract clean station code and province (e.g., 'ABKEN-B - บางเขน' -> code: 'ABKEN-B', prov: 'บางเขน')
        parts = [p.strip() for p in dest.split("-") if p.strip()]
        if len(parts) >= 3 and len(parts[1]) <= 2:
            st_code = f"{parts[0]}-{parts[1]}"
            prov = parts[-1]
        elif len(parts) >= 2:
            st_code = parts[0]
            prov = parts[-1]
        else:
            st_code = dest
            prov = ""
        
        cutoff_time = str(r.get("cutoff") or "").strip()
        driver_id_val = str(r.get("driverId") or "").replace(".0", "").strip()
        if not driver_id_val or driver_id_val.upper() in ["#N/A", "NAN", "NONE"]:
            driver_id_val = st_code
        
        cutoff_entry = {
            "station_name": dest,
            "station_code": st_code,
            "station_id": driver_id_val,
            "zone": zone,
            "area_group": "TTB Registration",
            "area": str(r.get("route") or "").strip(),
            "province": prov,
            "district": "",
            "op_type": str(r.get("vehicleType") or r.get("truckTypeReq") or "").strip(),
            "dock": str(r.get("dock") or "").strip(),
            "subcon": str(r.get("subcon") or "").strip(),
            "lh_trip": str(r.get("lhTrip") or "").strip(),
            "standby_time": str(r.get("standbyTime") or "").strip(),
            "loading_time": str(r.get("loadingTime") or "").strip(),
            "depart_time": str(r.get("departureTime") or "").strip(),
            "cut0_ob": cutoff_time if cutoff_time else "-",
            "cut1_ob": cutoff_time if cutoff_time else "-",
            "cut2_ob": "-",
            "cut3_ob": "-",
            "sun_ob": "-",
            "plate": str(r.get("plate") or "").strip(),
            "driver_name": str(r.get("driverName") or "").strip(),
            "new_trip": str(r.get("newTrip") or "").strip(),
            "remark_lh": str(r.get("remarkLh") or "").strip(),
            "remark_ob": str(r.get("remarkOb") or "").strip(),
            "late_type": str(r.get("lateType") or "").strip()
        }
        cutoff_master_entries.append(cutoff_entry)

    # Save to custom_cutoff_schedule.json for Cutoff Master page
    if cutoff_master_entries:
        with open(CUSTOM_CUTOFF_FILE, "w", encoding="utf-8") as f:
            json.dump(cutoff_master_entries, f, ensure_ascii=False, indent=2)

    # Save to ttb_registration_live.json for full live details
    live_data = {
        "updatedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "sourceSheet": source_sheet_name,
        "total": len(raw_rows),
        "stats": {
            "totalTrips": len(raw_rows),
            "totalStations": len(cutoff_master_entries),
            "zoneA": zone_a_count,
            "zoneB": zone_b_count,
            "zoneC": zone_c_count,
            "onTime": on_time_count,
            "late": late_count,
            "newTripsOrRemarks": new_trips_count
        },
        "rows": raw_rows
    }
    save_ttb_registration_live(live_data)
    log_activity("TTB_SHEET_SYNC", f"🔄 ซิงค์ข้อมูล TTB Registration สำเร็จ ({len(raw_rows):,} คัน, {len(cutoff_master_entries)} สถานี)")
    return live_data

@app.route("/api/ttb-registration/save-client-data", methods=["POST"])
def save_client_ttb_data_api():
    req_json = request.get_json() or {}
    raw_rows = req_json.get("rows", [])
    sheet_name = req_json.get("sheetName", "TTB - Registration")
    if not raw_rows:
        return jsonify({"success": False, "error": "ไม่มีข้อมูลแถวที่ส่งมา"}), 400
        
    live_data = process_and_save_ttb_rows(raw_rows, sheet_name)
    return jsonify({
        "success": True,
        "message": f"ซิงค์ข้อมูลผ่าน Browser สำเร็จ ({len(raw_rows):,} แถว, อัปเดต {live_data['stats']['totalStations']} สถานี)",
        "data": live_data
    })

@app.route("/api/ttb-registration/sync", methods=["GET", "POST"])
def ttb_registration_sync_api():
    import requests, csv, io
    settings = load_system_settings()
    ttb_cfg = settings.get("ttbSync", {})
    
    # Priority: Request body/param URL > Saved Settings URL
    url = request.args.get("url") or ""
    if not url and request.is_json:
        url = (request.get_json() or {}).get("url", "")
    if not url:
        url = ttb_cfg.get("url", "")
        
    if not url:
        return jsonify({"success": False, "error": "ยังไม่ได้ระบุ Google Apps Script Web App URL หรือ Google Sheet CSV URL กรุณาตั้งค่าในระบบก่อน"}), 400

    try:
        # Check if URL is standard Google Sheet URL -> convert to CSV export if so
        is_sheet_csv = "output=csv" in url or "export?format=csv" in url or "gviz/tq" in url
        if "docs.google.com/spreadsheets/d/" in url and not is_sheet_csv:
            # Auto-convert standard spreadsheet URL to CSV export URL
            sheet_id_match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", url)
            gid_match = re.search(r"[#&?]gid=([0-9]+)", url)
            if sheet_id_match:
                s_id = sheet_id_match.group(1)
                gid = gid_match.group(1) if gid_match else "0"
                url = f"https://docs.google.com/spreadsheets/d/{s_id}/export?format=csv&gid={gid}"
                is_sheet_csv = True

        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=25, allow_redirects=True)
        if resp.status_code != 200:
            return jsonify({"success": False, "requiresClientFetch": True, "url": url, "error": f"Google Sheets ตอบกลับด้วย HTTP Code {resp.status_code}"}), 502
            
        resp.encoding = "utf-8"
        raw_text = resp.content.decode("utf-8", errors="replace").strip()
        
        # Detect Google Login Redirect / Permission error
        if "accounts.google.com" in resp.url or "Sign in - Google Accounts" in raw_text or "ServiceLogin" in resp.url:
            return jsonify({
                "success": False,
                "requiresClientFetch": True,
                "url": url,
                "error": "ติดสิทธิ์โดเมนองค์กร (spxexpress.com): ระบบจะสลับไปดึงผ่าน Browser Session ของคุณให้อัตโนมัติ"
            }), 403

        raw_rows = []
        source_sheet_name = "TTB - Registration"

        if is_sheet_csv or not raw_text.startswith("{"):
            # Parse as CSV
            csv_reader = list(csv.reader(io.StringIO(raw_text)))
            if len(csv_reader) < 2:
                return jsonify({"success": False, "error": "ไม่พบข้อมูลแถวใน Google Sheet CSV"}), 400
                
            # Find header row dynamically (look for 'LH Trips' or 'Destination' or 'Cutoff')
            header_row_idx = 1 # Default row 2
            col_map = {}
            for r_idx in range(min(5, len(csv_reader))):
                row_cells = [str(c).strip().lower() for c in csv_reader[r_idx]]
                if any("lh" in c for c in row_cells) or any("destination" in c for c in row_cells):
                    header_row_idx = r_idx
                    for c_i, c_val in enumerate(row_cells):
                        if c_val in ["driver id", "รหัสคนขับ"]: col_map.setdefault("driverId", c_i)
                        elif any(x in c_val for x in ["ชื่อพนักงาน", "driver name", "ชื่อ พนักงาน"]): col_map.setdefault("driverName", c_i)
                        elif c_val in ["ทะเบียน", "plate"]: col_map.setdefault("plate", c_i)
                        elif c_val in ["ประเภทรถ", "truck type"]: col_map.setdefault("vehicleType", c_i)
                        elif c_val == "status": col_map.setdefault("status", c_i)
                        elif "assign" in c_val: col_map.setdefault("assignStatus", c_i)
                        elif c_val in ["lh trips", "lh trip", "lh_trip", "lh"]: col_map.setdefault("lhTrip", c_i)
                        elif c_val in ["standby time", "standby"]: col_map.setdefault("standbyTime", c_i)
                        elif c_val in ["loding time", "loading time", "loading"]: col_map.setdefault("loadingTime", c_i)
                        elif c_val in ["departure time", "depart time", "departure", "depart"] and "plan" not in c_val: col_map.setdefault("departureTime", c_i)
                        elif c_val in ["destination", "ปลายทาง", "สถานี"]: col_map.setdefault("destination", c_i)
                        elif c_val in ["dock", "ช่องจอด"] and "docked" not in c_val: col_map.setdefault("dock", c_i)
                        elif c_val in ["subcon", "sub contractor"]: col_map.setdefault("subcon", c_i)
                        elif c_val in ["สาย", "route"]: col_map.setdefault("route", c_i)
                        elif c_val in ["new trip", "new_trip"]: col_map.setdefault("newTrip", c_i)
                        elif c_val in ["เตือน", "alert"]: col_map.setdefault("warningAlert", c_i)
                        elif c_val in ["remark lh", "ว.สลับรถ"] or "สลับรถ" in c_val: col_map.setdefault("remarkLh", c_i)
                        elif c_val in ["ob zone", "obzone", "zone"]: col_map.setdefault("obZone", c_i)
                        elif c_val in ["arrival on-time/late", "arrival status", "arrival"] or "on-time/late" in c_val: col_map.setdefault("arrivalStatus", c_i)
                        elif c_val in ["remark ob", "remark_ob"]: col_map.setdefault("remarkOb", c_i)
                        elif c_val in ["late type", "late_type"]: col_map.setdefault("lateType", c_i)
                        elif c_val == "cot": col_map.setdefault("cot", c_i)
                        elif c_val in ["cutoff", "cut-off", "cut off"] and "2" not in c_val: col_map.setdefault("cutoff", c_i)
                        elif c_val in ["booked time", "booked"]: col_map.setdefault("bookedTime", c_i)
                    break

            start_idx = header_row_idx + 1
            for i in range(start_idx, len(csv_reader)):
                r = csv_reader[i]
                if not r or len(r) < 3: continue
                
                get_c = lambda k, default_idx: str(r[col_map.get(k, default_idx)] if len(r) > col_map.get(k, default_idx) else "").strip()
                
                lh_trip = get_c("lhTrip", 10)
                dest = get_c("destination", 16)
                if not lh_trip and not dest: continue

                raw_rows.append({
                    "rowIndex": i + 1,
                    "driverId": get_c("driverId", 1),
                    "driverName": get_c("driverName", 2),
                    "plate": get_c("plate", 3),
                    "vehicleType": get_c("vehicleType", 4),
                    "status": get_c("status", 8),
                    "assignStatus": get_c("assignStatus", 9),
                    "lhTrip": lh_trip,
                    "standbyTime": get_c("standbyTime", 13),
                    "loadingTime": get_c("loadingTime", 14),
                    "departureTime": get_c("departureTime", 15),
                    "destination": dest,
                    "truckTypeReq": get_c("truckTypeReq", 17),
                    "wheels": get_c("wheels", 17),
                    "dock": get_c("dock", 19),
                    "subcon": get_c("subcon", 20),
                    "route": get_c("route", 20),
                    "cot": get_c("cot", 21),
                    "newTrip": get_c("newTrip", 22),
                    "remarkLh": get_c("remarkLh", 23),
                    "warningAlert": get_c("warningAlert", 23),
                    "obZone": get_c("obZone", 24),
                    "arrivalStatus": get_c("arrivalStatus", 25),
                    "remarkOb": get_c("remarkOb", 26),
                    "lateType": get_c("lateType", 27),
                    "cutoff": get_c("cutoff", 29),
                    "dockedTime": get_c("dockedTime", 30),
                    "planDeparture": get_c("planDeparture", 31),
                    "completeTime": get_c("completeTime", 33)
                })
        else:
            try:
                data = json.loads(raw_text)
            except Exception as json_err:
                return jsonify({"success": False, "requiresClientFetch": True, "url": url, "error": f"ข้อมูลที่ได้รับไม่ใช่ JSON หรือ CSV ที่ถูกต้อง: {str(json_err)}"}), 502

            if not data.get("success") or "rows" not in data:
                return jsonify({"success": False, "error": data.get("error") or "โครงสร้างข้อมูลจาก Google Sheets ไม่ถูกต้อง"}), 502
            raw_rows = data.get("rows", [])
            source_sheet_name = data.get("sheetName", "TTB - Registration")

        live_data = process_and_save_ttb_rows(raw_rows, source_sheet_name)
        
        return jsonify({
            "success": True,
            "message": f"ซิงค์ข้อมูลจาก Google Sheets สำเร็จเรียบร้อยแล้ว ({len(raw_rows):,} แถว, อัปเดต {live_data['stats']['totalStations']} สถานี)",
            "data": live_data
        })
    except Exception as e:
        return jsonify({"success": False, "requiresClientFetch": True, "url": url, "error": f"เกิดข้อผิดพลาดในการเชื่อมต่อ Google Sheets: {str(e)}"}), 500

@app.route("/api/ttb-registration/live", methods=["GET"])
def get_ttb_registration_live_api():
    data = load_ttb_registration_live()
    return jsonify({"success": True, "data": data})

@app.route("/api/ttb-registration/update-row", methods=["POST"])
def update_ttb_registration_row_api():
    import requests
    req = request.get_json() or {}
    lh_trip = req.get("lhTrip", "").strip()
    row_idx = req.get("rowIndex")
    updates = req.get("updates", {})
    
    if not lh_trip and not row_idx:
        return jsonify({"success": False, "error": "กรุณาระบุ LH Trip หรือ Row Index ของแถวที่ต้องการแก้ไข"}), 400

    # 1. Update in local Live JSON Cache
    live_data = load_ttb_registration_live()
    rows = live_data.get("rows", [])
    found_row = None
    for r in rows:
        if (lh_trip and r.get("lhTrip") == lh_trip) or (row_idx and r.get("rowIndex") == row_idx):
            for k, v in updates.items():
                r[k] = v
            found_row = r
            break
            
    if found_row:
        # Re-save live data
        live_data["updatedAt"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        save_ttb_registration_live(live_data)
        
        # Also update Cutoff Master schedule if arrivalStatus / remark / cutoff / newTrip changed
        try:
            if os.path.exists(CUSTOM_CUTOFF_FILE):
                with open(CUSTOM_CUTOFF_FILE, "r", encoding="utf-8") as f:
                    cutoffs = json.load(f)
                for c in cutoffs:
                    if c.get("lh_trip") == lh_trip or (found_row.get("destination") and c.get("station_name") == found_row.get("destination")):
                        if "arrivalStatus" in updates: c["late_type"] = updates["arrivalStatus"]
                        if "remarkOb" in updates: c["remark_ob"] = updates["remarkOb"]
                        if "newTrip" in updates: c["new_trip"] = updates["newTrip"]
                        if "remarkLh" in updates: c["remark_lh"] = updates["remarkLh"]
                        if "dock" in updates: c["dock"] = updates["dock"]
                        if "plate" in updates: c["plate"] = updates["plate"]
                with open(CUSTOM_CUTOFF_FILE, "w", encoding="utf-8") as f:
                    json.dump(cutoffs, f, ensure_ascii=False, indent=2)
        except Exception as cutoff_err:
            print("Warning updating custom cutoff file:", cutoff_err)

    # 2. Write-back to Google Sheet via Apps Script Web App URL
    settings = load_system_settings()
    ttb_cfg = settings.get("ttbSync", {})
    apps_script_url = ttb_cfg.get("appsScriptUrl") or ttb_cfg.get("writeUrl") or ""
    
    # Check if main URL is a Web App URL (script.google.com)
    main_url = ttb_cfg.get("url", "")
    if "script.google.com" in main_url and not apps_script_url:
        apps_script_url = main_url

    sheet_write_status = "SAVED_LOCALLY"
    sheet_msg = "บันทึกลงในระบบเรียบร้อยแล้ว"
    
    if apps_script_url and "script.google.com" in apps_script_url:
        try:
            params = {
                "action": "UPDATE_ROW",
                "lhTrip": str(lh_trip or "").strip(),
                "rowIndex": str(row_idx or "").strip(),
                "arrivalStatus": str(updates.get("arrivalStatus") or "").strip(),
                "remarkOb": str(updates.get("remarkOb") or "").strip(),
                "newTrip": str(updates.get("newTrip") or "").strip(),
                "remarkLh": str(updates.get("remarkLh") or "").strip(),
                "dock": str(updates.get("dock") or "").strip(),
                "plate": str(updates.get("plate") or "").strip(),
                "driverName": str(updates.get("driverName") or "").strip(),
                "lateType": str(updates.get("lateType") or "").strip()
            }
            gs_resp = requests.get(apps_script_url, params=params, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
            if gs_resp.status_code == 200:
                try:
                    sheet_res = gs_resp.json()
                    if sheet_res.get("success"):
                        sheet_write_status = "SYNCED_TO_SHEET"
                        sheet_msg = f"✅ บันทึกและเขียนลง Google Sheet สำเร็จ (แถวที่ {sheet_res.get('rowIndex', row_idx)})"
                    else:
                        sheet_msg = f"⚠️ บันทึกในระบบแล้ว แต่ Google Sheet แจ้ง: {sheet_res.get('error')}"
                except Exception:
                    sheet_write_status = "SYNCED_TO_SHEET"
                    sheet_msg = "✅ ส่งคำขอเขียนข้อมูลลง Google Sheet สำเร็จ"
            else:
                sheet_msg = f"⚠️ บันทึกในระบบแล้ว (Apps Script ตอบกลับ Code {gs_resp.status_code})"
        except Exception as push_err:
            sheet_msg = f"⚠️ บันทึกในระบบแล้ว (ส่งไป Google Sheet ไม่สำเร็จ: {str(push_err)})"

    log_activity("TTB_ROW_UPDATE", f"✏️ อัปเดตข้อมูลทริป {lh_trip or row_idx}: Arrival={updates.get('arrivalStatus', '-')}, Remark={updates.get('remarkOb', '-')}")
    
    return jsonify({
        "success": True,
        "message": sheet_msg,
        "writeStatus": sheet_write_status,
        "row": found_row
    })

@app.route("/api/ttb-registration/push", methods=["POST"])
def push_ttb_registration_update_api():
    return update_ttb_registration_row_api()

def get_active_ttb_sheet(date_str):
    dt = None
    if date_str:
        try:
            dt = pd.to_datetime(date_str)
        except Exception:
            dt = None
    if dt is None or pd.isna(dt):
        dt = datetime.now()
    
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

@app.route("/ob-bl")
@app.route("/ob_bl.html")
@app.route("/ob-backlog")
def ob_bl_page():
    return send_from_directory(BASE_DIR, "ob_bl.html")

def process_ob_bl_df(df):
    headers = [str(c).strip() for c in df.columns]
    clean_df = df.fillna('')
    rows = clean_df.values.tolist()
    return {
        "success": True,
        "headers": headers,
        "rows": rows,
        "generatedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

@app.route("/api/load-ob-bl", methods=["GET"])
def load_ob_bl():
    filename = request.args.get("filename", "").strip()
    
    target = None
    if filename:
        t1 = os.path.join(UPLOAD_FOLDER, filename)
        t2 = os.path.join(BASE_DIR, filename)
        if os.path.exists(t1): target = t1
        elif os.path.exists(t2): target = t2

    if not target:
        candidates = ["LIVE_OB_BL_SYNC.csv", "LIVE_GOOGLE_SHEET_SYNC.csv"]
        for c in candidates:
            p = os.path.join(UPLOAD_FOLDER, c)
            if os.path.exists(p):
                target = p
                break

    if not target:
        csv_files = [f for f in os.listdir(UPLOAD_FOLDER) if f.endswith(".csv")]
        if csv_files:
            target = os.path.join(UPLOAD_FOLDER, csv_files[0])

    if not target or not os.path.exists(target):
        return jsonify({
            "success": False,
            "error": "ยังไม่มีไฟล์รายงาน OB BL ในระบบ (กรุณากดปุ่ม Sync Google Sheet หรือ อัปโหลด CSV/Excel)"
        }), 200

    try:
        if target.endswith((".xlsx", ".xls")):
            df = pd.read_excel(target)
        else:
            df = read_dataframe(target)
            
        data = process_ob_bl_df(df)
        data["filename"] = os.path.basename(target)
        return jsonify(data)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": f"ไม่สามารถประมวลผลไฟล์ OB BL ได้: {str(e)}"}), 200

GAS_OB_BL_URL = "https://script.google.com/a/spxexpress.com/macros/s/AKfycbxFOtGts0EfjNswnThfQhN57Q7zG5G6gPRGAG80lboIQfzhCh9W9t_d_uEP32Fi1Bc/exec"
GAS_API_KEY = "SOCN_OBBL_2026_SECRET_KEY_XK9M3"

@app.route("/api/sync-ob-bl-gas", methods=["POST"])
def sync_ob_bl_gas():
    """
    Server-side relay: ส่ง POST ไปหา Google Apps Script พร้อม API Key ลับ
    แก้ปัญหา domain restriction (/a/spxexpress.com/) — browser ยิงตรงไม่ได้
    """
    try:
        req_json = request.get_json(silent=True) or {}
        custom_url = (req_json.get("url") or "").strip()
        custom_key = (req_json.get("key") or "").strip()

        target_url = custom_url if custom_url else GAS_OB_BL_URL
        api_key = custom_key if custom_key else GAS_API_KEY

        payload = {"key": api_key, "page": "obbl"}

        resp = requests.post(
            target_url,
            json=payload,
            timeout=60,
            headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
            allow_redirects=True
        )

        if resp.status_code == 401:
            return jsonify({
                "success": False,
                "error": "HTTP 401: Google Apps Script ยังต้องการ Login\n\nกรุณาไปที่ Apps Script > Deploy > Manage Deployments > เปลี่ยน 'Who has access' เป็น 'Anyone' แล้ว Re-deploy"
            }), 200

        if resp.status_code != 200:
            return jsonify({"success": False, "error": f"Apps Script ตอบกลับ HTTP {resp.status_code}"}), 200

        # Check ถ้า Google redirect ไปหน้า login
        if (resp.content.strip().startswith(b"<!DOCTYPE html") or
                b"Sign in - Google Accounts" in resp.content or
                b"accounts.google.com" in resp.content):
            return jsonify({
                "success": False,
                "error": "Apps Script ยังติด Login Google ❌\n\nวิธีแก้:\n1. เปิด Apps Script > Deploy > Manage Deployments\n2. กด Edit (ดินสอ)\n3. เปลี่ยน 'Who has access' จาก 'Anyone with Google account' → 'Anyone'\n4. กด Deploy ใหม่\n5. คัดลอก URL ใหม่มาใช้"
            }), 200

        try:
            data = resp.json()
        except Exception:
            return jsonify({"success": False, "error": "Apps Script ไม่ได้ส่ง JSON กลับมา — ตรวจสอบ doPost() ใน Code.gs"}), 200

        if not data.get("success"):
            err_msg = data.get("error", "Apps Script ส่งข้อผิดพลาดกลับมา")
            return jsonify({"success": False, "error": err_msg}), 200

        # บันทึก cache ไว้ที่ server ด้วย
        if data.get("headers") and data.get("rows"):
            try:
                import csv as csv_lib
                cache_path = os.path.join(UPLOAD_FOLDER, "LIVE_OB_BL_SYNC.csv")
                with open(cache_path, "w", newline="", encoding="utf-8") as f:
                    writer = csv_lib.writer(f)
                    writer.writerow(data["headers"])
                    writer.writerows(data["rows"])
            except Exception:
                pass

        data["filename"] = "Live OB BL (Google Apps Script)"
        log_activity("SYNC_OB_BL_GAS", f"Synced OB BL via GAS API — {data.get('total', 0)} rows")
        return jsonify(data)

    except requests.Timeout:
        return jsonify({"success": False, "error": "Apps Script ใช้เวลานานเกินไป (Timeout 60s) — ข้อมูลอาจมีจำนวนมาก กรุณาลองใหม่"}), 200
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": f"เกิดข้อผิดพลาด server-side: {str(e)}"}), 200

@app.route("/api/sync-ob-bl", methods=["GET", "POST"])
def sync_ob_bl():
    req_json = request.get_json(silent=True) or {}
    url = (request.args.get("url") or req_json.get("url") or "").strip()
    if not url:
        url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRByU-6geOW_SbnQxFA4Y05WJMIkpRbUZMehfpDMTaHiXevL5mSA186BUybW3h8cgb4cWK2vOKuTIK3/pub?output=csv"

    import re
    gid_match = re.search(r'gid=([0-9]+)', url)
    gid_param = f"&gid={gid_match.group(1)}" if gid_match else ""

    if "/pubhtml" in url:
        url = url.replace("/pubhtml", "/pub?output=csv")
        if gid_match and "gid=" not in url:
            url += gid_param
    elif "docs.google.com/spreadsheets" in url and "gviz/tq" not in url and "export" not in url and "/pub" not in url:
        match = re.search(r'/d/e/([a-zA-Z0-9-_]+)', url) or re.search(r'/d/([a-zA-Z0-9-_]+)', url)
        if match:
            spreadsheet_id = match.group(1)
            url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/gviz/tq?tqx=out:csv{gid_param}"

    try:
        req = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"}, allow_redirects=True)
        if req.status_code == 401:
            return jsonify({
                "success": False,
                "error": "URL นี้ติดสิทธิ์เข้าถึงของ Google (HTTP 401 / Permission Required)\n\nกรุณาเลือกเปิดสิทธิ์อย่างใดอย่างหนึ่งดังนี้:\n1. หากเป็น Google Sheet: ไปที่ 'ไฟล์ (File)' > 'แชร์ (Share)' > 'เผยแพร่ไปยังเว็บ (Publish to web)' > เลือกแท็บ OB BL เป็น CSV แล้วกด 'เผยแพร่ (Publish)'\n2. หากเป็น Apps Script: ไปที่ 'Deploy' > 'Manage deployments' > เปลี่ยน 'Who has access' เป็น 'Anyone'"
            }), 200
        elif req.status_code != 200:
            return jsonify({"success": False, "error": f"ไม่สามารถเชื่อมต่อ URL ได้ (HTTP Status {req.status_code})"}), 200

        # Check if Google returned an HTML login redirect page instead of CSV/JSON
        if req.content.strip().startswith(b"<!DOCTYPE html") or req.content.strip().startswith(b"<html") or b"Sign in - Google Accounts" in req.content or b"accounts.google.com" in req.content:
            return jsonify({
                "success": False,
                "error": "URL นี้ติดสิทธิ์ล็อกอินของ Google (Google Accounts Required)\n\nกรุณาตั้งค่าเปิดสิทธิ์อย่างใดอย่างหนึ่งดังนี้ครับ:\n\n👉 วิธีที่ 1 (หากใช้ Apps Script Web App):\nไปที่หน้า Apps Script > กดปุ่ม 'Deploy' > 'Manage deployments' > ตรง 'Who has access (ผู้ที่มีสิทธิ์เข้าถึง)' เปลี่ยนเป็น 'Anyone (ทุกคน)' แล้วกด Deploy\n\n👉 วิธีที่ 2 (หากใช้ Google Sheet):\nไปที่ Google Sheet > 'ไฟล์ (File)' > 'แชร์ (Share)' > 'เผยแพร่ไปยังเว็บ (Publish to web)' > เลือกแท็บ OB BL เป็น CSV แล้วกด 'เผยแพร่ (Publish)'"
            }), 200

        try:
            json_resp = req.json()
            if isinstance(json_resp, dict) and ("rows" in json_resp or "headers" in json_resp):
                json_resp["success"] = True
                log_activity("SYNC_OB_BL", f"Successfully synced OB BL JSON data from {url}")
                return jsonify(json_resp)
        except Exception:
            pass

        target_path = os.path.join(UPLOAD_FOLDER, "LIVE_OB_BL_SYNC.csv")
        with open(target_path, "wb") as f:
            f.write(req.content)

        df = pd.read_csv(target_path, low_memory=False, on_bad_lines='skip')
        data = process_ob_bl_df(df)
        data["filename"] = "Live OB BL (Google Sheet)"
        data["success"] = True

        log_activity("SYNC_OB_BL", f"Successfully synced OB BL data from {url}")
        return jsonify(data)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": f"ไม่สามารถซิงค์ข้อมูล OB BL จาก URL ได้: {str(e)}"}), 200

# =======================================================================
# OB BACKLOG COMPARE API & PAGE ROUTES
# =======================================================================
@app.route("/ob-bl-compare")
@app.route("/ob_bl_compare.html")
def ob_bl_compare_page():
    return send_from_directory(BASE_DIR, "ob_bl_compare.html")

@app.route("/api/upload-compare-file", methods=["POST", "OPTIONS"])
@app.route("/upload-compare-file", methods=["POST", "OPTIONS"])
def upload_compare_file():
    if request.method == "OPTIONS":
        return jsonify({"success": True}), 200

    if "file" not in request.files:
        return jsonify({"success": False, "error": "ไม่ได้เลือกไฟล์"}), 400
    file = request.files["file"]
    if not file or file.filename == "":
        return jsonify({"success": False, "error": "ชื่อไฟล์ว่างเปล่า"}), 400

    filename = os.path.basename(file.filename)
    if not filename.lower().endswith((".csv", ".xlsx", ".xls")):
        return jsonify({"success": False, "error": "กรุณาอัปโหลดไฟล์ประเภท CSV หรือ Excel เท่านั้น"}), 400

    os.makedirs(BACKLOG_COMPARE_FOLDER, exist_ok=True)
    save_path = os.path.join(BACKLOG_COMPARE_FOLDER, filename)
    try:
        file.save(save_path)
        log_activity("UPLOAD_COMPARE_FILE", f"Uploaded compare file to Backlog Shipment: {filename}")
        return jsonify({"success": True, "filename": filename, "message": f"อัปโหลดไฟล์ {filename} เข้าสู่โฟลเดอร์ Backlog Shipment เรียบร้อยแล้ว"})
    except Exception as e:
        return jsonify({"success": False, "error": f"ไม่สามารถบันทึกไฟล์ได้: {str(e)}"}), 500

@app.route("/api/upload-compare-chunk", methods=["POST", "OPTIONS"])
@app.route("/upload-compare-chunk", methods=["POST", "OPTIONS"])
def upload_compare_chunk():
    if request.method == "OPTIONS":
        return jsonify({"success": True}), 200

    file_chunk = request.files.get("chunk")
    filename = (request.form.get("filename") or "").strip()
    chunk_index = int(request.form.get("chunk_index", 0))
    total_chunks = int(request.form.get("total_chunks", 1))

    if not file_chunk or not filename:
        return jsonify({"success": False, "error": "ข้อมูล chunk หรือชื่อไฟล์ไม่ถูกต้อง"}), 400

    filename = os.path.basename(filename)
    if not filename.lower().endswith((".csv", ".xlsx", ".xls")):
        return jsonify({"success": False, "error": "กรุณาอัปโหลดไฟล์ประเภท CSV หรือ Excel เท่านั้น"}), 400

    os.makedirs(BACKLOG_COMPARE_FOLDER, exist_ok=True)
    save_path = os.path.join(BACKLOG_COMPARE_FOLDER, filename)

    try:
        mode = "wb" if chunk_index == 0 else "ab"
        with open(save_path, mode) as f:
            f.write(file_chunk.read())

        if chunk_index == total_chunks - 1:
            log_activity("UPLOAD_COMPARE_FILE", f"Uploaded compare file (chunked) to Backlog Shipment: {filename}")
            return jsonify({
                "success": True,
                "completed": True,
                "filename": filename,
                "message": f"อัปโหลดไฟล์ {filename} เข้าสู่โฟลเดอร์ Backlog Shipment เรียบร้อยแล้ว"
            })
        else:
            return jsonify({
                "success": True,
                "completed": False,
                "chunk_index": chunk_index,
                "total_chunks": total_chunks
            })
    except Exception as e:
        return jsonify({"success": False, "error": f"ไม่สามารถบันทึก chunk ได้: {str(e)}"}), 500

@app.route("/api/list-compare-files", methods=["GET"])
def list_compare_files():
    files = []
    if os.path.exists(BACKLOG_COMPARE_FOLDER):
        for f in os.listdir(BACKLOG_COMPARE_FOLDER):
            if f.lower().endswith((".csv", ".xlsx", ".xls")):
                p = os.path.join(BACKLOG_COMPARE_FOLDER, f)
                files.append({
                    "filename": f,
                    "mtime": os.path.getmtime(p),
                    "size": os.path.getsize(p)
                })
    files.sort(key=lambda x: x["mtime"], reverse=True)
    return jsonify({"success": True, "files": files})

@app.route("/api/delete-compare-file", methods=["POST", "OPTIONS"])
@app.route("/api/delete-file", methods=["POST", "OPTIONS"])
def delete_compare_or_upload_file():
    if request.method == "OPTIONS":
        return jsonify({"success": True}), 200
    req_data = request.get_json(silent=True) or {}
    filename = (req_data.get("filename") or request.form.get("filename") or "").strip()
    if not filename:
        return jsonify({"success": False, "error": "ไม่ได้ระบุชื่อไฟล์ที่ต้องการลบ"}), 400
    
    # Safe base filename only
    safe_fn = os.path.basename(filename)
    deleted = False
    
    # Check in Backlog Shipment folder
    p1 = os.path.join(BACKLOG_COMPARE_FOLDER, safe_fn)
    if os.path.exists(p1):
        try:
            os.remove(p1)
            deleted = True
            log_activity("DELETE_COMPARE_FILE", f"ลบไฟล์ออกจาก Backlog Shipment: {safe_fn}")
        except Exception as e:
            return jsonify({"success": False, "error": f"ไม่สามารถลบไฟล์ {safe_fn}: {str(e)}"}), 500

    # Check in Upload folder
    p2 = os.path.join(UPLOAD_FOLDER, safe_fn)
    if os.path.exists(p2) and not deleted:
        try:
            os.remove(p2)
            deleted = True
            log_activity("DELETE_FILE", f"ลบไฟล์ออกจาก uploads: {safe_fn}")
        except Exception as e:
            return jsonify({"success": False, "error": f"ไม่สามารถลบไฟล์ {safe_fn}: {str(e)}"}), 500

    if deleted:
        return jsonify({"success": True, "message": f"ลบไฟล์ {safe_fn} เรียบร้อยแล้ว"})
    else:
        return jsonify({"success": False, "error": f"ไม่พบไฟล์ {safe_fn} บนเซิร์ฟเวอร์"}), 404

@app.route("/api/compare-ob-bl", methods=["GET", "POST"])
def api_compare_ob_bl():
    req_json = request.get_json(silent=True) or {}
    file1 = (request.args.get("filename1") or req_json.get("filename1") or "").strip()
    file2 = (request.args.get("filename2") or req_json.get("filename2") or "").strip()

    if not file1 or not file2:
        return jsonify({"success": False, "error": "กรุณาเลือกไฟล์ที่ต้องการเปรียบเทียบทั้ง 2 ไฟล์"}), 400

    path1 = os.path.join(BACKLOG_COMPARE_FOLDER, file1)
    if not os.path.exists(path1): path1 = os.path.join(UPLOAD_FOLDER, file1)
    if not os.path.exists(path1): path1 = os.path.join(BASE_DIR, file1)

    path2 = os.path.join(BACKLOG_COMPARE_FOLDER, file2)
    if not os.path.exists(path2): path2 = os.path.join(UPLOAD_FOLDER, file2)
    if not os.path.exists(path2): path2 = os.path.join(BASE_DIR, file2)

    if not os.path.exists(path1) or not os.path.exists(path2):
        return jsonify({"success": False, "error": "ไม่พบไฟล์รายงานบนเซิร์ฟเวอร์ กรุณาตรวจสอบและอัปโหลดไฟล์ใหม่อีกครั้ง"}), 404

    try:
        def parse_xlsx_fast(file_path):
            import zipfile, xml.etree.ElementTree as ET
            with zipfile.ZipFile(file_path, 'r') as z:
                strings = []
                if 'xl/sharedStrings.xml' in z.namelist():
                    tree = ET.fromstring(z.read('xl/sharedStrings.xml'))
                    for elem in tree.iter('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t'):
                        strings.append(elem.text if elem.text else '')

                sheet_tree = ET.fromstring(z.read('xl/worksheets/sheet1.xml'))
                ns = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
                
                rows = []
                for row_elem in sheet_tree.findall('.//s:row', ns):
                    row_vals = []
                    for cell in row_elem.findall('s:c', ns):
                        t = cell.get('t')
                        v_elem = cell.find('s:v', ns)
                        val = v_elem.text if v_elem is not None else ''
                        if t == 's' and val != '':
                            try:
                                idx_val = int(val)
                                val = strings[idx_val] if idx_val < len(strings) else val
                            except ValueError:
                                pass
                        row_vals.append(val)
                    if row_vals and any(row_vals):
                        rows.append(row_vals)
                if not rows:
                    return [], []
                return [str(h).strip() for h in rows[0]], rows[1:]

        def read_file_rows(file_path):
            headers = []
            rows = []
            if file_path.lower().endswith((".xlsx", ".xls")):
                try:
                    headers, rows = parse_xlsx_fast(file_path)
                except Exception:
                    df = read_dataframe(file_path)
                    headers = [str(c).strip() for c in df.columns]
                    rows = df.fillna('').values.tolist()
            else:
                with open(file_path, "r", encoding="utf-8-sig", errors="ignore") as f:
                    r = csv.reader(f)
                    try:
                        headers = [str(c).strip() for c in next(r)]
                    except StopIteration:
                        headers = []
                    rows = [row for row in r if row and any(row)]
            return headers, rows

        headers1, rows1 = read_file_rows(path1)
        headers2, rows2 = read_file_rows(path2)

        def get_col_indices(headers):
            idx = {}
            for i, h in enumerate(headers):
                h_lower = h.lower().replace("_", " ").strip()
                if "shipment" in h_lower or "tracking" in h_lower or h_lower == "col 1" or i == 1:
                    idx.setdefault("shipment_id", i)
                if "action" in h_lower or "flag" in h_lower:
                    idx.setdefault("action_flag", i)
                if "timestamp" in h_lower or "time" in h_lower or "status time" in h_lower:
                    idx.setdefault("latest_status_timestamp", i)
                if "day" in h_lower or "soc" in h_lower:
                    idx.setdefault("day_in_soc", i)
                if "station" in h_lower or "awb" in h_lower:
                    idx.setdefault("latest_awb_station_name", i)
                if "operator" in h_lower or "user" in h_lower:
                    idx.setdefault("latest_operator_name", i)
            return idx

        idx1 = get_col_indices(headers1)
        idx2 = get_col_indices(headers2)

        ob_actions = ["_02_pending_packed", "_03_pending_linehual_packed", "_04_pending_reworked"]

        def process_dataset(headers, rows, idx):
            dict_out = {}
            total_ob = 0
            for r in rows:
                if not r: continue
                s_id = str(r[idx.get("shipment_id", 1)]).strip() if len(r) > idx.get("shipment_id", 1) else ""
                if not s_id: continue

                af = str(r[idx.get("action_flag", 12)]).strip() if len(r) > idx.get("action_flag", 12) else ""
                af_lower = af.lower()
                is_ob = (af in ob_actions) or any(k in af_lower for k in ["packed", "linehual", "linehaul", "rework", "pending", "skip"])
                if not is_ob and af != "":
                    continue

                ts = str(r[idx.get("latest_status_timestamp", 7)]).strip() if len(r) > idx.get("latest_status_timestamp", 7) else ""
                ds = str(r[idx.get("day_in_soc", 13)]).strip() if len(r) > idx.get("day_in_soc", 13) else ""
                st = str(r[idx.get("latest_awb_station_name", 4)]).strip() if len(r) > idx.get("latest_awb_station_name", 4) else ""
                op = str(r[idx.get("latest_operator_name", 8)]).strip() if len(r) > idx.get("latest_operator_name", 8) else ""

                dict_out[s_id] = {
                    "shipment_id": s_id,
                    "action_flag": af or "_03_pending_linehual_packed",
                    "latest_status_timestamp": ts,
                    "day_in_soc": ds,
                    "latest_awb_station_name": st,
                    "latest_operator_name": op
                }
                total_ob += 1
            return dict_out, total_ob

        dict1, total_ob1 = process_dataset(headers1, rows1, idx1)
        dict2, total_ob2 = process_dataset(headers2, rows2, idx2)

        duplicate_ids = set(dict1.keys()).intersection(set(dict2.keys()))

        duplicate_list = []
        station_counts = {}
        action_counts = {}

        for s_id in duplicate_ids:
            item1 = dict1[s_id]
            item2 = dict2[s_id]

            ts1 = item1["latest_status_timestamp"]
            ts2 = item2["latest_status_timestamp"]
            ds = item2["day_in_soc"] or item1["day_in_soc"] or "-"
            st = item2["latest_awb_station_name"] or item1["latest_awb_station_name"] or "-"
            op = item2["latest_operator_name"] or item1["latest_operator_name"] or "-"
            af = item2["action_flag"] or item1["action_flag"] or "-"

            station_counts[st] = station_counts.get(st, 0) + 1
            action_counts[af] = action_counts.get(af, 0) + 1

            duplicate_list.append({
                "shipment_id": s_id,
                "action_flag": af,
                "station": st,
                "operator": op,
                "day_in_soc": ds,
                "file1_timestamp": ts1,
                "file2_timestamp": ts2
            })

        log_activity("COMPARE_OB_BL", f"Compared {file1} & {file2} — Found {len(duplicate_ids)} duplicate backlog shipments")

        return jsonify({
            "success": True,
            "file1": { "filename": file1, "total_rows": len(rows1), "ob_rows": total_ob1 },
            "file2": { "filename": file2, "total_rows": len(rows2), "ob_rows": total_ob2 },
            "duplicate_count": len(duplicate_ids),
            "duplicates": duplicate_list[:5000],
            "station_breakdown": station_counts,
            "action_breakdown": action_counts,
            "generatedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": f"เกิดข้อผิดพลาดในการเปรียบเทียบไฟล์: {str(e)}"}), 500

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

# ===== SYSTEM SETTINGS & SEATALK / HOURLY TRACKER =====
SYSTEM_SETTINGS_FILE = os.path.join(DATA_DIR, "system_settings.json")
HOURLY_TRACKER_FILE = os.path.join(DATA_DIR, "hourly_tracker_data.json")

def load_system_settings():
    if os.path.exists(SYSTEM_SETTINGS_FILE):
        try:
            with open(SYSTEM_SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print("Error loading system settings:", e)
    return {
        "updatedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "hourlyTarget": 45000,
        "hourlyMinimum": 40000,
        "hourlyMinimumPct": 90,
        "peakHourTarget": 50000,
        "peakHours": ["13:00", "14:00", "15:00", "19:00", "20:00", "21:00"],
        "overallSkipTargetPct": 0.80,
        "zoneSkipTargetPct": 0.27,
        "shifts": {
            "shift1": { "name": "กะกลางวัน (Day Shift)", "start": "08:00", "end": "20:00" },
            "shift2": { "name": "กะกลางคืน (Night Shift)", "start": "20:00", "end": "08:00" }
        },
        "seatalk": {
            "enabled": False,
            "webhookType": "seatalk",
            "webhookUrl": "",
            "triggerCondition": "below_minimum",
            "mentionType": "specific",
            "mentionEmails": ["guy.panmanee@spxexpress.com"],
            "ccText": "",
            "autoAlertIntervalMinutes": 60
        },
        "googleSheetSync": {
            "enabled": False,
            "url": "https://docs.google.com/spreadsheets/d/1b23i0TPw1NHQAoj-D3YeDe4khnXFn_d0MmxfFniuq-k/edit?gid=660104821#gid=660104821",
            "autoSyncIntervalMinutes": 15
        }
    }

def save_system_settings(data):
    try:
        data["updatedAt"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(SYSTEM_SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print("Error saving system settings:", e)
        return False

def load_hourly_tracker_data():
    if os.path.exists(HOURLY_TRACKER_FILE):
        try:
            with open(HOURLY_TRACKER_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print("Error loading hourly tracker data:", e)
    today = datetime.now().strftime("%Y-%m-%d")
    return {
        "updatedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "date": today,
        "records": { today: {} }
    }

def save_hourly_tracker_data(data):
    try:
        data["updatedAt"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(HOURLY_TRACKER_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print("Error saving hourly tracker data:", e)
        return False

def send_seatalk_alert(webhook_url, message, mention_emails=None, mention_all=False, webhook_type="seatalk"):
    if not webhook_url or not webhook_url.strip():
        return False, "Webhook URL is not configured"
    
    webhook_url = webhook_url.strip()
    try:
        if webhook_type == "seatalk":
            payload = {
                "tag": "text",
                "text": {
                    "content": message
                }
            }
            if mention_all:
                payload["text"]["mentioned_list"] = ["@all"]
            elif mention_emails and len(mention_emails) > 0:
                payload["text"]["mentioned_email_list"] = [e.strip() for e in mention_emails if e and e.strip()]
        else:
            # n8n or generic webhook payload
            payload = {
                "source": "SOCN_HOURLY_TRACKER",
                "message": message,
                "mentionAll": mention_all,
                "mentionEmails": mention_emails or [],
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

        headers = {"Content-Type": "application/json"}
        res = requests.post(webhook_url, json=payload, headers=headers, timeout=10)
        if res.status_code in [200, 201, 204]:
            return True, "Alert sent successfully"
        else:
            return False, f"Server returned HTTP {res.status_code}: {res.text[:200]}"
    except Exception as e:
        return False, str(e)


@app.route("/api/system-settings", methods=["GET", "POST"])
def manage_system_settings_api():
    if request.method == "GET":
        settings = load_system_settings()
        return jsonify({"success": True, "settings": settings})
    
    elif request.method == "POST":
        req = request.get_json(silent=True) or {}
        current = load_system_settings()
        current.update(req)
        
        save_system_settings(current)
        log_activity("SYSTEM_SETTINGS_UPDATE", f"🎯 อัปเดตการตั้งค่าเป้าหมาย & SeaTalk Webhook (Target: {current.get('hourlyTarget')}, Min: {current.get('hourlyMinimum')})")
        
        return jsonify({
            "success": True,
            "message": "บันทึกการตั้งค่าเป้าหมายและ Webhook เรียบร้อยแล้ว",
            "settings": current
        })


@app.route("/api/system-settings/test-seatalk", methods=["POST"])
def test_seatalk_alert_api():
    req = request.get_json(silent=True) or {}
    webhook_url = req.get("webhookUrl") or ""
    webhook_type = req.get("webhookType") or "seatalk"
    mention_type = req.get("mentionType") or "specific"
    mention_emails = req.get("mentionEmails") or []
    cc_text = (req.get("ccText") or "").strip()
    
    if not webhook_url:
        settings = load_system_settings()
        st_cfg = settings.get("seatalk", {})
        webhook_url = st_cfg.get("webhookUrl", "")
        webhook_type = st_cfg.get("webhookType", "seatalk")
        mention_type = st_cfg.get("mentionType", "specific")
        mention_emails = st_cfg.get("mentionEmails", [])
        if not cc_text:
            cc_text = (st_cfg.get("ccText") or "").strip()

    if not webhook_url:
        return jsonify({"success": False, "error": "กรุณาระบุ Webhook URL ก่อนกดทดสอบ"}), 400

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    test_msg = f"""🚨 [SOCN TEST NOTIFICATION] ทดสอบการเชื่อมต่อระบบแจ้งเตือน SeaTalk Webhook
━━━━━━━━━━━━━━━━━━━━
⏰ เวลาทดสอบ: {now_str}
🎯 เป้าหมายระบบ (Target): 45,000 ชิ้น/ชม.
⚠️ เกณฑ์ขั้นต่ำ (Minimum): 40,000 ชิ้น/ชม.
📡 สถานะการเชื่อมต่อ: ✅ เชื่อมต่อสำเร็จ (Connection Verified)"""
    if cc_text:
        test_msg += f"\nCC: {cc_text}"

    mention_all = (mention_type == "all")
    emails_to_tag = mention_emails if (mention_type == "specific") else []

    ok, msg = send_seatalk_alert(webhook_url, test_msg, mention_emails=emails_to_tag, mention_all=mention_all, webhook_type=webhook_type)
    if ok:
        log_activity("SEATALK_TEST_ALERT", f"🔔 ทดสอบยิงแจ้งเตือน SeaTalk Webhook สำเร็จ ({webhook_url[:30]}...)")
        return jsonify({"success": True, "message": "ส่งข้อความทดสอบเข้า SeaTalk เรียบร้อยแล้ว!"})
    else:
        return jsonify({"success": False, "error": f"ไม่สามารถส่งข้อความได้: {msg}"}), 400


def sync_productivity_orders_sheet(sheet_url=None, auto_save=True):
    import csv, io, re, urllib.request, time
    from datetime import datetime
    
    settings = load_system_settings()
    if not sheet_url:
        sheet_url = settings.get("googleSheetSync", {}).get("url", "")
    
    if not sheet_url:
        return False, "ยังไม่ได้กำหนด Google Sheet URL", None
        
    try:
        req = urllib.request.Request(sheet_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw_csv = resp.read().decode("utf-8", errors="ignore")
            
        reader = list(csv.reader(io.StringIO(raw_csv)))
        if not reader:
            return False, "ไม่พบข้อมูลใน Google Sheet", None
            
        def clean_num(val):
            if not val or str(val).strip() in ["-", "", "#REF!", "#ERROR!"]: return 0
            val_str = str(val).replace(",", "").replace("%", "").strip()
            try:
                return int(float(val_str))
            except:
                return 0

        def clean_float(val):
            if not val or str(val).strip() in ["-", "", "#REF!", "#ERROR!"]: return 0.0
            val_str = str(val).replace(",", "").replace("%", "").strip()
            try:
                return round(float(val_str), 2)
            except:
                return 0.0
                
        date_str = datetime.now().strftime("%Y-%m-%d")
        for r in reader[:6]:
            for cell in r:
                match = re.search(r"(\d{1,2})\s+([A-Za-z]{3})\s+(\d{2,4})", str(cell))
                if match:
                    day, mon, yr = match.groups()
                    try:
                        full_yr = int(yr) + 2000 if len(yr) == 2 else int(yr)
                        parsed_d = datetime.strptime(f"{day} {mon} {full_yr}", "%d %b %Y")
                        date_str = parsed_d.strftime("%Y-%m-%d")
                    except:
                        pass
                    break

        summary_rows = {}
        for r in reader[:10]:
            label = r[1].strip() if len(r) > 1 else ""
            if label in ["Total", "Max/hr", "Avg/hr"]:
                summary_rows[label] = {
                    "label": label,
                    "trucks": clean_num(r[2]),
                    "truckPct": clean_float(r[3]),
                    "truck4wh": clean_num(r[4]),
                    "truck4wj": clean_num(r[5]),
                    "truck6wh": clean_num(r[6]),
                    "truckSemi": clean_num(r[7]),
                    "actual": clean_num(r[8]),
                    "orderPct": clean_float(r[9]),
                    "zoneA": clean_num(r[10]),
                    "zoneB": clean_num(r[11]),
                    "zoneC": clean_num(r[12]),
                    "zoneD": clean_num(r[13]) if len(r) > 13 else 0,
                    "zoneE": clean_num(r[14]) if len(r) > 14 else 0,
                    "zoneOBC": clean_num(r[15]) if len(r) > 15 else 0
                }
                    
        records = {}
        zone_details = {}
        ordered_slots_from_sheet = []
        
        for r in reader:
            if len(r) < 9: continue
            time_col = r[1].strip()
            match = re.search(r"^(\d{1,2}):(\d{2})$", time_col)
            if match:
                h = int(match.group(1))
                slot_hour = 0 if h == 24 else h
                slot_label = f"{slot_hour:02d}:00"
                
                total_orders = clean_num(r[8])
                order_pct = clean_float(r[9]) if len(r) > 9 else 0.0
                trucks = clean_num(r[2]) if len(r) > 2 else 0
                truck_pct = clean_float(r[3]) if len(r) > 3 else 0.0
                truck_4wh = clean_num(r[4]) if len(r) > 4 else 0
                truck_4wj = clean_num(r[5]) if len(r) > 5 else 0
                truck_6wh = clean_num(r[6]) if len(r) > 6 else 0
                truck_semi = clean_num(r[7]) if len(r) > 7 else 0
                
                zone_a = clean_num(r[10]) if len(r) > 10 else 0
                zone_b = clean_num(r[11]) if len(r) > 11 else 0
                zone_c = clean_num(r[12]) if len(r) > 12 else 0
                zone_d = clean_num(r[13]) if len(r) > 13 else 0
                zone_e = clean_num(r[14]) if len(r) > 14 else 0
                zone_obc = clean_num(r[15]) if len(r) > 15 else 0
                
                if slot_label in records and records[slot_label] > 0 and total_orders == 0:
                    continue
                    
                records[slot_label] = total_orders
                zone_details[slot_label] = {
                    "originalHourLabel": time_col,
                    "slotHour": slot_hour,
                    "trucks": trucks,
                    "truckPct": truck_pct,
                    "truck4wh": truck_4wh,
                    "truck4wj": truck_4wj,
                    "truck6wh": truck_6wh,
                    "truckSemi": truck_semi,
                    "totalOrders": total_orders,
                    "orderPct": order_pct,
                    "zoneA": zone_a,
                    "zoneB": zone_b,
                    "zoneC": zone_c,
                    "zoneD": zone_d,
                    "zoneE": zone_e,
                    "zoneOBC": zone_obc
                }
                if slot_label not in ordered_slots_from_sheet:
                    ordered_slots_from_sheet.append(slot_label)
                
        if auto_save:
            tracker_data = load_hourly_tracker_data()
            if "records" not in tracker_data:
                tracker_data["records"] = {}
            if "zone_breakdowns" not in tracker_data:
                tracker_data["zone_breakdowns"] = {}
            if "summary_rows" not in tracker_data:
                tracker_data["summary_rows"] = {}
            if "last_alerted" not in tracker_data:
                tracker_data["last_alerted"] = {}
            if "alerted_hashes" not in tracker_data:
                tracker_data["alerted_hashes"] = []
            if "alerted_slots" not in tracker_data:
                tracker_data["alerted_slots"] = []
                
            prev_records = dict(tracker_data["records"].get(date_str, {}))
            is_board_data_changed = (prev_records != records)
            
            tracker_data["records"][date_str] = records
            tracker_data["zone_breakdowns"][date_str] = zone_details
            tracker_data["summary_rows"][date_str] = summary_rows
            tracker_data["lastSyncAt"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            tracker_data["lastSyncDate"] = date_str
            
            # Auto-alert evaluation:
            # 1. Skip if board data did NOT change
            # 2. Skip standby quiet hours 13:00 - 17:00
            # 3. Strictly 1 alert per hour slot & deduplicate by exact date_slot_actual hash
            st_cfg = settings.get("seatalk", {})
            if st_cfg.get("enabled") and st_cfg.get("webhookUrl") and is_board_data_changed:
                target_normal = settings.get("hourlyTarget", 45000)
                target_min = settings.get("hourlyMinimum", 40000)
                target_peak = settings.get("peakHourTarget", 50000)
                peak_hours = set(settings.get("peakHours", []))
                cond = st_cfg.get("triggerCondition", "below_minimum")
                
                if date_str not in tracker_data["last_alerted"]:
                    tracker_data["last_alerted"][date_str] = {}
                    
                current_timestamp = time.time()
                quiet_hours = {13, 14, 15, 16, 17} # Standby prep hours: 13:00 - 17:59 -> DO NOT ALERT
                
                # Order of operational shift hours: 13:00 to 12:00
                shift_hours = [13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
                
                # Identify slots eligible for alert (Strictly 1 alert per hour slot per date)
                slots_to_alert = []
                for h_val in shift_hours:
                    slot_lbl = f"{h_val:02d}:00"
                    act = records.get(slot_lbl, 0)
                    
                    # Skip quiet hours and zero orders
                    if h_val in quiet_hours or act == 0:
                        continue
                        
                    slot_key = f"{date_str}_{slot_lbl}"
                    slot_hash = f"{date_str}_{slot_lbl}_{act}"
                    
                    # STRICT DEDUPLICATION: If this slot or exact volume hash was already alerted, SKIP!
                    if (slot_key in tracker_data["alerted_slots"] or 
                        slot_hash in tracker_data["alerted_hashes"] or 
                        slot_lbl in tracker_data["last_alerted"].get(date_str, {}) or
                        prev_records.get(slot_lbl) == act):
                        continue
                        
                    is_peak = slot_lbl in peak_hours
                    slot_target = target_peak if is_peak else target_normal
                    
                    is_fail = False
                    if cond == "below_minimum" and act < target_min:
                        is_fail = True
                    elif cond == "below_target" and act < slot_target:
                        is_fail = True
                        
                    if is_fail:
                        slots_to_alert.append((slot_lbl, h_val, act, slot_target, is_peak))

                # Send AT MOST ONE alert per sync cycle (the latest failed hour)
                if slots_to_alert:
                    # Take the most recent failed slot
                    slot_lbl, h_val, act, slot_target, is_peak = slots_to_alert[-1]
                    slot_key = f"{date_str}_{slot_lbl}"
                    slot_hash = f"{date_str}_{slot_lbl}_{act}"
                    
                    gap = act - slot_target
                    pct = round((act / slot_target * 100), 1) if slot_target > 0 else 0.0
                    next_h_label = f"{(h_val+1)%24:02d}:00"
                    time_range = f"{slot_lbl} - {next_h_label}"
                    
                    zd = zone_details.get(slot_lbl, {})
                    za, zb, zc = zd.get('zoneA', 0), zd.get('zoneB', 0), zd.get('zoneC', 0)
                    
                    # Find lowest zone
                    z_list = [('Zone A', za), ('Zone B', zb), ('Zone C', zc)]
                    z_list.sort(key=lambda x: x[1])
                    lowest_zone_name = z_list[0][0]
                    lowest_str = f"{lowest_zone_name} ({z_list[0][1]:,} ชิ้น)"
                    
                    # Look up responsible staff from Staff Roster
                    roster = load_staff_roster_data()
                    roster_by_zone = roster.get("rosterByZone", {})
                    zone_key = lowest_zone_name.replace("Zone ", "").strip()
                    staff_names = roster_by_zone.get(zone_key, [])
                    sups = roster_by_zone.get("ALL", ["Chain", "Big"])
                    staff_str = ", ".join(staff_names) if staff_names else "ไม่ระบุใน Roster"
                    sups_str = ", ".join(sups) if sups else "Chain, Big"
                    
                    msg = f"""🚨 [SOCN ALERT] ยอดปล่อยหลุดเป้าหมายรายชั่วโมง (Hourly Release Under Target)
━━━━━━━━━━━━━━━━━━━━
📅 วันที่: {date_str}
⏰ ช่วงเวลา: {time_range}
🎯 เป้าหมาย (Target): {slot_target:,} ชิ้น
⚠️ เกณฑ์ขั้นต่ำ (Min): {target_min:,} ชิ้น
📦 ปล่อยจริง (Actual): {act:,} ชิ้น
📉 ส่วนต่าง (Gap): {gap:,} ชิ้น ({pct}% of Target)
🚚 เที่ยวรถ: {zd.get('trucks', 0)} เที่ยว
📍 ยอดตามโซน: A: {za:,} | B: {zb:,} | C: {zc:,}
⚠️ โซนที่หลุดเป้า/ช้าสุด: {lowest_str}
👤 ผู้รับผิดชอบ {lowest_zone_name} (ใครช้า): {staff_str}
👔 Supervisor ประจำรอบ: {sups_str}"""

                    cc_text = (st_cfg.get("ccText") or "").strip()
                    if cc_text:
                        msg += f"\nCC: {cc_text}"

                    mention_all = (st_cfg.get("mentionType") == "all")
                    emails = st_cfg.get("mentionEmails", []) if (st_cfg.get("mentionType") == "specific") else []
                    send_seatalk_alert(st_cfg.get("webhookUrl"), msg, mention_emails=emails, mention_all=mention_all, webhook_type=st_cfg.get("webhookType", "seatalk"))
                    
                    # Mark this slot and hash as permanently alerted
                    tracker_data["last_alerted"][date_str][slot_lbl] = current_timestamp
                    if slot_key not in tracker_data["alerted_slots"]:
                        tracker_data["alerted_slots"].append(slot_key)
                    if slot_hash not in tracker_data["alerted_hashes"]:
                        tracker_data["alerted_hashes"].append(slot_hash)
                        
                    # Also mark previous un-alerted failed slots in batch so they don't trigger in future cycles
                    for s_lbl, _, a_val, _, _ in slots_to_alert:
                        prev_k = f"{date_str}_{s_lbl}"
                        prev_h = f"{date_str}_{s_lbl}_{a_val}"
                        tracker_data["last_alerted"][date_str][s_lbl] = current_timestamp
                        if prev_k not in tracker_data["alerted_slots"]:
                            tracker_data["alerted_slots"].append(prev_k)
                        if prev_h not in tracker_data["alerted_hashes"]:
                            tracker_data["alerted_hashes"].append(prev_h)

                    log_activity("SEATALK_AUTO_ALERT", f"🚨 ส่งแจ้งเตือน SeaTalk (จำกัด 1 ข้อความ/ชม.): {date_str} {slot_lbl} ยอด {act:,} ชิ้น (หลุดเป้า: {lowest_str} | ผู้รับผิดชอบ: {staff_str})")

            save_hourly_tracker_data(tracker_data)
            log_activity("GOOGLE_SHEET_SYNC", f"🔄 ซิงค์ข้อมูล Google Sheet สำเร็จ (วันที่ {date_str}, ยอดรวม {sum(records.values()):,} ชิ้น, 24 ชั่วโมง)")
            
        return True, "ซิงค์ข้อมูล Google Sheet สำเร็จ", {
            "date": date_str,
            "totalOrders": sum(records.values()),
            "slotsCount": len(records),
            "summaryRows": summary_rows,
            "records": records,
            "zoneDetails": zone_details
        }
    except Exception as e:
        return False, f"เกิดข้อผิดพลาดในการซิงค์ Google Sheet: {str(e)}", None


# Evidence Directory Setup (C:\Users\spxth71637\Desktop\OB Dashboard\หลักฐาน)
EVIDENCE_BASE_DIR = os.path.join(BASE_DIR, "หลักฐาน")
EVIDENCE_METADATA_FILE = os.path.join(DATA_DIR, "hourly_evidence.json")

for z in ["Zone A", "Zone B", "Zone C"]:
    os.makedirs(os.path.join(EVIDENCE_BASE_DIR, z), exist_ok=True)

def load_evidence_metadata():
    if not os.path.exists(EVIDENCE_METADATA_FILE):
        return []
    try:
        with open(EVIDENCE_METADATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_evidence_metadata(data):
    try:
        with open(EVIDENCE_METADATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[Evidence Save Error]: {e}")


@app.route("/api/hourly-tracker/upload-evidence", methods=["POST"])
def upload_hourly_evidence_api():
    # Support both 2-slot upload (obs_image, obd_image) and fallback single 'image'
    has_obs = "obs_image" in request.files and request.files["obs_image"].filename != ""
    has_obd = "obd_image" in request.files and request.files["obd_image"].filename != ""
    has_generic = "image" in request.files and request.files["image"].filename != ""

    if not (has_obs or has_obd or has_generic):
        return jsonify({"success": False, "error": "กรุณาแนบรูปภาพหลักฐานอย่างน้อย 1 ช่อง (OBS หรือ OBD)"}), 400
        
    zone = request.form.get("zone", "Zone A").strip()
    if zone not in ["Zone A", "Zone B", "Zone C"]:
        zone = "Zone A"
        
    date_str = request.form.get("date", "").strip() or datetime.now().strftime("%Y-%m-%d")
    slot = request.form.get("slot", "").strip() or "N/A"
    note = request.form.get("note", "").strip()
    uploader = request.form.get("uploadedBy", "Ground User").strip()
    
    target_dir = os.path.join(EVIDENCE_BASE_DIR, zone)
    os.makedirs(target_dir, exist_ok=True)
    
    now = datetime.now()
    ts_str = now.strftime("%Y%m%d_%H%M%S")
    safe_slot = slot.replace(":", "-").replace(" ", "_")
    safe_zone = zone.replace(" ", "_")
    
    time_range = f"{slot} - {(int(slot.split(':')[0])+1)%24:02d}:00" if ":" in slot else slot
    
    files_to_save = []
    if has_obs:
        files_to_save.append(("OBS", "หลักฐาน OBS", request.files["obs_image"]))
    if has_obd:
        files_to_save.append(("OBD", "หลักฐาน OBD", request.files["obd_image"]))
    if has_generic and not (has_obs or has_obd):
        doc_type = request.form.get("type", "OBS").upper()
        if doc_type not in ["OBS", "OBD"]:
            doc_type = "OBS"
        files_to_save.append((doc_type, f"หลักฐาน {doc_type}", request.files["image"]))
        
    saved_records = []
    metadata = load_evidence_metadata()
    
    for doc_type, doc_title, file in files_to_save:
        ext = os.path.splitext(file.filename)[1].lower() or ".jpg"
        if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
            ext = ".jpg"
            
        saved_filename = f"{date_str}_{safe_slot}_{safe_zone}_{doc_type}_{ts_str}{ext}"
        target_path = os.path.join(target_dir, saved_filename)
        
        file.save(target_path)
        
        file_id = f"evi_{doc_type.lower()}_{int(time.time())}_{random.randint(100, 999)}"
        record = {
            "id": file_id,
            "type": doc_type,
            "title": doc_title,
            "date": date_str,
            "slot": slot,
            "timeRange": time_range,
            "zone": zone,
            "filename": saved_filename,
            "originalFilename": file.filename,
            "filePath": f"หลักฐาน/{zone}/{saved_filename}",
            "fileUrl": f"/evidence-image/{urllib.parse.quote(zone)}/{saved_filename}",
            "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
            "note": note,
            "uploadedBy": uploader,
            "sizeBytes": os.path.getsize(target_path)
        }
        
        saved_records.append(record)
        metadata.insert(0, record)
        log_activity("EVIDENCE_UPLOAD", f"📸 อัปโหลด{doc_title}: {zone} | {date_str} {slot} ({saved_filename})")
        time.sleep(0.05) # slight offset for unique timestamp IDs if multiple
        
    save_evidence_metadata(metadata)
    
    type_names = ", ".join([r["type"] for r in saved_records])
    return jsonify({
        "success": True,
        "message": f"อัปโหลดหลักฐาน [{type_names}] {zone} ช่วงเวลา {slot} สำเร็จ! ({len(saved_records)} ไฟล์)",
        "evidence": saved_records[0] if len(saved_records) == 1 else saved_records,
        "records": saved_records
    })


@app.route("/api/hourly-tracker/evidence", methods=["GET"])
def get_hourly_evidence_api():
    date_filter = request.args.get("date", "").strip()
    slot_filter = request.args.get("slot", "").strip()
    zone_filter = request.args.get("zone", "").strip()
    
    all_evidence = load_evidence_metadata()
    results = []
    
    for item in all_evidence:
        if date_filter and item.get("date") != date_filter:
            continue
        if slot_filter and item.get("slot") != slot_filter:
            continue
        if zone_filter and item.get("zone") != zone_filter:
            continue
        results.append(item)
        
    return jsonify({
        "success": True,
        "count": len(results),
        "evidence": results
    })


@app.route("/evidence-image/<zone>/<path:filename>")
def serve_evidence_image(zone, filename):
    safe_zone = zone if zone in ["Zone A", "Zone B", "Zone C"] else "Zone A"
    folder = os.path.join(EVIDENCE_BASE_DIR, safe_zone)
    return send_from_directory(folder, filename)


@app.route("/api/hourly-tracker/evidence/<evidence_id>", methods=["DELETE"])
def delete_hourly_evidence_api(evidence_id):
    metadata = load_evidence_metadata()
    found = None
    remaining = []
    
    for item in metadata:
        if item.get("id") == evidence_id:
            found = item
        else:
            remaining.append(item)
            
    if not found:
        return jsonify({"success": False, "error": "ไม่พบข้อมูลหลักฐานนี้"}), 404
        
    # Delete physical file
    zone = found.get("zone", "Zone A")
    filename = found.get("filename", "")
    full_path = os.path.join(EVIDENCE_BASE_DIR, zone, filename)
    if os.path.exists(full_path):
        try:
            os.remove(full_path)
        except Exception as e:
            print(f"Error removing file: {e}")
            
    save_evidence_metadata(remaining)
    log_activity("EVIDENCE_DELETE", f"🗑️ ลบหลักฐาน: {zone} {found.get('date')} {found.get('slot')} ({filename})")
    
    return jsonify({"success": True, "message": "ลบไฟล์หลักฐานเรียบร้อย"})


@app.route("/api/hourly-tracker/sync-google-sheet", methods=["POST"])
def sync_hourly_google_sheet_api():
    req = request.get_json(silent=True) or {}
    sheet_url = (req.get("url") or "").strip()
    
    ok, msg, res_data = sync_productivity_orders_sheet(sheet_url=sheet_url, auto_save=True)
    if ok:
        return jsonify({
            "success": True,
            "message": msg,
            "data": res_data
        })
    else:
        return jsonify({"success": False, "error": msg}), 400


@app.route("/api/hourly-tracker", methods=["GET"])
def get_hourly_tracker_api():
    settings = load_system_settings()
    hourly_data = load_hourly_tracker_data()
    evidence_data = load_evidence_metadata()
    
    auto_sync = request.args.get("sync") == "1"
    if auto_sync:
        ok, msg, _ = sync_productivity_orders_sheet(auto_save=True)
        if ok:
            hourly_data = load_hourly_tracker_data()
            
    date_param = hourly_data.get("lastSyncDate") or request.args.get("date", "").strip() or datetime.now().strftime("%Y-%m-%d")
    records_for_date = hourly_data.get("records", {}).get(date_param, {})
    zones_for_date = hourly_data.get("zone_breakdowns", {}).get(date_param, {})
    summary_rows_for_date = hourly_data.get("summary_rows", {}).get(date_param, {})
    
    target_normal = settings.get("hourlyTarget", 45000)
    target_min = settings.get("hourlyMinimum", 40000)
    target_peak = settings.get("peakHourTarget", 50000)
    peak_hours = set(settings.get("peakHours", ["13:00", "14:00", "15:00", "19:00", "20:00", "21:00"]))
    zone_targets_cfg = settings.get("zoneTargets", {
        "Zone A": {"target": 15000, "minimum": 13333, "peakTarget": 17000},
        "Zone B": {"target": 15000, "minimum": 13333, "peakTarget": 17000},
        "Zone C": {"target": 15000, "minimum": 13333, "peakTarget": 16000}
    })
    
    # Operational Shift Order from Sheet: 13:00 to 12:00
    shift_hour_order = [13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
    
    slots = []
    total_actual = 0
    total_target = 0
    hours_passed = 0
    hours_warning = 0
    hours_under = 0
    hours_standby = 0

    for h in shift_hour_order:
        slot_label = f"{h:02d}:00"
        next_label = f"{(h+1)%24:02d}:00"
        time_range = f"{slot_label} - {next_label}"
        
        is_quiet = h in [13, 14, 15, 16, 17] # Standby prep hours
        is_peak = slot_label in peak_hours
        slot_target = target_peak if is_peak else target_normal
        slot_min = target_min
        
        shift_name = "กะกลางวัน (Day)" if (8 <= h < 20) else "กะกลางคืน (Night)"
        
        actual_val = records_for_date.get(slot_label)
        has_data = (actual_val is not None)
        zone_info = zones_for_date.get(slot_label, {})
        
        gap = 0
        achieve_pct = 0.0
        status = "pending"
        
        za = zone_info.get("zoneA", 0)
        zb = zone_info.get("zoneB", 0)
        zc = zone_info.get("zoneC", 0)
        
        # Calculate lowest active zone
        lowest_zone = "-"
        if has_data and int(actual_val) > 0:
            z_tuples = [("Zone A", za), ("Zone B", zb), ("Zone C", zc)]
            z_tuples.sort(key=lambda x: x[1])
            lowest_zone = z_tuples[0][0]
        
        if has_data:
            act = int(actual_val)
            total_actual += act
            gap = act - slot_target
            achieve_pct = round((act / slot_target * 100), 1) if slot_target > 0 else 0.0
            
            if is_quiet and act == 0:
                status = "standby"
                hours_standby += 1
            elif act >= slot_target:
                status = "passed"
                hours_passed += 1
                total_target += slot_target
            elif act >= slot_min:
                status = "warning"
                hours_warning += 1
                total_target += slot_target
            else:
                status = "under_target"
                hours_under += 1
                total_target += slot_target
        else:
            if not is_quiet:
                total_target += slot_target
                
        # Attach evidence for this slot and date
        slot_evidences = [e for e in evidence_data if e.get("date") == date_param and e.get("slot") == slot_label]
        
        # Look up staff for the lowest zone
        staff_roster = load_staff_roster_data()
        roster_by_zone = staff_roster.get("rosterByZone", {})
        zone_key = lowest_zone.replace("Zone ", "").strip()
        slow_staff = roster_by_zone.get(zone_key, [])
        supervisors = roster_by_zone.get("ALL", ["Chain", "Big"])

        za_cfg = zone_targets_cfg.get("Zone A", {})
        za_tgt = za_cfg.get("peakTarget" if is_peak else "target", 15000)
        za_min = za_cfg.get("minimum", 13333)

        zb_cfg = zone_targets_cfg.get("Zone B", {})
        zb_tgt = zb_cfg.get("peakTarget" if is_peak else "target", 15000)
        zb_min = zb_cfg.get("minimum", 13333)

        zc_cfg = zone_targets_cfg.get("Zone C", {})
        zc_tgt = zc_cfg.get("peakTarget" if is_peak else "target", 15000)
        zc_min = zc_cfg.get("minimum", 13333)

        za_status = "passed" if za >= za_tgt else ("warning" if za >= za_min else "under")
        zb_status = "passed" if zb >= zb_tgt else ("warning" if zb >= zb_min else "under")
        zc_status = "passed" if zc >= zc_tgt else ("warning" if zc >= zc_min else "under")

        under_zones = []
        if has_data and act > 0:
            if za < za_tgt: under_zones.append("Zone A")
            if zb < zb_tgt: under_zones.append("Zone B")
            if zc < zc_tgt: under_zones.append("Zone C")

        slots.append({
            "hour": h,
            "slot": slot_label,
            "timeRange": time_range,
            "shift": shift_name,
            "isPeak": is_peak,
            "isQuiet": is_quiet,
            "target": slot_target,
            "minimum": slot_min,
            "actual": int(actual_val) if has_data else 0,
            "hasData": has_data,
            "gap": gap,
            "achievePct": achieve_pct,
            "status": status,
            "trucks": zone_info.get("trucks", 0),
            "truckPct": zone_info.get("truckPct", 0.0),
            "truck4wh": zone_info.get("truck4wh", 0),
            "truck4wj": zone_info.get("truck4wj", 0),
            "truck6wh": zone_info.get("truck6wh", 0),
            "truckSemi": zone_info.get("truckSemi", 0),
            "orderPct": zone_info.get("orderPct", 0.0),
            "zoneA": za,
            "zoneATarget": za_tgt,
            "zoneAMinimum": za_min,
            "zoneAStatus": za_status,
            "zoneB": zb,
            "zoneBTarget": zb_tgt,
            "zoneBMinimum": zb_min,
            "zoneBStatus": zb_status,
            "zoneC": zc,
            "zoneCTarget": zc_tgt,
            "zoneCMinimum": zc_min,
            "zoneCStatus": zc_status,
            "zoneD": zone_info.get("zoneD", 0),
            "zoneE": zone_info.get("zoneE", 0),
            "zoneOBC": zone_info.get("zoneOBC", 0),
            "lowestZone": lowest_zone,
            "underZones": under_zones,
            "slowStaff": slow_staff,
            "supervisors": supervisors,
            "evidenceCount": len(slot_evidences),
            "evidenceList": slot_evidences
        })
        
    overall_achieve = round((total_actual / total_target * 100), 1) if total_target > 0 else 0.0
    
    staff_roster = load_staff_roster_data()
    return jsonify({
        "success": True,
        "date": date_param,
        "updatedAt": hourly_data.get("updatedAt", ""),
        "lastSyncAt": hourly_data.get("lastSyncAt", ""),
        "settings": settings,
        "rosterByZone": staff_roster.get("rosterByZone", {}),
        "summary": {
            "totalActual": total_actual,
            "totalTarget": total_target,
            "overallAchievePct": overall_achieve,
            "hoursPassed": hours_passed,
            "hoursWarning": hours_warning,
            "hoursUnder": hours_under,
            "hoursStandby": hours_standby,
            "totalHoursRecorded": hours_passed + hours_warning + hours_under + hours_standby
        },
        "summaryRows": summary_rows_for_date,
        "slots": slots
    })


@app.route("/api/hourly-tracker/save", methods=["POST"])
def save_hourly_tracker_api():
    req = request.get_json(silent=True) or {}
    date_param = req.get("date") or datetime.now().strftime("%Y-%m-%d")
    hour_slot = req.get("slot") or ""
    actual_val = req.get("actual")
    
    if not hour_slot:
        return jsonify({"success": False, "error": "ไม่ได้ระบุช่วงเวลา (Hour Slot)"}), 400
        
    data = load_hourly_tracker_data()
    if "records" not in data:
        data["records"] = {}
    if date_param not in data["records"]:
        data["records"][date_param] = {}
        
    data["records"][date_param][hour_slot] = int(actual_val) if (actual_val is not None and str(actual_val).strip() != "") else None
    save_hourly_tracker_data(data)
    
    log_activity("HOURLY_ENTRY_SAVE", f"บันทึกยอดปล่อยรายชั่วโมง: {date_param} {hour_slot} = {actual_val:,} ชิ้น" if actual_val is not None else f"ล้างค่ายอดปล่อย: {date_param} {hour_slot}")
    
    # Auto Alert evaluation if SeaTalk enabled
    settings = load_system_settings()
    st_cfg = settings.get("seatalk", {})
    if st_cfg.get("enabled") and actual_val is not None and st_cfg.get("webhookUrl"):
        target_normal = settings.get("hourlyTarget", 45000)
        target_min = settings.get("hourlyMinimum", 40000)
        target_peak = settings.get("peakHourTarget", 50000)
        peak_hours = set(settings.get("peakHours", []))
        
        is_peak = hour_slot in peak_hours
        slot_target = target_peak if is_peak else target_normal
        act = int(actual_val)
        
        slot_key = f"{date_param}_{hour_slot}"
        cond = st_cfg.get("triggerCondition", "below_minimum")
        if slot_key not in data.get("alerted_slots", []):
            if cond == "below_minimum" and act < target_min:
                should_alert = True
            elif cond == "below_target" and act < slot_target:
                should_alert = True
            
        if should_alert:
            gap = act - slot_target
            pct = round((act / slot_target * 100), 1) if slot_target > 0 else 0.0
            msg = f"""🚨 [SOCN ALERT] ยอดปล่อยหลุดเป้าหมายรายชั่วโมง!
━━━━━━━━━━━━━━━━━━━━
📅 วันที่: {date_param}
⏰ ช่วงเวลา: {hour_slot}
🎯 เป้าหมาย (Target): {slot_target:,} ชิ้น
⚠️ เกณฑ์ขั้นต่ำ (Minimum): {target_min:,} ชิ้น
📦 ปล่อยจริง (Actual): {act:,} ชิ้น
📉 ส่วนต่าง (Gap): {gap:,} ชิ้น ({pct}% of Target)"""
            
            cc_text = (st_cfg.get("ccText") or "").strip()
            if cc_text:
                msg += f"\nCC: {cc_text}"
            
            mention_all = (st_cfg.get("mentionType") == "all")
            emails = st_cfg.get("mentionEmails", []) if (st_cfg.get("mentionType") == "specific") else []
            send_seatalk_alert(st_cfg.get("webhookUrl"), msg, mention_emails=emails, mention_all=mention_all, webhook_type=st_cfg.get("webhookType", "seatalk"))
            
            if "alerted_slots" not in data:
                data["alerted_slots"] = []
            data["alerted_slots"].append(slot_key)
            save_hourly_tracker_data(data)

    return jsonify({"success": True, "message": f"บันทึกยอด {hour_slot} เรียบร้อย"})


@app.route("/api/hourly-tracker/send-alert", methods=["POST"])
def send_manual_hourly_alert_api():
    req = request.get_json(silent=True) or {}
    slot_info = req.get("slotInfo") or {}
    date_str = req.get("date") or datetime.now().strftime("%Y-%m-%d")
    
    settings = load_system_settings()
    st_cfg = settings.get("seatalk", {})
    webhook_url = st_cfg.get("webhookUrl")
    if not webhook_url:
        return jsonify({"success": False, "error": "ยังไม่ได้ตั้งค่า SeaTalk Webhook URL ในระบบ Admin"}), 400
        
    hour_slot = slot_info.get("slot", "N/A")
    time_range = slot_info.get("timeRange", hour_slot)
    shift_name = slot_info.get("shift", "-")
    target = slot_info.get("target", 45000)
    min_val = slot_info.get("minimum", 40000)
    actual = slot_info.get("actual", 0)
    gap = slot_info.get("gap", 0)
    pct = slot_info.get("achievePct", 0)
    
    msg = f"""🚨 [SOCN ALERT] ยอดปล่อยหลุดเป้าหมายรายชั่วโมง ({shift_name})
━━━━━━━━━━━━━━━━━━━━
📅 วันที่: {date_str}
⏰ ช่วงเวลา: {time_range}
🎯 เป้าหมาย (Target): {target:,} ชิ้น
⚠️ เกณฑ์ขั้นต่ำ (Minimum): {min_val:,} ชิ้น
📦 ปล่อยจริง (Actual): {actual:,} ชิ้น
📉 ส่วนต่าง (Gap): {gap:,} ชิ้น ({pct}% of Target)"""

    cc_text = (st_cfg.get("ccText") or "").strip()
    if cc_text:
        msg += f"\nCC: {cc_text}"

    mention_all = (st_cfg.get("mentionType") == "all")
    emails = st_cfg.get("mentionEmails", []) if (st_cfg.get("mentionType") == "specific") else []
    
    ok, err_msg = send_seatalk_alert(webhook_url, msg, mention_emails=emails, mention_all=mention_all, webhook_type=st_cfg.get("webhookType", "seatalk"))
    if ok:
        log_activity("SEATALK_MANUAL_ALERT", f"📢 ส่งแจ้งเตือน SeaTalk รายชั่วโมง: {date_str} {time_range}")
        return jsonify({"success": True, "message": f"ส่งแจ้งเตือนช่วงเวลา {time_range} เข้า SeaTalk สำเร็จ!"})
    else:
        return jsonify({"success": False, "error": f"ส่งแจ้งเตือนไม่สำเร็จ: {err_msg}"}), 400


@app.route("/investigation")
def investigation_page():
    return send_from_directory(BASE_DIR, "investigation.html")

@app.route("/skip-process")
def skip_process_page():
    return send_from_directory(BASE_DIR, "skip_process.html")

@app.route("/cutoff-master")
def cutoff_master_page():
    return send_from_directory(BASE_DIR, "cutoff_master.html")

@app.route("/hourly-tracker")
def hourly_tracker_page():
    return send_from_directory(BASE_DIR, "hourly_tracker.html")

@app.route("/<path:filename>")
def serve_static_files(filename):
    allowed_ext = (".html", ".js", ".css", ".png", ".jpg", ".ico", ".webp", ".svg")
    if any(filename.endswith(ext) for ext in allowed_ext) and os.path.exists(os.path.join(BASE_DIR, filename)):
        return send_from_directory(BASE_DIR, filename)
    return jsonify({"success": False, "error": "File not found"}), 404

def start_hourly_sheet_background_sync():
    import threading, time
    def worker():
        time.sleep(10) # wait for app startup
        while True:
            try:
                settings = load_system_settings()
                gs_cfg = settings.get("googleSheetSync", {})
                if gs_cfg.get("enabled") and gs_cfg.get("url"):
                    sync_productivity_orders_sheet(sheet_url=gs_cfg.get("url"), auto_save=True)
            except Exception as e:
                print(f"[Hourly Sheet Background Sync Error]: {e}")
            time.sleep(300) # Sync every 5 minutes

    t = threading.Thread(target=worker, daemon=True)
    t.start()

start_hourly_sheet_background_sync()

if __name__ == "__main__":
    print("=" * 60)
    print(" Server started at http://localhost:5000")
    print(f" Uploaded files will be stored in: {UPLOAD_FOLDER}")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5000, debug=True)