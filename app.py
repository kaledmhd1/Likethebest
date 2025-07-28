from flask import Flask, request, jsonify
import asyncio
import httpx
import math
import urllib3
import time

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# ---------------------- الإعدادات ----------------------
MAX_CONCURRENCY = 100   # أقصى عدد مهام تعمل بالتوازي
JWT_TIMEOUT = 10        # timeout لطلب JWT
LIKE_TIMEOUT = 10       # timeout لطلب اللايك
TOKEN_TTL = 1200        # 20 دقيقة (بالثواني)
# ------------------------------------------------------

tokens1 = tokens1 = {
  "3686947614": "BBCB287183F61B1D6987DF3CC8F63BE5DF02497D10D61FD8A690AEA9EEC9D7C6",
  "3703589868": "D8AC9A88EC82547D2EEE5DF74A9DCA8938A6224F3135A3F79B61C4D72DC76D9F",
  "3703581616": "470A7B48E3CCA8FCB3AB038D45CA84137C944810C4A1AEDA522BED4C16245DDB",
  "3705091766": "05DA56414E76D9B3C0CCF53D39375EA2612A4A61048145489E94968937621A36",
  "3571068251": "7BE9F640DA9CF587165E7FC3E19D84D508434D854940C657DAC716681762DC58",
  "3570805077": "918375395A01CE646787A83B8462558883B344F02F2B67743905A0B1328C2803",
  "3570807153": "E3220E9AC6B22B4E8FF11399C283A637F549D473FBF3CF34AF1E1EB9BCE14073",
  "3570810070": "48B28D373FC4CFE7725E46FB9194328142995255EF308036355237F64D520C1B",
  "3570812747": "5A67DF078D9C473504529CB18292CAD0E7E1C011214A9CBF16F3DE7BE33C90C2",
  "3570815439": "BC483310D5ACD777CA961CF787B30DEC635843E0D2634C7E7E86367745094EFC",
  "3570973425": "A0D4F0AAD479CB96CA68F884803E5B5B7EFEF1E0D8DFD86BCEDE3124187D66E9",
  "3571071338": "9D2E44DD49041ED472D6B0A3135C7D8566F451F9E4294F236707F5F0F926C8D1",
  "3570987388": "E1BC7A76EA5A5FB04C575FAB3024707B0D1B56BBF46FE88CEC2F5B244E5D14BA",
  "3571038526": "129B4443B8EBE947B74B00E26904F4B41365AD4864F8A613B613BA024C1622DE",
  "3571060549": "AD852CFCBBE2831AFA8041E8916E5F15DF23F25AEB64A5AECDBED835BD982641",
  "3570961255": "B70802454A86BFEB381074A023E51256EEA6140051E07C7866B1E05D34C9A707",
  "3570947551": "2EE5B376D325ACC39124EE8E8F367E312824E7128E19303F7D4BB788ABA36128",
  "3571016121": "49C555117A8C3A48667118E9FFC4CE602E3ADCEE00F8CE043360D619BB5BF039",
  "3571022105": "D1F01B0039F578B8F57EB18AA2DDF484071692E7EBC3FB21FB3AC8C8E468CF3E",
  "3570994682": "BD3BF27B08AE2A49421ACA712DCA63A2E69BB4225A54A4CAB3D68E6CCAC48ED4",
  "3570978936": "0C750173514945F61BC9B6CBA403D9001BFB423D968661FA41C6CEDFD1377597",
  "3570985274": "3E926F4B80E982499125E5BF3DB07241CD17CD21E213ACC3EA00E0FF924C94F9",
  "3570963517": "33D49B0C9D08FFC0F6E6FB8493F470EEA7FE13C3E8C1407593B4E5D6B267F346",
  "3571019534": "578657947F3DC1DF51BA57EBF2F3D10E2E63563ED0371B16CA634C1385B53AC0",
  "3571042403": "B1C0EF9D629A5AC55649DBAFDF8007B57F2E2FFAEC2CBF0ED5C731F50BE66FB4",
  "3230912452": "0D21772B575B339BABAC31F9476625B0A2E5F50391691859F2B4ED9ED106E573",
  "3230917475": "CED8D6CD638A313EA408D47CA1D99FCBA86452FEBBC339EF49191F24A6754D07",
  "3230906826": "04982081167F54A01EC41D26D2FD8A75E05C3D9666631FDDE4686BE682299A3E",
  "3230914130": "7AEFBA50E7F3F3DEB9757C6823B9F35367CD72812BC86D3DDD5435BB199C8E5A",
  "3230917980": "A0C49616501B90BAA6F9690C2B77BBFDCDD7915CDBA829F95D527F27F5948043",
  "3230915072": "1C9F0FFE274B8313D9170E324402D166ED694503A8170F849518F191F1A69F1A",
  "3230916958": "564CA8E828CEF9BC60A97EEFCB03046D3A3AF581513CAB74DA1190DCF86F50BC",
  "3230914592": "0DEAD683E890F2E1FF180D2D160678BD562AA73366CE7E23E4A7CB913274F9F1",
  "3230918533": "AE8E0C19F31FA0591ECD8AC801C486E8932B08BCC98C9AAA586FC98E759535AE",
  "3230919054": "8A2957237C86860D2117A703508BB4DD1FF28E948F9F856F696418C36D193C93",
  "3230916138": "3F9DE62CD79782FB5DF05737EE9260754F56001093B4EDDD4B172F3A185B456C",
  "3230920064": "FD3D69E8C74132E05EB51F607361EDF5FFFFA4C14C9933F6873E9E4AFDA1CA61",
  "3230921609": "7AF295C59D93553828E73B1860DA7B3B4B68ABAAB45C62E2843DFFAF41B42159",
  "3230922683": "8436CE4B02529691CA964BC74812F2D0094A3985BAC9E2ED34FF3710D456A518",
  "3230919547": "476BA2388D194B3774F0716DB9DF0061742261F17CD995F7A875ECB293448A9B",
  "3230911916": "CE3BC9722ED40BE2030FD3818328B0989E14C7F4416822A4B9FABDFF8170D935",
  "3230922129": "EEB0AA01BCE43BE09C9EA3076F081F3DA9256CF5455D4275CD2E5A77AF5C85AA",
  "3230923217": "B7FEFC6A8C14807D97E3531DE5B9042150899C112C70118CF6FD3CA6400052CA",
  "3230925265": "6D7B6A4334C08D780ABEF70A63702118E25FFC8BDC155402CA583F63D3EFC9DE",
  "3230926745": "54B196281143670C9067DEB987A6AF31EF8E7B9F6AEFF3B37215A863CCB11EE9",
  "3230924748": "1A9BCC257D44833489BA8C3B609470EECAF7D7231E3B29F4177E04C7B4582181",
  "3230923739": "18453FBA06CB08E61EFA9B44F69E961CC206E0EE59051B3C194D62C6ADF7FED1",
  "3230924237": "DA1E9B60AE3036558A1339A1720CD000D27F6CB31495725FA9A3F3FBEA3CA171",
  "3230928917": "21A22C69EF45C716DEA8DBB046FE65E0311DCE0C0B93403A657ED34618246BCD",
  "3230920573": "FD15B18F46AF8AB71F68A83F0C7D84E77751F6F16F52B7F064FF72EE70066AE6",
  "3230929426": "97954DA77C020CCA9423DB423ADCB0BDEA38A175325918762237D60DAEAD5CA8",
  "3230921162": "2D7B4EA5F27E7BADE222C668B5911B2A51FFD0A31B44B97E171CAA274C431D0B",
  "3230931208": "5F6AF35191016532505B1455EC9914270C29E78C7E8A2CD271EAAC168199A731",
  "3230927310": "A92299F51A405F4E183442D8695E80F936150690289815BF87F5646ACC841179",
  "3230926228": "1EC17ED3FC8D239C148549460492DF4B0DD96159F6892DD8C4879B30A38F690F",
  "3230927911": "243D636D21A981514FA1D6660A6FF33556CEE7170E0E5F192973E4476E3D43E8",
  "3230928390": "08B0368B43287A1A8F31CCD9AB782E6B47CC5C8FFEE9493C3D6C37D4AB12C389",
  "3230932103": "C8980CF21CD09D471DC11BE5EB241D086EA3464338E8102C75C5859E625E63A0",
  "3230929960": "E84199343DE04683ECED05C95DEF4C597D3F78A3AA66216387130FF9486F5075",
  "3230930501": "441AB871A35AD7EF18F3BA1D4C686636547118D3D34758C034A0E93051968052",
  "3230933240": "AFBC808B368329C45EA44CB92CF4080D456E03C62BC9E24AF9D66AFAF54BBDBB",
  "3230934847": "D607AFEC598F0A1F982CD50EA7C49557194F055971BEE410985BCD7E327D1CA8",
  "3230934314": "1B3740940C427C2206FBCBABBD4F6906D1CCF4D563C8062AE40666A483CE87A3"
}

