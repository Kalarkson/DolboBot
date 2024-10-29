
import disnake
from disnake.ext import commands

from dotenv import load_dotenv, find_dotenv
import sqlite3, platform, os, requests

from config import *
from audit import audit
from func import *

load_dotenv(find_dotenv())
BOT_TOKEN = os.getenv('KLARKI_BOT_TOKEN')

bot = commands.Bot(
    command_prefix="*",
    intents=disnake.Intents().all(),
    reload=True,
    help_command=None
)

@bot.event
async def on_ready():
    ip = requests.get("https://api.ipify.org").text
    audit.info(f'Бот включен. Опреационная система: {platform.platform()}. IP Адрес: {ip}')
    print("◼" * 60)
    print(f"Бот {bot.user.name} | {bot.user.id} работает!")
    print("◼" * 60)

@bot.command()
@commands.is_owner()
async def load(ctx: commands.Context, extension: str):
    bot.load_extension(f'cogs.{extension}')
    audit.info(f'Ког {extension} загружен')
    await ctx.send(f'Ког {extension} загружен', delete_after=5 if ctx.guild != None else None)
    if ctx.guild != None:
        await ctx.message.delete()

@bot.command()
@commands.is_owner()
async def unload(ctx: commands.Context, extension: str):
    bot.unload_extension(f'cogs.{extension}')
    audit.info(f'Ког {extension} отгружен')
    await ctx.send(f'Ког {extension} отгружен', delete_after=5 if ctx.guild != None else None)
    if ctx.guild != None:
        await ctx.message.delete()

@bot.command()
@commands.is_owner()
async def reload(ctx: commands.Context, extension: str):
    bot.reload_extension(f'cogs.{extension}')
    audit.info(f'Ког {extension} перезагружен')
    await ctx.send(f'Ког {extension} перезагружен', delete_after=5 if ctx.guild != None else None)
    if ctx.guild != None:
        await ctx.message.delete()

bot.load_extension('cogs.chat_bot')
#bot.load_extensions('cogs')
bot.run(BOT_TOKEN)