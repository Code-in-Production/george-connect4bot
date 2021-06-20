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

@bot.command()
async def test(ctx):
    await ctx.send("works lol")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandInvokeError):
        error = error.original
    await ctx.send(f"Error: `{error!r}`")

bot.run(os.environ["CONNECT4_TOKEN"])
