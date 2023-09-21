# Copyright (C) 2022-2023 Indoc Systems
#
# Licensed under the GNU AFFERO GENERAL PUBLIC LICENSE, Version 3.0 (the "License") available at https://www.gnu.org/licenses/agpl-3.0.en.html.
# You may not use this file except in compliance with the License.

import httpx
from common import LoggerFactory

from app.commons.data_providers.redis import SrvAioRedisSingleton
from app.commons.kafka_producer import get_kafka_producer
from app.config import ConfigClass

logger = LoggerFactory(
    'health_check_api',
    level_default=ConfigClass.LEVEL_DEFAULT,
    level_file=ConfigClass.LEVEL_FILE,
    level_stdout=ConfigClass.LEVEL_STDOUT,
    level_stderr=ConfigClass.LEVEL_STDERR,
).get_logger()


async def check_redis() -> dict:
    """
    Summary:
        the function is to check if redis is available by `ping()`
        if cannot connect to redis, the function will return error
        otherwise will return online
    Return:
        - {"Redis": status}
    """

    try:
        redis_client = SrvAioRedisSingleton()
        if await redis_client.ping():
            logger.info('Redis is connected')
            return True
        else:
            logger.error('Redis is not connected')
            return False
    except Exception as e:
        logger.error(f'Fail with error: {e}')
        return False


async def check_minio() -> bool:
    """
    Summary:
        the function is to check if minio is available.
        it uses the minio health check endpoint for cluster.
        For more infomation, check document:
        https://github.com/minio/minio/blob/master/docs/metrics/healthcheck/README.md
    Return:
        - {"Minio": status}
    """

    http_protocal = 'https://' if ConfigClass.S3_INTERNAL_HTTPS else 'http://'
    url = http_protocal + ConfigClass.S3_INTERNAL + '/minio/health/cluster'

    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(url)

            if res.status_code != 200:
                logger.error('Cluster unavailable')
                return False

            logger.info('Minio is connected')
    except Exception as e:
        logger.error(f'Fail with error: {e}')
        return False

    return True


async def check_kafka():
    """
    Summary:
        the function is to check if kafka is available.
        this will just check if we successfully init the
        kafka producer
    Return:
        - {"Kafka": status}
    """

    kafka_connection = await get_kafka_producer()
    if kafka_connection.connected is False:
        logger.error('Kafka is not connected')
        return False

    logger.info('Kafka is connected')
    return True
