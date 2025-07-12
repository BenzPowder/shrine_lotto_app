# app.py
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from pymongo import MongoClient
from dotenv import load_dotenv
import os
from datetime import datetime
import random # For random number generation
from werkzeug.security import generate_password_hash, check_password_hash # For password hashing
from linebot_handler import handler
from functools import wraps
from flask import session, redirect, url_for
import certifi
# Removed: bs4, time, re, apscheduler, waitress (specific imports for scraping, scheduling)

load_dotenv()  # โหลดตัวแปรจากไฟล์ .env เข้าสู่ environment

LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET')
MONGODB_URI = os.getenv('MONGODB_URI')

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'super_secret_key_for_dev') # Needed for session management

# --- MongoDB Setup ---
# For local development, use default MongoDB URI
# For deployment, ensure you configure MONGODB_URI environment variable
mongo_uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
# client = MongoClient(mongo_uri)
client = MongoClient(mongo_uri, tls=True, tlsCAFile=certifi.where())
db = client.shrine_lotto # Database name

# Collection for lottery results (unused but kept for consistency)
lotto_results_collection = db.lotto_results
# Collection for user management
users_collection = db.users
# Collection for historical lottery results for AI
historical_lotto_collection = db.historical_lotto_results

# --- Hardcoded Static Historical Lottery Data for AI Prediction (Sample) ---
# This data will be used to seed the historical_lotto_results collection
# if it is empty.
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

# --- Debugging Paths ---
# These print statements help verify Flask's template folder and file existence.
print(f"Flask app root path: {app.root_path}")
print(f"Flask template folder: {app.template_folder}")
print(f"Checking for index.html at: {os.path.join(app.template_folder, 'index.html')}")
if os.path.exists(os.path.join(app.template_folder, 'index.html')):
    print("index.html found at expected path!")
else:
    print("WARNING: index.html NOT FOUND at expected path!")

# --- Helper Function to Seed Historical Lottery Data from Static List ---
def seed_historical_data_from_static_list():
    """
    Seeds historical lottery results from a static hardcoded list into MongoDB.
    This function should ideally be run once to seed the database.
    """
    inserted_count = 0
    print("Seeding historical lottery data from static list...")

    for draw_data in STATIC_HISTORICAL_LOTTO_DATA:
        iso_date = draw_data['date']
        two_digits_formatted = draw_data['two_digits']
        
        # Check if the draw already exists to prevent duplicates
        if not historical_lotto_collection.find_one({'date': iso_date, 'two_digits': two_digits_formatted}):
            historical_lotto_collection.insert_one({
                'date': iso_date,
                'two_digits': two_digits_formatted,
                'raw_data_source': 'static_seed' # Add source for clarity
            })
            inserted_count += 1
    
    print(f"Finished seeding {inserted_count} new historical lottery results from static list.")
    print(f"Total historical records in DB: {historical_lotto_collection.count_documents({})} documents.")
    return True

# --- Helper Function to Fetch Latest 5 Lottery Results from MongoDB ---
def fetch_latest_lotto_results_from_mongo():
    """
    Fetches the latest 5 lottery results from MongoDB.
    """
    try:
        # Ensure historical data exists, if not, seed from static list
        if historical_lotto_collection.count_documents({}) == 0:
            print("Historical data not found for latest results. Attempting to seed from static data.")
            seed_historical_data_from_static_list() 
            if historical_lotto_collection.count_documents({}) == 0:
                print("Failed to get initial data for latest results from static list. Returning dummy mock data.")
                # Fallback to dummy data if seeding fails (shouldn't happen with static data)
                return [
                    {"draw_date": "01/06/2568", "two_digit_end": "XX"},
                    {"draw_date": "16/05/2568", "two_digit_end": "XX"},
                    {"draw_date": "02/05/2568", "two_digit_end": "XX"},
                    {"draw_date": "16/04/2568", "two_digit_end": "XX"},
                    {"draw_date": "01/04/2568", "two_digit_end": "XX"},
                ]

        # Get the latest 5 unique lottery results from historical_lotto_collection
        # Sort by date descending and limit to 5 unique draws
        latest_5_results = list(
            historical_lotto_collection.find()
            .sort('date', -1) # Sort by date descending
            .limit(5) # Get top 5
        )
        
        # Format results for the frontend (to match previous mock_results structure)
        formatted_results = []
        for res in latest_5_results:
            # Convert ISO date (YYYY-MM-DD) back to DD/MM/YYYY for display if needed
            try:
                dt_object = datetime.strptime(res['date'], '%Y-%m-%d')
                # Convert year to Buddhist Era for display if desired (e.g., 2568)
                draw_date_display = dt_object.strftime('%d/%m/') + str(dt_object.year + 543) # Format to DD/MM/YYYY_BE
            except ValueError:
                draw_date_display = res['date'] # Fallback if parsing fails

            formatted_results.append({
                "draw_date": draw_date_display,
                "two_digit_end": res['two_digits']
            })
        
        return formatted_results
    except Exception as e:
        print(f"Error fetching latest 5 results from DB: {e}")
        # Fallback to mock data if DB query fails
        mock_results = [
            {"draw_date": "01/06/2568", "two_digit_end": "XX"},
            {"draw_date": "16/05/2568", "two_digit_end": "XX"},
            {"draw_date": "02/05/2568", "two_digit_end": "XX"},
            {"draw_date": "16/04/2568", "two_digit_end": "XX"},
            {"draw_date": "01/04/2568", "two_digit_end": "XX"},
        ]
        return mock_results


