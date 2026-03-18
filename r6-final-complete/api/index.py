from http.server import BaseHTTPRequestHandler
import json, os, time, random, urllib.request, urllib.error

try:
    from nacl.signing import VerifyKey
    from nacl.exceptions import BadSignatureError
    HAS_NACL = True
except ImportError:
    HAS_NACL = False

# ── Config ──────────────────────────────────────────────────────
OWNER_ID       = int(os.environ.get("OWNER_ID", "1455187536623304734"))
PUBLIC_KEY     = os.environ.get("DISCORD_PUBLIC_KEY", "").strip()
BOT_TOKEN      = os.environ.get("DISCORD_TOKEN", "").strip()
LOG_CHANNEL_ID = os.environ.get("LOG_CHANNEL_ID", "").strip()
DISCORD_API    = "https://discord.com/api/v10"
COOLDOWN_SEC   = 900
DAILY_LIMIT    = 5
DEFAULT_EMOJIS = {"success":"✅","error":"❌","account":"🎮","details":"📋","stock":"📦","cooldown":"⏳"}

# ── Vercel KV ───────────────────────────────────────────────────
KV_URL     = os.environ.get("KV_REST_API_URL",    "").strip()
KV_TOKEN_V = os.environ.get("KV_REST_API_TOKEN",  "").strip()

def kv_get(key):
    if not KV_URL: return None
    try:
        req = urllib.request.Request(f"{KV_URL}/get/{key}",
            headers={"Authorization": f"Bearer {KV_TOKEN_V}"})
        with urllib.request.urlopen(req, timeout=5) as r:
            return json.loads(r.read()).get("result")
    except: return None

def kv_set(key, value, ex=None):
    if not KV_URL: return
    try:
        path = f"{KV_URL}/set/{key}" + (f"?ex={ex}" if ex else "")
        req = urllib.request.Request(path, data=json.dumps(value).encode(),
            headers={"Authorization": f"Bearer {KV_TOKEN_V}",
                     "Content-Type": "application/json"}, method="POST")
        urllib.request.urlopen(req, timeout=5)
    except: pass

def kv_del(key):
    if not KV_URL: return
    try:
        req = urllib.request.Request(f"{KV_URL}/del/{key}",
            headers={"Authorization": f"Bearer {KV_TOKEN_V}"}, method="POST")
        urllib.request.urlopen(req, timeout=5)
    except: pass

def _jget(k, d):
    raw = kv_get(k)
    if raw is None: return d
    try: return json.loads(raw) if isinstance(raw, str) else raw
    except: return d

def _jset(k, v, ex=None): kv_set(k, json.dumps(v), ex)

def get_accounts():          return _jget("r6_accounts",         [])
def save_accounts(v):        _jset("r6_accounts", v)
def get_premium():           return _jget("r6_premium",          [])
def save_premium(v):         _jset("r6_premium", v)
def get_co_owners():         return _jget("r6_co_owners",        [])
def save_co_owners(v):       _jset("r6_co_owners", v)
def get_emojis():            return {**DEFAULT_EMOJIS, **_jget("r6_emojis", {})}
def save_emojis(v):          _jset("r6_emojis", v)
def get_bot_enabled():       return _jget("r6_enabled",          True)
def set_bot_enabled(v):      _jset("r6_enabled", v)
def get_gen_channel():       return _jget("r6_gen_channel",      "")
def set_gen_channel(v):      _jset("r6_gen_channel", v)
def get_feedback_channel():  return _jget("r6_feedback_channel", "")
def set_feedback_channel(v): _jset("r6_feedback_channel", v)

def push_log(message: str):
    logs = _jget("r6_logs", [])
    logs.append({"ts": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()), "msg": message})
    if len(logs) > 500: logs = logs[-500:]
    _jset("r6_logs", logs)

# ── Daily usage ─────────────────────────────────────────────────
def _today():      return time.strftime("%Y-%m-%d", time.gmtime())
def _day_key(uid): return f"daily_{uid}_{_today()}"

def get_daily_count(uid):
    raw = kv_get(_day_key(uid))
    try: return int(raw) if raw else 0
    except: return 0

def increment_daily(uid):
    count = get_daily_count(uid) + 1
    now = time.gmtime()
    ttl = (24-now.tm_hour)*3600 - now.tm_min*60 - now.tm_sec + 120
    kv_set(_day_key(uid), str(count), ex=ttl)
    return count

