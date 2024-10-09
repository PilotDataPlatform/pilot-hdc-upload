# Copyright (C) 2022-Present Indoc Systems
#
# Licensed under the GNU AFFERO GENERAL PUBLIC LICENSE,
# Version 3.0 (the "License") available at https://www.gnu.org/licenses/agpl-3.0.en.html.
# You may not use this file except in compliance with the License.

import asyncio
import json
import os
import shutil
import time
import unicodedata as ud
from typing import Optional
from uuid import uuid4

import httpx
from common import ProjectClient
from common import ProjectNotFoundException
from common.object_storage_adaptor.boto3_client import TokenError
from common.object_storage_adaptor.boto3_client import get_boto3_client
from fastapi import APIRouter
from fastapi import BackgroundTasks
from fastapi import File
from fastapi import Form
from fastapi import Header
from fastapi import UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi_utils import cbv

from app.commons.data_providers.redis_project_session_job import EFileStatus
from app.commons.data_providers.redis_project_session_job import SessionJob
from app.commons.data_providers.redis_project_session_job import get_fsm_object
from app.commons.kafka_producer import get_kafka_producer
from app.config import ConfigClass
from app.logger import logger
from app.models.base_models import APIResponse
from app.models.base_models import EAPIResponseCode
from app.models.folder import FolderMgr
from app.models.models_item import ItemStatus
from app.models.models_upload import ChunkUploadResponse
from app.models.models_upload import EUploadJobType
from app.models.models_upload import OnSuccessUploadPOST
from app.models.models_upload import POSTCombineChunksResponse
from app.models.models_upload import PreUploadPOST
from app.models.models_upload import PreUploadResponse
from app.resources.archive_file_type_mapping import ARCHIVE_TYPES
from app.resources.decorator import header_enforcement
from app.resources.error_handler import ECustomizedError
from app.resources.error_handler import catch_internal
from app.resources.error_handler import customized_error_template
from app.resources.helpers import generate_archive_preview

from .exceptions import InvalidPayload
from .exceptions import ResourceAlreadyExist

router = APIRouter()

_API_TAG = 'V1 Upload'
_API_NAMESPACE = 'api_data_upload'
_JOB_TYPE = 'data_upload'


