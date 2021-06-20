import asyncio
import discord
from discord.ext import commands

class Game(commands.Cog):

    COLUMN_EMOJIS = []
    for i in range(1, 10):
        COLUMN_EMOJIS.append(f"{i}\u20E3")
    for i in range(26):
        COLUMN_EMOJIS.append(chr(0x1F1E6 + i))

    CHIP_EMOJIS = {}
    CHIP_EMOJIS[-1] = "⚪"  # background gon be white
    for i, emoji in enumerate("🔴🔵🟢🟡🟣🟠"):
        CHIP_EMOJIS[i] = emoji

    def __init__(self, bot):
        self.bot = bot

    @commands.command(ignore_extra=False, require_var_positional=True)
    async def start(self, ctx, *users: discord.Member):
        if len(users) < 2:
            raise commands.CommandInvokeError("at least 2 players required")
        # start the game with the message
        width, height = 7, 6
        length = 4
        current_user_index = 0
        turn_number = 0
        message = await ctx.send("Preparing...")  # The message we gon be editing
        column_emojis = self.COLUMN_EMOJIS[:width]
        chip_emojis = self.CHIP_EMOJIS
        for emoji in column_emojis:
            await message.add_reaction(emoji)
        game_grid = [[-1] * width for _ in range(height)]
        game_history = []  # list of (user, column) pairs
        # Game loop
        try:
            while True:
                # Update game message
                current_user = users[current_user_index]
                embed = discord.Embed()
                embed.add_field(name=f"Turn {turn_number+1}", value=(
                    "\n".join("".join(chip_emojis[state] for state in row) for row in game_grid)
                    + "\n" + "".join(column_emojis)
                    + "\n" + f"{current_user.mention}'s move! {chip_emojis[current_user_index]}"
                    )
                )
                await message.edit(content="", embed=embed)
                # Wait for reaction from current user
                def check(reaction, user):
                    if reaction.message.id != message.id:
                        return False
                    if user.id != current_user.id:
                        return False
                    if reaction.emoji not in column_emojis:
                        return False
                    return True
                while True:
                    # Get user choice of row
                    reaction, user = await self.bot.wait_for("reaction_add", timeout=15, check=check)
                    await reaction.remove(user)
                    column_index = column_emojis.index(reaction.emoji)
                    # Try finding empty space in column
                    for row_index in range(height)[::-1]:
                        if game_grid[row_index][column_index] == -1:
                            break
                    else:
                        # If you cant, silently ignore the move lol
                        continue
                    break
                # Place chip
                game_history.append((current_user_index, column_index))
                game_grid[row_index][column_index] = current_user_index
                # Check for a win
                max_len_in_a_row = {(0, 1): 0, (1, 0): 0, (1, 1): 0, (1, -1): 0}  # All directions
                for offset in range(-length + 1, length):
                    for y, x in max_len_in_a_row:
                        try:
                            print(row_index + y*offset, column_index + x*offset)
                            if game_grid[row_index + y*offset][column_index + x*offset] == current_user_index:
                                max_len_in_a_row[y, x] += 1
                                if max_len_in_a_row[y, x] == length:
                                    break
                                continue
                        except IndexError:
                            pass
                        max_len_in_a_row[y, x] = 0
                    else:
                        continue
                    break
                else:
                    # No win, go to next user
                    current_user_index += 1
                    if current_user_index == len(users):
                        current_user_index = 0
                        turn_number += 1
                    continue
                break
        # Timed out waiting for a reaction
        except asyncio.TimeoutError:
            await message.reply("Game timed out")
        else:
            # Someone won :D
            await message.reply("Someone won xD")
            # (copied from "Update game message")
            current_user = users[current_user_index]
            embed = discord.Embed()
            embed.add_field(name=f"Turn {turn_number+1}", value=(
                "\n".join("".join(chip_emojis[state] for state in row) for row in game_grid)
                + "\n" + "".join(column_emojis)
                + "\n" + f"{current_user.mention}'s move! {chip_emojis[current_user_index]}"
                )
            )
            await message.edit(content="", embed=embed)

def setup(bot):
    bot.add_cog(Game(bot))
