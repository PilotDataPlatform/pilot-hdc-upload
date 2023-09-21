# Copyright (C) 2022-2023 Indoc Systems
#
# Licensed under the GNU AFFERO GENERAL PUBLIC LICENSE, Version 3.0 (the "License") available at https://www.gnu.org/licenses/agpl-3.0.en.html.
# You may not use this file except in compliance with the License.

from unittest import mock

import pytest

pytestmark = pytest.mark.asyncio


async def test_on_success_return_400_when_session_id_header_is_missing(test_async_client, httpx_mock):
    response = await test_async_client.post(
        '/v1/files',
        json={
            'project_code': 'any',
            'operator': 'me',
            'job_id': 'fake_id',
            'item_id': 'item_id',
            'resumable_identifier': 'fake_global_entity_id',
            'resumable_filename': 'any',
            'resumable_relative_path': './',
            'resumable_total_chunks': 1,
            'resumable_total_size': 10,
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


@mock.patch('minio.credentials.providers._urlopen')
@mock.patch('os.remove')
async def test_upload_zip_should_allow_zip_preview(
    fake_remove,
    fake_providers_urlopen,
    test_async_client,
    httpx_mock,
    create_job_folder,
    create_fake_job,
    mock_boto3,
    mock_kafka_producer,
    mocker,
):

    httpx_mock.add_response(
        method='PUT',
        url='http://metadata_service/v1/item/?id=item_id',
        json={'result': {'id': 'test_id'}},
        status_code=200,
    )

    httpx_mock.add_response(method='POST', url='http://DATAOPS_SERVICE/v1/archive', json={}, status_code=200)

    httpx_mock.add_response(
        method='POST',
        url='http://dataops_service/v1/task-stream/',
        json={},
        status_code=200,
    )

    response = await test_async_client.post(
        '/v1/files',
        headers={'Session-Id': '1234', 'Authorization': 'token', 'Refresh-Token': 'refresh_token'},
        json={
            'project_code': 'any',
            'operator': 'me',
            'job_id': 'fake_id',
            'item_id': 'item_id',
            'resumable_identifier': 'fake_global_entity_id',
            'resumable_filename': 'any.zip',
            'resumable_relative_path': './',
            'resumable_total_chunks': 1,
            'resumable_total_size': 10,
        },
    )

    assert response.status_code == 200
    result = response.json()['result']
    assert result['session_id'] == '1234'
    assert result['job_id'] == 'fake_id'
    assert result['target_names'] == ['./any.zip']
    assert result['container_code'] == 'any'
    assert result['container_type'] == 'project'
    assert result['action_type'] == 'data_upload'
    assert result['status'] == 'CHUNK_UPLOADED'


@mock.patch('minio.credentials.providers._urlopen')
@mock.patch('os.remove')
async def test_upload_any_file_should_return_200(
    fake_remove,
    fake_providers_urlopen,
    test_async_client,
    httpx_mock,
    create_job_folder,
    create_fake_job,
    mock_boto3,
    mock_kafka_producer,
    mocker,
):

    httpx_mock.add_response(
        method='PUT',
        url='http://metadata_service/v1/item/?id=item_id',
        json={'result': {'id': 'test_id'}},
        status_code=200,
    )

    httpx_mock.add_response(
        method='POST',
        url='http://dataops_service/v1/task-stream/',
        json={},
        status_code=200,
    )

    response = await test_async_client.post(
        '/v1/files',
        headers={'Session-Id': '1234', 'Authorization': 'token', 'Refresh-Token': 'refresh_token'},
        json={
            'project_code': 'any',
            'operator': 'me',
            'job_id': 'fake_id',
            'item_id': 'item_id',
            'resumable_identifier': 'fake_global_entity_id',
            'resumable_filename': 'test/folder/file',
            'resumable_relative_path': './',
            'resumable_total_chunks': 1,
            'resumable_total_size': 10,
        },
    )
    assert response.status_code == 200
    result = response.json()['result']
    assert result['session_id'] == '1234'
    assert result['job_id'] == 'fake_id'
    assert result['container_code'] == 'any'
    assert result['container_type'] == 'project'
    assert result['action_type'] == 'data_upload'
    assert result['status'] == 'CHUNK_UPLOADED'
