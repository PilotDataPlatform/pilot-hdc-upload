# Copyright (C) 2022-2023 Indoc Systems
#
# Licensed under the GNU AFFERO GENERAL PUBLIC LICENSE, Version 3.0 (the "License") available at https://www.gnu.org/licenses/agpl-3.0.en.html.
# You may not use this file except in compliance with the License.

FILES_MIMETYPE = {
    'application/x-7z-compressed': '7z',
    'application/zip': 'zip',
    'application/x-zip-compressed': 'zip',
    'multipart/x-zip': 'zip',
    'application/gzip': 'tar',
    'application/x-tar': 'tar',
    'application/x-gtar': 'tar',
    'application/x-bzip2': 'tar',
    'application/bzip2': 'tar',
    'application/lzip': 'tar',
    'application/x-brotli': 'tar',
    'application/x-lzip': 'tar',
    'application/x-xz': 'tar',
    'application/x-compress': 'tar',
    'application/x-compress': 'tar',
    'application/vnd.rar': 'rar',
    'application/x-rar-compressed': 'rar',
    'application/x-rar': 'rar',
}

TAR_TYPE = {
    'tar': 'tar',
    'tgz': 'tar',
    'tbz': 'tar',
    'txz': 'tar',
    'tzs': 'tar',
    'gz': 'tar',
    'br': 'tar',
    'bz2': 'tar',
    'xz': 'tar',
    'zst': 'tar',
    'tb2': 'tar',
    'tbz2': 'tar',
    'tz2': 'tar',
    'taz': 'tar',
    'tgz': 'tar',
    'lz': 'tar',
    'z': 'tar',
    'Z': 'tar',
}

RAR_TYPE = {'rar': 'rar', 'rev': 'rar', 'r00': 'rar', 'r01': 'rar'}

ZIP_TYPE = {'zip': 'zip', 'zipx': 'zip'}

ARCHIVE_TYPES = {**TAR_TYPE, **RAR_TYPE, **ZIP_TYPE, '7z': '7z'}
