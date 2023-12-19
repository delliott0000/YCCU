from __future__ import annotations
from typing import TYPE_CHECKING

from typing import Any
from logging import getLogger

from core.metadata import MetaData

from certifi import where
from motor.motor_asyncio import (
    AsyncIOMotorClient,
    AsyncIOMotorDatabase,
    AsyncIOMotorCollection,
    AsyncIOMotorClientSession
)
from pymongo import ReturnDocument
from pymongo.errors import ConfigurationError, ServerSelectionTimeoutError

if TYPE_CHECKING:
    from typing import Self
    from types import TracebackType

    from core.bot import CustomBot


_logger = getLogger(__name__)


Dict = dict[str, Any]


class MongoDBClient:

    __slots__ = (
        'bot',
        'uri',
        'client',
        'database',
        '__session'
    )

    def __init__(self, bot: CustomBot, uri: str, /) -> None:
        self.bot: CustomBot = bot
        self.uri: str = uri

        try:
            self.client = AsyncIOMotorClient(
                uri,
                tlsCAFile=where(),
                serverSelectionTimeoutMS=3000
            )
        except ConfigurationError as error:
            _logger.fatal(error)
            _logger.fatal('Invalid Mongo connection URI provided. Please check your config.py file is correct.')
            raise SystemExit()

        self.database: AsyncIOMotorDatabase = self.client.database

        self.__session: AsyncIOMotorClientSession | None = None

    async def __aenter__(self) -> Self:
        try:
            self.__session = await self.client.start_session()
        except ServerSelectionTimeoutError as error:
            _logger.fatal(error)
            _logger.fatal('Failed to connect to MongoDB. Please check your config.py file is correct.')
            raise SystemExit()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None
    ) -> None:
        await self.__session.end_session()

    async def get_metadata(self) -> MetaData:
        collection: AsyncIOMotorCollection = self.database.metadata
        data: Dict | None = await collection.find_one({}, session=self.__session)

        if data is None:
            data = {
                'logging_channel_id': None,
                'general_channel_id': None,

                'admin_role_id': None,
                'bot_role_id': None,
                'senior_role_id': None,
                'hmod_role_id': None,
                'smod_role_id': None,
                'rmod_role_id': None,
                'tmod_role_id': None,
                'helper_role_id': None,
                'active_role_id': None,

                'domain_bl': [],
                'domain_wl': [],

                'event_ignored_role_ids': [],
                'automod_ignored_role_ids': [],
                'event_ignored_channel_ids': [],
                'automod_ignored_channel_ids': [],

                'activity': None,
                'greeting': None,
                'appeal_url': None
            }
            await collection.insert_one(data, session=self.__session)

        data.pop('_id', None)
        return MetaData(bot=self.bot, **data)

    async def update_metadata(self, **kwargs) -> None:
        collection: AsyncIOMotorCollection = self.database.metadata
        data: Dict = await collection.find_one_and_update(
            {},
            {'$set': kwargs},
            return_document=ReturnDocument.AFTER,
            session=self.__session
        )
        data.pop('_id', None)
        self.bot.metadata = MetaData(bot=self.bot, **data)
