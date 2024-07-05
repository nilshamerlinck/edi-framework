# Copyright 2024 Camptocamp
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import SUPERUSER_ID, api
from odoo.tools.sql import column_exists, create_column, rename_column


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})

    required_modules = ("storage_backend", "edi_storage_oca")
    if not env["ir.module.module"].search(
        [("name", "in", required_modules), ("state", "=", "installed")]
    ):
        return
    if not column_exists(cr, "edi_backend", "new_storage_id"):
        create_column(cr, "edi_backend", "new_storage_id", "int4")
    _create_fs_storage_records(env)
    if column_exists(cr, "edi_backend", "new_storage_id"):
        rename_column(cr, "edi_backend", "storage_id", "old_storage_id")
        rename_column(cr, "edi_backend", "new_storage_id", "storage_id")


def _create_fs_storage_records(env):
    # Create a fs.storage record for each backend.storage
    storage_backend_records = env["storage.backend"].search([])
    if not storage_backend_records:
        return

    # make sure all backend_type can be mapped even if corresponding modules
    # have not been migrated (on purpose because we should switch to fs_storage)
    selection = [
        ("filesystem", "Filesystem"),
        ("ftp", "FTP"),
        ("sftp", "SFTP"),
        ("s3", "S3"),
    ]
    env["storage.backend"]._fields["backend_type"].selection = selection
    env["storage.backend"]._fields["backend_type_env_default"].selection = selection

    fs_storage = env["fs.storage"]
    for record in storage_backend_records:
        protocol = "file"
        if record.backend_type == "ftp":
            protocol = "ftp"
        elif record.backend_type == "sftp":
            protocol = "sftp"
        elif record.backend_type == "s3":
            protocol = "s3"

        res_id = fs_storage.create(
            {
                "name": record.name,
                "code": "storage_backend_%d" % record.id,
                "protocol": protocol,
                "directory_path": record.directory_path,
            }
        )

        env.cr.execute(
            "UPDATE edi_backend SET new_storage_id = %s WHERE storage_id = %s",
            (res_id.id, record.id),
        )
