# Copyright (C) 2022-Present Indoc Systems
#
# Licensed under the GNU AFFERO GENERAL PUBLIC LICENSE,
# Version 3.0 (the "License") available at https://www.gnu.org/licenses/agpl-3.0.en.html.
# You may not use this file except in compliance with the License.

import pytest

from app.routers.exceptions import NotFound

pytestmark = pytest.mark.asyncio


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
