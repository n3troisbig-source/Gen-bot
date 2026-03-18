# R6 Generator Bot — Railway Deploy

## Setup on Railway

1. **Upload this folder** to a new GitHub repo (all files at root, not in a subfolder)
2. Go to https://railway.app → New Project → Deploy from GitHub repo
3. In your Railway service → **Variables** tab → Add:
   ```
   DISCORD_TOKEN = your_bot_token_here
   ```
4. Railway will auto-detect Node.js and run `node index.js`

## File Structure (must be at ROOT of repo)
```
index.js        ← bot entry point
package.json    ← dependencies
railway.toml    ← Railway config
Procfile        ← start command
.env.example    ← token template
data/           ← auto-created at runtime
```

## Commands
- `/gen` — Generate account (premium users only)
- `/addaccount` — Add one account (owner only)
- `/addaccounts` — Bulk add accounts (owner only)
- `/addpremium @user` — Grant premium (owner only)
- `/removepremium @user` — Remove premium (owner only)
- `/premiumlist` — List premium users (owner only)
- `/stock` — Check stock (everyone)
