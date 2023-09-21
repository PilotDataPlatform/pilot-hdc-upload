# Copyright (C) 2022-2023 Indoc Systems
#
# Licensed under the GNU AFFERO GENERAL PUBLIC LICENSE, Version 3.0 (the "License") available at https://www.gnu.org/licenses/agpl-3.0.en.html.
# You may not use this file except in compliance with the License.

import pytest
from common import ProjectNotFoundException

pytestmark = pytest.mark.asyncio


async def test_files_jobs_return_400_when_session_id_header_is_missing(test_async_client, httpx_mock):
    response = await test_async_client.post(
        '/v1/files/jobs',
        json={
            'project_code': 'any',
            'parent_folder_id': 'parent_folder_id',
            'operator': 'me',
            'data': [{'resumable_filename': 'any'}],
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


async def test_files_jobs_return_400_when_session_job_type_is_wrong(test_async_client, httpx_mock):
    response = await test_async_client.post(
        '/v1/files/jobs',
        headers={'Session-Id': '1234'},
        json={
            'project_code': 'any',
            'parent_folder_id': 'parent_folder_id',
            'operator': 'me',
            'job_type': 'any',
            'data': [{'resumable_filename': 'any'}],
        },
    )
    assert response.status_code == 400
    assert response.json() == {
        'code': 400,
        'error_msg': 'Invalid job type: any',
        'page': 0,
        'total': 1,
        'num_of_pages': 1,
        'result': [],
    }


async def test_files_jobs_return_404_when_project_info_not_found(test_async_client, httpx_mock, mocker):

    m = mocker.patch('common.ProjectClient.get', return_value=[])
    m.side_effect = ProjectNotFoundException

    response = await test_async_client.post(
        '/v1/files/jobs',
        headers={'Session-Id': '1234'},
        json={
            'project_code': 'any',
            'parent_folder_id': 'parent_folder_id',
            'operator': 'me',
            'job_type': 'AS_FILE',
            'data': [{'resumable_filename': 'any'}],
        },
    )

    assert response.status_code == 404
    assert response.json() == {
        'code': 404,
        'error_msg': 'Project not found',
        'page': 0,
        'total': 1,
        'num_of_pages': 1,
        'result': [],
    }


async def test_file_with_conflict_path_should_return_409(test_async_client, httpx_mock, mocker, mock_boto3):

    mocker.patch('common.ProjectClient.get', return_value={'any': 'any', 'global_entity_id': 'fake_global_entity_id'})

    httpx_mock.add_response(
        method='POST',
        url='http://metadata_service/v1/items/batch/',
        json={},
        status_code=409,
    )

    response = await test_async_client.post(
        '/v1/files/jobs',
        headers={'Session-Id': '1234'},
        json={
            'project_code': 'any',
            'parent_folder_id': 'parent_folder_id',
            'operator': 'me',
            'job_type': 'AS_FILE',
            'data': [{'resumable_filename': 'any/test'}],
        },
    )
    assert response.status_code == 409
    assert response.json() == {
        'code': 409,
        'error_msg': 'The resource already exist: {}',
        'page': 0,
        'total': 1,
        'num_of_pages': 1,
        'result': [],
    }


async def test_folder_with_invalid_parameter_return_400(test_async_client, httpx_mock, mocker, mock_boto3):

    mocker.patch('common.ProjectClient.get', return_value={'any': 'any', 'global_entity_id': 'fake_global_entity_id'})

    response = await test_async_client.post(
        '/v1/files/jobs',
        headers={'Session-Id': '1234'},
        json={
            'project_code': 'any',
            'current_folder_node': 'root',
            'parent_folder_id': 'parent_folder_id',
            'operator': 'me',
            'job_type': 'AS_FOLDER',
            'data': [{'resumable_relative_path': 'path', 'resumable_filename': 'any'}],
        },
    )

    assert response.status_code == 400
    assert response.json() == {
        'code': 400,
        'error_msg': 'Cannot create folder directly under project node',
        'page': 0,
        'total': 1,
        'num_of_pages': 1,
        'result': [],
    }


async def test_files_jobs_should_return_200_when_success(
    test_async_client, httpx_mock, create_job_folder, mock_boto3, mocker
):

    mocker.patch('common.ProjectClient.get', return_value={'any': 'any', 'global_entity_id': 'fake_global_entity_id'})
    httpx_mock.add_response(
        method='POST',
        url='http://dataops_service/v1/task-stream/',
        json={
            'session_id': 1234,
            'operator': 'me',
            'dataset_code': 'any',
            'job_id': 'test',
            'action': 'data_download',
            'operator': 'me',
            'status': 'ZIPPING',
            'project_code': 'any',
            'payload': {'hash_code': 'test'},
        },
        status_code=200,
    )

    httpx_mock.add_response(
        method='POST',
        url='http://metadata_service/v1/items/batch/',
        json={
            'result': [
                {
                    'id': 'item-id',
                    'parent': 'parent-id',
                    'parent_path': 'path',
                    'restore_path': None,
                    'status': False,
                    'type': 'file',
                    'zone': 0,
                    'name': 'any',
                    'size': 0,
                    'owner': 'testuser',
                    'container_code': 'project_code',
                    'container_type': 'project',
                }
            ]
        },
        status_code=200,
    )

    response = await test_async_client.post(
        '/v1/files/jobs',
        headers={'Session-Id': '1234'},
        json={
            'project_code': 'any',
            'parent_folder_id': 'parent_folder_id',
            'operator': 'me',
            'job_type': 'AS_FILE',
            'data': [{'resumable_relative_path': 'path', 'resumable_filename': 'any'}],
        },
    )
    assert response.status_code == 200
    result = response.json()['result'][0]
    assert result['session_id'] == '1234'
    assert result['target_names'] == ['path/any']
    assert result['action_type'] == 'data_upload'
    assert result['status'] == 'RUNNING'


async def test_files_jobs_type_AS_FOLDER_should_return_200_when_success(
    test_async_client, httpx_mock, create_job_folder, mock_boto3, mocker, mock_redis
):

    mocker.patch('common.ProjectClient.get', return_value={'any': 'any', 'global_entity_id': 'fake_global_entity_id'})
    httpx_mock.add_response(
        method='POST',
        url='http://dataops_service/v1/task-stream/',
        json={
            'session_id': 1234,
            'operator': 'me',
            'dataset_code': 'any',
            'job_id': 'test',
            'action': 'data_download',
            'operator': 'me',
            'status': 'ZIPPING',
            'project_code': 'any',
            'payload': {'hash_code': 'test'},
        },
        status_code=200,
    )

    httpx_mock.add_response(
        method='POST',
        url='http://metadata_service/v1/items/batch/',
        json={
            'result': [
                {
                    'id': 'item-id',
                    'parent': 'parent-id',
                    'parent_path': 'path',
                    'restore_path': None,
                    'status': False,
                    'type': 'file',
                    'zone': 0,
                    'name': 'any',
                    'size': 0,
                    'owner': 'testuser',
                    'container_code': 'project_code',
                    'container_type': 'project',
                }
            ]
        },
        status_code=200,
    )

    response = await test_async_client.post(
        '/v1/files/jobs',
        headers={'Session-Id': '1234'},
        json={
            'project_code': 'any',
            'parent_folder_id': 'parent_folder_id',
            'operator': 'me',
            'job_type': 'AS_FOLDER',
            'data': [{'resumable_relative_path': 'path', 'resumable_filename': 'any'}],
            'current_folder_node': 'admin/test',
        },
    )
    assert response.status_code == 200
    result = response.json()['result'][0]
    assert result['session_id'] == '1234'
    assert result['target_names'] == ['path/any']
    assert result['action_type'] == 'data_upload'
    assert result['status'] == 'RUNNING'


async def test_files_jobs_adds_folder_should_return_200_when_success(
    test_async_client, httpx_mock, create_job_folder, mock_boto3, mocker, mock_redis
):

    mocker.patch('common.ProjectClient.get', return_value={'any': 'any', 'global_entity_id': 'fake_global_entity_id'})
    httpx_mock.add_response(
        method='POST',
        url='http://dataops_service/v1/task-stream/',
        json={
            'session_id': 1234,
            'operator': 'me',
            'dataset_code': 'any',
            'job_id': 'test',
            'action': 'data_download',
            'operator': 'me',
            'status': 'ZIPPING',
            'project_code': 'any',
            'payload': {'hash_code': 'test'},
        },
        status_code=200,
    )

    httpx_mock.add_response(
        method='POST',
        url='http://metadata_service/v1/items/batch/',
        json={
            'result': [
                {
                    'id': 'item-id',
                    'parent': 'parent-id',
                    'parent_path': 'tests/tmp',
                    'restore_path': None,
                    'status': False,
                    'type': 'file',
                    'zone': 0,
                    'name': 'any',
                    'size': 0,
                    'owner': 'testuser',
                    'container_code': 'project_code',
                    'container_type': 'project',
                }
            ]
        },
        status_code=200,
    )

    response = await test_async_client.post(
        '/v1/files/jobs',
        headers={'Session-Id': '1234'},
        json={
            'project_code': 'any',
            'parent_folder_id': 'parent_folder_id',
            'operator': 'me',
            'job_type': 'AS_FOLDER',
            'data': [{'resumable_filename': 'any', 'resumable_relative_path': 'tests/tmp'}],
            'current_folder_node': 'admin/test',
        },
    )

    assert response.status_code == 200
    result = response.json()['result'][0]
    assert result['session_id'] == '1234'
    assert result['target_names'] == ['tests/tmp/any']
    assert result['action_type'] == 'data_upload'
    assert result['status'] == 'RUNNING'