tokens_groups = {'sv1': tokens1}

# ---------------------- كاش للتوكن ----------------------
TOKEN_CACHE: dict[str, dict] = {}
TOKEN_LOCKS: dict[str, asyncio.Lock] = {}

def _get_lock(uid: str) -> asyncio.Lock:
    lock = TOKEN_LOCKS.get(uid)
    if lock is None:
        lock = asyncio.Lock()
        TOKEN_LOCKS[uid] = lock
    return lock

async def get_jwt_token_cached(uid: str, password: str, client: httpx.AsyncClient, force_refresh: bool = False):
    now = time.time()
    cache_entry = TOKEN_CACHE.get(uid)

    if not force_refresh and cache_entry and (now - cache_entry["time"] < TOKEN_TTL):
        return cache_entry["token"]

    lock = _get_lock(uid)
    async with lock:
        cache_entry = TOKEN_CACHE.get(uid)
        if not force_refresh and cache_entry and (now - cache_entry["time"] < TOKEN_TTL):
            return cache_entry["token"]

        token = await get_jwt_token_async(uid, password, client)
        if token:
            TOKEN_CACHE[uid] = {"token": token, "time": time.time()}
        return token

# ---------------------- دوال Async ----------------------

async def get_jwt_token_async(uid: str, password: str, client: httpx.AsyncClient):
    url = f"https://jwt-gen-api-v2.onrender.com/token?uid={uid}&password={password}"
    try:
        r = await client.get(url, timeout=JWT_TIMEOUT)
        if r.status_code == 200:
            data = r.json()
            if data.get('status') in ('success', 'live'):
                return data.get('token')
    except Exception as e:
        print(f"Error getting JWT token for UID {uid}: {e}")
    return None

