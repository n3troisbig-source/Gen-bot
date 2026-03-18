from http.server import BaseHTTPRequestHandler
import json
import os
import time
import urllib.request
import urllib.error
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError

# ── Config ────────────────────────────────────────────────────
OWNER_ID   = "1455187536623304734"
PUBLIC_KEY = os.environ.get("DISCORD_PUBLIC_KEY", "")
BOT_TOKEN  = os.environ.get("DISCORD_TOKEN", "")
DISCORD_API = "https://discord.com/api/v10"

# ── Vercel KV Store ───────────────────────────────────────────
KV_URL   = os.environ.get("KV_REST_API_URL", "")
KV_TOKEN = os.environ.get("KV_REST_API_TOKEN", "")

def kv_get(key):
    if not KV_URL:
        return None
    try:
        req = urllib.request.Request(
            f"{KV_URL}/get/{key}",
            headers={"Authorization": f"Bearer {KV_TOKEN}"}
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            return json.loads(r.read()).get("result")
    except:
        return None

def kv_set(key, value):
    if not KV_URL:
        return
    try:
        req = urllib.request.Request(
            f"{KV_URL}/set/{key}",
            data=json.dumps(value).encode(),
            headers={
                "Authorization": f"Bearer {KV_TOKEN}",
                "Content-Type": "application/json"
            },
            method="POST"
        )
        urllib.request.urlopen(req, timeout=5)
    except:
        pass

def get_accounts():
    raw = kv_get("r6_accounts")
    if raw is None:
        return []
    try:
        return json.loads(raw) if isinstance(raw, str) else raw
    except:
        return []

def save_accounts(accounts):
    kv_set("r6_accounts", json.dumps(accounts))

def get_premium():
    raw = kv_get("r6_premium")
    if raw is None:
        return []
    try:
        return json.loads(raw) if isinstance(raw, str) else raw
    except:
        return []

def save_premium(premium):
    kv_set("r6_premium", json.dumps(premium))

# ── Signature verification (Ed25519 via PyNaCl) ───────────────
def verify_signature(body: bytes, timestamp: str, signature: str) -> bool:
    try:
        vk = VerifyKey(bytes.fromhex(PUBLIC_KEY))
        vk.verify(timestamp.encode() + body, bytes.fromhex(signature))
        return True
    except (BadSignatureError, Exception):
        return False

# ── Discord API helpers ────────────────────────────────────────
def discord_request(method, endpoint, payload=None):
    url  = f"{DISCORD_API}{endpoint}"
    data = json.dumps(payload).encode() if payload else None
    req  = urllib.request.Request(
        url, data=data,
        headers={
            "Authorization": f"Bot {BOT_TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "R6Bot/1.0"
        },
        method=method
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"error": e.read().decode()}
    except Exception as ex:
        return {"error": str(ex)}

def send_dm(user_id, embed):
    channel = discord_request("POST", "/users/@me/channels", {"recipient_id": user_id})
    if "id" not in channel:
        return False
    result = discord_request("POST", f"/channels/{channel['id']}/messages", {"embeds": [embed]})
    return "id" in result

# ── Account parser ─────────────────────────────────────────────
def parse_account(line):
    parts = [p.strip() for p in line.split("|")]
    creds = parts[0].split(":", 1)
    obj = {
        "raw":      line,
        "email":    creds[0].strip() if len(creds) > 0 else "",
        "password": creds[1].strip() if len(creds) > 1 else ""
    }
    for part in parts[1:]:
        low = part.lower()
        val = ":".join(part.split(":")[1:]).strip()
        if low.startswith("verified"):    obj["verified"]  = val
        elif low.startswith("2fa"):       obj["twofa"]     = val
        elif low.startswith("banned"):    obj["banned"]    = val
        elif low.startswith("username"):  obj["username"]  = val
        elif low.startswith("level"):     obj["level"]     = val
        elif low.startswith("platform"):  obj["platforms"] = val
        elif low.startswith("credits"):   obj["credits"]   = val
        elif low.startswith("renown"):    obj["renown"]    = val
        elif low.startswith("items"):     obj["items"]     = val
        elif "rank" in low:               obj["ranks"]     = val
    return obj

# ── Embed builders ─────────────────────────────────────────────
def build_dm_embed(acc, remaining, user):
    fields = [
        {"name": "📧 Account Details",
         "value": f"**Account:** __{acc['email']}:{acc['password']}__",
         "inline": False}
    ]
    if acc.get("verified"):  fields.append({"name": "✅ Verified Email/Phone", "value": acc["verified"],  "inline": True})
    if acc.get("twofa"):     fields.append({"name": "🔐 2FA",                  "value": acc["twofa"],     "inline": True})
    if acc.get("banned"):    fields.append({"name": "🚫 Banned",               "value": acc["banned"],    "inline": True})
    if acc.get("username"):  fields.append({"name": "👤 Username",             "value": acc["username"],  "inline": True})
    if acc.get("level"):     fields.append({"name": "🎮 Level",                "value": acc["level"],     "inline": True})
    if acc.get("platforms"): fields.append({"name": "🕹️ Platforms",            "value": acc["platforms"], "inline": True})
    if acc.get("credits"):   fields.append({"name": "💰 Credits",              "value": acc["credits"],   "inline": True})
    if acc.get("renown"):    fields.append({"name": "🏅 Renown",               "value": acc["renown"],    "inline": True})
    if acc.get("items"):     fields.append({"name": "🎒 Items",                "value": acc["items"],     "inline": True})
    if acc.get("ranks"):     fields.append({"name": "🏆 Found Ranks",          "value": acc["ranks"],     "inline": False})
    fields += [
        {"name": "Type",                    "value": "Premium Account", "inline": True},
        {"name": "Remaining Premium Stock", "value": str(remaining),    "inline": True},
    ]
    avatar = f"https://cdn.discordapp.com/avatars/{user['id']}/{user.get('avatar','')}.png"
    return {
        "title":     "✨ Premium Account Generated",
        "color":     0xFFD700,
        "fields":    fields,
        "footer":    {"text": "R6 Generator • Keep this account safe!", "icon_url": avatar},
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }

def build_channel_embed(user, remaining):
    avatar = f"https://cdn.discordapp.com/avatars/{user['id']}/{user.get('avatar','')}.png"
    return {
        "title":     "✨ Premium Account Generated",
        "color":     0x00FF88,
        "thumbnail": {"url": avatar},
        "fields": [
            {"name": "User",              "value": f"<@{user['id']}>",  "inline": True},
            {"name": "Type",              "value": "Premium Account",   "inline": True},
            {"name": "Status",            "value": "✅ Check your DMs!", "inline": True},
            {"name": "Remaining Premium", "value": str(remaining),      "inline": True},
        ],
        "footer":    {"text": "R6 Generator"},
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }

def no_premium_embed(user):
    avatar = f"https://cdn.discordapp.com/avatars/{user['id']}/{user.get('avatar','')}.png"
    return {
        "title":       "❌ No Premium Access",
        "color":       0xFF1744,
        "description": "Please open a ticket to purchase premium.\nOnce premium has been purchased, you can generate an account.",
        "thumbnail":   {"url": avatar},
        "footer":      {"text": "R6 Generator"}
    }

# ── Response helpers ───────────────────────────────────────────
def msg(content=None, embeds=None, ephemeral=False):
    data = {}
    if content:   data["content"] = content
    if embeds:    data["embeds"]  = embeds
    if ephemeral: data["flags"]   = 64
    return {"type": 4, "data": data}

def get_user(interaction):
    return interaction["member"]["user"] if "member" in interaction else interaction["user"]

# ── Command handlers ───────────────────────────────────────────
def handle_addaccount(interaction):
    if get_user(interaction)["id"] != OWNER_ID:
        return msg("❌ Owner only.", ephemeral=True)
    line     = next(o["value"] for o in interaction["data"]["options"] if o["name"] == "account")
    accounts = get_accounts()
    accounts.append(parse_account(line))
    save_accounts(accounts)
    return msg(f"✅ Account added. Total: **{len(accounts)}**", ephemeral=True)

def handle_addaccounts(interaction):
    if get_user(interaction)["id"] != OWNER_ID:
        return msg("❌ Owner only.", ephemeral=True)
    raw      = next(o["value"] for o in interaction["data"]["options"] if o["name"] == "accounts")
    lines    = [l.strip() for l in raw.split("\n") if l.strip()]
    accounts = get_accounts()
    for line in lines:
        accounts.append(parse_account(line))
    save_accounts(accounts)
    return msg(f"✅ Added **{len(lines)}** accounts. Total: **{len(accounts)}**", ephemeral=True)

def handle_addpremium(interaction):
    if get_user(interaction)["id"] != OWNER_ID:
        return msg("❌ Owner only.", ephemeral=True)
    target_id = next(o["value"] for o in interaction["data"]["options"] if o["name"] == "user")
    premium   = get_premium()
    if target_id in premium:
        return msg(f"ℹ️ <@{target_id}> already has premium.", ephemeral=True)
    premium.append(target_id)
    save_premium(premium)
    return msg(f"✅ <@{target_id}> has been granted premium!", ephemeral=True)

def handle_removepremium(interaction):
    if get_user(interaction)["id"] != OWNER_ID:
        return msg("❌ Owner only.", ephemeral=True)
    target_id = next(o["value"] for o in interaction["data"]["options"] if o["name"] == "user")
    premium   = [i for i in get_premium() if i != target_id]
    save_premium(premium)
    return msg(f"✅ <@{target_id}>'s premium has been removed.", ephemeral=True)

def handle_premiumlist(interaction):
    if get_user(interaction)["id"] != OWNER_ID:
        return msg("❌ Owner only.", ephemeral=True)
    premium = get_premium()
    if not premium:
        return msg("No premium users.", ephemeral=True)
    lines = "\n".join(f"{i+1}. <@{uid}>" for i, uid in enumerate(premium))
    return msg(embeds=[{"title": "👑 Premium Users", "color": 0xFFD700,
                        "description": lines,
                        "footer": {"text": f"Total: {len(premium)}"}}], ephemeral=True)

def handle_stock(interaction):
    accounts = get_accounts()
    return msg(embeds=[{"title": "📦 Account Stock", "color": 0x00BFFF,
                        "fields": [{"name": "Premium Accounts", "value": str(len(accounts)), "inline": True}]}])

def handle_gen(interaction):
    user    = get_user(interaction)
    premium = get_premium()
    if user["id"] != OWNER_ID and user["id"] not in premium:
        return msg(embeds=[no_premium_embed(user)], ephemeral=True)

    accounts = get_accounts()
    if not accounts:
        return msg("❌ No accounts in stock right now. Check back soon!", ephemeral=True)

    acc       = accounts.pop(0)
    save_accounts(accounts)
    remaining = len(accounts)

    if not send_dm(user["id"], build_dm_embed(acc, remaining, user)):
        accounts.insert(0, acc)
        save_accounts(accounts)
        return msg("❌ Couldn't DM you! Please enable DMs from server members and try again.", ephemeral=True)

    return msg(embeds=[build_channel_embed(user, remaining)])

# ── Router ─────────────────────────────────────────────────────
COMMANDS = {
    "addaccount":    handle_addaccount,
    "addaccounts":   handle_addaccounts,
    "addpremium":    handle_addpremium,
    "removepremium": handle_removepremium,
    "premiumlist":   handle_premiumlist,
    "stock":         handle_stock,
    "gen":           handle_gen,
}

class handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"R6 Bot is alive!")

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body   = self.rfile.read(length)
        ts     = self.headers.get("X-Signature-Timestamp", "")
        sig    = self.headers.get("X-Signature-Ed25519", "")

        if not verify_signature(body, ts, sig):
            self.send_response(401)
            self.end_headers()
            self.wfile.write(b"Invalid signature")
            return

        interaction = json.loads(body)

        if interaction.get("type") == 1:
            response = {"type": 1}
        elif interaction.get("type") == 2:
            fn = COMMANDS.get(interaction["data"]["name"])
            response = fn(interaction) if fn else msg("Unknown command.")
        else:
            response = {"type": 1}

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode())
