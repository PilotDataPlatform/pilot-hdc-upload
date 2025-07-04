# Copyright (C) 2022-Present Indoc Systems
#
# Licensed under the GNU AFFERO GENERAL PUBLIC LICENSE,
# Version 3.0 (the "License") available at https://www.gnu.org/licenses/agpl-3.0.en.html.
# You may not use this file except in compliance with the License.

import enum
from functools import wraps

from fastapi import HTTPException

from app.logger import logger
from app.models.base_models import APIResponse
from app.models.base_models import EAPIResponseCode
from app.resources.decorator import HeaderMissingException


def catch_internal(api_namespace: str):
    """
    Summary:
        The decorator is to to catch internal server error.
    Parameter:
        - api_namespace(str): the namespace of api
    Return:
        - decorator function
    """

    def decorator(func):
        @wraps(func)
        async def inner(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except HTTPException as exce:
                respon = APIResponse()
                respon.code = EAPIResponseCode.internal_error
                err = api_namespace + ' ' + exce.detail
                err_msg = customized_error_template(ECustomizedError.INTERNAL) % err
                logger.error(err_msg)
                respon.error_msg = err_msg
                return respon.json_response()

            except HeaderMissingException as e:
                respon = APIResponse()
                respon.code = EAPIResponseCode.bad_request
                err_msg = str(e)
                logger.error(err_msg)
                respon.error_msg = err_msg
                return respon.json_response()

            except Exception as exce:
                respon = APIResponse()
                respon.code = EAPIResponseCode.internal_error
                err = api_namespace + ' ' + str(exce)
                err_msg = customized_error_template(ECustomizedError.INTERNAL) % err
                logger.error(err_msg)
                respon.error_msg = err_msg
                return respon.json_response()

        return inner

    return decorator


class ECustomizedError(enum.Enum):
    """Enum of customized errors."""

    FILE_NOT_FOUND = 'FILE_NOT_FOUND'
    INVALID_FILE_AMOUNT = 'INVALID_FILE_AMOUNT'
    JOB_NOT_FOUND = 'JOB_NOT_FOUND'
    FORGED_TOKEN = 'FORGED_TOKEN'
    TOKEN_EXPIRED = 'TOKEN_EXPIRED'
    INVALID_TOKEN = 'INVALID_TOKEN'
    INTERNAL = 'INTERNAL'
    INVALID_DATATYPE = 'INVALID_DATATYPE'
    INVALID_FOLDERNAME = 'INVALID_FOLDERNAME'
    INVALID_FILENAME = 'INVALID_FILENAME'
    INVALID_FOLDER_NAME_TYPE = 'INVALID_FOLDER_NAME_TYPE'


def customized_error_template(customized_error: ECustomizedError):
    """Get error template."""
    return {
        'FILE_NOT_FOUND': '[File not found] %s.',
        'INVALID_FILE_AMOUNT': '[Invalid file amount] must greater than 0',
        'JOB_NOT_FOUND': '[Invalid Job ID] Not Found',
        'FORGED_TOKEN': '[Invalid Token] System detected forged token, \
                    a report has been submitted.',
        'TOKEN_EXPIRED': '[Invalid Token] Already expired.',
        'INVALID_TOKEN': '[Invalid Token] %s',
        'INTERNAL': '[Internal] %s',
        'INVALID_DATATYPE': '[Invalid DataType]: %s',
        'INVALID_FOLDERNAME': '[Invalid Folder] Folder Name has already taken by other resources(file/folder)',
        'INVALID_FILENAME': '[Invalid File] File Name has already taken by other resources(file/folder)',
        'INVALID_FOLDER_NAME_TYPE': (
            'Folder name should not contain : ',
            '(\\/:?*<>|”\') and must contain 1 to 20 characters',
        ),
    }.get(customized_error.name, 'Unknown Error')
