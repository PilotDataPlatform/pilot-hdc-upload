# Copyright (C) 2022-Present Indoc Systems
#
# Licensed under the GNU AFFERO GENERAL PUBLIC LICENSE,
# Version 3.0 (the "License") available at https://www.gnu.org/licenses/agpl-3.0.en.html.
# You may not use this file except in compliance with the License.

import pytest

from app.config import ConfigClass


@pytest.mark.asyncio
async def test_root_request_should_return_app_status(test_async_client):
    response = await test_async_client.get('/')
    assert response.status_code == 200
    assert response.json() == {
        'status': 'OK',
        'name': ConfigClass.APP_NAME,
        'version': ConfigClass.VERSION,
    }
