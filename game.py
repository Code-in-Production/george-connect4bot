import asyncio
import discord
from discord.ext import commands

class Game(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(require_var_positional=False)
    async def start(self, ctx, *users: discord.User):
        # start the game with the message
        message = await ctx.send("Preparing...")
        for emoji in "1⃣ 2⃣ 3⃣ 4⃣ 5⃣ 6⃣ 7⃣ ".split():
            await message.add_reaction(emoji)
        current_user_index = 0
        turn_number = 0
        # loop for reactions and stuff
        try:
            while True:
                # Update game message
                current_user = users[current_user_index]
                await message.edit(content=f"Turn {turn_number+1}. {current_user.mention}'s move! [{current_user_index+1}]")
                # Wait for reaction from current user
                def check(reaction, user):
                    if user.id != current_user.id:
                        return False
                    if reaction.emoji not in "1⃣ 2⃣ 3⃣ 4⃣ 5⃣ 6⃣ 7⃣ ".split():
                        return False
                    return True
                reaction, user = await self.bot.wait_for("reaction_add", timeout=5, check=check)
                await reaction.remove(user)
                # Go to next user
                current_user_index += 1
                if current_user_index == len(users):
                    current_user_index = 0
                    turn_number += 1
        except asyncio.TimeoutError:
            await message.reply("Game timed out")

def setup(bot):
    bot.add_cog(Game(bot))
