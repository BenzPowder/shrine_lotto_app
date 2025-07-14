# app.py
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from dotenv import load_dotenv
import os
print("Credentials Path:", os.getenv('GOOGLE_APPLICATION_CREDENTIALS'))
from datetime import datetime
import pytz
import random
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from gsheet_db import read_range, write_range  # เชื่อม Google Sheets API
import datetime
print("Server UTC time:", datetime.datetime.utcnow())
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'super_secret_key_for_dev')

# Google Sheet ranges (แก้ให้ตรงกับชีต Google Sheets ของสมเบ็นซ์)
SHEET_LOTTO_RANGE = 'historical_lotto!A:B'  # คอลัมน์ A = date, B = two_digits
SHEET_USERS_RANGE = 'users!A:E'  # A=username, B=password_hash, C=credits, D=role, E=is_banned

# --- Helper Functions for Users in Google Sheets ---

STATIC_HISTORICAL_LOTTO_DATA = [
    {"date": "2025-06-01", "two_digits": "20"}, # สมมติงวดล่าสุด 1 มิ.ย. 68
    {"date": "2025-05-16", "two_digits": "87"},
    {"date": "2025-05-02", "two_digits": "06"},
    {"date": "2025-04-16", "two_digits": "85"},
    {"date": "2025-04-01", "two_digits": "36"},
    {"date": "2025-03-16", "two_digits": "32"},
    {"date": "2025-03-01", "two_digits": "54"},
    {"date": "2025-02-16", "two_digits": "50"},
    {"date": "2025-02-01", "two_digits": "51"},
    {"date": "2025-01-17", "two_digits": "23"},
    {"date": "2025-01-02", "two_digits": "51"},
    {"date": "2024-12-16", "two_digits": "21"},
    {"date": "2024-12-01", "two_digits": "61"},
    {"date": "2024-11-16", "two_digits": "38"},
    {"date": "2024-11-01", "two_digits": "32"},
    {"date": "2024-10-16", "two_digits": "00"},
    {"date": "2024-10-01", "two_digits": "59"},
    {"date": "2024-09-16", "two_digits": "37"},
    {"date": "2024-09-01", "two_digits": "94"},
    {"date": "2024-08-16", "two_digits": "28"},
    {"date": "2024-08-01", "two_digits": "46"},
    {"date": "2024-07-16", "two_digits": "21"},
    {"date": "2024-07-01", "two_digits": "89"},
    {"date": "2024-06-16", "two_digits": "31"},
    {"date": "2024-06-01", "two_digits": "42"},
    {"date": "2024-05-16", "two_digits": "60"},
    {"date": "2025-05-02", "two_digits": "17"}, # Corrected year to 2025
    {"date": "2025-04-16", "two_digits": "79"}, # Corrected year to 2025
    {"date": "2025-04-01", "two_digits": "90"}, # Corrected year to 2025
    {"date": "2025-03-16", "two_digits": "78"}, # Corrected year to 2025
    {"date": "2025-03-01", "two_digits": "79"}, # Corrected year to 2025
    {"date": "2025-02-16", "two_digits": "43"}, # Corrected year to 2025
    {"date": "2025-02-01", "two_digits": "42"}, # Corrected year to 2025
    {"date": "2025-01-17", "two_digits": "58"}, # Corrected year to 2025
    {"date": "2025-01-02", "two_digits": "82"}, # Corrected year to 2025
    {"date": "2024-12-16", "two_digits": "15"},
    {"date": "2024-12-01", "two_digits": "74"},
    {"date": "2024-11-16", "two_digits": "45"},
    {"date": "2024-11-01", "two_digits": "70"},
    {"date": "2024-10-16", "two_digits": "66"},
    {"date": "2024-10-01", "two_digits": "12"},
    {"date": "2024-09-16", "two_digits": "83"},
    {"date": "2024-09-01", "two_digits": "75"},
    {"date": "2024-08-16", "two_digits": "42"},
    {"date": "2024-08-01", "two_digits": "64"},
    {"date": "2024-07-16", "two_digits": "53"},
    {"date": "2024-07-01", "two_digits": "92"},
    {"date": "2024-06-16", "two_digits": "17"},
    {"date": "2024-06-01", "two_digits": "05"},
    {"date": "2024-05-16", "two_digits": "38"},
    {"date": "2024-05-02", "two_digits": "71"},
    {"date": "2024-04-16", "two_digits": "07"},
    {"date": "2024-04-01", "two_digits": "18"},
]

