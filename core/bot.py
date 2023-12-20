from __future__ import annotations
from typing import TYPE_CHECKING

from datetime import datetime, timezone, timedelta
from logging import getLogger
from asyncio import run
from os import listdir

from resources.config import *
from core.mongo import MongoDBClient
from core.mee6 import MEE6APIClient
from core.help import CustomHelpCommand
from core.errors import DurationError
from core.modlog import Modlog

from discord.ext import commands, tasks
from discord.utils import MISSING
from discord import (
    Intents,
    LoginFailure,
    PrivilegedIntentsRequired,
    HTTPException,
    Activity,
    ActivityType,
    Embed,
    Colour
)

if TYPE_CHECKING:
    from types import TracebackType

    from core.metadata import MetaData

    from discord.ui import View
    from discord.abc import Messageable
    from discord.utils import _MissingSentinel
    from discord import (
        Guild,
        User,
        Message,
        Member
    )


_logger = getLogger(__name__)


ViewType = View | _MissingSentinel


class CustomBot(commands.Bot):

    __durations__ = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400, 'w': 604800, 'y': 31536000}

    def __init__(self) -> None:
        intents = Intents.all()
        intents.typing = intents.presences = False

        super().__init__(
            intents=intents,
            max_messages=10000,
            case_insensitive=True,
            help_command=CustomHelpCommand(),
            command_prefix=PREFIX,
            owner_ids=OWNER_IDS
        )

        self.start_time: datetime = self.now

        self.guild_id: int = GUILD_ID
        self.guild: Guild | None = None

        self.owners: list[User] = []

        self.bans: list[int] = []
        self.PERM_DURATION: int = 2 ** 32 - 1

        self.mongo: MongoDBClient | None = None
        self.mee6: MEE6APIClient | None = None

        self.metadata: MetaData | None = None

        self.LOOPS: tuple[tasks.Loop, ...] = self.manage_modlogs, self.init_status

        self.add_check(self.enforce_clearance, call_once=True)

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None
    ) -> None:
        for loop in self.LOOPS:
            loop.cancel()
            loop.remove_exception_type(Exception)

        return await super().__aexit__(exc_type, exc_val, exc_tb)

    @property
    def now(self) -> datetime:
        return datetime.now(tz=timezone.utc)

    def convert_duration(self, duration: str, /, *, allow_any: bool = False) -> timedelta:
        try:
            n = int(duration[:-1])
            multiplier = self.__durations__[duration[-1:].lower()]
            td = timedelta(seconds=n * multiplier)
        except (KeyError, ValueError):
            raise DurationError()
        if td.total_seconds() < 60 and allow_any is False:
            raise DurationError()
        return td

    @staticmethod
    async def enforce_clearance(ctx: CustomContext, /) -> bool:
        return await ctx.author_clearance() >= ctx.command.extras.get('requirement', 0)

    @staticmethod
    async def basic_embed(
        destination: Messageable,
        message: str,
        colour: Colour,
        /, *,
        view: ViewType = MISSING
    ) -> Message:
        embed = Embed(description=message, colour=colour)
        return await destination.send(embed=embed, view=view)

    async def neutral_embed(self, destination: Messageable, message: str, /, *, view: ViewType = MISSING) -> Message:
        return await self.basic_embed(destination, message, Colour.blue(), view=view)

    async def good_embed(self, destination: Messageable, message: str, /, *, view: ViewType = MISSING) -> Message:
        return await self.basic_embed(destination, message, Colour.green(), view=view)

    async def bad_embed(self, destination: Messageable, message: str, /, *, view: ViewType = MISSING) -> Message:
        return await self.basic_embed(destination, message, Colour.red(), view=view)

    async def user_to_member(self, user: User, /, *, raise_exception: bool = False) -> Member | None:
        try:
            return self.guild.get_member(user.id) or await self.guild.fetch_member(user.id)
        except HTTPException:
            if raise_exception is True:
                raise

    async def member_clearance(self, member: Member | User, /) -> int:
        if member in self.owners or member == self.guild.owner:
            return 9
        elif isinstance(member, User):
            try:
                member = await self.user_to_member(member, raise_exception=True)
            except HTTPException:
                return 0

        role_ids = [role.id for role in member.roles]
        data = self.metadata

        return \
            8 if data.admin_role_id in role_ids else  \
            7 if data.bot_role_id in role_ids else    \
            6 if data.senior_role_id in role_ids else \
            5 if data.hmod_role_id in role_ids else   \
            4 if data.smod_role_id in role_ids else   \
            3 if data.rmod_role_id in role_ids else   \
            2 if data.tmod_role_id in role_ids else   \
            1 if data.helper_role_id in role_ids else 0

    async def check_target_member(self, member: Member | User, /) -> None:
        clearance = await self.member_clearance(member)
        if clearance > 0:
            raise commands.CheckFailure('The target of this moderation is protected.')

    @tasks.loop(minutes=1)
    async def manage_modlogs(self) -> None:
        await self.wait_until_ready()

        ...

    @tasks.loop(count=1)
    async def init_status(self) -> None:
        await self.wait_until_ready()
        await self.change_presence(activity=Activity(type=ActivityType.listening, name=self.metadata.activity))

    async def on_message(self, message: Message, /) -> None:
        if message.guild is None or message.guild != self.guild or message.author.bot is True:
            return

        ctx = await self.get_context(message, cls=CustomContext)
        await self.invoke(ctx)

    async def on_member_join(self, member: Member, /) -> None:
        ...

    async def on_command_error(self, ctx: CustomContext, error: commands.CommandError, /) -> None:
        ...

    async def setup_hook(self) -> None:
        _logger.info(f'Logging in as {self.user.name} (ID: {self.user.id})...')

        try:
            self.owners = [await self.fetch_user(user_id) for user_id in OWNER_IDS]
            self.guild = await self.fetch_guild(self.guild_id)
        except HTTPException as error:
            _logger.fatal(error)
            _logger.fatal('Please double-check your config.py file is correct.')
            raise SystemExit()

        _logger.info(f'Owner(s): {", ".join(owner.name for owner in self.owners)}')
        _logger.info(f'Guild: {self.guild.name}')

        _logger.info('Fetching guild bans, this may take a while...')
        self.bans = [entry.user.id async for entry in self.guild.bans(limit=None)]

        self.metadata = await self.mongo.get_metadata()
        # TODO: Set view listeners

        for loop in self.LOOPS:
            loop.add_exception_type(Exception)
            loop.start()

    def run_bot(self) -> None:

        async def runner() -> None:
            async with self:
                async with MongoDBClient(self, MONGO) as self.mongo, MEE6APIClient() as self.mee6:

                    for folder in ('./ext', './events'):
                        for file in listdir(folder):
                            if file.endswith('.py'):

                                extension = f'{folder[2:]}.{file[:-3]}'
                                try:
                                    await self.load_extension(extension)
                                except (commands.ExtensionFailed, commands.NoEntryPointError) as extension_error:
                                    _logger.error(f'Extension {extension} could not be loaded: {extension_error}')

                    try:
                        await self.start(TOKEN)
                    except LoginFailure:
                        _logger.fatal('Invalid token passed.')
                    except PrivilegedIntentsRequired:
                        _logger.fatal('Intents are being requested that have not been enabled in the developer portal.')

        try:
            run(runner())
        except (KeyboardInterrupt, SystemExit):
            _logger.info('Received signal to terminate bot and event loop.')
        finally:
            _logger.info('Done. Have a nice day!')


class CustomContext(commands.Context[CustomBot]):

    __enduring_log_types__ = 'mute', 'ban', 'channel_ban'

    async def author_clearance(self) -> int:
        return await self.bot.member_clearance(self.author)

    async def to_modlog(
        self,
        user_id: int,
        /, *,
        channel_id: int | None = None,
        reason: str = 'No reason provided.',
        duration: timedelta | None = None,
        received: bool = False
    ) -> Modlog:
        return Modlog(
            bot=self.bot,
            case_id=await self.bot.mongo.generate_modlog_id(),
            user_id=user_id,
            mod_id=self.author.id,
            channel_id=channel_id,
            type=self.command.callback.__name__,
            reason=reason,
            created=self.bot.now,
            duration=duration,
            received=received,
            deleted=False,
            active=self.command.callback.__name__ in self.__enduring_log_types__
        )
