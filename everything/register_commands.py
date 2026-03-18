"""
Run ONCE locally after deploying to Vercel.
  export DISCORD_TOKEN=your_token
  export DISCORD_APP_ID=your_app_id
  python register_commands.py
"""
import urllib.request, json, os, sys

TOKEN  = os.environ.get("DISCORD_TOKEN", "")
APP_ID = os.environ.get("DISCORD_APP_ID", "")

if not TOKEN or not APP_ID:
    print("❌ Set DISCORD_TOKEN and DISCORD_APP_ID first.")
    sys.exit(1)

STR  = 3   # string option type
USER = 6   # user option type
CH   = 7   # channel option type

commands = [
    # ── Co-owner management ──────────────────────────────────
    {"name": "addowner",    "description": "[Main Owner] Grant owner access to a user.",
     "options": [{"name":"user","description":"User to make owner","type":USER,"required":True}]},
    {"name": "removeowner", "description": "[Main Owner] Revoke owner access from a user.",
     "options": [{"name":"user","description":"User to remove","type":USER,"required":True}]},
    {"name": "listowners",  "description": "[Owner] List all current co-owners."},

    # ── Account management ───────────────────────────────────
    {"name": "addaccount",  "description": "[Owner] Add an account to the pool.",
     "options": [{"name":"account","description":"Paste the full account info","type":STR,"required":True}]},
    {"name": "accountcount","description": "[Owner] Show number of accounts in pool."},
    {"name": "listaccounts","description": "[Owner] DM yourself a preview of stored accounts."},

    # ── Premium management ───────────────────────────────────
    {"name": "addpremium",    "description": "[Owner] Grant premium access to a user.",
     "options": [{"name":"user","description":"User to grant premium","type":USER,"required":True}]},
    {"name": "removepremium", "description": "[Owner] Revoke premium access from a user.",
     "options": [{"name":"user","description":"User to revoke","type":USER,"required":True}]},

    # ── Bot controls ─────────────────────────────────────────
    {"name": "botstatus",   "description": "[Owner] Enable or disable the bot.",
     "options": [{"name":"action","description":"enable or disable","type":STR,"required":True,
                  "choices":[{"name":"enable","value":"enable"},{"name":"disable","value":"disable"}]}]},

    # ── Emoji customization ──────────────────────────────────
    {"name": "setemoji",    "description": "[Owner] Customize emojis used in bot responses.",
     "options": [
         {"name":"emoji_type","description":"Which emoji to change","type":STR,"required":True,
          "choices":[{"name":"success","value":"success"},{"name":"error","value":"error"},
                     {"name":"account","value":"account"},{"name":"details","value":"details"},
                     {"name":"stock","value":"stock"},{"name":"cooldown","value":"cooldown"}]},
         {"name":"emoji","description":"The new emoji","type":STR,"required":True}
     ]},

    # ── Stock announcement ───────────────────────────────────
    {"name": "sendstock",   "description": "[Owner] Send stock announcement to a channel.",
     "options": [{"name":"channel","description":"Channel to send to","type":CH,"required":True,
                  "channel_types":[0]}]},

    # ── Generation ───────────────────────────────────────────
    {"name": "generate",    "description": "Generate a Rainbow Six Siege account (premium only)."},
]

url  = f"https://discord.com/api/v10/applications/{APP_ID}/commands"
data = json.dumps(commands).encode()
req  = urllib.request.Request(
    url, data=data,
    headers={"Authorization": f"Bot {TOKEN}", "Content-Type": "application/json"},
    method="PUT"
)

try:
    with urllib.request.urlopen(req) as r:
        result = json.loads(r.read())
        print(f"✅ Registered {len(result)} commands:")
        for c in result: print(f"   /{c['name']}")
except urllib.error.HTTPError as e:
    print(f"❌ Error {e.code}: {e.read().decode()}")
