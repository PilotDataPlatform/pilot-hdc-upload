# Copyright (C) 2022-2023 Indoc Systems
#
# Licensed under the GNU AFFERO GENERAL PUBLIC LICENSE, Version 3.0 (the "License") available at https://www.gnu.org/licenses/agpl-3.0.en.html.
# You may not use this file except in compliance with the License.

import json
import os
import time
import uuid

from common import LoggerFactory

from app.commons.data_providers.redis import SrvAioRedisSingleton
from app.config import ConfigClass
from app.models.models_item import ItemStatus
from app.routers.v1.exceptions import InvalidPayload

_file_mgr_logger = LoggerFactory(
    'folder_manager',
    level_default=ConfigClass.LEVEL_DEFAULT,
    level_file=ConfigClass.LEVEL_FILE,
    level_stdout=ConfigClass.LEVEL_STDOUT,
    level_stderr=ConfigClass.LEVEL_STDERR,
).get_logger()

redis_srv = SrvAioRedisSingleton()


class FolderMgr:
    """Folder Manager."""

    def __init__(self, project_code, relative_path):
        self.project_code = project_code
        self.relative_path = relative_path
        self.last_node = None
        self.to_create = []
        self.relations_data = []
        self.zone = ConfigClass.namespace

    async def create(self, creator: str, current_folder: str, parent_folder_id: str):
        """create folder nodes and connect them to the parent."""
        try:
            #
            to_create_path = (self.relative_path + '/').replace(current_folder + '/', '')
            to_create_path = to_create_path.split('/')[:-1]
            node_chain = []
            read_db_duration = 0

            if len(current_folder.rsplit('/')) < 2:
                raise InvalidPayload('Cannot create folder directly under project node')
            current_folder_path, current_folder_name = current_folder.rsplit('/', 1)
            current_folder_node = await get_folder_node(
                self.project_code, current_folder_name, current_folder_path, creator, self.zone
            )
            current_folder_node.folder_parent_geid = parent_folder_id

            if current_folder_node.exist is False:
                lazy_save = await current_folder_node.lazy_save()
                self.to_create.append(lazy_save)
            node_chain.append(current_folder_node)
            self.last_node = current_folder_node

            for folder_name in to_create_path:
                parent_node = self.last_node
                folder_relative_path = os.path.join(parent_node.folder_relative_path, parent_node.folder_name)
                read_db_start_time = time.time()

                new_node = await get_folder_node(
                    self.project_code, folder_name, folder_relative_path, creator, self.zone
                )

                if not new_node.exist:
                    new_node.folder_parent_geid = parent_node.global_entity_id
                    lazy_save = await new_node.lazy_save()
                    self.to_create.append(lazy_save)

                read_db_duration += time.time() - read_db_start_time

                node_chain.append(new_node)
                self.last_node = new_node

            _file_mgr_logger.info(f'Read From db cost {read_db_duration}')

        except Exception:
            raise


async def get_folder_node(project_code, folder_name, folder_relative_path, creator, zone):
    folder_node = FolderNode(project_code, folder_name, folder_relative_path, creator, zone)
    await folder_node.read_node()
    return folder_node


class FolderNode:
    """Folder Node Model."""

    def __init__(self, project_code, folder_name, folder_relative_path, creator, zone):
        self.exist = False

        self.global_entity_id = str(uuid.uuid4())
        self.folder_name = folder_name
        self.folder_parent_geid = ''
        self.folder_creator = creator
        self.zone = zone
        self.project_code = project_code
        self.folder_relative_path = folder_relative_path

        if folder_relative_path is None:
            self.folder_relative_path = ''

    async def read_node(self):

        await self.read_from_cache(
            self.folder_relative_path,
            self.folder_name,
            self.project_code,
            self.zone,
        )

        if not self.exist:

            if self.folder_relative_path:
                obj_path = os.path.join(self.zone, self.project_code, self.folder_relative_path, self.folder_name)
            else:
                obj_path = os.path.join(self.zone, self.project_code, self.folder_name)
            await redis_srv.set_by_key(obj_path, json.dumps(self.__dict__))

    async def read_from_cache(self, folder_relative_path, folder_name, project_code, zone):
        """read created nodes in the cache."""

        obj_path = os.path.join(zone, project_code, folder_relative_path, folder_name)
        found = await redis_srv.get_by_key(obj_path)
        if found:
            found = json.loads(found)
            self.global_entity_id = found.get('global_entity_id')
            self.folder_parent_geid = found.get('folder_parent_geid')
            self.folder_creator = found.get('folder_creator')
            self.project_code = found.get('project_code')
            self.exist = True
        return self.exist

    async def lazy_save(self):

        zone_mapping = {'greenroom': 0}.get(self.zone, 1)

        payload = {
            'id': self.global_entity_id,
            'parent': self.folder_parent_geid,
            'parent_path': self.folder_relative_path,
            'type': 'folder',
            'status': ItemStatus.ACTIVE,
            'zone': zone_mapping,
            'name': self.folder_name,
            'size': 0,
            'owner': self.folder_creator,
            'container_code': self.project_code,
            'container_type': 'project',
            'location_uri': '',
            'version': '',
            'tags': [],
        }

        return payload