def decrement_daily(uid):
    count = max(0, get_daily_count(uid)-1)
    now = time.gmtime()
    ttl = (24-now.tm_hour)*3600 - now.tm_min*60 - now.tm_sec + 120
    kv_set(_day_key(uid), str(count), ex=ttl)

# ── Cooldown ────────────────────────────────────────────────────
def get_cooldown(uid):
    raw = kv_get(f"cd_{uid}")
    try: return float(raw) if raw else None
    except: return None

def set_cooldown(uid):
    exp = time.time() + COOLDOWN_SEC
    kv_set(f"cd_{uid}", str(exp), ex=COOLDOWN_SEC+60)
    return exp

def clear_cooldown(uid): kv_del(f"cd_{uid}")

# ── Auth ────────────────────────────────────────────────────────
def is_main_owner(uid): return uid == OWNER_ID
def is_owner(uid):      return uid == OWNER_ID or uid in get_co_owners()

def verify_sig(body: bytes, ts: str, sig: str) -> bool:
    if not PUBLIC_KEY or not HAS_NACL: return False
    try:
        VerifyKey(bytes.fromhex(PUBLIC_KEY)).verify(ts.encode() + body, bytes.fromhex(sig))
        return True
    except: return False

# ── Discord helpers ─────────────────────────────────────────────
def discord_req(method, endpoint, payload=None):
    data = json.dumps(payload).encode() if payload else None
    req  = urllib.request.Request(f"{DISCORD_API}{endpoint}", data=data,
        headers={"Authorization": f"Bot {BOT_TOKEN}",
                 "Content-Type": "application/json", "User-Agent": "R6Bot/1.0"},
        method=method)
    try:
        with urllib.request.urlopen(req, timeout=8) as r: return json.loads(r.read())
    except urllib.error.HTTPError as e: return {"error": e.read().decode()}
    except Exception as ex: return {"error": str(ex)}

def send_dm(uid, embeds=None, content=None):
    ch = discord_req("POST", "/users/@me/channels", {"recipient_id": str(uid)})
    if "id" not in ch: return False
    p = {}
    if content: p["content"] = content
    if embeds:  p["embeds"]  = embeds
    return "id" in discord_req("POST", f"/channels/{ch['id']}/messages", p)

def post_to_ch(channel_id, embeds=None, content=None):
    if not channel_id: return False
    p = {}
    if content: p["content"] = content
    if embeds:  p["embeds"]  = embeds
    return "id" in discord_req("POST", f"/channels/{channel_id}/messages", p)

def log_to_channel(message: str):
    ch = LOG_CHANNEL_ID or _jget("r6_log_channel", "")
    if ch and BOT_TOKEN:
        discord_req("POST", f"/channels/{ch}/messages", {"content": message})
    push_log(message)

def get_opt(options, name):
    for o in (options or []):
        if o["name"] == name: return o.get("value")
    return None

def get_user(ix):
    return ix.get("member", {}).get("user") or ix.get("user", {})

def msg(content=None, embeds=None, ephemeral=False):
    d = {}
    if content:   d["content"] = content
    if embeds:    d["embeds"]  = embeds
    if ephemeral: d["flags"]   = 64
    return {"type": 4, "data": d}

