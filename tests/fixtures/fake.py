# Copyright (C) 2022-Present Indoc Systems
#
# Licensed under the GNU AFFERO GENERAL PUBLIC LICENSE,
# Version 3.0 (the "License") available at https://www.gnu.org/licenses/agpl-3.0.en.html.
# You may not use this file except in compliance with the License.

import faker
import pytest


class Faker(faker.Faker):
    def container_code(self) -> str:
        return self.pystr_format('?#' * 10).lower()

    def project_code(self) -> str:
        return self.container_code()

    def dataset_code(self) -> str:
        return self.container_code()


@pytest.fixture(scope='session')
def fake() -> Faker:
    return Faker()
