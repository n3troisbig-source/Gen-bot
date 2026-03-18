# 🎯 R6 Account Generator Bot

A full Discord bot + management dashboard for generating Rainbow Six Siege accounts.

---

## 📁 Structure

```
r6-bot/
├── bot/           ← Discord bot (Node.js + discord.js)
│   ├── index.js
│   ├── package.json
│   └── .env.example
├── web/           ← Management dashboard
│   ├── server.js
│   ├── package.json
│   └── public/
│       └── index.html
├── vercel.json    ← Vercel deploy config
├── Procfile       ← Railway deploy config
└── README.md
```

---

## ⚡ Quick Setup

### 1. Create your Discord Bot
1. Go to https://discord.com/developers/applications
2. New Application → Bot → Reset Token → copy it
3. Enable: **Server Members Intent**, **Message Content Intent**
4. OAuth2 → URL Generator → `bot` + `applications.commands` scopes
5. Bot permissions: Send Messages, Embed Links, Use Slash Commands
6. Invite bot to your server

### 2. Install & Run Locally

```bash
# Install bot dependencies
cd bot
npm install
cp .env.example .env
# → Paste your token into .env

node index.js
```

```bash
# Install & run dashboard
cd web
npm install
node server.js
# → Open http://localhost:3000
# → Password: lightwork
```

---

## 🚀 Deploy Bot on Railway (Free 24/7 hosting)

1. Push this repo to GitHub
2. Go to https://railway.app → New Project → Deploy from GitHub
3. Select your repo
4. Add environment variable: `DISCORD_TOKEN` = your token
5. In the "Start Command" field, set: `node bot/index.js`
6. Deploy!

---

## 🌐 Deploy Dashboard on Vercel

1. Push repo to GitHub (same repo)
2. Go to https://vercel.com → New Project → Import from GitHub
3. Set Root Directory to `web`
4. Framework: Other
5. Build command: (leave empty)
6. Output directory: `public`
7. Deploy!

---

## 🎮 Bot Commands

| Command | Who | Description |
|---------|-----|-------------|
| `/gen` | Premium Users | Generate an account → sent to DMs |
| `/addaccount` | Owner only | Add a single account |
| `/addaccounts` | Owner only | Bulk add accounts (newline-separated) |
| `/addpremium @user` | Owner only | Grant premium to a user |
| `/removepremium @user` | Owner only | Remove premium from a user |
| `/premiumlist` | Owner only | View all premium users |
| `/stock` | Everyone | Check how many accounts are in stock |

---

## 📋 Account Format

```
email:password | Verified Email/Phone: No/No | 2FA: Yes | Banned: No | Username: TechnoTobi | Level: 70 | Platforms: [XBL & PSN Linkable] | Credits: 677 | Renown: 49044 | Items: 44 | Found Ranks: [Platinum (Void Edge)]
```

---

## 🔐 Dashboard Password

Default password: **lightwork**

---

## 👑 Owner ID

Your Discord ID is hardcoded: `1455187536623304734`

Only you can use owner-only commands.