# --- AI Prediction Logic ---
def get_ai_prediction_from_historical_data():
    """
    Analyzes historical lottery data from MongoDB to provide a 2-digit prediction.
    For MVP, this will be a simple frequency analysis of the most common numbers.
    """
    try:
        # Ensure historical data exists, if not, attempt to seed from static list
        if historical_lotto_collection.count_documents({}) == 0:
            print("Historical data not found in DB for AI prediction. Attempting to seed from static data.")
            seed_historical_data_from_static_list() 
            if historical_lotto_collection.count_documents({}) == 0:
                print("Failed to get initial data for AI prediction from static list. Returning dummy prediction.")
                return ["XX", "YY", "ZZ"] 

        # Aggregate to find the frequency of each two_digits number
        # We'll use all available historical data (no limit for general frequency)
        pipeline = [
            {'$group': {
                '_id': '$two_digits',
                'count': {'$sum': 1}
            }},
            {'$sort': {'count': -1}}, # Sort by frequency descending
            {'$limit': 3} # Get the top 3 most frequent numbers
        ]

        top_numbers = list(historical_lotto_collection.aggregate(pipeline))
        
        predicted_numbers = [num['_id'] for num in top_numbers]
        
        # If less than 3 numbers found (shouldn't happen with ample data), pad with random numbers
        while len(predicted_numbers) < 3:
            random_num = str(random.randint(0, 99)).zfill(2)
            if random_num not in predicted_numbers: # Ensure uniqueness
                predicted_numbers.append(random_num)

        return predicted_numbers

    except Exception as e:
        print(f"Error generating AI prediction: {e}")
        return ["XX", "YY", "ZZ"] # Fallback to dummy on error


# --- Routes ---
@app.route('/')
def index():
    """
    Renders the main view. Shows public data or logged-in view based on session.
    """
    print("Attempting to render index.html in main app.") # Debug print

    latest_results = fetch_latest_lotto_results_from_mongo()
    ai_prediction_numbers = get_ai_prediction_from_historical_data()

    logged_in_status = session.get('logged_in', False)
    username = session.get('username', 'Guest')
    credits = session.get('credits', 0)

    try:
        return render_template('index.html',
                       latest_lotto_results=latest_results,
                       ai_prediction=ai_prediction_numbers,
                       logged_in=logged_in_status,
                       username=username,
                       credits=credits,
                       role=session.get('role', 'user'))

    except Exception as e:
        print(f"ERROR: Failed to render index.html. Exception: {e}")
        return f"Error rendering page: {e}", 500 # Return 500 if rendering fails

@app.route('/login')
def login_page():
    if 'username' in session:
        return redirect(url_for('index'))
    return render_template('auth.html')

@app.route('/register')
def register_page():
    # # Registration logic will be here, for now it renders auth.html
    # return render_template('auth.html') # Corrected: Direct rendering, not redirecting to login_page
    # แสดงหน้า QR code ให้สแกนเพื่อ add LINE
    line_qr_link = "https://lin.ee/Bs6u0mw"  # ลิงก์ LINE OA ของสมเบ็นซ์
    return render_template('register_qr.html', line_qr_link=line_qr_link)