@cbv.cbv(router)
class APIUpload:
    """
    Summary:
        Upload workflow will involve three api *in a row*. They are following:
            - Pre upload api
            - Chunk upload api
            - Combine chunks api
        The upload process in both frontend/command line tool will follow this
        workflow:
            1. before the upload, call the pre upload api to do the name check
            2. then each file will be chunked up into 2MB(current setting),
                then each chunk will upload to server one by one with chunk
                upload api.
            3. finally, if the client side detect it uploaded ALL chunks, it will
                signal out the combine chunks api to backend. The backend will
                start a background job to process chunks and meta.
        The detail description of EACH api will be shown underneath
    Special Note:
        The file and folder cannot with same name
    """

    def __init__(self):
        self.project_client = ProjectClient(ConfigClass.PROJECT_SERVICE, ConfigClass.REDIS_URL)
        self.boto3_client, self.boto3_client_public = self._connect_to_object_storage()

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

            boto3_client_public = loop.run_until_complete(
                get_boto3_client(
                    ConfigClass.S3_PUBLIC,
                    access_key=ConfigClass.S3_ACCESS_KEY,
                    secret_key=ConfigClass.S3_SECRET_KEY,
                    https=ConfigClass.S3_PUBLIC_HTTPS,
                )
            )

        except Exception:
            logger.exception('Fail to create connection with boto3')
            raise

        loop.close()
        return boto3_client, boto3_client_public

    @router.post(
        '/files/jobs',
        tags=[_API_TAG],
        response_model=PreUploadResponse,
        summary='Always would be called first when upload, \
                 Init an async upload job, returns list of job identifier.',
    )
    @catch_internal(_API_NAMESPACE)
    @header_enforcement(['session_id'])
    async def upload_pre(  # noqa: C901
        self,
        request_payload: PreUploadPOST,
        session_id=Header(None),
        Authorization: Optional[str] = Header(None),
    ):
        """
        Summary:
            This is the first api the client side will call before upload
            Its allow to create an async upload job(s) for all upload files.
            It will make following checks for uploaded file(s):
                1. check if project exist
                2. check if the root folder is duplicate
                3. normalize the filename with different client(firefox/chrome)
                4. initialize the job for ALL upload files
                5. lock all file/node will be
        Header:
            - session_id(string): The unique session id from client side
        Payload:
            - project_code(string): the target project will upload to
            - operator(string): the name of operator
            - job_type(str): either can be file upload or folder upload
            - data(SingleFileForm):
                - resumable_filename(string): the name of file
                - resumable_relative_path: the relative path of the file
            - upload_message(string):
            - current_folder_node(string): the root level folder that will be
                uploaded
            - incremental(integer):
        Special Note:
            the folder upload & file upload has different payload structure.
            When the file upload, the current_folder_node will be '' (empty string)
            When the folder uplaod, the current_folder_node will be the root folder
        Return:
            - 200, job list
        """

        _res = APIResponse()
        project_code = request_payload.project_code
        namespace = ConfigClass.namespace

        logger.info('Upload Job start')
        if not (
            request_payload.job_type == EUploadJobType.AS_FILE.name
            or request_payload.job_type == EUploadJobType.AS_FOLDER.name
        ):
            _res.code = EAPIResponseCode.bad_request
            _res.error_msg = 'Invalid job type: {}'.format(request_payload.job_type)
            return _res.json_response()

        try:
            _ = await self.project_client.get(code=request_payload.project_code)

            for upload_data in request_payload.data:
                upload_data.resumable_filename = ud.normalize('NFC', upload_data.resumable_filename)
            status_mgr = await get_fsm_object(
                session_id,
                project_code,
                request_payload.operator,
            )

            bucket = ('gr-' if namespace == 'greenroom' else 'core-') + project_code
            file_keys = [os.path.join(x.resumable_relative_path, x.resumable_filename) for x in request_payload.data]
            upload_ids = await self.boto3_client.prepare_multipart_upload(bucket, file_keys)

            job_list = []
            to_create_items, item_list = [], []
            for file_key, upload_id in zip(file_keys, upload_ids):

                file_path, file_name = file_key.rsplit('/', 1)
                items_info, file_info = await folder_creation(
                    project_code,
                    request_payload.operator,
                    request_payload.current_folder_node,
                    request_payload.parent_folder_id,
                    file_path,
                    file_name,
                    request_payload.job_type,
                    upload_id,
                )
                to_create_items.extend(items_info)
                item_list.append(file_info)

            url = ConfigClass.METADATA_SERVICE + 'items/batch/'
            async with httpx.AsyncClient() as client:
                item_res = await client.post(url, json={'items': to_create_items}, timeout=10)
                if item_res.status_code == 409:
                    raise ResourceAlreadyExist(f'The resource already exist: {item_res.text}')
                elif item_res.status_code != 200:
                    raise Exception('Fail to create metadata %s in postgres: %s' % (to_create_items, item_res.text))

            for item in item_list:
                await status_mgr.set_job_id(str(uuid4()))
                status_mgr.set_source([item.get('parent_path') + '/' + item.get('name')])
                status_mgr.add_payload('resumable_identifier', item.get('upload_id'))

                status_mgr.add_payload('item_id', item.get('id'))
                await status_mgr.set_status(EFileStatus.RUNNING)

                _, _, job_recorded = status_mgr.get_kv_entity()
                job_list.append(job_recorded)

            _res.result = job_list

        except (TokenError, InvalidPayload) as e:
            _res.error_msg = str(e)
            _res.code = EAPIResponseCode.bad_request

        except ProjectNotFoundException as e:
            _res.error_msg = str(e)
            _res.code = EAPIResponseCode.not_found

        except ResourceAlreadyExist as e:
            _res.error_msg = str(e)
            _res.code = EAPIResponseCode.conflict

        except Exception as e:
            _res.error_msg = 'Error when pre uploading ' + str(e)
            _res.code = EAPIResponseCode.internal_error

        return _res.json_response()

    @router.post('/files/chunks', tags=[_API_TAG], response_model=ChunkUploadResponse, summary='upload chunks process.')
    @catch_internal(_API_NAMESPACE)
    @header_enforcement(['session_id'])
    async def upload_chunks(
        self,
        project_code: str = Form(...),
        operator: str = Form(...),
        resumable_identifier: str = Form(...),
        resumable_filename: str = Form(...),
        resumable_relative_path: str = Form(''),
        resumable_chunk_number: int = Form(...),
        session_id: str = Header(None),
        chunk_data: UploadFile = File(...),
    ):
        """
        Summary:
            The second api that the client side will call during the file
             upload. The data is uploaded throught the <Multipart Upload>.
            The api will create the temp folder if it does not exist. Then
             the chunk_data will be saved into the temp folder.
        Header:
            - session_id(string): The unique session id from client side
        Form:
            - project_code(string): the target project will upload to
            - operator(string): the name of operator
            - resumable_filename(string): the name of file
            - resumable_relative_path(string): the relative path of the file
            - resumable_identifier(string): The job identifier for each file
            - resumable_chunk_number(string): The integer id for each chunk
        Return:
            - 200, Succeed
        """

        _res = APIResponse()

        resumable_filename = ud.normalize('NFC', resumable_filename)
        file_key = resumable_relative_path + '/' + resumable_filename

        logger.info('Uploading file %s chunk %s', resumable_filename, resumable_chunk_number)
        try:
            bucket = ('gr-' if ConfigClass.namespace == 'greenroom' else 'core-') + project_code

            logger.info('Start to read the chunks')
            file_content = await chunk_data.read()
            logger.info('Chunk size is %s', len(file_content))
            etag_info = await self.boto3_client.part_upload(
                bucket, file_key, resumable_identifier, resumable_chunk_number, file_content
            )

            logger.info('finish the chunk upload: %s', json.dumps(etag_info))

            _res.code = EAPIResponseCode.success
            _res.result = {'msg': 'Succeed'}
        except Exception as e:
            error_message = str(e)
            logger.error('Fail to upload chunks: %s', error_message)

            status_mgr = await get_fsm_object(
                session_id,
                project_code,
                operator,
                resumable_identifier,
            )
            status_mgr.add_payload('error_msg', str(e))
            await status_mgr.set_status(EFileStatus.FAILED)

            _res.code = EAPIResponseCode.internal_error
            _res.error_msg = error_message

        return _res.json_response()

    @router.get(
        '/files/chunks/presigned', tags=[_API_TAG], response_model=ChunkUploadResponse, summary='upload chunks process.'
    )
    @catch_internal(_API_NAMESPACE)
    async def generate_presigned_url_chunks(self, bucket: str, key: str, upload_id: str, chunk_number: int):
        """
        Summary:
            The second api that the client side will call during the file
             upload. I will return presigned upload url for EACH chunk. Then
             client side will upload content throught it direcly into minio
        Parameter:
            - bucket(string): the unique bucket name
            - key(string): the path of object
            - upload_id(string): The job identifier for each file
            - chunk_number(string): The integer id for each chunk
        Return:
            - 200, presigned url(str)
        """

        res = APIResponse()

        try:
            presigned_url = await self.boto3_client_public.generate_presigned_url(bucket, key, upload_id, chunk_number)

            res.code = EAPIResponseCode.success
            res.result = presigned_url
        except Exception as e:
            error_message = str(e)
            logger.error('Fail to generate presigned url for chunks: %s', error_message)
            res.code = EAPIResponseCode.internal_error
            res.error_msg = error_message

        return res.json_response()

    @router.post(
        '/files',
        tags=[_API_TAG],
        response_model=POSTCombineChunksResponse,
        summary='create a background worker to combine chunks, transfer file to the destination namespace',
    )
    @catch_internal(_API_NAMESPACE)
    @header_enforcement(['session_id'])
    async def on_success(
        self,
        request_payload: OnSuccessUploadPOST,
        background_tasks: BackgroundTasks,
        session_id: str = Header(None),
        Authorization: Optional[str] = Header(None),
        refresh_token: Optional[str] = Header(None),
    ):
        """
        Summary:
            The third api will be called by client side. The client send
            the acknoledgement for all chunks uploaded by signaling this
            api. Once the upload service recieve the api calling, it will
            start a background job to combine the chunks and process the
            metadata
        Form:
            - project_code(string): the target project will upload to
            - operator(string): the name of operator
            - resumable_filename(string): the name of file
            - resumable_relative_path(string): the relative path of the file
            - resumable_identifier(string): The job identifier for each file
            - resumable_total_chunks(string): The number of total chunks
            - resumable_total_size(float): the file size
            - process_pipeline(string optional): default is None  # cli
            - from_parents(list optional): default is None  # cli
            - upload_message(string optional): default is ''  # cli
        Return:
            - 200, Succeed
        """

        _res = APIResponse()

        logger.info(f'resumable_filename: {request_payload.resumable_filename}')
        request_payload.resumable_filename = ud.normalize('NFC', request_payload.resumable_filename)

        status_mgr = await get_fsm_object(
            session_id,
            request_payload.project_code,
            request_payload.operator,
            request_payload.job_id,
        )
        obj_path = await run_in_threadpool(
            os.path.join, request_payload.resumable_relative_path, request_payload.resumable_filename
        )
        status_mgr.set_source([obj_path])

        background_tasks.add_task(
            finalize_worker,
            logger,
            request_payload,
            status_mgr,
            self.boto3_client,
        )

        logger.info('finalize_worker started')
        job_recorded = await status_mgr.set_status(EFileStatus.CHUNK_UPLOADED)
        _res.code = EAPIResponseCode.success
        _res.result = job_recorded
        return _res.json_response()


