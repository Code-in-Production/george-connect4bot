import os
import asyncio
import discord
from discord.ext import commands

bot = commands.Bot(command_prefix="]")

async def input_handler():
    while True:
        try:
            await asyncio.to_thread(input)
        except EOFError:
            break
    await bot.close()

@bot.event
async def on_ready():
    print("Bot now running")
    asyncio.create_task(input_handler())

@bot.command(ignore_extra=False)
@commands.is_owner()
async def load(ctx, name):
    bot.load_extension(name)
    await ctx.send("Extension loaded")

@bot.command(ignore_extra=False)
@commands.is_owner()
async def unload(ctx):
    bot.unload_extension(name)
    await ctx.send("Extension loaded")

@bot.command(ignore_extra=False)
@commands.is_owner()
async def reload(ctx):
    bot.reload_extension(name)
    await ctx.send("Extension loaded")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandInvokeError):
        error = error.original
    await ctx.send(f"Error: `{error!r}`")

bot.run(os.environ["CONNECT4_TOKEN"])
