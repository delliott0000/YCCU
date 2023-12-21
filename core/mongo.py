from __future__ import annotations
from typing import TYPE_CHECKING

from logging import getLogger
from datetime import timedelta

from core.metadata import MetaData
from core.modlog import Modlog
from core.errors import ModlogNotFound

from certifi import where
from pymongo import ReturnDocument, DESCENDING
from pymongo.errors import ConfigurationError, ServerSelectionTimeoutError
from motor.motor_asyncio import AsyncIOMotorClient

if TYPE_CHECKING:
    from typing import Self, Any
    from types import TracebackType

    from core.bot import CustomBot

    from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection, AsyncIOMotorClientSession

    Dict = dict[str, Any]


_logger = getLogger(__name__)


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

    def prep_modlog_data(self, data: Dict) -> None:
        data['created'] = self.bot.dt_from_timestamp(data['created'])
        data['duration'] = timedelta(seconds=data['duration'])
        data.pop('_id', None)

    async def get_metadata(self) -> MetaData:
        collection: AsyncIOMotorCollection = self.database.meta_data
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

    async def update_metadata(self, **kwargs: Any) -> None:
        collection: AsyncIOMotorCollection = self.database.meta_data
        data: Dict = await collection.find_one_and_update(
            {},
            {'$set': kwargs},
            return_document=ReturnDocument.AFTER,
            session=self.__session
        )
        data.pop('_id', None)
        self.bot.metadata = MetaData(bot=self.bot, **data)

    async def generate_modlog_id(self) -> int:
        collection: AsyncIOMotorCollection = self.database.modlogs
        most_recent_modlog: Dict | None = await collection.find_one(
            sort=[('case_id', DESCENDING)],
            session=self.__session
        )
        return most_recent_modlog.get('case_id') + 1 if most_recent_modlog is not None else 1

    async def insert_modlog(self, modlog: Modlog, /) -> None:
        collection: AsyncIOMotorCollection = self.database.modlogs
        await collection.insert_one(
            {
                'case_id': modlog.case_id,
                'user_id': modlog.user_id,
                'mod_id': modlog.mod_id,
                'channel_id': modlog.channel_id,
                'type': modlog.type,
                'reason': modlog.reason,
                'created': round(modlog.created.timestamp()),
                'duration': modlog.duration.total_seconds(),
                'received': modlog.received,
                'deleted': modlog.deleted,
                'active': modlog.active
            },
            session=self.__session
        )
        _logger.info(f'New Modlog entry created - Case ID: {modlog.case_id}')

    async def update_modlog(self, **kwargs: Any) -> Modlog:
        # Kwargs with leading underscores are our search parameters
        # Kwargs without leading underscores are our values to update
        search_dict = {}
        update_dict = {}

        for key, value in kwargs.items():
            if key.startswith('_'):
                search_dict[key[1:]] = value
            else:
                update_dict[key] = value

        collection: AsyncIOMotorCollection = self.database.modlogs
        data: Dict | None = await collection.find_one_and_update(
            search_dict,
            {'$set': update_dict},
            return_document=ReturnDocument.AFTER,
            session=self.__session
        )

        if data is None:
            raise ModlogNotFound(**search_dict)

        _logger.info(f'Updated existing modlog entry - Case ID: {data.get("case_id")} - Updated: {update_dict}')

        self.prep_modlog_data(data)
        return Modlog(bot=self.bot, **data)

    async def search_modlog(self, **kwargs: Any) -> list[Modlog]:
        collection: AsyncIOMotorCollection = self.database.modlogs
        modlogs = []

        entry: Dict
        async for entry in collection.find(kwargs, session=self.__session):

            self.prep_modlog_data(entry)
            modlog = Modlog(bot=self.bot, **entry)

            modlogs.append(modlog)

        if not modlogs:
            raise ModlogNotFound(**kwargs)

        return modlogs
