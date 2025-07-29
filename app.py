from flask import Flask, request, jsonify
import requests
import json
import threading
import time
import os
import urllib3
from concurrent.futures import ThreadPoolExecutor

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# ---------------- إعدادات ----------------
ACC_FILE = 'accs.txt'
JWT_API_URL = "https://jwt-gen-api-v2.onrender.com/token"
LIKE_API_URL = "https://arifi-like-token.vercel.app/like"
PLAYER_INFO_URL = "https://razor-info.vercel.app/player-info"
MAX_PARALLEL_REQUESTS = 150
TOKEN_REFRESH_INTERVAL = 300        # 5 دقائق لتحديث التوكنات العادية
SKIPPED_REFRESH_INTERVAL = 3600     # ساعة لتحديث التوكنات المتخطاة
LIKE_TARGET_EXPIRY = 86400          # 24 ساعة

# ------------------------------------------

skipped_accounts = {}       # (uid: timestamp)
jwt_tokens_cache = {}       # (uid: token)
accounts_passwords = {}     # (uid: password) لتحميلها مرة واحدة فقط
liked_targets_cache = {}    # (target_uid: last_like_timestamp)
liked_targets_lock = threading.Lock()

cache_lock = threading.Lock()
skipped_lock = threading.Lock()

def add_to_skipped(uid):
    with skipped_lock:
        skipped_accounts[uid] = time.time()
    with cache_lock:
        if uid in jwt_tokens_cache:
            del jwt_tokens_cache[uid]

def is_skipped(uid):
    with skipped_lock:
        now = time.time()
        if uid in skipped_accounts:
            if now - skipped_accounts[uid] < 86400:  # 24 ساعة
                return True
            else:
                del skipped_accounts[uid]
                return False
        return False

def load_accounts(filepath=ACC_FILE):
    global accounts_passwords
    if not os.path.exists(filepath):
        print(f"[ERROR] الملف {filepath} غير موجود.")
        return {}
    try:
        with open(filepath, 'r') as f:
            all_accounts = json.load(f)
            accounts_passwords = all_accounts  # حفظ للمراجعة لاحقاً
            return all_accounts
    except Exception as e:
        print(f"[ERROR] خطأ أثناء قراءة {filepath}: {e}")
        return {}

