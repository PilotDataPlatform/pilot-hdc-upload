# Copyright (C) 2022-2023 Indoc Systems
#
# Licensed under the GNU AFFERO GENERAL PUBLIC LICENSE, Version 3.0 (the "License") available at https://www.gnu.org/licenses/agpl-3.0.en.html.
# You may not use this file except in compliance with the License.

import json
import time
from enum import Enum
from typing import List

import httpx

from app.config import ConfigClass

_JOB_TYPE = 'data_upload'


class EFileStatus(Enum):
    WAITING = 0
    RUNNING = 1
    SUCCEED = 2
    FAILED = 3
    CHUNK_UPLOADED = 4

    def __str__(self):
        return '%s' % self.name


class SessionJob:
    """Session Job ORM."""

    def __init__(self, session_id, project_code, operator, job_id=None):
        """Init function, if provide job_id, will read from redis.

        If not provide, create a new job, and need to call set_job_id to set a new geid
        """
        self.session_id = session_id
        self.job_id = job_id
        self.project_code = project_code
        self.action = _JOB_TYPE
        self.operator = operator
        self.target_names = None
        self.status = EFileStatus.WAITING
        self.progress = 0
        self.payload = {}

    async def set_job_id(self, job_id):
        """set job id."""
        self.job_id = job_id

    def set_source(self, target_names: str):
        """set job target file."""
        self.target_names = target_names

    def add_payload(self, key: str, value):
        """will update if exists the same key."""
        self.payload[key] = value

    async def set_status(self, status: str):
        """set job status."""
        self.status = status
        return await self.save()

    def set_progress(self, progress: int):
        """set job status."""
        self.progress = progress

    async def save(self):
        """save in redis."""
        if not self.job_id:
            raise (Exception('[SessionJob] job_id not provided'))
        if not self.target_names:
            raise (Exception('[SessionJob] target_names not provided'))
        if not self.status:
            raise (Exception('[SessionJob] status not provided'))

        return await session_job_set_status(
            self.target_names,
            self.project_code,
            'project',
            self.status,
            self.job_id,
            self.session_id,
        )

    async def read(self):
        """read from redis."""
        fetched = await session_job_get_status(
            self.session_id, self.project_code, 'project', action_type=self.action, job_id=self.job_id
        )
        if not fetched:
            raise Exception('[SessionJob] Not found job: {}'.format(self.job_id))
        job_read = fetched[-1]
        self.target_names = job_read.get('target_names', None)
        self.status = job_read.get('status', EFileStatus.WAITING)
        self.payload = job_read.get('payload', {})

    def get_kv_entity(self):
        """get redis key value pair return key, value, job_dict."""
        my_key = 'dataaction:{}:Container:{}:{}:{}:{}:{}'.format(
            self.session_id, self.job_id, self.action, self.project_code, self.operator, self.target_names
        )
        record = {
            'session_id': self.session_id,
            'job_id': self.job_id,
            'target_names': self.target_names,
            'action_type': self.action,
            'status': str(self.status),
            'project_code': self.project_code,
            'payload': {
                'task_id': self.payload.get('task_id'),
                'resumable_identifier': self.payload.get('resumable_identifier'),
                'item_id': self.payload.get('item_id'),
            },
            'update_timestamp': str(round(time.time())),
        }
        my_value = json.dumps(record)
        return my_key, my_value, record


async def get_fsm_object(session_id: str, project_code: str, operator: str, job_id: str = None) -> SessionJob:

    fms_object = SessionJob(session_id, project_code, operator, job_id)
    return fms_object


async def session_job_set_status(
    target_names: List[str],
    container_code: str,
    container_type: str,
    status: EFileStatus,
    job_id: str,
    session_id: str = None,
    target_type: str = 'file',
    action_type: str = _JOB_TYPE,
) -> dict:
    """
    Summary:
        This function will call the DataOps service and write into
        Redis the inputs as a download job status.
    Parameter:
        - target_names(list[str]): the source file of current action..
        - container_code(str): the unique code of project/dataset.
        - container_type(str): project/dataset.
        - status(EFileStatus): job status; check EFileStatus object.
        - job_id(str): the job identifier for running action
        - session_id(str): the session id for current user
        - target_type(str): type of item.
        - action_type(str): type of action, in download service this
            will be marked as data_download.
    Return:
        - dict: the detail job info
    """

    task_url = ConfigClass.DATAOPS_SERVICE + 'task-stream/'
    payload = {
        'session_id': session_id,
        'target_names': target_names,
        'target_type': target_type,
        'container_code': container_code,
        'container_type': container_type,
        'action_type': action_type,
        'status': str(status),
        'job_id': job_id,
    }
    async with httpx.AsyncClient() as client:
        res = await client.request(method='POST', url=task_url, json=payload)
        if res.status_code != 200:
            raise Exception(f'Failed to write job status: {res.text}')

    return payload


async def session_job_get_status(
    session_id: str,
    container_code: str,
    container_type: str,
    action_type: str = _JOB_TYPE,
    target_names: List[str] = None,
    job_id: str = None,
) -> List[dict]:
    """
    Summary:
        The function will fetch the existing job from redis by the input.
        Return empty list if job does not exist
    Parameter:
        - session_id(str): the session id for current user
        - job_id(str): the job identifier for running action
        - project_code(str): the unique code of project
        - action(str): in download service this will be marked as data_download
        - operator(str) default=None: the user who takes current action
    Return:
        - dict: the detail job info
    """

    task_url = ConfigClass.DATAOPS_SERVICE + 'task-stream/static/'
    params = {
        'session_id': session_id,
        'container_code': container_code,
        'container_type': container_type,
        'action_type': action_type,
    }
    if target_names:
        params['target_names'] = target_names
    if job_id:
        params['job_id'] = job_id
    async with httpx.AsyncClient() as client:
        res = await client.get(url=task_url, params=params)

    if res.status_code == 404:
        return []
    elif res.status_code != 200:
        raise Exception(f'Fail to get job status: {res.text}')

    return res.json().get('stream_info')
