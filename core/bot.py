from __future__ import annotations
from typing import TYPE_CHECKING

from datetime import datetime, timezone
from logging import getLogger
from asyncio import run
from os import listdir

from resources.config import *
from core.metadata import MetaData
from core.mongo import MongoDBClient
from core.mee6 import MEE6APIClient
from core.help import CustomHelpCommand

from discord.ext import commands, tasks
from discord import (
    Intents,
    LoginFailure,
    PrivilegedIntentsRequired,
    HTTPException
)

if TYPE_CHECKING:
    from types import TracebackType

    from discord import (
        Guild,
        User,
        Message,
        Member
    )


_logger = getLogger(__name__)


class CustomBot(commands.Bot):

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

    @tasks.loop(minutes=1)
    async def manage_modlogs(self) -> None:
        ...

    @tasks.loop(count=1)
    async def init_status(self) -> None:
        ...

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
        # Set view listeners

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

    async def author_clearance(self) -> int:
        ...
