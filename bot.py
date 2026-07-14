"""
Vantrix - Discord bot (discord.py).
Runs in the same process as the website (see main.py) so Flask routes can
read live guild/channel/role data straight from this bot's cache.
"""
import random
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands

import config
import db

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix=config.BOT_PREFIX, intents=intents)

# in-memory anti-nuke trackers (per guild): recent destructive actions
_recent_actions: dict[int, list[float]] = {}
ANTI_NUKE_WINDOW_SECONDS = 10
ANTI_NUKE_THRESHOLD = 5

MEMES = [
    "https://i.imgur.com/6IWGRWl.png",
    "https://i.imgur.com/2X4bJ3d.png",
    "https://i.imgur.com/9y8Ffhd.png",
]
EIGHT_BALL_ANSWERS = [
    "Yes, definitely.", "No way.", "Ask again later.", "It is certain.",
    "Very doubtful.", "Absolutely!", "Cannot predict now.",
]


def module_enabled(guild_id: int, module: str) -> bool:
    s = db.get_settings(guild_id)
    return s.get("modules", {}).get(module, True)


@bot.event
async def on_ready():
    print(f"[Vantrix] Logged in as {bot.user} ({bot.user.id})")
    try:
        await bot.tree.sync()
    except Exception as e:
        print(f"[Vantrix] Slash sync failed: {e}")


# ---------- Leveling ----------
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or not message.guild:
        return
    if module_enabled(message.guild.id, "leveling"):
        result = db.add_xp(message.guild.id, message.author.id, random.randint(5, 15))
        if result.get("leveled_up"):
            try:
                await message.channel.send(
                    f"🎉 {message.author.mention} leveled up to **level {result['level']}**!"
                )
            except discord.Forbidden:
                pass
    await bot.process_commands(message)


# ---------- Welcome / Goodbye ----------
@bot.event
async def on_member_join(member: discord.Member):
    if not module_enabled(member.guild.id, "welcome"):
        return
    s = db.get_settings(member.guild.id)
    channel_id = s.get("welcome_channel_id")
    if channel_id:
        channel = member.guild.get_channel(int(channel_id))
        if channel:
            msg = s.get("welcome_message", "Welcome {user}!").format(
                user=member.mention, server=member.guild.name
            )
            await channel.send(msg)


@bot.event
async def on_member_remove(member: discord.Member):
    if not module_enabled(member.guild.id, "welcome"):
        return
    s = db.get_settings(member.guild.id)
    channel_id = s.get("goodbye_channel_id")
    if channel_id:
        channel = member.guild.get_channel(int(channel_id))
        if channel:
            msg = s.get("goodbye_message", "{user} left.").format(
                user=member.display_name, server=member.guild.name
            )
            await channel.send(msg)


# ---------- Anti-Nuke ----------
async def _flag_destructive_action(guild: discord.Guild, actor: discord.Member):
    if not module_enabled(guild.id, "anti_nuke"):
        return
    if actor.id in config.OWNER_IDS or actor.id == guild.owner_id:
        return
    now = datetime.now(timezone.utc).timestamp()
    bucket = _recent_actions.setdefault(guild.id, [])
    bucket.append(now)
    _recent_actions[guild.id] = [t for t in bucket if now - t < ANTI_NUKE_WINDOW_SECONDS]
    if len(_recent_actions[guild.id]) >= ANTI_NUKE_THRESHOLD:
        try:
            await guild.ban(actor, reason="Vantrix Anti-Nuke: suspicious mass action detected")
        except discord.Forbidden:
            pass


@bot.event
async def on_guild_channel_delete(channel: discord.abc.GuildChannel):
    async for entry in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
        await _flag_destructive_action(channel.guild, entry.user)


@bot.event
async def on_member_ban(guild: discord.Guild, user: discord.User):
    async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.ban):
        await _flag_destructive_action(guild, entry.user)


# ---------- Reaction Roles ----------
@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    if payload.member is None or payload.member.bot:
        return
    if not module_enabled(payload.guild_id, "reaction_roles"):
        return
    rr = db.get_reaction_role(payload.guild_id, payload.message_id, str(payload.emoji))
    if rr:
        guild = bot.get_guild(payload.guild_id)
        role = guild.get_role(int(rr["role_id"]))
        if role:
            await payload.member.add_roles(role, reason="Vantrix reaction role")


@bot.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent):
    if not module_enabled(payload.guild_id, "reaction_roles"):
        return
    rr = db.get_reaction_role(payload.guild_id, payload.message_id, str(payload.emoji))
    if rr:
        guild = bot.get_guild(payload.guild_id)
        member = guild.get_member(payload.user_id)
        role = guild.get_role(int(rr["role_id"]))
        if member and role:
            await member.remove_roles(role, reason="Vantrix reaction role")


# ---------- Auto-responder ----------
@bot.event
async def on_message_edit(before, after):
    pass  # placeholder hook, keyword auto-responder handled below via listener


@bot.listen("on_message")
async def auto_responder(message: discord.Message):
    if message.author.bot or not message.guild:
        return
    if not module_enabled(message.guild.id, "auto_responder"):
        return
    s = db.get_settings(message.guild.id)
    responses = s.get("auto_responses", {})
    content = message.content.lower()
    for trigger, reply in responses.items():
        if trigger.lower() in content:
            await message.channel.send(reply)
            break


# ---------- Moderation (slash commands) ----------
@bot.tree.command(name="kick", description="Kick a member")
@app_commands.checks.has_permissions(kick_members=True)
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    await member.kick(reason=reason)
    await interaction.response.send_message(f"👢 Kicked {member.mention} — {reason}")


