# Copyright (C) 2022-Present Indoc Systems
#
# Licensed under the GNU AFFERO GENERAL PUBLIC LICENSE,
# Version 3.0 (the "License") available at https://www.gnu.org/licenses/agpl-3.0.en.html.
# You may not use this file except in compliance with the License.

from ipaddress import AddressValueError
from ipaddress import IPv4Address

from fastapi.datastructures import Headers
from pydantic import BaseModel


class Network(BaseModel):
    origin: str

    @classmethod
    def from_headers(cls, headers: Headers) -> 'Network':
        header = headers.get('X-Forwarded-For', '')
        x_forwarded_ip = header.split(',').pop(0).strip()

        try:
            ip_v4_address = IPv4Address(x_forwarded_ip)
        except AddressValueError:
            return cls(origin='unknown')

        first_ip_octet = ip_v4_address.compressed.split('.', 1).pop(0) + '.'
        if first_ip_octet in {'10.', '192.', '148.'}:
            return cls(origin='internal')

        return cls(origin='external')
