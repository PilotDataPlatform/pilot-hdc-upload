# Copyright (C) 2022-Present Indoc Systems
#
# Licensed under the GNU AFFERO GENERAL PUBLIC LICENSE,
# Version 3.0 (the "License") available at https://www.gnu.org/licenses/agpl-3.0.en.html.
# You may not use this file except in compliance with the License.

from enum import Enum


class ItemStatus(str, Enum):
    """The new enum type for file status.

    - REGISTERED means file is created by upload service but not complete yet. either in progress or fail.
    - ACTIVE means file uploading is complete.
    - ARCHIVED means the file has been deleted.
    """

    REGISTERED = 'REGISTERED'
    ACTIVE = 'ACTIVE'
    ARCHIVED = 'ARCHIVED'

    def __str__(self):
        return '%s' % self.name