@bot.tree.command(name="ban", description="Ban a member")
@app_commands.checks.has_permissions(ban_members=True)
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    await member.ban(reason=reason)
    await interaction.response.send_message(f"🔨 Banned {member.mention} — {reason}")


@bot.tree.command(name="mute", description="Timeout a member for N minutes")
@app_commands.checks.has_permissions(moderate_members=True)
async def mute(interaction: discord.Interaction, member: discord.Member, minutes: int = 10):
    import datetime as dt
    await member.timeout(dt.timedelta(minutes=minutes))
    await interaction.response.send_message(f"🔇 Muted {member.mention} for {minutes} minutes")


@bot.tree.command(name="warn", description="Warn a member")
@app_commands.checks.has_permissions(moderate_members=True)
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str):
    db.add_warning(interaction.guild_id, member.id, interaction.user.id, reason)
    await interaction.response.send_message(f"⚠️ Warned {member.mention} — {reason}")


@bot.tree.command(name="clear", description="Bulk delete messages")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(interaction: discord.Interaction, amount: int = 10):
    await interaction.channel.purge(limit=amount)
    await interaction.response.send_message(f"🧹 Cleared {amount} messages", ephemeral=True)


@bot.tree.command(name="lock", description="Lock the current channel")
@app_commands.checks.has_permissions(manage_channels=True)
async def lock(interaction: discord.Interaction):
    await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=False)
    await interaction.response.send_message("🔒 Channel locked")


# ---------- Fun / Utility ----------
@bot.tree.command(name="meme", description="Get a random meme")
async def meme(interaction: discord.Interaction):
    await interaction.response.send_message(random.choice(MEMES))


@bot.tree.command(name="8ball", description="Ask the magic 8-ball")
async def eight_ball(interaction: discord.Interaction, question: str):
    await interaction.response.send_message(f"🎱 **{question}**\n{random.choice(EIGHT_BALL_ANSWERS)}")


@bot.tree.command(name="avatar", description="Show a member's avatar")
async def avatar(interaction: discord.Interaction, member: discord.Member = None):
    member = member or interaction.user
    await interaction.response.send_message(member.display_avatar.url)


@bot.tree.command(name="userinfo", description="Show info about a member")
async def userinfo(interaction: discord.Interaction, member: discord.Member = None):
    member = member or interaction.user
    embed = discord.Embed(title=f"{member.display_name}", color=discord.Color.purple())
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="Joined", value=member.joined_at.strftime("%Y-%m-%d"))
    embed.add_field(name="Account Created", value=member.created_at.strftime("%Y-%m-%d"))
    embed.add_field(name="Roles", value=", ".join(r.name for r in member.roles[1:]) or "None")
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="serverinfo", description="Show info about this server")
async def serverinfo(interaction: discord.Interaction):
    guild = interaction.guild
    embed = discord.Embed(title=guild.name, color=discord.Color.blue())
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.add_field(name="Members", value=guild.member_count)
    embed.add_field(name="Created", value=guild.created_at.strftime("%Y-%m-%d"))
    embed.add_field(name="Owner", value=str(guild.owner))
    await interaction.response.send_message(embed=embed)


# ---------- Tickets ----------
class TicketView(discord.ui.View):
    @discord.ui.button(label="Open Ticket", style=discord.ButtonStyle.green, emoji="🎫")
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        }
        channel = await guild.create_text_channel(
            f"ticket-{interaction.user.name}", overwrites=overwrites
        )
        db.create_ticket(guild.id, channel.id, interaction.user.id)
        await channel.send(f"🎫 {interaction.user.mention} welcome to your ticket!", view=CloseTicketView())
        await interaction.response.send_message(f"Ticket created: {channel.mention}", ephemeral=True)


class CloseTicketView(discord.ui.View):
    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.red, emoji="🔒")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        db.close_ticket(interaction.channel_id)
        await interaction.response.send_message("Closing ticket in 5 seconds...")
        await interaction.channel.delete(delay=5)


@bot.tree.command(name="ticket-panel", description="Post the ticket panel")
@app_commands.checks.has_permissions(manage_guild=True)
async def ticket_panel(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Need help?",
        description="Click the button below to open a support ticket.",
        color=discord.Color.dark_purple(),
    )
    await interaction.response.send_message(embed=embed, view=TicketView())


# ---------- Reaction role setup ----------
@bot.tree.command(name="reactionrole", description="Bind an emoji reaction on a message to a role")
@app_commands.checks.has_permissions(manage_roles=True)
async def reactionrole(interaction: discord.Interaction, message_id: str, emoji: str, role: discord.Role):
    db.add_reaction_role(interaction.guild_id, int(message_id), emoji, role.id)
    await interaction.response.send_message(f"✅ Bound {emoji} → {role.mention} on message `{message_id}`")


# ---------- Leaderboard ----------
@bot.tree.command(name="leaderboard", description="Show the XP leaderboard")
async def leaderboard(interaction: discord.Interaction):
    top = db.get_leaderboard(interaction.guild_id)
    if not top:
        await interaction.response.send_message("No XP data yet.")
        return
    lines = []
    for i, entry in enumerate(top, start=1):
        member = interaction.guild.get_member(entry["user_id"])
        name = member.display_name if member else f"User {entry['user_id']}"
        lines.append(f"**#{i}** {name} — Level {entry['level']} ({entry['xp']} XP)")
    embed = discord.Embed(title="🏆 XP Leaderboard", description="\n".join(lines), color=discord.Color.gold())
    await interaction.response.send_message(embed=embed)


def run_bot():
    if not config.DISCORD_BOT_TOKEN:
        print("[Vantrix] DISCORD_BOT_TOKEN missing — bot will not start.")
        return
    bot.run(config.DISCORD_BOT_TOKEN)
