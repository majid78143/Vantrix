"""
Vantrix - central configuration.
All values come from environment variables / Replit Secrets.
Never hardcode tokens or credentials here.
"""
import os

from dotenv import load_dotenv

load_dotenv()

# --- Discord ---
DISCORD_BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")
DISCORD_CLIENT_ID = os.environ.get("DISCORD_CLIENT_ID", "")
DISCORD_CLIENT_SECRET = os.environ.get("DISCORD_CLIENT_SECRET", "")
DISCORD_REDIRECT_URI = os.environ.get("DISCORD_REDIRECT_URI", "http://localhost:5000/callback")
OWNER_IDS = [x.strip() for x in os.environ.get("OWNER_ID", "").split(",") if x.strip()]

# --- Database ---
MONGO_URI = os.environ.get("MONGO_URI", "")
MONGO_DB_NAME = os.environ.get("MONGO_DB_NAME", "codeforge_market")

# --- Web ---
SESSION_SECRET = os.environ.get("SESSION_SECRET", "dev-secret-change-me")
PORT = int(os.environ.get("PORT", "5000"))

# --- Bot branding ---
BOT_NAME = "Vantrix"
BOT_PREFIX = "!"

DISCORD_API_BASE = "https://discord.com/api/v10"
DISCORD_OAUTH_SCOPE = "identify guilds"