@app.route('/auth/login', methods=['POST'])
def auth_login():
    # เคลียร์ session ก่อน
    session.clear()

    username = request.form.get('username')
    password = request.form.get('password')

    user = users_collection.find_one({'username': username})
    print(f"DEBUG: user found: {user}")

    if user:
        print(f"DEBUG: is_banned = {user.get('is_banned', False)}")
        is_banned = user.get('is_banned', False)
        if isinstance(is_banned, str):
            is_banned = is_banned.lower() == 'true'  # แปลง string เป็น bool
        if not check_password_hash(user['password'], password):
            return jsonify({"success": False, "message": "ชื่อผู้ใช้งานหรือรหัสผ่านไม่ถูกต้อง"})
        if is_banned:
            return jsonify({"success": False, "message": "บัญชีของคุณถูกระงับการใช้งาน กรุณาติดต่อแอดมิน"})
        
        # เข้าสู่ระบบ
        session['username'] = username
        session['logged_in'] = True
        session['credits'] = user.get('credits', 0)
        session['role'] = user.get('role', 'user')

        # ส่ง redirect ไปหน้า index ทุกคน
        redirect_url = url_for('index')

        return jsonify({"success": True, "message": "Logged in successfully!", "redirect_url": redirect_url})

    else:
        return jsonify({"success": False, "message": "ชื่อผู้ใช้งานหรือรหัสผ่านไม่ถูกต้อง"})

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in') or session.get('role') != 'admin':
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/admin/users')
@admin_required
def admin_users():
    print("DEBUG: admin_users page requested")
    users = list(users_collection.find({}, {'password': 0}))  # ไม่เอารหัสผ่าน
    return render_template('admin_users.html', users=users)

@app.route('/admin/users/ban/<username>', methods=['POST'])
@admin_required
def ban_user(username):
    users_collection.update_one({'username': username}, {'$set': {'is_banned': True}})
    return jsonify({"success": True, "message": f"{username} ถูกแบนแล้ว"})

@app.route('/admin/users/unban/<username>', methods=['POST'])
@admin_required
def unban_user(username):
    users_collection.update_one({'username': username}, {'$set': {'is_banned': False}})
    return jsonify({"success": True, "message": f"{username} ถูกปลดแบนแล้ว"})

@app.route('/admin/users/delete/<username>', methods=['POST'])
@admin_required
def delete_user(username):
    users_collection.delete_one({'username': username})
    return jsonify({"success": True, "message": f"{username} ถูกลบแล้ว"})

@app.route('/admin/users/update/<username>', methods=['POST'])
@admin_required
def admin_update_user(username):
    new_role = request.form.get('role')
    try:
        new_credits = int(request.form.get('credits'))
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "เครดิตต้องเป็นตัวเลข"}), 400

    # ป้องกัน admin แก้สิทธิ์ตัวเองให้ตกลง
    if username == session.get('username') and new_role != 'admin':
        return jsonify({"success": False, "message": "คุณไม่สามารถเปลี่ยนสิทธิ์ตัวเองได้"}), 400

    result = users_collection.update_one(
        {'username': username},
        {'$set': {'role': new_role, 'credits': new_credits}}
    )
    if result.modified_count == 1:
        return redirect(url_for('admin_users'))
    else:
        return jsonify({"success": False, "message": "ไม่พบผู้ใช้งาน หรือข้อมูลไม่เปลี่ยนแปลง"}), 404
    
@app.route('/api/get_credits')
def api_get_credits():
    if 'username' not in session:
        return jsonify({"success": False, "credits": 0}), 401
    username = session['username']
    user = users_collection.find_one({'username': username})
    credits = user.get('credits', 0) if user else 0
    return jsonify({"success": True, "credits": credits})

@app.route('/auth/register', methods=['POST'])
def auth_register():
    username = request.form.get('username')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')

    if not username or not password or not confirm_password:
        return jsonify({"success": False, "message": "กรุณากรอกข้อมูลให้ครบถ้วน"})
    
    if password != confirm_password:
        return jsonify({"success": False, "message": "รหัสผ่านไม่ตรงกัน"})

    if users_collection.find_one({'username': username}):
        return jsonify({"success": False, "message": "ชื่อผู้ใช้งานนี้ถูกใช้ไปแล้ว"})

    hashed_password = generate_password_hash(password)
    
    new_user = {
        'username': username,
        'password': hashed_password,
        'credits': 50,        # เครดิตเริ่มต้น
        'role': 'user',       # กำหนด role ให้เป็น user
        'is_banned': False    # ตั้งค่าเริ่มต้นไม่ถูกแบน
    }
    users_collection.insert_one(new_user)

    session['username'] = username
    session['logged_in'] = True
    session['credits'] = new_user['credits']
    session['role'] = new_user['role']   # เก็บ role ไว้ใน session

    return jsonify({"success": True, "message": "สมัครสมาชิกสำเร็จ!", "redirect_url": url_for('index')})

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('username', None)
    session.pop('credits', None)
    session.pop('role', None)
    return redirect(url_for('index'))

