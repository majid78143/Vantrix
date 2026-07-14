# Vantrix

Discord bot + companion website, running together as **one Python process**
so they can be hosted as a single Render web service.

## Structure (flat by design)

```
vantrix/
  main.py        entry point — starts bot + website together
  bot.py         discord.py bot (moderation, anti-nuke, XP, tickets, reaction roles...)
  website.py     Flask website + dashboard + embed builder API
  db.py          MongoDB access layer
  config.py      env var loading
  templates/     Flask HTML templates
  static/        CSS/JS
  requirements.txt
  .env.example
```

## Local run

1. `pip install -r requirements.txt`
2. Copy `.env.example` to `.env` and fill in the values.
3. `python main.py`

## Deploying on Render (single service)

1. Push this folder to a GitHub repo.
2. Render → New → Web Service → connect the repo.
3. Build command: `pip install -r requirements.txt`
4. Start command: `python main.py`
5. Add environment variables from `.env.example` in Render's dashboard (never commit real secrets).
6. Render assigns `PORT` automatically — `main.py` already reads it.

## Discord Developer Portal setup

1. Create an application at https://discord.com/developers/applications
2. Bot tab → copy the token → `DISCORD_BOT_TOKEN`
3. OAuth2 tab → copy Client ID / Secret → `DISCORD_CLIENT_ID` / `DISCORD_CLIENT_SECRET`
4. OAuth2 → Redirects → add `https://your-app.onrender.com/callback` → same value as `DISCORD_REDIRECT_URI`
5. Bot tab → enable **Server Members Intent** and **Message Content Intent**