# เพิ่มฟังก์ชันนี้ใน app.py เลย
def utc_to_bangkok(utc_dt):
    bangkok_tz = pytz.timezone('Asia/Bangkok')
    utc_tz = pytz.utc
    # กำหนด timezone ให้ utc_dt เป็น UTC ก่อน
    if utc_dt.tzinfo is None:
        utc_dt = utc_tz.localize(utc_dt)
    # แปลงเป็นเวลาบางกอก
    return utc_dt.astimezone(bangkok_tz)

def get_all_users():
    rows = read_range(SHEET_USERS_RANGE)
    users = []
    # ข้าม header แถวแรก
    for row in rows[1:]:
        if len(row) < 5:
            continue
        users.append({
            'username': row[0],
            'password': row[1],
            'credits': int(row[2]),
            'role': row[3],
            'is_banned': row[4].lower() == 'true'
        })
    return users


def find_user(username):
    users = get_all_users()
    for u in users:
        if u['username'] == username:
            return u
    return None

def update_user(username, field, value):
    rows = read_range(SHEET_USERS_RANGE)
    for i, row in enumerate(rows):
        if row and row[0] == username:
            # แก้ค่าในแถวที่ i
            col_map = {'password': 1, 'credits': 2, 'role': 3, 'is_banned': 4}
            col_index = col_map.get(field)
            if col_index is not None:
                # แก้ข้อมูลใน rows
                rows[i][col_index] = str(value)
                # อัปเดตข้อมูลใน Google Sheets
                write_range(SHEET_USERS_RANGE, rows)
                return True
    return False

def add_user(user):
    rows = read_range(SHEET_USERS_RANGE)
    # เพิ่มแถวใหม่
    new_row = [
        user['username'],
        user['password'],
        str(user['credits']),
        user['role'],
        str(user['is_banned'])
    ]
    rows.append(new_row)
    write_range(SHEET_USERS_RANGE, rows)

def delete_user(username):
    rows = read_range(SHEET_USERS_RANGE)
    rows = [row for row in rows if not (row and row[0] == username)]
    write_range(SHEET_USERS_RANGE, rows)


# --- Helper Functions for Lotto in Google Sheets ---

def fetch_latest_lotto_results_from_sheet():
    values = read_range(SHEET_LOTTO_RANGE)
    results = []
    for row in values:
        if len(row) < 2:
            continue
        date_str, two_digits = row[0], row[1]
        try:
            # แปลง string เป็น datetime แบบไม่มี timezone (สมมติเป็น UTC)
            dt_object = datetime.strptime(date_str, '%Y-%m-%d')
            # แปลง UTC > Bangkok
            dt_object_bkk = utc_to_bangkok(dt_object)
            # แสดงวันที่แบบ dd/mm/yyyy + ปี พศ. (อิงเวลาบางกอก)
            draw_date_display = dt_object_bkk.strftime('%d/%m/') + str(dt_object_bkk.year + 543)
            results.append({"draw_date": draw_date_display, "two_digit_end": two_digits})
        except Exception:
            continue
    # เรียงจากใหม่สุดไปเก่าสุด (แปลงกลับมาเป็น datetime จริงเพื่อ sort)
    results.sort(key=lambda x: datetime.strptime(x['draw_date'], '%d/%m/%Y'), reverse=True)
    return results[:5]

def get_ai_prediction_from_sheet():
    values = read_range(SHEET_LOTTO_RANGE)
    freq = {}
    for row in values:
        if row and len(row) > 1:
            num = row[1]
            freq[num] = freq.get(num, 0) + 1
    sorted_nums = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    predicted_numbers = [num for num, count in sorted_nums[:3]]
    while len(predicted_numbers) < 3:
        rand_num = str(random.randint(0, 99)).zfill(2)
        if rand_num not in predicted_numbers:
            predicted_numbers.append(rand_num)
    return predicted_numbers


