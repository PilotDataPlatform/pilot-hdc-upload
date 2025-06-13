# Copyright (C) 2022-Present Indoc Systems
#
# Licensed under the GNU AFFERO GENERAL PUBLIC LICENSE,
# Version 3.0 (the "License") available at https://www.gnu.org/licenses/agpl-3.0.en.html.
# You may not use this file except in compliance with the License.

from aioredis import StrictRedis

from app.config import ConfigClass
from app.logger import logger

REDIS_INSTANCE = {}


class SrvAioRedisSingleton:
    """we should replace StrictRedis with aioredis https://aioredis.readthedocs.io/en/latest/getting-started/"""

    def __init__(self):
        self.host = ConfigClass.REDIS_HOST
        self.port = ConfigClass.REDIS_PORT
        self.db = ConfigClass.REDIS_DB
        self.pwd = ConfigClass.REDIS_PASSWORD
        self.connect()

    def connect(self):
        global REDIS_INSTANCE
        if REDIS_INSTANCE:
            self.__instance = REDIS_INSTANCE
            pass
        else:

            REDIS_INSTANCE = StrictRedis(host=self.host, port=self.port, db=self.db, password=self.pwd)
            self.__instance = REDIS_INSTANCE
            logger.info('[SUCCEED] SrvAioRedisSingleton Connection initialized.')

    async def ping(self):
        return await self.__instance.ping()

    async def get_pipeline(self):
        return await self.__instance.pipeline()

    async def get_by_key(self, key: str):
        return await self.__instance.get(key)

    async def set_by_key(self, key: str, content: str, expire_time: int = 86400):
        return await self.__instance.set(key, content, ex=expire_time)

    async def mget_by_prefix(self, prefix: str):
        query = f'{prefix}:*'
        keys = await self.__instance.keys(query)
        return await self.__instance.mget(keys)

    async def check_by_key(self, key: str):
        return await self.__instance.exists(key)

    async def delete_by_key(self, key: str):
        return await self.__instance.delete(key)

    async def mdelete_by_prefix(self, prefix: str):
        logger.debug(prefix)
        query = f'{prefix}:*'
        keys = await self.__instance.keys(query)
        for key in keys:
            await self.__instance.delete(key)
