# Copyright (C) 2022-2023 Indoc Systems
#
# Licensed under the GNU AFFERO GENERAL PUBLIC LICENSE, Version 3.0 (the "License") available at https://www.gnu.org/licenses/agpl-3.0.en.html.
# You may not use this file except in compliance with the License.

from fastapi import FastAPI

from app.routers import api_root
from app.routers.v1 import api_data_upload
from app.routers.v1.api_resumable_upload import api_resumable_upload


def api_registry(app: FastAPI):
    app.include_router(api_root.router)
    app.include_router(api_data_upload.router, prefix='/v1')
    app.include_router(api_resumable_upload.router, prefix='/v1')
