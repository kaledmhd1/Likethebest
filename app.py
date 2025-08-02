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

LIKE_API_URL = "https://like-bjwt-bngx.onrender.com/send_like"
PLAYER_INFO_URL = "https://bngx-info-player-x551.onrender.com/"
MAX_PARALLEL_REQUESTS = 40
LIKE_TARGET_EXPIRY = 86400  # 24 ساعة

# ⚠️ أدخل حساباتك هنا
accounts_passwords = {
    "4016272811": "7C9B67FD6A47A62C04FCD7BB68EF479168B7520A3E3F4EDA1415DCCF10F46311",
    "3231016152": "8AD81FC469728920C8454DCB23345022470774580030A36D7CA74A194229EAE4",
    "3231006740": "8133B583B7F2B0701733C5A0586F28205C3CC8B0DB5004EC731C7BB1EB64FA9F",
    "3231018315": "C1B0AC574DA747386676FEAC0A15DB6C7DCF1CCE9EFF71AD305C329AAF44ADF9",
    "3231016672": "FAB40727917046A4C9792FC693690F21C75B48DC2432984960E31DF794B114C9"
}

jwt_tokens_cache = {}
liked_targets_cache = {}
skipped_accounts = {}

cache_lock = threading.Lock()
liked_targets_lock = threading.Lock()
skipped_lock = threading.Lock()

last_tokens_refresh_time = 0


def split_accounts_into_groups(accounts_dict, n_groups=4):
    items = list(accounts_dict.items())
    group_size = (len(items) + n_groups - 1) // n_groups
    return [dict(items[i:i + group_size]) for i in range(0, len(items), group_size)]


def add_to_skipped(uid):
    with skipped_lock:
        skipped_accounts[uid] = time.time()
    with cache_lock:
        if uid in jwt_tokens_cache:
            del jwt_tokens_cache[uid]


def is_skipped(uid):
    with skipped_lock:
        if uid in skipped_accounts and time.time() - skipped_accounts[uid] < 86400:
            return True
        skipped_accounts.pop(uid, None)
        return False


def get_jwt_token(uid, password):
    try:
        url = f"https://ffwlxd-access-jwt.vercel.app/api/get_jwt?guest_uid={uid}&guest_password={password}"
        res = requests.get(url, timeout=10)
        print(f"[JWT] UID {uid} -> {res.status_code}")
        if res.status_code == 200:
            data = res.json()
            return data.get("BearerAuth")
    except Exception as e:
        print(f"[JWT ERROR] UID {uid} -> {e}")
    return None


def refresh_tokens_group(accounts_group, group_index):
    new_cache = {}
    print(f"[GROUP {group_index}] تحديث توكنات {len(accounts_group)} حساب...")
    with ThreadPoolExecutor(max_workers=MAX_PARALLEL_REQUESTS) as executor:
        futures = {executor.submit(get_jwt_token, uid, pwd): uid for uid, pwd in accounts_group.items() if not is_skipped(uid)}
        for future in futures:
            uid = futures[future]
            token = future.result()
            if token:
                new_cache[uid] = token
    with cache_lock:
        jwt_tokens_cache.update(new_cache)
    print(f"[GROUP {group_index}] ✅ تم تحديث {len(new_cache)} توكن.")


def refresh_all_tokens():
    print("[TOKEN REFRESH] تحديث جميع التوكنات...")
    groups = split_accounts_into_groups(accounts_passwords)
    for i, group in enumerate(groups):
        refresh_tokens_group(group, i + 1)
        time.sleep(1)
    print("[TOKEN REFRESH] ✅ الانتهاء من التحديث.")


def FOX_RequestAddingFriend(token, target_id):
    try:
        params = {"player_id": target_id, "token": token}
        headers = {
            "Accept": "*/*",
            "Authorization": f"Bearer {token}",
            "User-Agent": "Free Fire/2019117061 CFNetwork/1399 Darwin/22.1.0",
            "X-GA": "v1 1",
            "ReleaseVersion": "OB50",
        }
        res = requests.get(LIKE_API_URL, params=params, headers=headers, timeout=7)
        try:
            return res.status_code, res.json()
        except:
            return res.status_code, res.text
    except Exception as e:
        return 0, str(e)


def get_player_info(uid):
    try:
        res = requests.get(f"{PLAYER_INFO_URL}/{uid}", timeout=5)
        if res.status_code == 200:
            data = res.json()
            basic = data.get("basicinfo", [{}])[0]
            return {
                "nickname": basic.get("username", "Unknown"),
                "liked": basic.get("likes", 0),
                "accountId": uid
            }
    except Exception as e:
        print(f"[INFO ERROR] {uid} -> {e}")
    return {"nickname": "Unknown", "liked": 0, "accountId": uid}


@app.route("/add_likes", methods=["GET"])
def add_likes():
    global last_tokens_refresh_time
    uid = request.args.get("uid")
    if not uid or not uid.isdigit():
        return jsonify({"error": "uid مطلوب"}), 400

    now = time.time()
    if now - last_tokens_refresh_time >= 3600:
        threading.Thread(target=refresh_all_tokens).start()
        last_tokens_refresh_time = now

    with liked_targets_lock:
        expired = [u for u, t in liked_targets_cache.items() if now - t > LIKE_TARGET_EXPIRY]
        for u in expired:
            del liked_targets_cache[u]
        if uid in liked_targets_cache:
            return jsonify({"message": f"🚫 UID {uid} تم لايكه مسبقًا. انتظر 24 ساعة."}), 429
        liked_targets_cache[uid] = now

    with cache_lock:
        if not jwt_tokens_cache:
            return jsonify({"message": "🚧 التوكنات قيد التحميل... حاول بعد قليل."}), 503

    likes_sent = send_likes_background(uid)
    return jsonify({
        "message": f"✅ تم إرسال لايكات لـ UID {uid} بنجاح!",
        "likes_sent": likes_sent
    })


def send_likes_background(uid):
    print(f"[LIKE START] UID {uid}")
    try:
        player = get_player_info(uid)
        before = player["liked"]

        with cache_lock:
            tokens = dict(jwt_tokens_cache)

        success = 0
        stop_flag = threading.Event()

        def process(account_uid, token):
            nonlocal success
            if stop_flag.is_set():
                return
            status, res = FOX_RequestAddingFriend(token, uid)
            print(f"[LIKE TRY] {account_uid} -> status {status}, res: {res}")
            if isinstance(res, dict) and "BR_ACCOUNT_DAILY_LIKE_PROFILE_LIMIT" in str(res.get("response_text", "")):
                add_to_skipped(account_uid)
            elif status == 200:
                success += 1
                if success >= 60:
                    stop_flag.set()

        with ThreadPoolExecutor(max_workers=MAX_PARALLEL_REQUESTS) as executor:
            futures = [executor.submit(process, uid, token) for uid, token in tokens.items()]
            for f in futures:
                f.result()
                if stop_flag.is_set():
                    break

        after = before + success
        print(f"[LIKE DONE] UID {uid} 👍 {success} لايكات (قبل: {before}, بعد: {after})")
        return success
    except Exception as e:
        print(f"[LIKE ERROR] UID {uid} -> {e}")
        return 0


if __name__ == "__main__":
    print("[INIT] ✅ تشغيل السيرفر... التوكنات ستُحدث بالخلفية")
    threading.Thread(target=refresh_all_tokens).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
