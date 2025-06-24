# Copyright (C) 2022-Present Indoc Systems
#
# Licensed under the GNU AFFERO GENERAL PUBLIC LICENSE,
# Version 3.0 (the "License") available at https://www.gnu.org/licenses/agpl-3.0.en.html.
# You may not use this file except in compliance with the License.

import pytest
from fastapi.datastructures import Headers

from app.components.request.network import Network


class TestNetwork:

    @pytest.mark.parametrize(
        'header,expected_origin',
        [
            ('', 'unknown'),
            ('invalid', 'unknown'),
            ('148.187.151.172, 192.168.147.154', 'internal'),
            ('87.141.46.228, 10.233.105.0', 'external'),
        ],
    )
    def test_from_headers_properly_converts_x_forwarded_for_header_into_origin(self, header, expected_origin):
        network = Network.from_headers(Headers(headers={'X-Forwarded-For': header}))

        assert network.origin == expected_origin
