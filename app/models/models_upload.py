# Copyright (C) 2022-Present Indoc Systems
#
# Licensed under the GNU AFFERO GENERAL PUBLIC LICENSE,
# Version 3.0 (the "License") available at https://www.gnu.org/licenses/agpl-3.0.en.html.
# You may not use this file except in compliance with the License.

from enum import Enum

from pydantic import BaseModel
from pydantic import Field

from .base_models import APIResponse


class EUploadJobType(Enum):
    AS_FOLDER = 'AS_FOLDER'
    AS_FILE = 'AS_FILE'


class SingleFileForm(BaseModel):
    resumable_filename: str
    resumable_relative_path: str = ''


class PreUploadPOST(BaseModel):
    """Pre upload payload model."""

    project_code: str
    operator: str
    job_type: str = 'AS_FOLDER | AS_FILE'
    data: list[SingleFileForm]
    current_folder_node: str = ''
    parent_folder_id: str
    incremental = False


class PreUploadResponse(APIResponse):
    """Pre upload response class."""

    result: dict = Field(
        {},
        example=[
            {
                'session_id': 'unique_session_2021',
                'job_id': '1bfe8fd8-8b41-11eb-a8bd-eaff9e667817-1616439732',
                'target_names': 'file1.png',
                'action': 'data_upload',
                'status': 'PRE_UPLOADED',
                'project_code': 'gregtest',
                'operator': 'zhengyang',
                'progress': 0,
                'payload': {
                    'resumable_identifier': '1bfe8fd8-8b41-11eb-a8bd-eaff9e667817-1616439732',
                    'parent_folder_geid': '1bcbe182-8b41-11eb-bf7a-eaff9e667817-1616439732',
                },
                'update_timestamp': '1616439731',
            },
        ],
    )


class ChunkUploadPOST(BaseModel):
    """Chunk upload payload model."""

    project_code: str
    operator: str
    resumable_identifier: str
    resumable_filename: str
    resumable_chunk_number: int
    resumable_total_chunks: int
    resumable_total_size: float
    tags: list[str] = []
    metadatas: dict = None


class ChunkUploadResponse(APIResponse):
    """Chunk upload response class."""

    result: dict = Field({}, example={'msg': 'Succeed'})


class OnSuccessUploadPOST(BaseModel):
    """Merge chunks payload model."""

    project_code: str
    operator: str
    job_id: str
    item_id: str
    resumable_identifier: str
    resumable_filename: str
    resumable_relative_path: str
    resumable_total_chunks: int
    resumable_total_size: float
    tags: list[str] = []
    metadatas: dict = None
    process_pipeline: str = None
    from_parents: list = None
    upload_message = ''


class POSTCombineChunksResponse(APIResponse):
    """Get Job status response class."""

    result: dict = Field(
        {},
        example={
            'session_id': 'unique_session',
            'job_id': 'upload-0a572418-7c2b-11eb-8428-be498ca98c54-1614780986',
            'target_names': '<path>',
            'action': 'data_upload',
            'status': 'PRE_UPLOADED | SUCCEED',
            'project_code': 'em0301',
            'operator': 'zhengyang',
            'progress': 0,
            'payload': {
                'resumable_identifier': 'upload-0a572418-7c2b-11eb-8428-be498ca98c54-1614780986',
                'parent_folder_geid': '1e3fa930-8b41-11eb-845f-eaff9e667817-1616439736',
            },
            'update_timestamp': '1614780986',
        },
    )
