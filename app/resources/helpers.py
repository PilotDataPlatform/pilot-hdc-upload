# Copyright (C) 2022-Present Indoc Systems
#
# Licensed under the GNU AFFERO GENERAL PUBLIC LICENSE,
# Version 3.0 (the "License") available at https://www.gnu.org/licenses/agpl-3.0.en.html.
# You may not use this file except in compliance with the License.

import tarfile
import zipfile
from abc import ABCMeta
from abc import abstractmethod
from typing import Any
from typing import Dict
from typing import List

import py7zr
import rarfile
from fastapi.concurrency import run_in_threadpool
from magic import Magic

from app.logger import logger
from app.resources.archive_file_type_mapping import FILES_MIMETYPE


class ArchiveFile(metaclass=ABCMeta):
    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def is_dir(self) -> bool:
        raise NotImplementedError

    @property
    @abstractmethod
    def size(self) -> int:
        raise NotImplementedError


class TarFile(ArchiveFile):
    def __init__(self, file_info: tarfile.TarInfo) -> None:
        self.file_info = file_info

    @property
    def name(self) -> str:
        return self.file_info.name

    @property
    def is_dir(self) -> bool:
        return self.file_info.isdir()

    @property
    def size(self) -> int:
        return self.file_info.size


class SevenZipFile(ArchiveFile):
    def __init__(self, file_info: py7zr.py7zr.ArchiveFile) -> None:
        self.file_info = file_info

    @property
    def name(self) -> str:
        return self.file_info.filename

    @property
    def is_dir(self) -> bool:
        return self.file_info.is_directory

    @property
    def size(self) -> int:
        return 0


class RarFile(ArchiveFile):
    def __init__(self, file_info: rarfile.RarInfo) -> None:
        self.file_info = file_info

    @property
    def name(self) -> str:
        return self.file_info.filename

    @property
    def is_dir(self) -> bool:
        return self.file_info.is_dir()

    @property
    def size(self) -> int:
        return self.file_info.file_size


class ZipFile(ArchiveFile):
    def __init__(self, file_info: zipfile.ZipInfo) -> None:
        self.file_info = file_info

    @property
    def name(self) -> str:
        return self.file_info.filename

    @property
    def is_dir(self) -> bool:
        return self.file_info.is_dir()

    @property
    def size(self) -> int:
        return self.file_info.file_size


class Archive:
    def __init__(self, file_list: List[ArchiveFile]):
        self.file_list = file_list

    def get_structure(self):
        results = {}
        for file in self.file_list:
            filename = file.name.split('/')[-1]
            if not filename:
                filename = file.name.split('/')[-2]
            current_path = results
            for path in file.name.split('/')[:-1]:
                if path:
                    if not current_path.get(path):
                        current_path[path] = {'is_dir': True}
                    current_path = current_path[path]

            if not file.is_dir:
                current_path[filename] = {
                    'filename': filename,
                    'size': file.size,
                    'is_dir': False,
                }
        return results


def read_tar(file_path: str) -> Dict[str, Any]:
    try:
        with tarfile.open(file_path, mode='r:*') as archive_files:
            archive = Archive([TarFile(file) for file in archive_files])
        return archive.get_structure()
    except tarfile.TarError:
        logger.exception(f'The file {file_path} is not a valid 7z')
        return {'Error: The file is not a valid 7z file': ''}


def read_7z(file_path: str) -> Dict[str, Any]:
    try:
        with py7zr.SevenZipFile(file_path, 'r') as archive_files:
            archive = Archive([SevenZipFile(file) for file in archive_files.files])
        return archive.get_structure()
    except py7zr.Bad7zFile:
        logger.exception(f'The file {file_path} is not a valid 7z')
        return {'Error: The file is not a valid 7z file': ''}


def read_zip(file_path: str) -> Dict[str, Any]:
    try:
        with zipfile.ZipFile(file_path, 'r') as archive_files:
            archive = Archive([ZipFile(file) for file in archive_files.infolist()])
        return archive.get_structure()
    except zipfile.BadZipfile:
        logger.exception(f'The file {file_path} is not a valid zip')
        return {'Error: The file is not a valid zip file': ''}


def read_rar(file_path: str) -> Dict[str, Any]:
    try:
        with rarfile.RarFile(file_path, 'r') as archive_files:
            archive = Archive([RarFile(file) for file in archive_files.infolist()])
        return archive.get_structure()
    except rarfile.BadRarFile:
        logger.exception(f'The file {file_path} is not a valid rar')
        return {'Error: The file is not a valid rar file': ''}


async def generate_archive_preview(file_path: str, file_type: str) -> dict:
    """
    Parameters:
        - file_path(string): the path of file
        - file_type(string): the extestension of the file
    Return:
        - (dict) folder structure inside
    """
    m = Magic(mime=True)
    file_mimetype = await run_in_threadpool(m.from_file, file_path)
    extracted_mine_type = FILES_MIMETYPE.get(file_mimetype, None)

    if file_type != extracted_mine_type:
        logger.warning(f'file type {file_type} is wrong based on file mine type {file_mimetype}')

    try:
        if extracted_mine_type == 'zip':
            return await run_in_threadpool(read_zip, file_path)
        elif extracted_mine_type == 'tar':
            return await run_in_threadpool(read_tar, file_path)
        elif extracted_mine_type == '7z':
            return await run_in_threadpool(read_7z, file_path)
        elif extracted_mine_type == 'rar':
            return await run_in_threadpool(read_rar, file_path)
    except Exception as e:
        logger.exception(f'Error adding file preview for {file_path}: {str(e)}')
        raise e
