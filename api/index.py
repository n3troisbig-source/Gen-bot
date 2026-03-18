"""
R6 Account Generator — Vercel Serverless Bot
Matches every feature from bot.py, runs as HTTP interactions endpoint.
"""
from http.server import BaseHTTPRequestHandler
import json, os, time, random, urllib.request, urllib.error
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError

# ── Config ─────────────────────────────────────────────────────
OWNER_ID       = int(os.environ.get("OWNER_ID", "1455187536623304734"))
PUBLIC_KEY     = os.environ.get("DISCORD_PUBLIC_KEY", "")
BOT_TOKEN      = os.environ.get("DISCORD_TOKEN", "")
LOG_CHANNEL_ID = os.environ.get("LOG_CHANNEL_ID", "1469885026283028500")
DISCORD_API    = "https://discord.com/api/v10"
COOLDOWN_SEC   = 900   # 15 minutes
DAILY_LIMIT    = 5

DEFAULT_EMOJIS = {
    "success":  "✅",
    "error":    "❌",
    "account":  "🎮",
    "details":  "📋",
    "stock":    "📦",
    "cooldown": "⏳",
}

# ── Vercel KV ──────────────────────────────────────────────────
KV_URL   = os.environ.get("KV_REST_API_URL", "")
KV_TOKEN = os.environ.get("KV_REST_API_TOKEN", "")