async def folder_creation(
    project_code: str,
    operator: str,
    current_folder: str,
    parent_folder_id: str,
    file_path: str,
    file_name: str,
    job_type: str,
    upload_id: str,
):  # noqa: C901
    """
    Summary:
        The function will batch create the tree path based on file_path.
        For example, if the file_path is /A/B/C that folder B and C
        do not exist, then function will batch create them
    Parameters:
        - project_code(string): the target project will upload to
        - operator(string): the name of operator
        - file_path(string): the relative path of the file(without ending
            slash)
        - file_name: the name of tile
        - job_type: AS_FOLDER or AS_FILE
        - upload_id: the unique id for each upload
    Return:
        - The last node in the tree path. In the above example, the function
            will return folder node C
    """

    folder_create_duration = 0

    folder_create_start_time = time.time()
    folder_mgr = FolderMgr(
        project_code,
        file_path,
    )

    to_create_items = []
    last_node_id = parent_folder_id
    if job_type == 'AS_FOLDER':
        await folder_mgr.create(operator, current_folder, parent_folder_id)
        to_create_items = folder_mgr.to_create
        last_node_id = folder_mgr.last_node.global_entity_id

    folder_create_duration += time.time() - folder_create_start_time

    logger.info(f'Save to Cache Folder Time: {folder_create_duration}')

    batch_folder_create_start_time = time.time()
    try:

        data = {
            'id': str(uuid4()),
            'parent': last_node_id,
            'parent_path': file_path,
            'type': 'file',
            'status': ItemStatus.REGISTERED,
            'zone': {'greenroom': 0}.get(ConfigClass.namespace, 1),
            'name': file_name,
            'owner': operator,
            'container_code': project_code,
            'container_type': 'project',
            'upload_id': upload_id,
        }
        to_create_items.append(data)

        logger.info(f'New Folders saved: {len(to_create_items)}')
        logger.info(f'New Node Creation Time: {time.time() - batch_folder_create_start_time}')

    except Exception:
        logger.exception('Error when create the folder tree')
        raise

    logger.info('[SUCCEED] Done')

    return to_create_items, data


