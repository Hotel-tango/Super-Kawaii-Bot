# An idiot admires complexity, a genius admires simplicity

import asyncio
import discord
import json
import random
from dotenv import load_dotenv
import os
from discord import app_commands
from discord.ext import commands
from typing import Optional, Union
import signal

load_dotenv()

# --- Setup ---
intents = discord.Intents.default()
intents.members = True          # needed to resolve members reliably
intents.voice_states = True     # needed to see/move voice state

bot = commands.Bot(command_prefix="!", intents=intents)  # compatibility

GUILD_ID = None

OLD_GUILD_IDS = [
    1546165428823392297,
    1546145792283386016,
]

# Add commands here that require /set-channel
CHANNEL_COMMANDS = {
    "get-a-room": "voice", "get-a-room_text": "text", "banish": "voice", "startup": "text"
    }

# saves configurations for each server to make it keep restarts (which happen very often)
DESTINATION_CHANNELS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "destination_channels.json")
GUILDS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "guilds.json")
 
 
def load_destination_channels() -> dict[int, dict[str, int]]:
    if not os.path.exists(DESTINATION_CHANNELS_PATH):
        print("No destination channels json file found")
        return {}
    try:
        with open(DESTINATION_CHANNELS_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
        return {
            int(guild_id): {cmd: int(chan_id) for cmd, chan_id in cmds.items()}
            for guild_id, cmds in raw.items()
        }
    except (json.JSONDecodeError, ValueError, OSError) as e:
        print(f"Couldn't load {DESTINATION_CHANNELS_PATH} ({e}).")
        return {}

def save_destination_channels() -> None:
    try:
        with open(DESTINATION_CHANNELS_PATH, "w", encoding="utf-8") as f:
            json.dump(destination_channels, f)
    except OSError as e:
        print(f"Couldn't save {DESTINATION_CHANNELS_PATH} ({e}).")

def load_guild_roster():
    if not os.path.exists(GUILDS_PATH):
        print("No guilds path json file found")
        return {}
    try:
        with open(GUILDS_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
        return{int(guild_id): name for guild_id, name in raw.items()}
    except (json.JSONDecodeError, ValueError, OSError) as e:
        print(f"Couldn't update/read {GUILDS_PATH} ({e})")
        return {}

def save_guild_roster():
    try:
        with open(GUILDS_PATH, "w", encoding="utf-8") as f:
            json.dump(guilds, f)
    except OSError as e:
        print(f"Couldn't save {GUILDS_PATH} ({e})")
    

 
 
destination_channels: dict[int, dict[str, int]] = load_destination_channels()
guilds: dict[int, str] = load_guild_roster()



console_input = "N/A"

Startup_message = "Hewwo everynyan! I'm online now~!"
shutdown_message = "Bai everynyan! I'm going offline now~!"
frequent_maintanace_message = "Sowwy for going online and offline! I was having some updates and they needed to be tested, sowwy!"
shutting_down = False



async def status_announce(command_key: str, message: str):
    for guild_id, cmds in destination_channels.items():
        channel_id = cmds.get(command_key)
        if channel_id is None:
            continue
        channel = bot.get_channel(channel_id)
        if channel:
            try:
                await channel.send(message)
            except discord.HTTPException as e:
                print(f"Couldn't send startup/shutdown message in guild {guild_id}: {e}")

@bot.event
async def on_ready():
    if GUILD_ID:
        guild = discord.Object(id=GUILD_ID)
        bot.tree.copy_global_to(guild=guild)
        synced = await bot.tree.sync(guild=guild)
    else:
        synced = await bot.tree.sync()   

    print(f"Logged in as {bot.user}. Synced {len(synced)} command(s).")
    await status_announce("startup", Startup_message)

    for guild in bot.guilds:
        guilds.setdefault(guild.id, guild.name)
    save_guild_roster()
        

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown()))
        except (NotImplementedError, RuntimeError):
            pass  # windows doesn't support add_signal_handler

    bot.loop.create_task(console())

@bot.event
async def on_guild_join(guild):
    guilds.setdefault(guild.id, guild.name)
    save_guild_roster()

async def shutdown():
    global shutting_down
    if shutting_down:
        return
    shutting_down = True
    await status_announce("startup", shutdown_message)
    await bot.close()

