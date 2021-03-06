from __future__ import annotations

import asyncio
import typing
from copy import deepcopy
from dataclasses import dataclass, field

import discord
from discord.ext import commands

@dataclass
class Round:
    users: list[discord.Member]
    game_id: int = field(init=False)
    width: int = 7
    height: int = 6
    length: int = 4
    current_user_index: int = 0
    turn_number: int = 0
    game_ended: bool = False
    winner_index: int = -1
    game_grid: list[list[int]] = field(init=False)
    game_history: list[tuple[int, int, int]] = field(default_factory=list, init=False)
    _message: typing.Optional[discord.Message] = field(default=None, init=False)

    next_game_id: typing.ClassVar[int] = 1
    rounds_from_message: typing.ClassVar[dict[discord.Message, Round]] = {}
    rounds_from_id: typing.ClassVar[dict[discord.Message, Round]] = {}

    COLUMN_EMOJIS: typing.ClassVar[list[str]] = []
    for i in range(1, 10):
        COLUMN_EMOJIS.append(f"{i}\u20E3")
    for i in range(26):
        COLUMN_EMOJIS.append(chr(0x1F1E6 + i))

    CHIP_EMOJIS: typing.ClassVar[dict[int, str]] = {}
    CHIP_EMOJIS[-1] = "⚪"  # background gon be white
    for i, emoji in enumerate("🔴🔵🟢🟡🟣🟠"):
        CHIP_EMOJIS[i] = emoji

    def __post_init__(self):
        self.game_id = Round.next_game_id
        Round.rounds_from_id[self.game_id] = self
        Round.next_game_id += 1
        self.game_grid = [[-1]*self.width for _ in range(self.height)]

    @property
    def info(self):
        return []

    @property
    def message(self):
        return self._message

    @message.setter
    def message(self, value):
        if self._message is not None:
            del self.rounds_from_message[self._message]
        self._message = value
        if self._message is not None:
            self.rounds_from_message[self._message] = self

    @property
    def current_user(self):
        return self.users[self.current_user_index]

    @property
    def column_emojis(self):
        return self.COLUMN_EMOJIS[:self.width]

    def create_embed(self, *, game_grid=None):
        if game_grid is None:
            game_grid = self.game_grid
        embed = discord.Embed()
        embed.add_field(name=f"Turn {self.turn_number+1}", value=(
            "\n".join("".join(self.CHIP_EMOJIS[state] for state in row) for row in game_grid)
            + "\n" + "".join(self.column_emojis)
            + "\n" + (
                f"{self.current_user.mention}'s move! {self.CHIP_EMOJIS[self.current_user_index]}"
                if not self.game_ended else
                (
                    f"{self.users[self.winner_index].mention} won! {self.CHIP_EMOJIS[self.winner_index]}"
                    if self.winner_index != -1 else
                    ""
                )
            )
        ))
        return embed

    def check_win(self, row_index, column_index, user_index, game_grid=None):
        if game_grid is None:
            game_grid = self.game_grid
        max_len_in_a_row = {(0, 1): 0, (1, 0): 0, (1, 1): 0, (1, -1): 0}  # All directions
        for offset in range(-self.length + 1, self.length):
            for y, x in max_len_in_a_row:
                if 0 <= row_index + y*offset < self.height and 0 <= column_index + x*offset < self.width:
                    if game_grid[row_index + y*offset][column_index + x*offset] == user_index:
                        max_len_in_a_row[y, x] += 1
                        if max_len_in_a_row[y, x] == self.length:
                            return True
                        continue
                max_len_in_a_row[y, x] = 0
        return False

    async def new_message(self, message):
        if not self.game_ended:
            for emoji in self.column_emojis:
                await message.add_reaction(emoji)
            await message.add_reaction("❌")
        self.message = message
        await self.refresh_message()

    async def refresh_message(self):
        states = [*self.info]
        if self.game_ended:
            states.append("Ended")
        if states:
            suffix = f" ({', '.join(states)})"
        else:
            suffix = ""
        await self.message.edit(content=f"Game {self.game_id}{suffix}", embed=self.create_embed())

    async def place_and_check(self, column_index):
        # Try finding empty space in column
        for row_index in range(self.height)[::-1]:
            if self.game_grid[row_index][column_index] == -1:
                break
        else:
            # If you cant, silently ignore the move lol
            return None
        # Place chip
        self.game_history.append((self.current_user_index, column_index, row_index))
        self.game_grid[row_index][column_index] = self.current_user_index
        # Check for a win
        if not self.check_win(row_index, column_index, self.current_user_index):
            # No win, go to next user
            self.current_user_index += 1
            if self.current_user_index == len(self.users):
                self.current_user_index = 0
                self.turn_number += 1
            await self.refresh_message()
            return False
        # Someone won :D
        self.game_ended = True
        self.winner_index = self.current_user_index
        await self.refresh_message()
        await self.message.reply(f"{self.current_user.mention} won :D")
        self.message = None
        return True

    async def end(self):
        if self.game_ended:
            return
        self.game_ended = True
        self.winner_index = -1
        await self.refresh_message()
        await self.message.reply(f"Game ended")
        self.message = None