@app.route('/topup')
def topup_page_placeholder():
    # This route should actually render topup.html and check login
    if 'username' not in session:
        return redirect(url_for('login_page'))
    
    username = session['username']
    user = users_collection.find_one({'username': username})
    credits = user.get('credits', 0) if user else 0

    return render_template('topup.html', credits=credits)

@app.route('/api/request_lotto_number', methods=['POST'])
def request_lotto_number():
    if 'username' not in session:
        return jsonify({"success": False, "message": "กรุณาเข้าสู่ระบบเพื่อขอเลขนำโชค"})

    username = session['username']
    user = users_collection.find_one({'username': username})

    if not user:
        session.pop('username', None)
        session.pop('logged_in', None)
        session.pop('credits', None)
        return jsonify({"success": False, "message": "ไม่พบข้อมูลผู้ใช้งาน กรุณาเข้าสู่ระบบใหม่"})

    cost_per_incense = 5
    current_credits = user.get('credits', 0)

    if current_credits < cost_per_incense:
        return jsonify({"success": False, "message": "เครดิตไม่เพียงพอ กรุณาเติมเงิน"}), 400

    lucky_number = str(random.randint(0, 99)).zfill(2)

    # อัพเดตเครดิต
    new_credits = current_credits - cost_per_incense
    users_collection.update_one(
        {'username': username},
        {'$set': {'credits': new_credits}}
    )
    session['credits'] = new_credits

    # บันทึก transaction ขอเลข
    db.transactions.insert_one({
        'user_id': user['_id'],
        'type': 'request_number',
        'amount': cost_per_incense,
        'lotto_number': lucky_number,
        'timestamp': datetime.utcnow()
    })

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

    user = users_collection.find_one({'username': username})
    if not user:
        session.pop('username', None)
        session.pop('logged_in', None)
        session.pop('credits', None)
        return jsonify({"success": False, "message": "ไม่พบข้อมูลผู้ใช้งาน กรุณาเข้าสู่ระบบใหม่"}), 404

    current_credits = user.get('credits', 0)
    new_credits = current_credits + amount

    users_collection.update_one(
        {'username': username},
        {'$set': {'credits': new_credits}}
    )
    session['credits'] = new_credits

    # บันทึก transaction เติมเครดิต
    db.transactions.insert_one({
        'user_id': user['_id'],
        'type': 'topup',
        'amount': amount,
        'lotto_number': None,
        'timestamp': datetime.utcnow()
    })

    return jsonify({
        "success": True,
        "message": f"เติมเครดิต {amount} สำเร็จ! เครดิตใหม่: {new_credits}",
        "new_credits": new_credits
    })

# --- route แสดงหน้า profile ---
@app.route('/profile')
def profile():
    if 'username' not in session:
        return redirect(url_for('login_page'))
    return render_template('profile.html')

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature")
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"

@app.route('/admin/update_lotto', methods=['POST'])
@admin_required
def admin_update_lotto():
    data = request.get_json()
    lotto_results = data.get('lotto_results', [])  # [{"date": "2025-07-01", "two_digits": "45"}, ...]

    if not lotto_results:
        return jsonify({"success": False, "message": "ข้อมูลไม่ครบถ้วน"}), 400

    try:
        # อัปเดตฐานข้อมูลโดย upsert ตามวันที่ (date)
        for item in lotto_results:
            date = item.get('date')
            two_digits = item.get('two_digits')
            if date and two_digits:
                historical_lotto_collection.update_one(
                    {'date': date},
                    {'$set': {'two_digits': two_digits, 'raw_data_source': 'admin_update'}},
                    upsert=True
                )

        # รีคำนวณเลข AI ใหม่หลัง update
        new_ai_prediction = get_ai_prediction_from_historical_data()

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




if __name__ == '__main__':
    # Ensure templates folder exists
    os.makedirs('templates', exist_ok=True)
    # Seed historical lottery data ONCE if the collection is empty
    if historical_lotto_collection.count_documents({}) == 0:
        print("Historical lottery data collection is empty on startup. Attempting to seed from static data.")
        seed_historical_data_from_static_list()
    else:
        print("Historical lottery data already exists. Skipping initial data seeding from static data.")

    # Run the Flask app with explicit host and port for stability
    # Using built-in Flask server, NOT debug=True, NOT use_reloader=True
    # app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)
    app.run(host='127.0.0.1', port=5000, debug=True)