async def console():
    global current_channel
    current_channel = None
    await bot.wait_until_ready()
    loop = asyncio.get_event_loop()

    while not bot.is_closed():
        msg = await loop.run_in_executor(None, input, "> ")
        if not msg.strip():
            continue

        if msg.startswith("help"):
            print("Clear cache: Clears old server sync for new updates in case of commands not syncing.")
            print("Switch: Switches the channel you send messages in when using send")
            print("Send: Sends a message on the dedicated channel used with switch.")
        elif msg.startswith("command "):
            if await loop.run_in_executor(None, input, "Clear old server cache? > ") == "y":
                print("Clearing...")
                for old_id in OLD_GUILD_IDS:
                    old_guild = discord.Object(id=old_id)
                    bot.tree.clear_commands(guild=old_guild)
                    await bot.tree.sync(guild=old_guild)
                print("Done!")
            else:
                print("Cache clearing refused")  
        elif msg.startswith("switch "):
            arg = msg.split(" ", 1)[1].strip()
            channel = bot.get_channel(int(arg)) if arg.isdigit() else None
            if channel:
                current_channel = channel
                print(f"Switched to #{channel.name} ({channel.guild.name})")
            else:
                print("Couldn't find that channel, input channel id")
            continue
        elif msg == "shutdown":
                msg = await loop.run_in_executor(None, input, "Confirm shutdown? (y/n) > ")
                if msg == "y":
                    await shutdown()
                    break
        elif msg.startswith("send "):
            msg = msg.split(" ", 1)[1]
            await current_channel.send(msg)
            if current_channel is None:
                print("No channel selected, input channel id")
                continue
        



@bot.tree.command(name="coin-flip", description="Just a coin flip")
async def coin_flip(interaction: discord.Interaction):
    side = random.randint(1, 2)
    if side == 1:
        await interaction.response.send_message("It landed on heads")
    elif side == 2:
        await interaction.response.send_message("It landed on tails")
    else:
        await interaction.response.send_message(r"There's a coding error, sowwy ¯\_(ツ)_/¯ ")



@app_commands.checks.has_permissions(manage_channels=True)
@bot.tree.command(name="set-channel", description="Sets the destination voice channel for a command")
@app_commands.describe(channel="Channel for the command",)
@app_commands.choices(
    command=[app_commands.Choice(name=c, value=c) for c in CHANNEL_COMMANDS]
)
async def set_channel(
    interaction: discord.Interaction,
    command: app_commands.Choice[str],
    channel: Union[discord.VoiceChannel, discord.TextChannel] = None,
):
    if channel is None:
        await interaction.response.send_message("Specify the channel you want to use", ephemeral=True)
        return
    elif command is None:
        await interaction.response.send_message("Specify the command you want to use", ephemeral=True)
        return

    if isinstance(channel, discord.VoiceChannel) and command in CHANNEL_COMMANDS:
        if not CHANNEL_COMMANDS.get(command.value) != "voice":
            await interaction.response.send_message("Command is for a voice channel, you gave a text channel")
            return
    elif channel is discord.TextChannel and command in CHANNEL_COMMANDS:
        if not CHANNEL_COMMANDS.get(command.value) != "text":
            await interaction.response.send_message("Command is for a text channel, you gave a voice channel")
            return



    destination_channels.setdefault(interaction.guild.id, {})[command.value] = channel.id
    save_destination_channels()
    await interaction.response.send_message(f"{command.value}'s channel is now set to {channel.name}.")


@set_channel.error
async def set_channel_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message(
            "You need Manage Channels permission to set the room channel, eat shit and die >:3"
        )
    else:
        raise error