@dataclass
class LightningRound(Round):
    timeout: int = 10

    @property
    def info(self):
        return ["Lightning", f"{self.timeout} Second Timeout"]

    async def end_if_no_change(self):
        aaa = self.turn_number, self.current_user_index
        await asyncio.sleep(self.timeout)
        if (self.turn_number, self.current_user_index) != aaa:
            return
        if self.game_ended:
            return
        await self.end()

    async def place_and_check(self, column_index):
        await super().place_and_check(column_index)
        asyncio.create_task(self.end_if_no_change())

@dataclass
class DelayedRound(Round):
    delay: int = 2

    @property
    def info(self):
        return ["Delayed", f"{self.delay} Move Delay"]

    def create_embed(self):
        if self.game_ended:
            game_grid = None
        else:
            game_grid = deepcopy(self.game_grid)
            for user_index, column_index, row_index in self.game_history[-self.delay:]:
                game_grid[row_index][column_index] = -1
        return super().create_embed(game_grid=game_grid)

    def check_win(self, row_index, column_index, user_index):
        game_grid = deepcopy(self.game_grid)
        for user_index, column_index, row_index in self.game_history[-self.delay:]:
            game_grid[row_index][column_index] = -1
        if len(self.game_history) <= self.delay:
            return False
        user_index, column_index, row_index = self.game_history[-self.delay-1]
        return super().check_win(row_index, column_index, user_index, game_grid=game_grid)