def fmt_time(s):
    m, s = int(s//60), int(s%60)
    if m and s: return f"{m}m {s}s"
    if m: return f"{m} minute{'s' if m!=1 else ''}"
    return f"{s}s"

# ── Embeds ──────────────────────────────────────────────────────
def dm_embed(account, remaining, cd_str, today_rem, emojis, user):
    av = f"https://cdn.discordapp.com/avatars/{user['id']}/{user.get('avatar','')}.png" if user.get("avatar") else "https://cdn.discordapp.com/embed/avatars/0.png"
    return {
        "title": f"{emojis['account']}  Rainbow Six Siege Account",
        "color": 0xDC143C, "thumbnail": {"url": av},
        "fields": [
            {"name": f"{emojis['details']}  Account Details",
             "value": f"```\n{account}\n```", "inline": False},
            {"name": f"{emojis['stock']}  Accounts Remaining",
             "value": f"**{remaining}** still in stock", "inline": True},
            {"name": f"{emojis['cooldown']}  Your Cooldown",
             "value": f"Next generate available in **{cd_str}**", "inline": True},
            {"name": "📅  Today's Remaining",
             "value": f"**{today_rem}** of {DAILY_LIMIT} accounts left today", "inline": True},
        ],
        "footer": {"text": "Keep this account safe — do not share it.", "icon_url": av},
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }

def channel_embed(user, remaining):
    av = f"https://cdn.discordapp.com/avatars/{user['id']}/{user.get('avatar','')}.png" if user.get("avatar") else "https://cdn.discordapp.com/embed/avatars/0.png"
    return {
        "title": "✨ Premium Account Generated", "color": 0x2B2D31,
        "thumbnail": {"url": av},
        "fields": [
            {"name": "User",              "value": f"<@{user['id']}>",  "inline": True},
            {"name": "Type",              "value": "Premium Account",   "inline": True},
            {"name": "Status",            "value": "✅ Check your DMs!", "inline": True},
            {"name": "Remaining Premium", "value": str(remaining),      "inline": True},
        ],
        "footer": {"text": f"developed by @Ego and @Death • {time.strftime('%m/%d/%Y', time.gmtime())}",
                   "icon_url": av},
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }

def stock_embed(count):
    return {
        "title": "📦 Account Stock Update",
        "description": f"Current account inventory: **{count}** accounts remaining.",
        "color": 0x5865F2,
        "footer": {"text": time.strftime("Last updated • %Y-%m-%d %H:%M UTC", time.gmtime())}
    }

# ── Commands ────────────────────────────────────────────────────
def cmd_addowner(ix):
    uid = int(get_user(ix)["id"])
    if not is_main_owner(uid): return msg("Only the main owner can manage co-owners.", ephemeral=True)
    target = int(get_opt(ix["data"].get("options",[]), "user"))
    if target == OWNER_ID: return msg("That user is already the main owner.", ephemeral=True)
    owners = get_co_owners()
    if target in owners: return msg(f"<@{target}> is already an owner.", ephemeral=True)
    owners.append(target); save_co_owners(owners)
    log_to_channel(f"📋 /addowner — granted owner to <@{target}>")
    return msg(f"✅ Owner access granted to <@{target}>.", ephemeral=True)

def cmd_removeowner(ix):
    uid = int(get_user(ix)["id"])
    if not is_main_owner(uid): return msg("Only the main owner can manage co-owners.", ephemeral=True)
    target = int(get_opt(ix["data"].get("options",[]), "user"))
    owners = get_co_owners()
    if target not in owners: return msg(f"<@{target}> is not a co-owner.", ephemeral=True)
    owners.remove(target); save_co_owners(owners)
    log_to_channel(f"📋 /removeowner — revoked owner from <@{target}>")
    return msg(f"✅ Owner access revoked from <@{target}>.", ephemeral=True)

def cmd_listowners(ix):
    uid = int(get_user(ix)["id"])
    if not is_owner(uid): return msg("You do not have permission.", ephemeral=True)
    owners = get_co_owners()
    if not owners: return msg(f"No co-owners. Only main owner <@{OWNER_ID}>.", ephemeral=True)
    return msg("\n".join(f"<@{i}>" for i in owners), ephemeral=True)

def cmd_addaccount(ix):
    uid = int(get_user(ix)["id"])
    if not is_owner(uid): return msg("You do not have permission.", ephemeral=True)
    account = get_opt(ix["data"].get("options",[]), "account")
    accs = get_accounts(); accs.append(account); save_accounts(accs)
    log_to_channel(f"📋 /addaccount — pool size now {len(accs)}")
    return msg(f"✅ Account added. Pool size: **{len(accs)}**.", ephemeral=True)

def cmd_addpremium(ix):
    uid = int(get_user(ix)["id"])
    if not is_owner(uid): return msg("You do not have permission.", ephemeral=True)
    target = int(get_opt(ix["data"].get("options",[]), "user"))
    p = get_premium()
    if target in p: return msg(f"<@{target}> already has premium.", ephemeral=True)
    p.append(target); save_premium(p)
    log_to_channel(f"📋 /addpremium — granted premium to <@{target}>")
    return msg(f"✅ Premium granted to <@{target}>.", ephemeral=True)

def cmd_removepremium(ix):
    uid = int(get_user(ix)["id"])
    if not is_owner(uid): return msg("You do not have permission.", ephemeral=True)
    target = int(get_opt(ix["data"].get("options",[]), "user"))
    p = [i for i in get_premium() if i != target]; save_premium(p)
    log_to_channel(f"📋 /removepremium — revoked premium from <@{target}>")
    return msg(f"✅ Premium revoked from <@{target}>.", ephemeral=True)

def cmd_accountcount(ix):
    uid = int(get_user(ix)["id"])
    if not is_owner(uid): return msg("You do not have permission.", ephemeral=True)
    return msg(f"There are **{len(get_accounts())}** account(s) in the pool.", ephemeral=True)

def cmd_listaccounts(ix):
    uid = int(get_user(ix)["id"])
    if not is_owner(uid): return msg("You do not have permission.", ephemeral=True)
    accs = get_accounts()
    if not accs: return msg("The account pool is empty.", ephemeral=True)
    lines = "\n".join(f"{i+1}. {a[:60]}{'...' if len(a)>60 else ''}" for i,a in enumerate(accs))
    if not send_dm(uid, content=f"**Account Pool ({len(accs)} total):**\n{lines}"):
        return msg("I couldn't DM you. Please enable DMs.", ephemeral=True)
    return msg("Account list sent to your DMs.", ephemeral=True)

def cmd_setemoji(ix):
    uid = int(get_user(ix)["id"])
    if not is_owner(uid): return msg("You do not have permission.", ephemeral=True)
    opts = ix["data"].get("options",[])
    et = get_opt(opts, "emoji_type"); em = get_opt(opts, "emoji")
    emojis = get_emojis(); emojis[et] = em; save_emojis(emojis)
    return msg(f"✅ Emoji for **{et}** set to {em}", ephemeral=True)

def cmd_sendstock(ix):
    uid = int(get_user(ix)["id"])
    if not is_owner(uid): return msg("You are not authorized.", ephemeral=True)
    ch = get_opt(ix["data"].get("options",[]), "channel")
    res = discord_req("POST", f"/channels/{ch}/messages", {"embeds": [stock_embed(len(get_accounts()))]})
    if "error" in res: return msg(f"Failed: {res['error']}", ephemeral=True)
    return msg(f"✅ Stock update sent to <#{ch}>.", ephemeral=True)

def cmd_botstatus(ix):
    uid = int(get_user(ix)["id"])
    if not is_owner(uid): return msg("You do not have permission.", ephemeral=True)
    action = get_opt(ix["data"].get("options",[]), "action")
    set_bot_enabled(action == "enable")
    log_to_channel(f"📋 /botstatus — bot {'ENABLED' if action=='enable' else 'DISABLED'}")
    return msg(f"{'✅ Bot enabled.' if action=='enable' else '🔴 Bot disabled (maintenance).'}", ephemeral=True)

def cmd_setchannel(ix):
    uid = int(get_user(ix)["id"])
    if not is_owner(uid): return msg("You do not have permission.", ephemeral=True)
    ch = get_opt(ix["data"].get("options",[]), "channel")
    set_gen_channel(ch)
    log_to_channel(f"📋 /setchannel — gen channel set to <#{ch}>")
    return msg(f"✅ Generate channel set to <#{ch}>.", ephemeral=True)

def cmd_setfeedbackchannel(ix):
    uid = int(get_user(ix)["id"])
    if not is_owner(uid): return msg("You do not have permission.", ephemeral=True)
    ch = get_opt(ix["data"].get("options",[]), "channel")
    set_feedback_channel(ch)
    log_to_channel(f"📋 /setfeedbackchannel — set to <#{ch}>")
    return msg(f"✅ Feedback channel set to <#{ch}>.", ephemeral=True)

def cmd_feedback(ix):
    user  = get_user(ix)
    uid   = int(user["id"])
    uname = user.get("global_name") or user.get("username") or "Unknown"
    av    = f"https://cdn.discordapp.com/avatars/{user['id']}/{user.get('avatar','')}.png" if user.get("avatar") else "https://cdn.discordapp.com/embed/avatars/0.png"
    text  = get_opt(ix["data"].get("options",[]), "message") or ""
    if not text.strip(): return msg("❌ Please include a feedback message.", ephemeral=True)

    now_str = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())
    staff_embed = {
        "title": "📬 New Feedback Received", "color": 0x5865F2,
        "thumbnail": {"url": av},
        "fields": [
            {"name": "👤 User",     "value": f"<@{uid}> ({uname})", "inline": True},
            {"name": "🆔 User ID",  "value": str(uid),              "inline": True},
            {"name": "📝 Feedback", "value": text,                  "inline": False},
        ],
        "footer": {"text": f"Submitted • {now_str}", "icon_url": av},
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }

    fb_ch = get_feedback_channel() or LOG_CHANNEL_ID or _jget("r6_log_channel", "")
    if fb_ch: post_to_ch(fb_ch, embeds=[staff_embed])

    log_to_channel(f"📬 /feedback — {uname} ({uid}) submitted feedback")

    user_embed = {
        "title": "✅ Feedback Received!",
        "description": f"<@{uid}> thanks for your feedback, we will look into this! 🙏",
        "color": 0x00E676,
        "fields": [{"name": "Your Feedback", "value": text, "inline": False}],
        "footer": {"text": "R6 Generator • We appreciate your input!"},
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }
    return msg(embeds=[user_embed], ephemeral=True)