@app_commands.checks.has_permissions(move_members=True)
@bot.tree.command(name="banish", description="Sends someone to a channel of your choosing, if none is given it sends to the default banish channel")
@app_commands.describe(
    member1="Member1 to banish",
    member2="OPTIONAL Member2 to banish",
    member3="OPTIONAL Member3 to banish",
    member4="OPTIONAL Member4 to banish",
    member5="OPTIONAL Member5 to banish",
    channel="OPTIONAL Channel to banish to, defaults to default channel",
)
async def banish(
    interaction: discord.Interaction,
    member1: discord.Member,
    member2: Optional[discord.Member] = None,
    member3: Optional[discord.Member] = None,
    member4: Optional[discord.Member] = None,
    member5: Optional[discord.Member] = None,
    channel: Optional[discord.VoiceChannel] = None,
):
    destination = channel
    if destination is None:
        dest_id = destination_channels.get(interaction.guild.id, {}).get("banish")
        if dest_id is None:
            await interaction.response.send_message(
                "No banish channel set yet, and you didn't specify one, get someone with Manage Channels to run /set-channel, or type a channel directly",
                ephemeral=True,
            )
            return
        destination = interaction.guild.get_channel(dest_id)
        if not isinstance(destination, discord.VoiceChannel):
            await interaction.response.send_message(
                "What happend to the room? Welp, can't send someone somewhere that doesn't exist. Sowwy daddy/mommy D: ", ephemeral=True
            )
            return
    
    targets = [m for m in (member1, member2, member3, member4, member5) if m is not None]
 
    banished, skipped = [], []
    for m in targets:
        if m.voice is None or m.voice.channel is None:
            skipped.append(m.display_name)
            continue
        await m.move_to(destination)
        banished.append(m.display_name)
 
    parts = []
    if banished:
        parts.append(f"Banished {', '.join(banished)} to {destination.name}.")
    if skipped:
        parts.append(f"Skipped (not in a voice channel): {', '.join(skipped)}.")
    await interaction.response.send_message(" ".join(parts) or "Nothing to do.")

@banish.error
async def banish_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message(
            "You don't have permission to do this command, eat shit and die >:3"
        )
    else:
        raise error


@app_commands.checks.has_permissions(move_members=True, manage_channels=True)
@bot.tree.command(name="get-a-room", description="Make two people get a room (moves them to the configured voice channel)")
@app_commands.describe(
    member="Member1",
    member2="Member2",
)
async def get_a_room(
    interaction: discord.Interaction,
    member: discord.Member,
    member2: discord.Member,
):
    dest_id = destination_channels.get(interaction.guild.id, {}).get("get-a-room")
    if dest_id is None:
        await interaction.response.send_message(
            "No room channel yet, get someone with the manage channels permission to set a channel", ephemeral=True
        )
        return
    destination = interaction.guild.get_channel(dest_id)
    if not isinstance(destination, discord.VoiceChannel):
        await interaction.response.send_message(
            "What happend to the room? Welp, can't send someone somewhere that doesn't exist. Sowwy daddy/mommy D: ", ephemeral=True
        )
        return

    same_channel = (
        member.voice is not None
        and member2.voice is not None
        and member.voice.channel == member2.voice.channel
    )
    if not same_channel:
        await interaction.response.send_message(
            f"{member.display_name} and {member2.display_name} ain't in the same voice channel dumbass, or they're not in one at all"
        )
        return

    await member.move_to(destination)
    await member2.move_to(destination)
    await interaction.response.send_message(
        f"{member.display_name} and {member2.display_name} got a room"
    )


@get_a_room.error
async def move_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message(
            "You don't have permission to do this command, eat shit and die >:3"
        )
    else:
        raise error


@app_commands.checks.has_permissions(move_members=True)
@bot.tree.command(name="kidnap", description="Drag someone into whatever voice channel you're currently in")
@app_commands.describe(member="Member1")
async def kidnap(
    interaction: discord.Interaction,
    member: discord.Member,
):
    if interaction.user.voice is None or interaction.user.voice.channel is None:
        await interaction.response.send_message(
            "You need to be in a voice channel yourself to kidnap someone into it."
        )
        return
    destination = interaction.user.voice.channel

    if member.voice is None or member.voice.channel is None:
        await interaction.response.send_message(
            f"{member.display_name} ain't in a voice channel right now, dumbass"
        )
        return

    await member.move_to(destination)
    await interaction.response.send_message(
        f"{member.display_name} has been kidnapped"
    )


@kidnap.error
async def kidnap_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message(
            "You don't have permission to do this command, eat shit and die >:3"
        )
    else:
        raise error


# --- Run ---
bot.run(os.getenv("DISCORD_TOKEN"))