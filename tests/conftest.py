# Copyright (C) 2022-2023 Indoc Systems
#
# Licensed under the GNU AFFERO GENERAL PUBLIC LICENSE, Version 3.0 (the "License") available at https://www.gnu.org/licenses/agpl-3.0.en.html.
# You may not use this file except in compliance with the License.

import asyncio
import json
import os
import shutil
from io import BytesIO
from zipfile import ZipFile

import pytest
from async_asgi_testclient import TestClient as TestAsyncClient
from fastapi.testclient import TestClient
from httpx import Response
from starlette.config import environ
from urllib3 import HTTPResponse

environ['namespace'] = 'dev'
environ['CONFIG_CENTER_ENABLED'] = 'false'
environ['CORE_ZONE_LABEL'] = 'Core'
environ['GREEN_ZONE_LABEL'] = 'Greenroom'

environ['METADATA_SERVICE'] = 'http://METADATA_SERVICE'
environ['DATAOPS_SERVICE'] = 'http://DATAOPS_SERVICE'
environ['PROJECT_SERVICE'] = 'http://PROJECT_SERVICE'

environ['KAFKA_URL'] = 'http://KAFKA_URL'

environ['S3_INTERNAL'] = 'S3_INTERNAL'
environ['S3_INTERNAL_HTTPS'] = 'false'
environ['S3_PUBLIC'] = 'S3_PUBLIC'
environ['S3_PUBLIC_HTTPS'] = 'TRUE'
environ['S3_ACCESS_KEY'] = 'S3_ACCESS_KEY'
environ['S3_SECRET_KEY'] = 'S3_SECRET_KEY'

environ['REDIS_HOST'] = 'localhost'
environ['REDIS_PORT'] = '6379'
environ['REDIS_DB'] = '0'
environ['REDIS_PASSWORD'] = ''

environ['ROOT_PATH'] = 'tests/'

environ['OPEN_TELEMETRY_ENABLED'] = 'false'


@pytest.fixture(scope='session')
def event_loop(request):
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
    asyncio.set_event_loop_policy(None)


@pytest.fixture(autouse=True)
def mock_settings(monkeypatch):
    from app.config import ConfigClass

    monkeypatch.setattr(ConfigClass, 'TEMP_BASE', './tests/')


@pytest.fixture
def test_client():
    from run import app

    return TestClient(app)


@pytest.fixture
def test_async_client():
    from run import app

    return TestAsyncClient(app)


@pytest.fixture()
def create_job_folder():
    folder_path = 'tests/fake_global_entity_id'
    os.mkdir(folder_path)
    with open(f'{folder_path}/any.zip_part_001', 'x') as f:
        f.write('Create a new text file!')
    with open(f'{folder_path}/any_part_001', 'x') as f:
        f.write('Create a new text file!')
    with ZipFile(f'{folder_path}/any.zip', 'w') as myzip:
        myzip.write(f'{folder_path}/any.zip_part_001')
    yield
    if os.path.exists(folder_path):
        shutil.rmtree(folder_path)


@pytest.fixture()
async def create_fake_job(monkeypatch):
    from app.commons.data_providers.redis import SrvAioRedisSingleton

    fake_job = {
        'session_id': '1234',
        'job_id': 'fake_global_entity_id',
        'target_names': 'any',
        'action': 'data_upload',
        'status': 'PRE_UPLOADED',
        'project_code': 'any',
        'operator': 'me',
        'progress': 0,
        'payload': {
            'task_id': 'fake_global_entity_id',
            'resumable_identifier': 'fake_global_entity_id',
            'parent_folder_geid': None,
        },
        'update_timestamp': '1643041439',
    }

    async def fake_return(x, y):
        return [bytes(json.dumps(fake_job), 'utf-8')]

    monkeypatch.setattr(SrvAioRedisSingleton, 'mget_by_prefix', fake_return)

    fake_credentials = {
        'AccessKeyId': 'AccessKeyId',
        'SecretAccessKey': 'SecretAccessKey',
        'SessionToken': 'SessionToken',
    }

    async def fake_return_c(x, y):
        return bytes(json.dumps(fake_credentials), 'utf-8')

    monkeypatch.setattr(SrvAioRedisSingleton, 'get_by_key', fake_return_c)


@pytest.fixture()
def mock_boto3(monkeypatch):
    from common.object_storage_adaptor.boto3_client import Boto3Client

    class FakeObject:
        size = b'a'

    http_response = HTTPResponse()
    response = Response(status_code=200, json={})
    response.raw = http_response
    response.raw._fp = BytesIO(b'File like object')

    async def fake_init_connection():
        pass

    async def fake_prepare_multipart_upload(x, y, z):
        return 'fake_upload_id'

    async def fake_part_upload(x, y, z, z1, z2, z3):
        pass

    async def fake_combine_chunks(x, y, z, z1, z2):
        return {'VersionId': 'fake_version'}

    async def fake_download_object(x, y, z, z1):
        return response

    async def fake_list_chunks(x, y, z, z1):
        return {'Parts': []}

    monkeypatch.setattr(Boto3Client, 'init_connection', lambda x: fake_init_connection())
    monkeypatch.setattr(Boto3Client, 'prepare_multipart_upload', lambda x, y, z: fake_prepare_multipart_upload(x, y, z))
    monkeypatch.setattr(Boto3Client, 'part_upload', lambda x, y, z, z1, z2, z3: fake_part_upload(x, y, z, z1, z2, z3))
    monkeypatch.setattr(Boto3Client, 'combine_chunks', lambda x, y, z, z1, z2: fake_combine_chunks(x, y, z, z1, z2))
    monkeypatch.setattr(Boto3Client, 'download_object', lambda x, y, z, z1: fake_download_object(x, y, z, z1))
    monkeypatch.setattr(Boto3Client, 'list_chunks', lambda x, y, z, z1: fake_list_chunks(x, y, z, z1))


@pytest.fixture
def mock_kafka_producer(monkeypatch):
    from app.commons.kafka_producer import KakfaProducer

    async def fake_init_connection():
        pass

    async def fake_send_message(x, y, z):
        pass

    async def fake_validate_message(x, y, z):
        pass

    async def fake_create_activity_log(x, y, z, z1, z2):
        pass

    monkeypatch.setattr(KakfaProducer, 'init_connection', lambda x: fake_init_connection())
    monkeypatch.setattr(KakfaProducer, '_send_message', lambda x, y, z: fake_send_message(x, y, z))
    monkeypatch.setattr(KakfaProducer, '_validate_message', lambda x, y, z: fake_validate_message(x, y, z))
    monkeypatch.setattr(
        KakfaProducer, 'create_activity_log', lambda x, y, z, z1, z2: fake_create_activity_log(x, y, z, z1, z2)
    )


@pytest.fixture
def mock_redis(monkeypatch):
    from app.commons.data_providers.redis import SrvAioRedisSingleton

    async def fake_set(x, y):
        pass

    async def fake_get(x):
        return {}

    monkeypatch.setattr(SrvAioRedisSingleton, 'set_by_key', lambda x, y, z: fake_set(y, z))
    monkeypatch.setattr(SrvAioRedisSingleton, 'get_by_key', lambda x, y: fake_get(y))