async def finalize_worker(
    logger,
    request_payload: OnSuccessUploadPOST,
    status_mgr: SessionJob,
    boto3_client,
):
    """
    Summary:
        The function is the background job to combine chunks and process the
        metadata. The metadata process including following:
            - lock the target file node.
            - create the folder tree if the folder structure does not exist.
            - combine chunks and upload to minio.
            - calling the dataops utility api to create postgres/es/atlas record.
            - calling the provenence service to create activity log of file.
            - calling the dataops utiltiy api to add the zip preview if upload
                zip file.
            - update the job status.
            - remove the temperary folder
            - unlock the file node
    Parameter:
        - request_payload(OnSuccessUploadPOST)
            - project_code(string): the target project will upload to
            - operator(string): the name of operator
            - resumable_filename(string): the name of file
            - resumable_relative_path(string): the relative path of the file
            - resumable_identifier(string): The job identifier for each file
            - resumable_total_chunks(string): The number of total chunks
            - resumable_total_size(float): the file size
            - process_pipeline(string optional): default is None  # cli
            - from_parents(list optional): default is None  # cli
            - upload_message(string optional): default is ''  # cli
        - status_mgr(SessionJob): the object manage the job status
        - access_token(str): the token for user to upload into minio
        - refresh_token(str): the token to refresh the access
    Return:
        - None
    """
    start_time = time.time()

    namespace = ConfigClass.namespace
    project_code = request_payload.project_code
    file_path = request_payload.resumable_relative_path
    file_name = request_payload.resumable_filename
    operator = request_payload.operator
    resumable_identifier = request_payload.resumable_identifier
    bucket = ('gr-' if namespace == 'greenroom' else 'core-') + project_code
    obj_path = await run_in_threadpool(os.path.join, file_path, file_name)

    temp_dir = await run_in_threadpool(os.path.join, ConfigClass.TEMP_BASE, resumable_identifier)

    pre_time = time.time()
    logger.warning(f'prepare time is {pre_time - start_time}')

    try:

        logger.info('Start to create folder trees')

        s3_parts_info = await boto3_client.list_chunks(bucket, obj_path, resumable_identifier)
        chunks_info = [
            {'PartNumber': x.get('PartNumber'), 'ETag': x.get('ETag').replace("\"", '')}
            for x in s3_parts_info.get('Parts', [])
        ]

        for retry_count in range(0, 3):
            if len(chunks_info) != request_payload.resumable_total_chunks:
                await asyncio.sleep(1 * retry_count)
            else:
                break

        result = await boto3_client.combine_chunks(bucket, obj_path, resumable_identifier, chunks_info)
        version_id = result.get('VersionId', '')

        logger.info('start to create item in metadata service')
        item_id = request_payload.item_id
        data = {
            'status': ItemStatus.ACTIVE,
            'size': request_payload.resumable_total_size,
            'location_uri': 'minio://%s/%s/%s' % (ConfigClass.S3_INTERNAL, bucket, obj_path),
            'version': version_id,
            'tags': request_payload.tags,
        }

        async with httpx.AsyncClient() as client:
            response = await client.put(
                ConfigClass.METADATA_SERVICE + 'item/', params={'id': item_id}, json=data, timeout=10
            )
            if response.status_code != 200:
                raise Exception('Fail to create metadata in postgres: %s' % (response.__dict__))

        created_entity = response.json().get('result')
        file_id = item_id

        file_type = await run_in_threadpool(os.path.splitext, file_name)
        archive_type = ARCHIVE_TYPES.get(file_type[1].lstrip('.'), False)

        if archive_type:
            logger.info('Start to create archvie preview')
            await boto3_client.download_object(bucket, obj_path, temp_dir + '/' + obj_path)

            archive_preview = await generate_archive_preview(temp_dir + '/' + obj_path, archive_type)
            payload = {
                'archive_preview': archive_preview,
                'file_id': file_id,
            }
            async with httpx.AsyncClient() as client:
                await client.post(ConfigClass.DATAOPS_SERVICE + 'archive', json=payload, timeout=3600)

        obj_path = (
            (ConfigClass.GREEN_ZONE_LABEL if namespace == 'greenroom' else ConfigClass.CORE_ZONE_LABEL) + '/' + obj_path
        )

        kp = await get_kafka_producer()
        await kp.create_activity_log(
            created_entity, 'metadata_items_activity.avsc', operator, ConfigClass.KAFKA_ACTIVITY_TOPIC
        )

        status_mgr.add_payload('source_geid', created_entity.get('id'))
        await status_mgr.set_status(EFileStatus.SUCCEED)
        logger.info('Upload Job Done.')

    except FileNotFoundError as e:
        error_msg = 'folder {} is already empty: {}'.format(temp_dir, str(e))
        logger.error(error_msg)
        status_mgr.add_payload('error_msg', str(error_msg))
        await status_mgr.set_status(EFileStatus.FAILED)

    except Exception as exce:
        logger.error(f'Fail with error: {exce}')
        status_mgr.add_payload('error_msg', str(exce))
        await status_mgr.set_status(EFileStatus.FAILED)
        raise exce

    finally:
        if os.path.isdir(temp_dir):
            shutil.rmtree(temp_dir)


