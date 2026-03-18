# R6 Generator Bot — Vercel Deploy (Python)

## File Structure (upload ALL files to GitHub root)
```
api/
└── index.py          ← Discord interactions handler (Python)
register_commands.py  ← Run ONCE locally to register slash commands
requirements.txt      ← PyNaCl dependency
vercel.json           ← Vercel routing config
README.md
```

---

## Step 1 — Discord Developer Portal Setup
1. Go to https://discord.com/developers/applications
2. Open your app → **General Information** → copy **Public Key**
3. **Bot** tab → copy/reset **Token**
4. Copy your **Application ID** (shown on General Information page)
5. Enable **Server Members Intent** and **Message Content Intent**
6. OAuth2 → URL Generator → scopes: `bot` + `applications.commands`
7. Bot permissions: Send Messages, Embed Links, Use Slash Commands, Read Messages
8. Invite bot to your server

---

## Step 2 — Push to GitHub
Upload these files to your GitHub repo **at the root level** (not in a subfolder):
- `api/index.py`
- `requirements.txt`
- `vercel.json`
- `register_commands.py`

---

## Step 3 — Vercel KV Setup (for data storage)
1. Go to https://vercel.com/dashboard → **Storage** tab
2. Create a new **KV** database (free tier)
3. After creation, go to the KV database → **.env.local** tab
4. Copy the values for:
   - `KV_REST_API_URL`
   - `KV_REST_API_TOKEN`

---

## Step 4 — Deploy on Vercel
1. Go to https://vercel.com → New Project → Import GitHub repo
2. Framework Preset: **Other**
3. Click **Environment Variables** and add:
   ```
   DISCORD_TOKEN       = your_bot_token
   DISCORD_PUBLIC_KEY  = your_public_key_from_dev_portal
   KV_REST_API_URL     = from_vercel_kv
   KV_REST_API_TOKEN   = from_vercel_kv
   ```
4. Deploy!
5. Copy your Vercel URL (e.g. `https://your-project.vercel.app`)

---

## Step 5 — Set Interactions Endpoint in Discord
1. Discord Developer Portal → your app → **General Information**
2. Set **Interactions Endpoint URL** to:
   ```
   https://your-project.vercel.app/api/index
   ```
3. Click Save — Discord will verify it (it sends a PING, bot responds)

---

## Step 6 — Register Slash Commands (run once locally)
```bash
# Install PyNaCl locally
pip install PyNaCl

# Set env vars
export DISCORD_TOKEN=your_bot_token
export DISCORD_APP_ID=your_application_id

# Register commands
python register_commands.py
```

---

## Commands
| Command | Who | Description |
|---------|-----|-------------|
| `/gen` | Premium users | Generates an account → sends to DMs |
| `/addaccount` | Owner only | Add a single account |
| `/addaccounts` | Owner only | Bulk add (newline-separated) |
| `/addpremium` | Owner only | Grant premium (enter user ID) |
| `/removepremium` | Owner only | Remove premium |
| `/premiumlist` | Owner only | View all premium users |
| `/stock` | Everyone | Check how many accounts in stock |

---

## Account Format
```
email:password | Verified Email/Phone: No/No | 2FA: Yes | Banned: No | Username: TechnoTobi | Level: 70 | Platforms: [XBL & PSN Linkable] | Credits: 677 | Renown: 49044 | Items: 44 | Found Ranks: [Platinum (Void Edge)]
```