async def fox_request_adding_friend_async(token: str, target_id: int, client: httpx.AsyncClient):
    url = "https://arifi-like-token.vercel.app/like"
    params = {"token": token, "id": target_id}
    headers = {"Authorization": f"Bearer {token}"}
    res = await client.get(url, params=params, headers=headers, timeout=LIKE_TIMEOUT)
    return {"ok": res.status_code == 200}

async def do_like_async(uid: str, password: str, target_id: int, client: httpx.AsyncClient):
    token = await get_jwt_token_cached(uid, password, client)
    if not token:
        return {"ok": False}

    res = await fox_request_adding_friend_async(token, target_id, client)

    if not res["ok"]:
        refreshed = await get_jwt_token_cached(uid, password, client, force_refresh=True)
        if refreshed and refreshed != token:
            res = await fox_request_adding_friend_async(refreshed, target_id, client)

    return res

async def run_add_likes_async(selected_tokens, target_id: int, n: int):
    per_token = math.ceil(n / len(selected_tokens))
    executed = 0
    success_count = 0

    limits = httpx.Limits(max_keepalive_connections=MAX_CONCURRENCY, max_connections=MAX_CONCURRENCY)
    async with httpx.AsyncClient(verify=False, limits=limits) as client:
        sem = asyncio.Semaphore(min(MAX_CONCURRENCY, n))
        tasks = []

        async def bounded(uid, password):
            async with sem:
                return await do_like_async(uid, password, target_id, client)

        for uid, password in selected_tokens:
            for _ in range(per_token):
                if executed >= n:
                    break
                tasks.append(asyncio.create_task(bounded(uid, password)))
                executed += 1
            if executed >= n:
                break

        results = await asyncio.gather(*tasks, return_exceptions=True)
        success_count = sum(1 for r in results if not isinstance(r, Exception) and r.get("ok"))

    return success_count

# ---------------------- الراوت ----------------------

@app.route('/add_likes', methods=['GET'])
@app.route('/sv<int:sv_number>/add_likes', methods=['GET'])
def send_friend_requests(sv_number=None):
    target_id = request.args.get('uid')
    n = int(request.args.get('n', 100))

    if not target_id:
        return jsonify({"error": "target_id is required"}), 400

    try:
        target_id = int(target_id)
    except ValueError:
        return jsonify({"error": "target_id must be an integer"}), 400

    if sv_number is not None:
        group_name = f'sv{sv_number}'
        selected_tokens = list(tokens_groups.get(group_name, {}).items())
        if not selected_tokens:
            return jsonify({"error": f"Invalid group: {group_name}"}), 400
    else:
        selected_tokens = list(tokens1.items())

    if not selected_tokens:
        return jsonify({"error": "no tokens available"}), 500

    # جلب معلومات اللاعب قبل اللايك
    info_url = f"https://razor-info.vercel.app/player-info?uid={target_id}&region=me"
    try:
        info_resp = httpx.get(info_url, timeout=5)
        basic_info = info_resp.json().get("basicInfo", {})
        player_name = basic_info.get("nickname", "unknown")
        likes_before = int(basic_info.get("liked", 0))
    except Exception:
        player_name = "unknown"
        likes_before = 0

    # تشغيل اللايكات
    likes_added = asyncio.run(run_add_likes_async(selected_tokens, target_id, n))
    likes_after = likes_before + likes_added

    return jsonify({
        "uid": target_id,
        "player_name": player_name,
        "likes_before": likes_before,
        "likes_after": likes_after,
        "likes_added": likes_added
    })

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
