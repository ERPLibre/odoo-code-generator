from odoo import api, fields, models, modules, tools


class CodeGeneratorModule(models.Model):
    _inherit = "code.generator.module"

    migrate_from_db_server = fields.Boolean(
        string="Generate db server migration template script."
    )

    migrate_db_server_relation_table_ids = fields.Many2many(
        string="Relation table migration",
        comodel_name="code.generator.db.table",
    )

    migrate_db_server_param_python_lib = fields.Char(default="psycopg2")
