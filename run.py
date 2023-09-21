# Copyright (C) 2022-2023 Indoc Systems
#
# Licensed under the GNU AFFERO GENERAL PUBLIC LICENSE, Version 3.0 (the "License") available at https://www.gnu.org/licenses/agpl-3.0.en.html.
# You may not use this file except in compliance with the License.

import uvicorn

from app.main import create_app

app = create_app()

if __name__ == '__main__':
    uvicorn.run('run:app', host='127.0.0.1', port=5079, log_level='info', reload=True)
