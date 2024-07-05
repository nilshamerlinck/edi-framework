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

    required_modules = ("storage_backend", "edi_storage_oca")
    if not env["ir.module.module"].search(
        [("name", "in", required_modules), ("state", "=", "installed")]
    ):
        return
    _create_mapping_records(env)
    _export_mapping_data(env)
    return


def _create_mapping_records(env):
    # Create mapping between fs.storage and backend.storage records
    storage_backend_records = (
        env["storage.backend"]
        .search([])
        .filtered(lambda record: _get_unique_storage_code(env, record))
    )
    if not storage_backend_records:
        return

    _map_to_fs_storage_file(
        env,
        storage_backend_records.filtered(
            lambda record: record.backend_type == "filesystem"
        ),
    )
    _map_to_fs_storage_ftp(
        env,
        storage_backend_records.filtered(lambda record: record.backend_type == "ftp"),
    )
    _map_to_fs_storage_sftp(
        env,
        storage_backend_records.filtered(lambda record: record.backend_type == "sftp"),
    )
    # TODO: Add support for other types of backend.storage if any
    return


def _export_mapping_data(env):
    # Export the data to use in post-migration for updating the backend
    env.cr.execute("SELECT id, storage_id FROM edi_backend")
    # Ex: {5: 1}
    # 5 is backend_id
    # 1 is storage_id
    data = {
        str(row[0]): row[1] for row in env.cr.fetchall() if row[1] not in (False, None)
    }
    if not data:
        return

    file_content = json.dumps(data)

    with open(os.path.join(directory, "files", "data.txt"), "w") as file:
        file.write(file_content)
    return


def _map_to_fs_storage_file(env, records):
    if not records:
        return

    fs_storage = env["fs.storage"]
    vals_list = []
    for record in records:
        vals_list.append(
            {
                "name": _get_mapping_storage_name(record.name),
                "code": _get_unique_storage_code(env, record),
                "protocol": "file",
                "directory_path": record.directory_path,
            }
        )
    fs_storage.create(vals_list)


def _map_to_fs_storage_ftp(env, records):
    records = records.filtered(lambda record: record.ftp_server)
    if not records:
        return

    fs_storage = env["fs.storage"]
    for record in records:
        # We need to create record first because of selections in `protocol`
        mapping_fs_record = fs_storage.create(
            {
                "name": _get_mapping_storage_name(record.name),
                "code": _get_unique_storage_code(env, record),
                "directory_path": record.directory_path,
            }
        )
        options = {
            "host": record.ftp_server,
            "port": record.ftp_port or 21,
        }
        if record.ftp_login and record.ftp_password:
            options["username"] = record.ftp_login
            options["password"] = record.ftp_password
        mapping_fs_record.write(
            {
                "protocol": "ftp",
                "options": json.dumps(options),
            }
        )


def _map_to_fs_storage_sftp(env, records):
    records = records.filtered(lambda record: record.sftp_server)
    if not records:
        return

    fs_storage = env["fs.storage"]
    for record in records:
        # We need to create record first because of selections in `protocol`
        mapping_fs_record = fs_storage.create(
            {
                "name": _get_mapping_storage_name(record.name),
                "code": _get_unique_storage_code(env, record),
                "directory_path": record.directory_path,
            }
        )
        options = {
            "host": record.sftp_server,
            "port": record.sftp_port or 22,
            "username": record.sftp_login or "",
            "password": record.sftp_password or "",
        }

        mapping_fs_record.write(
            {
                "protocol": "sftp",
                "options": json.dumps(options),
            }
        )


def _get_unique_storage_code(env, record):
    # Return False if the code has already existed
    unique_code = "storage_backend_%s" % record.id
    is_existed = env["fs.storage"].search([("code", "=", unique_code)], limit=1)
    return unique_code if not is_existed else False


def _get_mapping_storage_name(name):
    return "%s (Backend Storage)" % name
