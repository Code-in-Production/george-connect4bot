import os
import asyncio
import discord
from discord.ext import commands

bot = commands.Bot(command_prefix="]")
extensions = ["game"]

@bot.event
async def on_ready():
    if extensions:
        print(f"Loading extensions: {', '.join(extensions)}")
        for name in extensions:
            print(f"Loading {name}")
            bot.load_extension(name)
        print("All extensions loaded")
    print("Bot now running")

@bot.command(ignore_extra=False, hidden=True)
@commands.is_owner()
async def load(ctx, name):
    bot.load_extension(name)
    await ctx.send("Extension loaded")

@bot.command(ignore_extra=False, hidden=True)
@commands.is_owner()
async def unload(ctx, name):
    bot.unload_extension(name)
    await ctx.send("Extension loaded")

@bot.command(ignore_extra=False, hidden=True)
@commands.is_owner()
async def reload(ctx, name):
    bot.reload_extension(name)
    await ctx.send("Extension loaded")

@bot.command(ignore_extra=False, hidden=True)
@commands.is_owner()
async def stop(ctx):
    await ctx.send("Stopping bot")
    await bot.close()

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandInvokeError):
        error = error.original
    await ctx.send(f"Error: `{error!r}`")

bot.run(os.environ["CONNECT4_TOKEN"])
