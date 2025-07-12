from dotenv import load_dotenv
import os
from werkzeug.security import generate_password_hash
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from pymongo import MongoClient

load_dotenv()  # โหลดตัวแปรจากไฟล์ .env เข้าสู่ environment

LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET')
MONGODB_URI = os.getenv('MONGODB_URI')

# ตั้งค่า LINE API
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# เชื่อม MongoDB
mongo_client = MongoClient(MONGODB_URI)
db = mongo_client['shrine_lotto']  # ชื่อตามที่สมเบ็นซ์ใช้จริง
users_collection = db['users']

mongo_client = MongoClient(MONGODB_URI)
db = mongo_client['shrine_lotto']  # ชื่อฐานข้อมูลที่ตั้งใน Atlas
users_collection = db['users']

# เก็บสถานะ user ชั่วคราว (แนะนำให้เปลี่ยนเป็น DB หรือ Redis ใน production)
user_states = {}

def create_user(username, password):
    existing = users_collection.find_one({'username': username})
    if existing:
        return False
    hashed_password = generate_password_hash(password)
    users_collection.insert_one({
        'username': username,
        'password': hashed_password,
        'credits': 0
    })
    return True

# Handler webhook LINE
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    text = event.message.text.strip()

    if user_id not in user_states:
        user_states[user_id] = {'expecting_phone': False}

    state = user_states[user_id]

    if text.lower() == 'สมัครสมาชิก':
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text='กรุณาส่งเบอร์โทร เช่น 0900000000 โดยไม่ต้องมี -')
        )
        state['expecting_phone'] = True
        return

    if state['expecting_phone']:
        phone = ''.join(filter(str.isdigit, text))  # ดึงแต่ตัวเลข
        if len(phone) == 10:
            username = phone
            password = phone[-4:]
            success = create_user(username, password)
            if success:
                reply_text = f"สมัครสมาชิกเรียบร้อย!\nusername: {username}\npassword: {password}"
            else:
                reply_text = "เบอร์นี้ถูกใช้สมัครแล้ว กรุณาลองใหม่"
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=reply_text)
            )
            state['expecting_phone'] = False
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text='เบอร์โทรไม่ถูกต้อง กรุณาส่งเบอร์โทร 10 หลัก เช่น 0900000000')
            )
        return

    # ถ้าไม่เข้าเงื่อนไขข้างบน ตอบ default
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text='ขอโทษค่ะ ไม่เข้าใจคำสั่งนี้ กรุณาพิมพ์ "สมัครสมาชิก" เพื่อเริ่มต้นสมัคร')
    )