# --- Decorator for admin role ---
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in') or session.get('role') != 'admin':
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function


# --- Routes ---

@app.route('/')
def index():
    latest_results = fetch_latest_lotto_results_from_sheet()
    ai_prediction_numbers = get_ai_prediction_from_sheet()
    logged_in_status = session.get('logged_in', False)
    username = session.get('username', 'Guest')
    credits = session.get('credits', 0)
    return render_template('index.html',
                           latest_lotto_results=latest_results,
                           ai_prediction=ai_prediction_numbers,
                           logged_in=logged_in_status,
                           username=username,
                           credits=credits,
                           role=session.get('role', 'user'))


@app.route('/login')
def login_page():
    if 'username' in session:
        return redirect(url_for('index'))
    return render_template('auth.html')


@app.route('/register')
def register_page():
    line_qr_link = "https://lin.ee/Bs6u0mw"
    return render_template('register_qr.html', line_qr_link=line_qr_link)

@app.route('/auth/login', methods=['POST'])
def auth_login():
    session.clear()
    username = request.form.get('username')
    password = request.form.get('password')
    user = find_user(username)
    if user:
        print(f"DEBUG: password input = '{password}'")
        print(f"DEBUG: stored_password = '{user['password']}'")
        if user['is_banned']:
            return jsonify({"success": False, "message": "บัญชีของคุณถูกระงับการใช้งาน กรุณาติดต่อแอดมิน"})
        if user['password'] != password:
            return jsonify({"success": False, "message": "ชื่อผู้ใช้งานหรือรหัสผ่านไม่ถูกต้อง"})
        session['username'] = username
        session['logged_in'] = True
        session['credits'] = user['credits']
        session['role'] = user['role']
        redirect_url = url_for('index')
        return jsonify({"success": True, "message": "Logged in successfully!", "redirect_url": redirect_url})
    else:
        return jsonify({"success": False, "message": "ชื่อผู้ใช้งานหรือรหัสผ่านไม่ถูกต้อง"})



@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


@app.route('/topup')
def topup_page_placeholder():
    if 'username' not in session:
        return redirect(url_for('login_page'))
    username = session['username']
    user = find_user(username)
    credits = user['credits'] if user else 0
    return render_template('topup.html', credits=credits)


@app.route('/api/request_lotto_number', methods=['POST'])
def request_lotto_number():
    if 'username' not in session:
        return jsonify({"success": False, "message": "กรุณาเข้าสู่ระบบเพื่อขอเลขนำโชค"})
    username = session['username']
    user = find_user(username)
    if not user:
        session.clear()
        return jsonify({"success": False, "message": "ไม่พบข้อมูลผู้ใช้งาน กรุณาเข้าสู่ระบบใหม่"})
    cost_per_incense = 5
    current_credits = user['credits']
    if current_credits < cost_per_incense:
        return jsonify({"success": False, "message": "เครดิตไม่เพียงพอ กรุณาเติมเงิน"}), 400
    lucky_number = str(random.randint(0, 99)).zfill(2)
    new_credits = current_credits - cost_per_incense
    update_user(username, 'credits', new_credits)
    session['credits'] = new_credits
    # อาจบันทึก transaction ไว้ Google Sheets หรือระบบอื่นในอนาคต
    return jsonify({
        "success": True,
        "lucky_number": lucky_number,
        "new_credits": new_credits
    })


@app.route('/api/topup_confirm', methods=['POST'])
def api_topup_confirm():
    if 'username' not in session:
        return jsonify({"success": False, "message": "กรุณาเข้าสู่ระบบเพื่อเติมเครดิต"}), 401
    username = session['username']
    data = request.get_json()
    amount = data.get('amount')
    if not isinstance(amount, int) or amount <= 0:
        return jsonify({"success": False, "message": "จำนวนเงินไม่ถูกต้อง"}), 400
    user = find_user(username)
    if not user:
        session.clear()
        return jsonify({"success": False, "message": "ไม่พบข้อมูลผู้ใช้งาน กรุณาเข้าสู่ระบบใหม่"}), 404
    new_credits = user['credits'] + amount
    update_user(username, 'credits', new_credits)
    session['credits'] = new_credits
    return jsonify({
        "success": True,
        "message": f"เติมเครดิต {amount} สำเร็จ! เครดิตใหม่: {new_credits}",
        "new_credits": new_credits
    })


