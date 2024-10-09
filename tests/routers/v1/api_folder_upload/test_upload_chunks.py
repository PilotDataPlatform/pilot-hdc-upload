# Copyright (C) 2022-Present Indoc Systems
#
# Licensed under the GNU AFFERO GENERAL PUBLIC LICENSE,
# Version 3.0 (the "License") available at https://www.gnu.org/licenses/agpl-3.0.en.html.
# You may not use this file except in compliance with the License.

import pytest

pytestmark = pytest.mark.asyncio


async def test_upload_chunks_return_400_when_session_id_header_is_missing(test_async_client, httpx_mock):
    response = await test_async_client.post(
        '/v1/files/chunks',
        files={
            'project_code': 'any',
            'operator': 'me',
            'resumable_identifier': 'fake_global_entity_id',
            'resumable_filename': 'any',
            'resumable_chunk_number': str(1),
            'resumable_total_chunks': str(1),
            'resumable_total_size': str(10),
            'chunk_data': ('chunk.txt', open('tests/routers/v1/api_folder_upload/chunk.txt', 'rb'), 'text/plain'),
        },
    )
    assert response.status_code == 400
    assert response.json() == {
        'code': 400,
        'error_msg': 'session_id is required',
        'page': 0,
        'total': 1,
        'num_of_pages': 1,
        'result': [],
    }


async def test_upload_chunks_return_200_when_when_success(
    test_async_client,
    httpx_mock,
    create_job_folder,
    create_fake_job,
    mock_boto3,
    mock_redis,
):

    response = await test_async_client.post(
        '/v1/files/chunks',
        headers={'Session-Id': '1234'},
        files={
            'project_code': 'any',
            'operator': 'me',
            'resumable_identifier': 'fake_global_entity_id',
            'resumable_filename': 'any',
            'resumable_chunk_number': str(1),
            'resumable_total_chunks': str(1),
            'resumable_total_size': str(10),
            'chunk_data': ('chunk.txt', open('tests/routers/v1/api_folder_upload/chunk.txt', 'rb'), 'text/plain'),
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        'code': 200,
        'error_msg': '',
        'page': 0,
        'total': 1,
        'num_of_pages': 1,
        'result': {'msg': 'Succeed'},
    }