def get_jwt_token(uid, password):
    url = f"{JWT_API_URL}?uid={uid}&password={password}"
    try:
        response = requests.get(url, timeout=10)
        print(f"[JWT] UID {uid} -> {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            if data.get('status') in ['success', 'live']:
                return data.get('token')
    except Exception as e:
        print(f"[JWT ERROR] UID {uid} -> {e}")
    return None

def refresh_all_tokens():
    global jwt_tokens_cache
    print("[TOKEN REFRESH] بدء تحديث توكنات JWT لجميع الحسابات (غير المتخطاة)...")
    accounts = load_accounts()
    new_cache = {}
    with ThreadPoolExecutor(max_workers=MAX_PARALLEL_REQUESTS) as executor:
        futures = {executor.submit(get_jwt_token, uid, pwd): uid for uid, pwd in accounts.items() if not is_skipped(uid)}
        for future in futures:
            uid = futures[future]
            token = future.result()
            if token:
                new_cache[uid] = token
            else:
                print(f"[TOKEN REFRESH] فشل تحديث التوكن للحساب {uid}")

    with cache_lock:
        for uid in new_cache:
            jwt_tokens_cache[uid] = new_cache[uid]
        for uid in list(jwt_tokens_cache.keys()):
            if is_skipped(uid):
                del jwt_tokens_cache[uid]

    print(f"[TOKEN REFRESH] تم تحديث {len(new_cache)} توكنات بنجاح.")

def refresh_skipped_tokens():
    print("[SKIPPED REFRESH] بدء تحديث توكنات الحسابات المتخطاة (الحد اليومي)...")
    to_remove = []
    with skipped_lock:
        uids = list(skipped_accounts.keys())

    with ThreadPoolExecutor(max_workers=MAX_PARALLEL_REQUESTS) as executor:
        futures = {}
        for uid in uids:
            pwd = accounts_passwords.get(uid)
            if pwd:
                futures[executor.submit(get_jwt_token, uid, pwd)] = uid

        for future in futures:
            uid = futures[future]
            token = future.result()
            if token:
                status, content = FOX_RequestAddingFriend(token, target_id="0")
                if status == 200:
                    if not (isinstance(content, dict) and "BR_ACCOUNT_DAILY_LIKE_PROFILE_LIMIT" in str(content.get("response_text", ""))):
                        print(f"[SKIPPED REFRESH] تم إعادة تفعيل الحساب {uid} بعد انتهاء الحد اليومي.")
                        with skipped_lock:
                            if uid in skipped_accounts:
                                del skipped_accounts[uid]
                        with cache_lock:
                            jwt_tokens_cache[uid] = token
                else:
                    print(f"[SKIPPED REFRESH] الحساب {uid} لا يزال في الحد اليومي أو فشل التحقق.")
            else:
                print(f"[SKIPPED REFRESH] فشل تحديث التوكن للحساب {uid}")

def token_refresh_worker():
    while True:
        try:
            refresh_all_tokens()
        except Exception as e:
            print(f"[TOKEN REFRESH ERROR] {e}")
        time.sleep(TOKEN_REFRESH_INTERVAL)

def skipped_refresh_worker():
    while True:
        try:
            refresh_skipped_tokens()
        except Exception as e:
            print(f"[SKIPPED REFRESH ERROR] {e}")
        time.sleep(SKIPPED_REFRESH_INTERVAL)

def FOX_RequestAddingFriend(token, target_id):
    try:
        params = {"token": token, "id": target_id}
        headers = {
            "Accept": "*/*",
            "Authorization": f"Bearer {token}",
            "User-Agent": "Free Fire/2019117061 CFNetwork/1399 Darwin/22.1.0",
            "X-GA": "v1 1",
            "ReleaseVersion": "OB49",
        }
        response = requests.get(LIKE_API_URL, params=params, headers=headers, timeout=5)
        try:
            return response.status_code, response.json()
        except:
            return response.status_code, response.text
    except Exception as e:
        return 0, str(e)

def get_player_info(uid):
    try:
        url = f"{PLAYER_INFO_URL}?uid={uid}&region=me"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            basic = data.get('basicInfo', {})
            nickname = basic.get('nickname', 'Unknown')
            liked = basic.get('liked', 0)
            accountId = basic.get('accountId', uid)
            return {"nickname": nickname, "liked": liked, "accountId": accountId}
    except Exception as e:
        print(f"[PLAYER INFO ERROR] UID {uid} -> {e}")
    return {"nickname": "Unknown", "liked": 0, "accountId": uid}

from flask import Response

@app.route('/add_likes', methods=['GET'])
def send_likes():
    target_id = request.args.get('uid')
    if not target_id or not target_id.isdigit():
        return jsonify({"error": "uid is required and must be an integer"}), 400

    player_info = get_player_info(target_id)
    likes_before = player_info["liked"]

    now = time.time()
    with liked_targets_lock:
        to_delete = [uid for uid, ts in liked_targets_cache.items() if now - ts > LIKE_TARGET_EXPIRY]
        for uid in to_delete:
            del liked_targets_cache[uid]

        if target_id in liked_targets_cache:
            return Response(json.dumps({
                "message": f"🚫 لا يمكن إرسال لايك لنفس الـ UID {target_id} إلا بعد مرور 24 ساعة من آخر مرة."
            }, ensure_ascii=False), mimetype='application/json'), 429

        liked_targets_cache[target_id] = now

    with cache_lock:
        if not jwt_tokens_cache:
            return Response(json.dumps({
                "message": "🚧 التوكنات لم تُجهز بعد، الرجاء المحاولة لاحقاً."
            }, ensure_ascii=False), mimetype='application/json'), 503

        tokens_to_use = dict(jwt_tokens_cache)

    success_count = 0
    skipped_count = 0
    failed_count = 0
    successful_uids = []
    stop_flag = threading.Event()

    def process(uid, token):
        nonlocal success_count, skipped_count, failed_count
        if stop_flag.is_set():
            return

        status, content = FOX_RequestAddingFriend(token, target_id)

        if isinstance(content, dict) and "BR_ACCOUNT_DAILY_LIKE_PROFILE_LIMIT" in str(content.get("response_text", "")):
            skipped_count += 1
            add_to_skipped(uid)
            return

        if status == 200:
            success_count += 1
            successful_uids.append(uid)
            if success_count >= 100:
                stop_flag.set()
        else:
            failed_count += 1

    with ThreadPoolExecutor(max_workers=MAX_PARALLEL_REQUESTS) as executor:
        futures = [executor.submit(process, uid, token) for uid, token in tokens_to_use.items()]
        for future in futures:
            future.result()
            if stop_flag.is_set():
                break

    likes_after = likes_before + success_count

    message = (
        f"✅ الاسم: {player_info['nickname']}\n"
        f"🆔 UID: {player_info['accountId']}\n"
        f"👍 قبل: {likes_before} لايك\n"
        f"➕ المضافة: {success_count} لايك\n"
        f"💯 بعد: {likes_after} لايك"
    )

    return Response(json.dumps({
        "message": message
    }, ensure_ascii=False), mimetype='application/json')

if __name__ == '__main__':
    load_accounts()
    refresh_all_tokens()
    threading.Thread(target=token_refresh_worker, daemon=True).start()
    threading.Thread(target=skipped_refresh_worker, daemon=True).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