def cmd_generate(ix):
    user   = get_user(ix)
    uid    = int(user["id"])
    emojis = get_emojis()

    if not get_bot_enabled():
        return msg("The bot is currently **offline** for maintenance.", ephemeral=True)

    if not is_owner(uid) and uid not in get_premium():
        log_to_channel(f"📋 /generate — {user.get('username','?')} ({uid}) ❌ no premium")
        return msg(f"{emojis['error']} You do not have premium access. Please open a ticket to purchase premium.", ephemeral=True)

    if not is_owner(uid):
        cd_ts = get_cooldown(uid)
        if cd_ts is not None:
            left = cd_ts - time.time()
            if left > 0:
                log_to_channel(f"📋 /generate — {user.get('username','?')} ({uid}) ❌ cooldown")
                return msg(f"{emojis['cooldown']} You are on cooldown. Please wait **{fmt_time(left)}**.", ephemeral=True)

    if not is_owner(uid):
        if get_daily_count(uid) >= DAILY_LIMIT:
            log_to_channel(f"📋 /generate — {user.get('username','?')} ({uid}) ❌ daily limit")
            return msg(f"{emojis['error']} Daily limit of **{DAILY_LIMIT}** reached. Come back tomorrow!", ephemeral=True)

    accs = get_accounts()
    if not accs:
        log_to_channel(f"📋 /generate — {user.get('username','?')} ({uid}) ❌ pool empty")
        return msg(f"{emojis['error']} No accounts available at the moment.", ephemeral=True)

    account = random.choice(accs)
    accs.remove(account); save_accounts(accs)
    remaining = len(accs)
    cd_str = fmt_time(COOLDOWN_SEC)

    if not is_owner(uid):
        set_cooldown(uid)
        today_rem = DAILY_LIMIT - increment_daily(uid)
    else:
        today_rem = "∞"

    if not send_dm(uid, embeds=[dm_embed(account, remaining, cd_str, today_rem, emojis, user)]):
        accs.append(account); save_accounts(accs)
        if not is_owner(uid): clear_cooldown(uid); decrement_daily(uid)
        log_to_channel(f"📋 /generate — {user.get('username','?')} ({uid}) ❌ DMs closed")
        return msg(f"{emojis['error']} I couldn't DM you. Please enable DMs from server members.", ephemeral=True)

    gen_ch = get_gen_channel()
    if gen_ch: post_to_ch(gen_ch, embeds=[channel_embed(user, remaining)])

    log_to_channel(f"📋 /generate — {user.get('username','?')} ({uid}) ✅ sent — {remaining} remaining")
    return msg(f"{emojis['success']} Your account has been sent to your DMs!", ephemeral=True)

