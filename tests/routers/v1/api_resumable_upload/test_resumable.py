# Copyright (C) 2022-Present Indoc Systems
#
# Licensed under the GNU AFFERO GENERAL PUBLIC LICENSE,
# Version 3.0 (the "License") available at https://www.gnu.org/licenses/agpl-3.0.en.html.
# You may not use this file except in compliance with the License.

import botocore.exceptions
from common.object_storage_adaptor.boto3_client import Boto3Client

from app.models.models_resumable_upload import ObjectInfo
from app.routers.exceptions import NotFound
from app.routers.v1.api_resumable_upload.utils import get_chunks_info


async def test_resumable_success_return_200(test_async_client, mocker):
    mocker.patch('app.routers.v1.api_resumable_upload.api_resumable_upload.get_chunks_info', return_value=['test'])
    response = await test_async_client.post(
        '/v1/files/resumable',
        json={'bucket': 'test', 'object_infos': [{'object_path': 'test', 'resumable_id': 'test'}]},
    )
    assert response.status_code == 200
    assert response.json() == {
        'code': 200,
        'error_msg': '',
        'page': 0,
        'total': 1,
        'num_of_pages': 1,
        'result': ['test'],
    }


async def test_resumable_success_return_400(test_async_client, mocker):
    m = mocker.patch('app.routers.v1.api_resumable_upload.api_resumable_upload.get_chunks_info', return_value=['test'])
    m.side_effect = Exception

    try:
        await test_async_client.post(
            '/v1/files/resumable',
            json={'bucket': 'test', 'object_infos': [{'object_path': 'test', 'resumable_id': 'test'}]},
        )
    except NotFound:
        pass
    except Exception:
        AssertionError()


async def test_get_chunks_info_skips_chunks_that_do_not_exist(mocker, fake):
    object_infos = [
        ObjectInfo(object_path=fake.file_path(depth=3), resumable_id=fake.pystr(min_chars=50, max_chars=50))
        for _ in range(2)
    ]

    boto3_client = Boto3Client('', '', '')
    boto3_client.list_chunks = mocker.AsyncMock(
        side_effect=[{'Parts': []}, botocore.exceptions.ClientError({'Error': {'Code': 'NoSuchUpload'}}, 'ListParts')]
    )

    chunks_info = await get_chunks_info(boto3_client, 'test-bucket', object_infos)

    assert len(chunks_info) == 1
    assert chunks_info[0]['object_path'] == object_infos[0].object_path
    assert chunks_info[0]['resumable_id'] == object_infos[0].resumable_id
