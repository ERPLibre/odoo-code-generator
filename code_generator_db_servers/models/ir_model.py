import logging

from odoo import models, fields, api, _, tools

_logger = logging.getLogger(__name__)


class IrModelFields(models.Model):
    _inherit = "ir.model.fields"

    ddb_field_foreign_key_column = fields.Char(string="Foreign key field")

    ddb_field_name = fields.Char(help="Name before migration.")

    ddb_field_description = fields.Char(help="Description before migration.")

    # ddb_field_help = fields.Char(help="Help before migration.")

    ddb_field_required = fields.Boolean(help="Required before migration.")

    ddb_field_type = fields.Char(help="Type before migration.")

    ddb_field_relation = fields.Char(
        help="Relation before migration, for a foreign key."
    )

    ddb_cmd_delete = fields.Boolean(
        help="Delete this field after compute data when migrate."
    )

    add_one2many = fields.Boolean(
        string="Add one2many",
        help="Add field one2many to related model on this field.",
    )

    path_binary = fields.Char(
        string="Path binary type",
        help=(
            "Attribut path to use with value of char to binary, import binary"
            " in database."
        ),
    )
