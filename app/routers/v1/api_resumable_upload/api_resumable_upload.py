# Copyright (C) 2022-Present Indoc Systems
#
# Licensed under the GNU AFFERO GENERAL PUBLIC LICENSE,
# Version 3.0 (the "License") available at https://www.gnu.org/licenses/agpl-3.0.en.html.
# You may not use this file except in compliance with the License.

import asyncio

from common.object_storage_adaptor.boto3_client import get_boto3_client
from fastapi import APIRouter
from fastapi_utils import cbv

from app.config import ConfigClass
from app.logger import logger
from app.models.base_models import APIResponse
from app.models.models_resumable_upload import ResumableUploadPOST
from app.models.models_resumable_upload import ResumableUploadResponse
from app.routers.exceptions import NotFound
from app.routers.v1.api_resumable_upload.utils import get_chunks_info

router = APIRouter()


@cbv.cbv(router)
class APIResumableUpload:
    """
    Summary:
        this is the api related to resume multipart upload
    """

    def __init__(self):
        self.boto3_client = self._connect_to_object_storage()

    def _connect_to_object_storage(self):
        loop = asyncio.new_event_loop()

        logger.info('Initialize the boto3 client')
        try:
            boto3_client = loop.run_until_complete(
                get_boto3_client(
                    ConfigClass.S3_INTERNAL,
                    access_key=ConfigClass.S3_ACCESS_KEY,
                    secret_key=ConfigClass.S3_SECRET_KEY,
                    https=ConfigClass.S3_INTERNAL_HTTPS,
                )
            )
            boto3_client._config.max_pool_connections = 1000
            logger.warning(f'temporary increase the boto3 connections to {boto3_client._config.max_pool_connections}')

        except Exception:
            logger.exception('Fail to create connection with boto3')
            raise

        loop.close()
        return boto3_client

    @router.post(
        '/files/resumable',
        response_model=ResumableUploadResponse,
        summary='allow user to retrive the uploaded chunk number',
    )
    async def resumable_upload(
        self,
        request_payload: ResumableUploadPOST,
    ):
        """
        Summary:
            The api to retrieve the uploaded parts. afterwards, client
            side will call /v1/chunks and /v1/files to continue upload
        Parameter:
            - bucket(str): the unique code of bucket
            - object_infos(List[ObjectInfo]): the list of pairs contains following:
                - object_path(str): the unique path in object storage
                - resumable_id(str): the unique identifier for resumable upload
        return:
            - result(list):
                - object_path(str): the unique path in object storage
                - resumable_id(str): the unique identifier for resumable upload
                - chunks_info(dict[str: str]): the pair of chunk_number: etag
        """
        api_response = APIResponse()

        try:
            chunk_info = await get_chunks_info(self.boto3_client, request_payload.bucket, request_payload.object_infos)
            api_response.result = chunk_info
        except Exception as e:
            raise NotFound(str(e))

        return api_response.json_response()