# ── Dashboard API ───────────────────────────────────────────────
def handle_api(path, method, body_bytes):
    try: body = json.loads(body_bytes) if body_bytes else {}
    except: body = {}

    if path == "/api/status" and method == "GET":
        return 200, {"enabled": get_bot_enabled(), "accounts": len(get_accounts()),
                     "premium": len(get_premium()), "owners": len(get_co_owners()),
                     "gen_channel": get_gen_channel(), "feedback_channel": get_feedback_channel(),
                     "has_token": bool(BOT_TOKEN), "nacl": HAS_NACL, "pubkey": bool(PUBLIC_KEY)}

    if path == "/api/logs" and method == "GET":
        return 200, {"logs": _jget("r6_logs", [])}

    if path == "/api/premium" and method == "GET":
        return 200, {"premium": get_premium()}

    if path == "/api/premium" and method == "POST":
        action = body.get("action"); uid_s = str(body.get("user_id",""))
        if not uid_s: return 400, {"error": "user_id required"}
        uid = int(uid_s); p = get_premium()
        if action == "add":
            if uid not in p: p.append(uid)
            save_premium(p); push_log(f"✅ Premium granted to {uid} via dashboard")
            return 200, {"ok": True, "premium": p}
        elif action == "remove":
            p = [i for i in p if i != uid]; save_premium(p)
            push_log(f"Premium removed from {uid} via dashboard")
            return 200, {"ok": True, "premium": p}
        return 400, {"error": "invalid action"}

    if path == "/api/setchannel" and method == "POST":
        ch = str(body.get("channel_id",""))
        set_gen_channel(ch); push_log(f"Gen channel set to {ch} via dashboard")
        return 200, {"ok": True}

    if path == "/api/feedbackchannel" and method == "POST":
        ch = str(body.get("channel_id",""))
        set_feedback_channel(ch); push_log(f"Feedback channel set to {ch} via dashboard")
        return 200, {"ok": True}

    if path == "/api/toggle" and method == "POST":
        new_state = not get_bot_enabled(); set_bot_enabled(new_state)
        push_log(f"Bot {'ENABLED' if new_state else 'DISABLED'} via dashboard")
        return 200, {"enabled": new_state}

    if path == "/api/accounts" and method == "GET":
        return 200, {"accounts": get_accounts(), "count": len(get_accounts())}

    if path == "/api/accounts" and method == "POST":
        acc = body.get("account","").strip()
        if not acc: return 400, {"error": "account required"}
        accs = get_accounts(); accs.append(acc); save_accounts(accs)
        push_log(f"✅ Account added via dashboard — pool: {len(accs)}")
        return 200, {"ok": True, "count": len(accs)}

    if path == "/api/accounts" and method == "DELETE":
        idx = body.get("index"); accs = get_accounts()
        if idx is None or idx < 0 or idx >= len(accs): return 400, {"error": "invalid index"}
        accs.pop(idx); save_accounts(accs)
        push_log(f"Account removed via dashboard — pool: {len(accs)}")
        return 200, {"ok": True, "count": len(accs)}

    return 404, {"error": "not found"}