@app.route('/admin/users')
@admin_required
def admin_users():
    users = get_all_users()
    return render_template('admin_users.html', users=users)


@app.route('/admin/users/ban/<username>', methods=['POST'])
@admin_required
def ban_user(username):
    update_user(username, 'is_banned', True)
    return jsonify({"success": True, "message": f"{username} ถูกแบนแล้ว"})


@app.route('/admin/users/unban/<username>', methods=['POST'])
@admin_required
def unban_user(username):
    update_user(username, 'is_banned', False)
    return jsonify({"success": True, "message": f"{username} ถูกปลดแบนแล้ว"})


@app.route('/admin/users/delete/<username>', methods=['POST'])
@admin_required
def delete_user_route(username):
    delete_user(username)
    return jsonify({"success": True, "message": f"{username} ถูกลบแล้ว"})


@app.route('/admin/users/update/<username>', methods=['POST'])
@admin_required
def admin_update_user(username):
    new_role = request.form.get('role')
    try:
        new_credits = int(request.form.get('credits'))
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "เครดิตต้องเป็นตัวเลข"}), 400
    if username == session.get('username') and new_role != 'admin':
        return jsonify({"success": False, "message": "คุณไม่สามารถเปลี่ยนสิทธิ์ตัวเองได้"}), 400
    update_user(username, 'role', new_role)
    update_user(username, 'credits', new_credits)
    return redirect(url_for('admin_users'))


@app.route('/profile')
def profile():
    if 'username' not in session:
        return redirect(url_for('login_page'))
    return render_template('profile.html')


@app.route('/admin/update_lotto', methods=['POST'])
@admin_required
def admin_update_lotto():
    data = request.get_json()
    lotto_results = data.get('lotto_results', [])  # [{"date": "2025-07-01", "two_digits": "45"}, ...]
    if not lotto_results:
        return jsonify({"success": False, "message": "ข้อมูลไม่ครบถ้วน"}), 400
    try:
        values_to_write = [[item['date'], item['two_digits']] for item in lotto_results]
        write_range(SHEET_LOTTO_RANGE, values_to_write)
        new_ai_prediction = get_ai_prediction_from_sheet()
        return jsonify({
            "success": True,
            "message": "อัปเดตผลหวยย้อนหลังเรียบร้อย",
            "new_ai_prediction": new_ai_prediction
        })
    except Exception as e:
        return jsonify({"success": False, "message": f"เกิดข้อผิดพลาด: {e}"}), 500


@app.route('/admin/update')
@admin_required
def admin_update_page():
    return render_template('admin_update_lotto.html')

def seed_historical_data_to_sheet():
    # แปลงข้อมูล dict เป็น list ของ list
    values = [[item['date'], item['two_digits']] for item in STATIC_HISTORICAL_LOTTO_DATA]
    # ลบข้อมูลเดิมในช่วงนั้นก่อน (ถ้ามี) ด้วยการเขียนแถวหัวตารางก่อน
    write_range(SHEET_LOTTO_RANGE, [])  # ล้างข้อมูลเก่า (ถ้าต้องการ)
    # เขียนข้อมูลใหม่ลง Google Sheets
    write_range(SHEET_LOTTO_RANGE, values)
    print(f"Seeded {len(values)} rows to Google Sheets.")


if __name__ == '__main__':
    os.makedirs('templates', exist_ok=True)
    # เช็ค Google Sheets ว่างไหม
    current_data = read_range(SHEET_LOTTO_RANGE)
    if not current_data or len(current_data) == 0:
        print("Google Sheets is empty. Seeding initial historical lotto data.")
        seed_historical_data_to_sheet()
    else:
        print("Google Sheets already has data. Skipping seeding.")
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True)