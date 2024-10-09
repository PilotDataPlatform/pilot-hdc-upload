# Copyright (C) 2022-Present Indoc Systems
#
# Licensed under the GNU AFFERO GENERAL PUBLIC LICENSE,
# Version 3.0 (the "License") available at https://www.gnu.org/licenses/agpl-3.0.en.html.
# You may not use this file except in compliance with the License.

import pytest

from app.resources.helpers import generate_archive_preview

pytestmark = pytest.mark.asyncio


@pytest.mark.parametrize(
    'file_path,file_type',
    [
        ['tests/resources/archive.zip', 'zip'],
        ['tests/resources/archive.tar.gz', 'tar'],
        ['tests/resources/archive.7z', '7z'],
        ['tests/resources/archive.rar', 'rar'],
    ],
)
async def test_generate_archive_preview(file_path, file_type):
    archive_preview = await generate_archive_preview(file_path, file_type)
    assert archive_preview == {
        'archive': {
            'is_dir': True,
            'folder1': {
                'is_dir': True,
                'file1.txt': {'filename': 'file1.txt', 'size': 0, 'is_dir': False},
                'folder2': {'is_dir': True, 'file2.txt': {'filename': 'file2.txt', 'size': 0, 'is_dir': False}},
            },
            'root.txt': {'filename': 'root.txt', 'is_dir': False, 'size': 0},
        }
    }


async def test_generate_archive_preview_when_file_mimetype_is_different_from_extension(caplog):
    archive_preview = await generate_archive_preview('tests/resources/desktop.rar', 'rar')
    assert caplog.records[0].message == 'file type rar is wrong based on file mine type application/x-tar'
    assert archive_preview == {
        'bff.json': {'filename': 'bff.json', 'size': 34822, 'is_dir': False},
        'dataset.json': {'filename': 'dataset.json', 'size': 36439, 'is_dir': False},
    }