# ── Commands map ────────────────────────────────────────────────
COMMANDS = {
    "addowner":            cmd_addowner,
    "removeowner":         cmd_removeowner,
    "listowners":          cmd_listowners,
    "addaccount":          cmd_addaccount,
    "addpremium":          cmd_addpremium,
    "removepremium":       cmd_removepremium,
    "accountcount":        cmd_accountcount,
    "listaccounts":        cmd_listaccounts,
    "setemoji":            cmd_setemoji,
    "sendstock":           cmd_sendstock,
    "botstatus":           cmd_botstatus,
    "setchannel":          cmd_setchannel,
    "setfeedbackchannel":  cmd_setfeedbackchannel,
    "feedback":            cmd_feedback,
    "generate":            cmd_generate,
}

# ── Vercel handler ──────────────────────────────────────────────
class handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def _json(self, code, data):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,DELETE,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type,Authorization")
        self.end_headers()

    def do_GET(self):
        path = self.path.split("?")[0]
        if path.startswith("/api/") and path != "/api/index":
            code, data = handle_api(path, "GET", None)
            return self._json(code, data)
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", "13")
        self.end_headers()
        self.wfile.write(b"R6 Bot online!")

    def do_POST(self):
        path   = self.path.split("?")[0]
        length = int(self.headers.get("Content-Length", 0))
        body   = self.rfile.read(length)

        if path.startswith("/api/") and path != "/api/index":
            code, data = handle_api(path, "POST", body)
            return self._json(code, data)

        # Discord interactions endpoint
        ts  = self.headers.get("X-Signature-Timestamp", "")
        sig = self.headers.get("X-Signature-Ed25519",   "")

        if not verify_sig(body, ts, sig):
            self.send_response(401)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"invalid request signature")
            return

        try:
            data = json.loads(body)
        except Exception:
            self.send_response(400)
            self.end_headers()
            return

        # PING — must respond with {"type":1}
        if data.get("type") == 1:
            return self._json(200, {"type": 1})

        # Slash command
        if data.get("type") == 2:
            name = data.get("data", {}).get("name", "")
            fn   = COMMANDS.get(name)
            resp = fn(data) if fn else msg(f"Unknown command: {name}")
            return self._json(200, resp)

        # fallback
        return self._json(200, {"type": 1})

    def do_DELETE(self):
        path   = self.path.split("?")[0]
        length = int(self.headers.get("Content-Length", 0))
        body   = self.rfile.read(length)
        if path.startswith("/api/"):
            code, data = handle_api(path, "DELETE", body)
            return self._json(code, data)
        self.send_response(404)
        self.end_headers()
