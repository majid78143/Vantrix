"""
Vantrix - MongoDB access layer.
Single shared client used by both the bot and the website (same process).
"""
from datetime import datetime, timezone

from pymongo import MongoClient

import config

_client = MongoClient(config.MONGO_URI) if config.MONGO_URI else None
_db = _client[config.MONGO_DB_NAME] if _client is not None else None

settings_col = _db["settings"] if _db is not None else None
xp_col = _db["xp"] if _db is not None else None
warnings_col = _db["warnings"] if _db is not None else None
tickets_col = _db["tickets"] if _db is not None else None
reaction_roles_col = _db["reaction_roles"] if _db is not None else None
developers_col = _db["developers"] if _db is not None else None
polls_col = _db["polls"] if _db is not None else None
giveaways_col = _db["giveaways"] if _db is not None else None

DEFAULT_MODULES = {
    "moderation": True,
    "anti_nuke": True,
    "leveling": True,
    "welcome": True,
    "tickets": True,
    "reaction_roles": True,
    "auto_responder": True,
}


def get_settings(guild_id: int) -> dict:
    doc = settings_col.find_one({"guild_id": guild_id})
    if doc:
        return doc
    doc = {
        "guild_id": guild_id,
        "prefix": config.BOT_PREFIX,
        "modules": dict(DEFAULT_MODULES),
        "welcome_channel_id": None,
        "goodbye_channel_id": None,
        "welcome_message": "Welcome {user} to {server}! 🎉",
        "goodbye_message": "{user} left the server. 👋",
        "mod_log_channel_id": None,
        "showcase_opt_in": False,
        "auto_responses": {},
    }
    settings_col.insert_one(doc)
    return doc


def update_settings(guild_id: int, updates: dict) -> None:
    settings_col.update_one({"guild_id": guild_id}, {"$set": updates}, upsert=True)


def add_xp(guild_id: int, user_id: int, amount: int) -> dict:
    doc = xp_col.find_one_and_update(
        {"guild_id": guild_id, "user_id": user_id},
        {"$inc": {"xp": amount}, "$setOnInsert": {"level": 1}},
        upsert=True,
        return_document=True,
    )
    xp_needed = doc["level"] * 100
    leveled_up = False
    while doc["xp"] >= xp_needed:
        doc = xp_col.find_one_and_update(
            {"guild_id": guild_id, "user_id": user_id},
            {"$inc": {"level": 1}},
            return_document=True,
        )
        xp_needed = doc["level"] * 100
        leveled_up = True
    doc["leveled_up"] = leveled_up
    return doc


def get_leaderboard(guild_id: int, limit: int = 10) -> list:
    return list(xp_col.find({"guild_id": guild_id}).sort("xp", -1).limit(limit))


def add_warning(guild_id: int, user_id: int, moderator_id: int, reason: str) -> None:
    warnings_col.insert_one({
        "guild_id": guild_id,
        "user_id": user_id,
        "moderator_id": moderator_id,
        "reason": reason,
        "timestamp": datetime.now(timezone.utc),
    })


def get_warnings(guild_id: int, user_id: int) -> list:
    return list(warnings_col.find({"guild_id": guild_id, "user_id": user_id}))


def create_ticket(guild_id: int, channel_id: int, user_id: int) -> None:
    tickets_col.insert_one({
        "guild_id": guild_id,
        "channel_id": channel_id,
        "user_id": user_id,
        "status": "open",
        "created_at": datetime.now(timezone.utc),
    })


def close_ticket(channel_id: int) -> None:
    tickets_col.update_one({"channel_id": channel_id}, {"$set": {"status": "closed"}})


def add_reaction_role(guild_id: int, message_id: int, emoji: str, role_id: int) -> None:
    reaction_roles_col.update_one(
        {"guild_id": guild_id, "message_id": message_id, "emoji": emoji},
        {"$set": {"role_id": role_id}},
        upsert=True,
    )


def get_reaction_role(guild_id: int, message_id: int, emoji: str):
    return reaction_roles_col.find_one({"guild_id": guild_id, "message_id": message_id, "emoji": emoji})


def get_developer(discord_id: str) -> dict:
    return developers_col.find_one({"discord_id": str(discord_id)}) or {}


def get_all_showcase_guild_ids() -> list:
    return [d["guild_id"] for d in settings_col.find({"showcase_opt_in": True})]