async def get_conflict_folder_paths(project_code: str, current_folder_node: str):
    """
    Summary:
        The function will check and return conflict folder paths for
        folder upload only.
    Parameter:
       project_code(string): The unique code of target project
       current_folder_node(string): the root folder name
    Return:
        list of dict
            - display_path(string): the path of conflict folder
            - type(string): Folder
    """
    namespace = ConfigClass.namespace

    conflict_folder_paths = []
    file_path, file_name = current_folder_node.rsplit('/', 1)
    params = {
        'parent_path': file_path,
        'name': file_name,
        'container_code': project_code,
        'status': ItemStatus.ACTIVE,
        'zone': 0 if namespace == 'greenroom' else 1,
        'recursive': False,
    }
    # also check if it is in greeroom or core
    node_query_url = ConfigClass.METADATA_SERVICE + 'items/search/'
    async with httpx.AsyncClient() as client:
        response = await client.get(node_query_url, params=params)
    nodes = response.json().get('result', [])

    if len(nodes) > 0:
        conflict_folder_paths.append({'display_path': current_folder_node, 'type': 'Folder'})

    return conflict_folder_paths


async def get_conflict_file_paths(data, project_code):
    """
    Summary:
        The function will check and return conflict file paths for
        file upload only.
    Parameter:
        data(list of dict):
            - resumable_filename(string): the name of file
            - resumable_relative_path: the relative path of the file
        project_code(string): The unique code of target project
    Return:
        list of dict
            - display_path(string): the path of conflict file
            - type(string): File
    """
    namespace = ConfigClass.namespace
    conflict_file_paths = []
    for upload_data in data:
        params = {
            'parent_path': upload_data.resumable_relative_path,
            'name': upload_data.resumable_filename,
            'container_code': project_code,
            'status': ItemStatus.ACTIVE,
            'zone': 0 if namespace == 'greenroom' else 1,
            'recursive': False,
        }

        # search upto the new metadata service if the input files
        node_query_url = ConfigClass.METADATA_SERVICE + 'items/search/'
        async with httpx.AsyncClient() as client:
            response = await client.get(node_query_url, params=params)
        nodes = response.json().get('result', [])

        if len(nodes) > 0:
            conflict_file_paths.append(
                {
                    'name': upload_data.resumable_filename,
                    'relative_path': upload_data.resumable_relative_path,
                    'type': 'File',
                }
            )

    return conflict_file_paths


def response_conflic_folder_file_names(_res, conflict_file_paths, conflict_folder_paths):
    """set conflict response when filename or folder name conflics."""
    if len(conflict_file_paths) > 0:
        _res.code = EAPIResponseCode.conflict
        _res.error_msg = customized_error_template(ECustomizedError.INVALID_FILENAME)
        _res.result = {'failed': conflict_file_paths}
        return _res.json_response()
    if len(conflict_folder_paths) > 0:
        _res.code = EAPIResponseCode.conflict
        _res.error_msg = customized_error_template(ECustomizedError.INVALID_FOLDERNAME)
        _res.result = {'failed': conflict_folder_paths}
        return _res.json_response()
