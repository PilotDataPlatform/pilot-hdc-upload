# Copyright (C) 2022-Present Indoc Systems
#
# Licensed under the GNU AFFERO GENERAL PUBLIC LICENSE,
# Version 3.0 (the "License") available at https://www.gnu.org/licenses/agpl-3.0.en.html.
# You may not use this file except in compliance with the License.

import botocore.exceptions

from app.logger import logger
from app.models.models_resumable_upload import ObjectInfo


async def get_chunks_info(boto3_client, bucket, object_infos: list[ObjectInfo]) -> list[dict]:
    result = []
    for obj_info in object_infos:
        try:
            s3_parts_res = await boto3_client.list_chunks(bucket, obj_info.object_path, obj_info.resumable_id)
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchUpload':
                logger.warning(
                    f'Upload for object "{obj_info.object_path}" '
                    f'with upload ID "{obj_info.resumable_id}" does not exist.'
                )
                continue
            raise

        s3_parts_info = {x.get('PartNumber'): x.get('ETag').replace("\"", '') for x in s3_parts_res.get('Parts', [])}

        result.append(
            {
                'object_path': obj_info.object_path,
                'resumable_id': obj_info.resumable_id,
                'chunks_info': s3_parts_info,
            }
        )

    return result