def kv_get(key):
    if not KV_URL: return None
    try:
        req = urllib.request.Request(
            f"{KV_URL}/get/{key}",
            headers={"Authorization": f"Bearer {KV_TOKEN}"}
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            return json.loads(r.read()).get("result")
    except: return None

def kv_set(key, value, ex=None):
    if not KV_URL: return
    try:
        path = f"{KV_URL}/set/{key}" + (f"?ex={ex}" if ex else "")
        req = urllib.request.Request(
            path, data=json.dumps(value).encode(),
            headers={"Authorization": f"Bearer {KV_TOKEN}", "Content-Type": "application/json"},
            method="POST"
        )
        urllib.request.urlopen(req, timeout=5)
    except: pass

def kv_del(key):
    if not KV_URL: return
    try:
        req = urllib.request.Request(
            f"{KV_URL}/del/{key}",
            headers={"Authorization": f"Bearer {KV_TOKEN}"},
            method="POST"
        )
        urllib.request.urlopen(req, timeout=5)
    except: pass

# ── Data helpers ───────────────────────────────────────────────
def _jget(key, default):
    raw = kv_get(key)
    if raw is None: return default
    try: return json.loads(raw) if isinstance(raw, str) else raw
    except: return default

def _jset(key, val, ex=None): kv_set(key, json.dumps(val), ex)

def get_accounts():    return _jget("r6_accounts",   [])
def save_accounts(v):  _jset("r6_accounts", v)
def get_premium():     return _jget("r6_premium",    [])
def save_premium(v):   _jset("r6_premium", v)
def get_co_owners():   return _jget("r6_co_owners",  [])
def save_co_owners(v): _jset("r6_co_owners", v)
def get_emojis():      return {**DEFAULT_EMOJIS, **_jget("r6_emojis", {})}
def save_emojis(v):    _jset("r6_emojis", v)
def get_bot_enabled(): return _jget("r6_enabled", True)
def set_bot_enabled(v):_jset("r6_enabled", v)

# ── Daily usage ────────────────────────────────────────────────
def _today(): return time.strftime("%Y-%m-%d", time.gmtime())

def _day_key(uid): return f"daily_{uid}_{_today()}"

def get_daily_count(uid):
    raw = kv_get(_day_key(uid))
    try: return int(raw) if raw else 0
    except: return 0

def increment_daily(uid):
    count = get_daily_count(uid) + 1
    now   = time.gmtime()
    ttl   = (24 - now.tm_hour) * 3600 - now.tm_min * 60 - now.tm_sec + 120
    kv_set(_day_key(uid), str(count), ex=ttl)
    return count

def decrement_daily(uid):
    count = max(0, get_daily_count(uid) - 1)
    now   = time.gmtime()
    ttl   = (24 - now.tm_hour) * 3600 - now.tm_min * 60 - now.tm_sec + 120
    kv_set(_day_key(uid), str(count), ex=ttl)

def daily_remaining(uid): return max(0, DAILY_LIMIT - get_daily_count(uid))

# ── Cooldown ───────────────────────────────────────────────────
def get_cooldown(uid):
    raw = kv_get(f"cd_{uid}")
    try: return float(raw) if raw else None
    except: return None

def set_cooldown(uid):
    exp = time.time() + COOLDOWN_SEC
    kv_set(f"cd_{uid}", str(exp), ex=COOLDOWN_SEC + 60)
    return exp

def clear_cooldown(uid): kv_del(f"cd_{uid}")

# ── Logging to Discord channel ─────────────────────────────────
def log_to_channel(message: str):
    if not LOG_CHANNEL_ID or not BOT_TOKEN: return
    try:
        discord_request("POST", f"/channels/{LOG_CHANNEL_ID}/messages",
                        {"content": message})
    except: pass

# ── Owner check ────────────────────────────────────────────────
def is_main_owner(uid: int): return uid == OWNER_ID
def is_owner(uid: int):      return uid == OWNER_ID or uid in get_co_owners()

# ── Sig verify ────────────────────────────────────────────────
def verify_sig(body: bytes, ts: str, sig: str) -> bool:
    try:
        VerifyKey(bytes.fromhex(PUBLIC_KEY)).verify(ts.encode() + body, bytes.fromhex(sig))
        return True
    except: return False

# ── Discord API ────────────────────────────────────────────────
def discord_request(method, endpoint, payload=None):
    data = json.dumps(payload).encode() if payload else None
    req  = urllib.request.Request(
        f"{DISCORD_API}{endpoint}", data=data,
        headers={"Authorization": f"Bot {BOT_TOKEN}",
                 "Content-Type": "application/json", "User-Agent": "R6Bot/1.0"},
        method=method
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as r: return json.loads(r.read())
    except urllib.error.HTTPError as e: return {"error": e.read().decode()}
    except Exception as ex: return {"error": str(ex)}

def send_dm(uid, content=None, embeds=None):
    ch = discord_request("POST", "/users/@me/channels", {"recipient_id": str(uid)})
    if "id" not in ch: return False
    payload = {}
    if content: payload["content"] = content
    if embeds:  payload["embeds"]  = embeds
    res = discord_request("POST", f"/channels/{ch['id']}/messages", payload)
    return "id" in res

def get_option(options, name):
    for o in (options or []):
        if o["name"] == name: return o.get("value")
    return None

def get_user(interaction):
    return interaction.get("member", {}).get("user") or interaction.get("user", {})

# ── Response helpers ───────────────────────────────────────────
def msg(content=None, embeds=None, ephemeral=False):
    data = {}
    if content:   data["content"] = content
    if embeds:    data["embeds"]  = embeds
    if ephemeral: data["flags"]   = 64
    return {"type": 4, "data": data}

def fmt_time(seconds):
    m, s = int(seconds // 60), int(seconds % 60)
    if m and s: return f"{m}m {s}s"
    if m: return f"{m} minute{'s' if m!=1 else ''}"
    return f"{s}s"

# ── Embed builders ─────────────────────────────────────────────
def gen_dm_embed(account, remaining, cooldown_str, today_remaining, emojis, user):
    avatar = f"https://cdn.discordapp.com/avatars/{user['id']}/{user.get('avatar','')}.png"
    return {
        "title":  f"{emojis['account']}  Rainbow Six Siege Account",
        "color":  0xDC143C,
        "thumbnail": {"url": avatar},
        "fields": [
            {"name": f"{emojis['details']}  Account Details",
             "value": f"```\n{account}\n```", "inline": False},
            {"name": f"{emojis['stock']}  Accounts Remaining",
             "value": f"**{remaining}** still in stock", "inline": True},
            {"name": f"{emojis['cooldown']}  Your Cooldown",
             "value": f"Next generate available in **{cooldown_str}**", "inline": True},
            {"name": "📅  Today's Remaining",
             "value": f"**{today_remaining}** of {DAILY_LIMIT} accounts left today", "inline": True},
        ],
        "footer": {"text": "Keep this account safe — do not share it.", "icon_url": avatar},
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }

def gen_channel_embed(user, remaining, emojis):
    avatar = f"https://cdn.discordapp.com/avatars/{user['id']}/{user.get('avatar','')}.png"
    return {
        "title":     "✨ Premium Account Generated",
        "color":     0x00FF88,
        "thumbnail": {"url": avatar},
        "fields": [
            {"name": "User",   "value": f"<@{user['id']}>",  "inline": True},
            {"name": "Type",   "value": "Premium Account",    "inline": True},
            {"name": "Status", "value": "✅ Check your DMs!", "inline": True},
            {"name": f"{emojis['stock']} Remaining",
             "value": f"**{remaining}** still in stock",      "inline": True},
        ],
        "footer":    {"text": "R6 Generator"},
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }

def stock_embed(count):
    return {
        "title":       "📦 Account Stock Update",
        "description": f"Current account inventory: **{count}** accounts remaining.",
        "color":       0x5865F2,
        "footer":      {"text": time.strftime("Last updated • %Y-%m-%d %H:%M UTC", time.gmtime())}
    }

# ══════════════════════════════════════════════════════════════
#  COMMAND HANDLERS
# ══════════════════════════════════════════════════════════════

def cmd_addowner(interaction):
    uid  = int(get_user(interaction)["id"])
    if not is_main_owner(uid):
        return msg("Only the main owner can manage co-owners.", ephemeral=True)
    opts     = interaction["data"].get("options", [])
    target   = int(get_option(opts, "user"))
    if target == OWNER_ID:
        return msg("That user is already the main owner.", ephemeral=True)
    owners = get_co_owners()
    if target in owners:
        return msg(f"<@{target}> is already an owner.", ephemeral=True)
    owners.append(target); save_co_owners(owners)
    log_to_channel(f"📋 /addowner — granted owner to <@{target}>")
    return msg(f"Owner access granted to <@{target}>.", ephemeral=True)

def cmd_removeowner(interaction):
    uid  = int(get_user(interaction)["id"])
    if not is_main_owner(uid):
        return msg("Only the main owner can manage co-owners.", ephemeral=True)
    opts   = interaction["data"].get("options", [])
    target = int(get_option(opts, "user"))
    owners = get_co_owners()
    if target not in owners:
        return msg(f"<@{target}> is not a co-owner.", ephemeral=True)
    owners.remove(target); save_co_owners(owners)
    log_to_channel(f"📋 /removeowner — revoked owner from <@{target}>")
    return msg(f"Owner access revoked from <@{target}>.", ephemeral=True)

def cmd_listowners(interaction):
    uid = int(get_user(interaction)["id"])
    if not is_owner(uid):
        return msg("You do not have permission.", ephemeral=True)
    owners = get_co_owners()
    if not owners:
        return msg(f"No co-owners set. Only the main owner (<@{OWNER_ID}>) has access.", ephemeral=True)
    lines = "\n".join(f"<@{i}>" for i in owners)
    return msg(f"**Co-owners ({len(owners)}):**\n{lines}", ephemeral=True)

def cmd_addaccount(interaction):
    uid = int(get_user(interaction)["id"])
    if not is_owner(uid):
        return msg("You do not have permission.", ephemeral=True)
    opts    = interaction["data"].get("options", [])
    account = get_option(opts, "account")
    accounts = get_accounts(); accounts.append(account); save_accounts(accounts)
    log_to_channel(f"📋 /addaccount — pool size now {len(accounts)}")
    return msg(f"Account added. Pool size: **{len(accounts)}**.", ephemeral=True)

def cmd_addpremium(interaction):
    uid = int(get_user(interaction)["id"])
    if not is_owner(uid):
        return msg("You do not have permission.", ephemeral=True)
    opts    = interaction["data"].get("options", [])
    target  = int(get_option(opts, "user"))
    premium = get_premium()
    if target in premium:
        return msg(f"<@{target}> already has premium.", ephemeral=True)
    premium.append(target); save_premium(premium)
    log_to_channel(f"📋 /addpremium — granted premium to <@{target}>")
    return msg(f"Premium granted to <@{target}>.", ephemeral=True)

def cmd_removepremium(interaction):
    uid = int(get_user(interaction)["id"])
    if not is_owner(uid):
        return msg("You do not have permission.", ephemeral=True)
    opts    = interaction["data"].get("options", [])
    target  = int(get_option(opts, "user"))
    premium = get_premium()
    if target not in premium:
        return msg(f"<@{target}> does not have premium.", ephemeral=True)
    premium.remove(target); save_premium(premium)
    log_to_channel(f"📋 /removepremium — revoked premium from <@{target}>")
    return msg(f"Premium revoked from <@{target}>.", ephemeral=True)

def cmd_accountcount(interaction):
    uid = int(get_user(interaction)["id"])
    if not is_owner(uid):
        return msg("You do not have permission.", ephemeral=True)
    n = len(get_accounts())
    log_to_channel(f"📋 /accountcount — pool size: {n}")
    return msg(f"There are **{n}** account(s) in the pool.", ephemeral=True)

def cmd_listaccounts(interaction):
    uid  = int(get_user(interaction)["id"])
    if not is_owner(uid):
        return msg("You do not have permission.", ephemeral=True)
    accounts = get_accounts()
    if not accounts:
        return msg("The account pool is empty.", ephemeral=True)
    lines = "\n".join(
        f"{i+1}. {a[:60]}{'...' if len(a)>60 else ''}"
        for i, a in enumerate(accounts)
    )
    preview = f"**Account Pool ({len(accounts)} total):**\n{lines}"
    ok = send_dm(uid, content=preview)
    if not ok:
        return msg("I couldn't DM you. Please enable DMs from server members.", ephemeral=True)
    log_to_channel(f"📋 /listaccounts — viewed {len(accounts)} accounts")
    return msg("Account list sent to your DMs.", ephemeral=True)

def cmd_setemoji(interaction):
    uid = int(get_user(interaction)["id"])
    if not is_owner(uid):
        return msg("You do not have permission.", ephemeral=True)
    opts       = interaction["data"].get("options", [])
    emoji_type = get_option(opts, "emoji_type")
    emoji      = get_option(opts, "emoji")
    emojis     = get_emojis()
    emojis[emoji_type] = emoji
    save_emojis(emojis)
    log_to_channel(f"📋 /setemoji — set '{emoji_type}' to {emoji}")
    return msg(f"Emoji for **{emoji_type}** set to {emoji}", ephemeral=True)

def cmd_sendstock(interaction):
    uid = int(get_user(interaction)["id"])
    if not is_owner(uid):
        return msg("You are not authorized.", ephemeral=True)
    opts       = interaction["data"].get("options", [])
    channel_id = get_option(opts, "channel")
    count      = len(get_accounts())
    res = discord_request("POST", f"/channels/{channel_id}/messages",
                          {"embeds": [stock_embed(count)]})
    if "error" in res:
        return msg(f"Failed to send: {res['error']}", ephemeral=True)
    log_to_channel(f"📋 /sendstock — sent to <#{channel_id}>")
    return msg(f"Stock update sent to <#{channel_id}>.", ephemeral=True)

def cmd_botstatus(interaction):
    uid = int(get_user(interaction)["id"])
    if not is_owner(uid):
        return msg("You do not have permission.", ephemeral=True)
    opts   = interaction["data"].get("options", [])
    action = get_option(opts, "action")
    if action == "enable":
        set_bot_enabled(True)
        log_to_channel("📋 /botstatus — bot ENABLED")
        return msg("✅ Bot has been **enabled**.", ephemeral=True)
    else:
        set_bot_enabled(False)
        log_to_channel("📋 /botstatus — bot DISABLED")
        return msg("🔴 Bot has been **disabled** (maintenance mode).", ephemeral=True)

def cmd_generate(interaction):
    user   = get_user(interaction)
    uid    = int(user["id"])
    emojis = get_emojis()

    if not get_bot_enabled():
        return msg("The bot is currently **offline** for maintenance. Please check back later.", ephemeral=True)

    if not is_owner(uid) and uid not in get_premium():
        log_to_channel(f"📋 /generate — {user.get('username','?')} ({uid}) ❌ no premium")
        return msg(
            f"{emojis['error']} You do not have premium access. Please open a ticket to purchase premium.",
            ephemeral=True
        )

    # Cooldown check
    if not is_owner(uid):
        cd_ts = get_cooldown(uid)
        if cd_ts is not None:
            left = cd_ts - time.time()
            if left > 0:
                log_to_channel(f"📋 /generate — {user.get('username','?')} ({uid}) ❌ cooldown {fmt_time(left)}")
                return msg(
                    f"{emojis['cooldown']} You are on cooldown. Please wait **{fmt_time(left)}** before generating again.",
                    ephemeral=True
                )

    # Daily limit check
    if not is_owner(uid):
        count = get_daily_count(uid)
        if count >= DAILY_LIMIT:
            log_to_channel(f"📋 /generate — {user.get('username','?')} ({uid}) ❌ daily limit")
            return msg(
                f"{emojis['error']} You have reached your daily limit of **{DAILY_LIMIT}** accounts. Come back tomorrow!",
                ephemeral=True
            )

    accounts = get_accounts()
    if not accounts:
        log_to_channel(f"📋 /generate — {user.get('username','?')} ({uid}) ❌ pool empty")
        return msg(f"{emojis['error']} Sorry, no accounts are available at the moment.", ephemeral=True)

    # Pick and remove account
    account = random.choice(accounts)
    accounts.remove(account)
    save_accounts(accounts)

    # Set cooldown + increment daily (non-owners)
    cooldown_str = fmt_time(COOLDOWN_SEC)
    if not is_owner(uid):
        set_cooldown(uid)
        new_count    = increment_daily(uid)
        today_remain = DAILY_LIMIT - new_count
    else:
        today_remain = "∞"

    remaining = len(accounts)

    # Send DM
    dm_ok = send_dm(uid, embeds=[gen_dm_embed(account, remaining, cooldown_str, today_remain, emojis, user)])
    if not dm_ok:
        # Roll back
        accounts.append(account); save_accounts(accounts)
        if not is_owner(uid):
            clear_cooldown(uid)
            decrement_daily(uid)
        log_to_channel(f"📋 /generate — {user.get('username','?')} ({uid}) ❌ DMs closed")
        return msg(
            f"{emojis['error']} I couldn't DM you. Please enable DMs from server members and try again.",
            ephemeral=True
        )

    log_to_channel(f"📋 /generate — {user.get('username','?')} ({uid}) ✅ account sent — {remaining} remaining")
    return msg(embeds=[gen_channel_embed(user, remaining, emojis)])


# ── Router ─────────────────────────────────────────────────────
COMMANDS = {
    "addowner":      cmd_addowner,
    "removeowner":   cmd_removeowner,
    "listowners":    cmd_listowners,
    "addaccount":    cmd_addaccount,
    "addpremium":    cmd_addpremium,
    "removepremium": cmd_removepremium,
    "accountcount":  cmd_accountcount,
    "listaccounts":  cmd_listaccounts,
    "setemoji":      cmd_setemoji,
    "sendstock":     cmd_sendstock,
    "botstatus":     cmd_botstatus,
    "generate":      cmd_generate,
}

# ── Vercel handler ─────────────────────────────────────────────
class handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"R6 Bot online!")

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body   = self.rfile.read(length)
        ts     = self.headers.get("X-Signature-Timestamp", "")
        sig    = self.headers.get("X-Signature-Ed25519", "")

        if not verify_sig(body, ts, sig):
            self.send_response(401); self.end_headers()
            self.wfile.write(b"Invalid signature"); return

        data = json.loads(body)

        if data.get("type") == 1:
            resp = {"type": 1}
        elif data.get("type") == 2:
            fn   = COMMANDS.get(data["data"]["name"])
            resp = fn(data) if fn else msg("Unknown command.")
        else:
            resp = {"type": 1}

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(resp).encode())