@dataclass
class Game(commands.Cog):
    """Play Connect 4 in Discord :D"""

    bot: commands.Bot
    kwargs: dict[str, typing.Any] = field(default_factory=dict)

    def __hash__(self):
        return hash(id(self))

    @commands.group()
    async def options(self, ctx, *args):
        """Set or view options for the next game.

        Possible options:
            height - height of the board (default=6)
            width - width of the board (default=7)
            length - length of consecutive chips needed to win (default=4)
            timeout - number of seconds for each player's turn (default=10)
            delay - number of moves to hide each chip for (default=# of players)

        Usage:
            ]options                        - this shows the current options
            ]options height=69              - this sets height to 69
            ]options width=420 length=69    - this sets width to 420 and length to 69
            ]options timeout=               - this resets timeout to the default value
        """
        if not args:
            if not self.kwargs:
                await ctx.send(f"Options: *Empty :/*")
            else:
                await ctx.send(f"Options: {', '.join(f'{name}={value}' for name, value in self.kwargs.items())}")
            return
        for arg in args:
            if "=" not in arg:
                raise commands.CommandInvokeError(f"no = in {arg}")
            name, _, value = arg.partition("=")
            if name not in "width height length timeout delay".split():
                raise commands.CommandInvokeError(f"unknown option: {name}")
            if not value:
                continue
            try:
                value = int(value)
            except ValueError:
                raise commands.CommandInvokeError(f"option {name}'s value not an int: {value}")
            if value <= 0:
                raise commands.CommandInvokeError(f"option {name}'s value must be positive: {value}")
        for arg in args:
            name, _, value = arg.partition("=")
            if not value:
                del self.kwargs[name]
            else:
                self.kwargs[name] = int(value)
        await ctx.send("Updated options")

    @commands.command(aliases=["startnormal", "s"], ignore_extra=False, require_var_positional=True)
    async def start(self, ctx, *users: discord.Member):
        """Start a normal game of Connect 4 with the specified players."""
        if len(users) < 2:
            raise commands.CommandInvokeError("at least 2 players required")
        kwargs = self.kwargs.copy()
        kwargs.pop("delay", None)
        kwargs.pop("timeout", None)
        round = Round(users=users, **kwargs)
        await round.new_message(await ctx.send("..."))

    @commands.command(aliases=["l"], ignore_extra=False, require_var_positional=True)
    async def startlightning(self, ctx, *users: discord.Member):
        """Start a lightning game of Connect 4 with the specified players.

        The countdown starts after the first player has made a move.

        Use ]options timeout=<seconds> to change the number of seconds each
        player can have for a turn.

        """
        if len(users) < 2:
            raise commands.CommandInvokeError("at least 2 players required")
        kwargs = self.kwargs.copy()
        kwargs.pop("delay", None)
        round = LightningRound(users=users, **kwargs)
        await round.new_message(await ctx.send("..."))

    @commands.command(aliases=["d"], ignore_extra=False, require_var_positional=True)
    async def startdelayed(self, ctx, *users: discord.Member):
        """Start a delayed game of Connect 4 with the specified players.

        Use ]options delay=<moves> to change the number of moves that will be
        hidden.

        """
        if len(users) < 2:
            raise commands.CommandInvokeError("at least 2 players required")
        kwargs = self.kwargs.copy()
        kwargs.pop("timeout", None)
        round = DelayedRound(users=users, **{"delay": len(users), **kwargs})
        await round.new_message(await ctx.send("..."))

    @commands.command(ignore_extra=False)
    async def show(self, ctx, id: int):
        """Creates a new message for the game with the specified id.

        Any reactions on previous messages will no longer work.

        """
        if id not in Round.rounds_from_id.keys():
            raise commands.CommandInvokeError(f"no game with id {id} found")
        round = Round.rounds_from_id[id]
        await round.new_message(await ctx.send("..."))

    @commands.command(ignore_extra=False)
    async def end(self, ctx, id: int):
        """Ends the game with the specified id."""
        if id not in Round.rounds_from_id.keys():
            raise commands.CommandInvokeError(f"no game with id {id} found")
        round = Round.rounds_from_id[id]
        if round.game_ended:
            raise commands.CommandInvokeError(f"game with id {id} already ended")
        await round.end()

    @commands.command(ignore_extra=False)
    async def place(self, ctx, id: int, column: int):
        """Places a chip on the column in the game with the specified id.

        This is an alternative to using the emojis.

        """
        if id not in Round.rounds_from_id.keys():
            raise commands.CommandInvokeError(f"no game with id {id} found")
        round = Round.rounds_from_id[id]
        if round.game_ended:
            raise commands.CommandInvokeError(f"game with id {id} already ended")
        if ctx.author.id != round.current_user.id:
            raise commands.CommandInvokeError(f"not your turn lol")
        if not 1 <= column <= round.width:
            raise commands.CommandInvokeError(f"column must be between 1 and {round.width}")
        await round.place_and_check(column-1)

    @commands.command(ignore_extra=False)
    async def history(self, ctx, id: int):
        """Views the history of the game with the specified id.

        In delayed games, hidden moves will be shown as question marks.

        """
        if id not in Round.rounds_from_id.keys():
            raise commands.CommandInvokeError(f"no game with id {id} found")
        round = Round.rounds_from_id[id]
        if not round.game_history:
            await ctx.send("Game History:\n*Empty :/*")
            return
        game_history = round.game_history.copy()
        for i, (user_index, column_index, row_index) in enumerate(game_history):
            game_history[i] = user_index, column_index+1, round.height-row_index
        if isinstance(round, DelayedRound) and not round.game_ended:
            for i in range(len(game_history))[-round.delay:]:
                game_history[i] = game_history[i][0], "?", "?"
        for i, (user_index, column_index, row_index) in enumerate(game_history):
            game_history[i] = f"{round.users[user_index].display_name} {round.CHIP_EMOJIS[user_index]} at column {column_index} row {row_index}"
        await ctx.send(f"Game History:\n" + "\n".join(game_history))

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        # Validate the reaction
        if reaction.message not in Round.rounds_from_message.keys():
            return
        round = Round.rounds_from_message[reaction.message]
        if round.game_ended:
            return
        if user.id != round.current_user.id:
            return
        if reaction.emoji == "❌":
            await round.end()
            return
        if reaction.emoji not in round.column_emojis:
            return
        # Remove the reaction
        await reaction.remove(user)
        # Get user choice of row
        column_index = round.column_emojis.index(reaction.emoji)
        # Try placing it and check for win
        await round.place_and_check(column_index)

def setup(bot):
    bot.add_cog(Game(bot))
