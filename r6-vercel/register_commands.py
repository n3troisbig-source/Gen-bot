"""
Run this ONCE locally after deploying to Vercel to register slash commands.
Usage: python register_commands.py
Set DISCORD_TOKEN and DISCORD_APP_ID in your environment first.
"""
import urllib.request
import json
import os

TOKEN  = os.environ.get("DISCORD_TOKEN", "")
APP_ID = os.environ.get("DISCORD_APP_ID", "")

if not TOKEN or not APP_ID:
    print("❌ Set DISCORD_TOKEN and DISCORD_APP_ID environment variables first.")
    print("   export DISCORD_TOKEN=your_token")
    print("   export DISCORD_APP_ID=your_app_id")
    exit(1)

commands = [
    {
        "name": "addaccount",
        "description": "[Owner] Add a single account to the list",
        "options": [{"name": "account", "description": "email:pass | field | field ...", "type": 3, "required": True}]
    },
    {
        "name": "addaccounts",
        "description": "[Owner] Bulk add accounts (one per line)",
        "options": [{"name": "accounts", "description": "Paste multiple accounts separated by newlines", "type": 3, "required": True}]
    },
    {
        "name": "addpremium",
        "description": "[Owner] Grant premium to a user",
        "options": [{"name": "user", "description": "User ID to add", "type": 3, "required": True}]
    },
    {
        "name": "removepremium",
        "description": "[Owner] Remove premium from a user",
        "options": [{"name": "user", "description": "User ID to remove", "type": 3, "required": True}]
    },
    {
        "name": "gen",
        "description": "Generate a premium R6 account (premium only)"
    },
    {
        "name": "stock",
        "description": "Check current account stock"
    },
    {
        "name": "premiumlist",
        "description": "[Owner] View all premium users"
    }
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
        print(f"✅ Registered {len(result)} commands successfully!")
        for cmd in result:
            print(f"   /{cmd['name']}")
except urllib.error.HTTPError as e:
    print(f"❌ Error: {e.read().decode()}")
