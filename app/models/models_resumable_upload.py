# Copyright (C) 2022-Present Indoc Systems
#
# Licensed under the GNU AFFERO GENERAL PUBLIC LICENSE,
# Version 3.0 (the "License") available at https://www.gnu.org/licenses/agpl-3.0.en.html.
# You may not use this file except in compliance with the License.

from pydantic import BaseModel

from .base_models import APIResponse


class ObjectInfo(BaseModel):
    object_path: str
    resumable_id: str


class ResumableUploadPOST(BaseModel):
    """Pre upload payload model."""

    bucket: str
    object_infos: list[ObjectInfo]


class ResumableUploadGET(BaseModel):
    pass


class ResumableUploadResponse(APIResponse):
    pass
