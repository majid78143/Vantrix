"""
Vantrix - single entry point.
Runs the Discord bot and the Flask website TOGETHER in one Python process,
so both can be deployed as ONE service (one Render web service, one PORT).

The website reads live guild/channel/role data straight from the bot's
in-memory cache (no separate internal API needed) because they share memory.
"""
import threading

import config
import website
from bot import bot, run_bot


def start_website():
    website.attach_bot(bot)
    website.app.run(host="0.0.0.0", port=config.PORT, use_reloader=False)


if __name__ == "__main__":
    web_thread = threading.Thread(target=start_website, daemon=True)
    web_thread.start()
    print(f"[Vantrix] Website starting on port {config.PORT}")
    if config.DISCORD_BOT_TOKEN:
        run_bot()
    else:
        print("[Vantrix] DISCORD_BOT_TOKEN missing — bot will not start. Website keeps running.")
        web_thread.join()
