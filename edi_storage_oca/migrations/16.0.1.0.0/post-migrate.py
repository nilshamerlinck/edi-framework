# Copyright 2024 Camptocamp
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json
import os

from odoo import SUPERUSER_ID, api

directory = os.path.dirname(__file__)


def migrate(cr, version):
    if not version:
        return

    env = api.Environment(cr, SUPERUSER_ID, {})

    with open(os.path.join(directory, "files", "data.txt"), "rb") as file:
        data = file.read()

    if (
        not env["ir.module.module"].search(
            [("name", "=", "storage_backend"), ("state", "=", "installed")]
        )
        or not data
    ):
        return

    data = json.loads(data)
    # Update the backend with the mapping record
    edi_backend = env["edi.backend"].search([])
    fs_storage = env["fs.storage"].search([])

    # backend_id_str is string because of json.dumps in pre-migration
    for backend_id_str, storage_code in data.items():
        backend_id = int(backend_id_str)
        backend_rec = edi_backend.filtered(lambda b: b.id == backend_id)
        storage = fs_storage.filtered(
            lambda s: s.code == _get_fs_storage_code(storage_code)
        )
        if not backend_rec.storage_id and storage:
            backend_rec.write({"storage_id": storage.id})
    # Reset data in data.txt
    with open(os.path.join(directory, "files", "data.txt"), "w") as file:
        data = file.write("")
    return


def _get_fs_storage_code(storage_id):
    return "storage_backend_%s" % storage_id
