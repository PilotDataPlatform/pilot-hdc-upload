# Copyright (C) 2022-2023 Indoc Systems
#
# Licensed under the GNU AFFERO GENERAL PUBLIC LICENSE, Version 3.0 (the "License") available at https://www.gnu.org/licenses/agpl-3.0.en.html.
# You may not use this file except in compliance with the License.

from common import LoggerFactory
from fastapi import APIRouter
from fastapi import Depends
from fastapi import Request
from fastapi.responses import Response

from app.commons.kafka_producer import get_kafka_producer
from app.config import ConfigClass
from app.resources.health_check import check_kafka
from app.resources.health_check import check_minio
from app.resources.health_check import check_redis

router = APIRouter()


@router.get('/')
async def root(request: Request):
    """Healthcheck route."""

    logger = LoggerFactory('test_logger').get_logger()
    logger.warning(request.__dict__)

    return {
        'status': 'OK',
        'name': ConfigClass.APP_NAME,
        'version': ConfigClass.VERSION,
    }


@router.on_event('shutdown')
async def shutdown_event():
    """
    Summary:
        the shutdown event to gracefully close the
        kafka producer.
    """

    kp = await get_kafka_producer()
    await kp.close_connection()

    return


@router.get('/v1/health', summary='Health check for RDS, Redis and Kafka')
async def check_db_connection(
    check_kafka: bool = Depends(check_kafka),
    check_minio: bool = Depends(check_minio),
    check_redis: bool = Depends(check_redis),
) -> Response:
    if check_kafka and check_redis and check_minio:
        return Response(status_code=204)
    return Response(status_code=503)
