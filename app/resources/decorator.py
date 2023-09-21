# Copyright (C) 2022-2023 Indoc Systems
#
# Licensed under the GNU AFFERO GENERAL PUBLIC LICENSE, Version 3.0 (the "License") available at https://www.gnu.org/licenses/agpl-3.0.en.html.
# You may not use this file except in compliance with the License.

from functools import wraps


class HeaderMissingException(Exception):
    pass


def header_enforcement(required_headers: list):
    """
    Summary:
        The decorator is to check if the required headers present in the
        http request. Raise the exception if not exist
    Parameter:
        - required_headers(list): the required header value to be checked
    Return:
        - decorator function
    """

    def decorator(func):
        @wraps(func)
        async def inner(*arg, **kwargs):

            for header in required_headers:
                if not kwargs.get(header):
                    raise HeaderMissingException('%s is required' % header)

            return await func(*arg, **kwargs)

        return inner

    return decorator
