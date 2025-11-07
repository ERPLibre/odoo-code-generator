import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class CodeGeneratorWriter(models.Model):
    _inherit = "code.generator.writer"

    def code_write_hook_header_inherit(self, cw, module):
        super().code_write_hook_header_inherit(cw, module)

        if (
            not module.migrate_from_db_server
            or not module.migrate_db_server_relation_table_ids
        ):
            return
        db_id = module.migrate_db_server_relation_table_ids[0].m2o_db

        cw.emit("from odoo.exceptions import ValidationError")
        # TODO suppose to be add into parent
        cw.emit("import logging")
        # TODO this case need import os, find another dynamic way to specify import before write code
        cw.emit()
        cw.emit("_logger = logging.getLogger(__name__)")
        cw.emit()
        cw.emit("# TODO don't forget to increase memory")
        cw.emit(
            "# --limit-memory-soft=8589934592 --limit-memory-hard=10737418240"
        )
        cw.emit()
        cw.emit(f"HOST = '{db_id.host}'")
        cw.emit(f"PORT = '{db_id.port}'")
        cw.emit(f"USER = '{db_id.user}'")
        cw.emit(f"PASSWD = '{db_id.password}'")
        cw.emit(f"DB_NAME = '{db_id.database}'")
        cw.emit('BACKUP_PATH = "/tmp/"')
        cw.emit('FILE_PATH = f"{BACKUP_PATH}/document/doc"')
        cw.emit("DEBUG_LIMIT = False")
        cw.emit("LIMIT = 20")
        cw.emit('GENERIC_EMAIL = f"%s_membre@exemple.ca"')
        cw.emit()
        cw.emit("try:")
        # TODO use variable to selection importation
        with cw.indent():
            cw.emit(f"import {module.migrate_db_server_param_python_lib}")
            cw.emit(f"assert {module.migrate_db_server_param_python_lib}")
        cw.emit("except ImportError:")
        with cw.indent():
            cw.emit(
                "raise"
                f" ValidationError('{module.migrate_db_server_param_python_lib} is"
                " not available. Please install"
                f' "{module.migrate_db_server_param_python_lib}" python'
                " package.')"
            )
        cw.emit("if not HOST or not USER or not PASSWD or not DB_NAME:")
        with cw.indent():
            cw.emit(
                'raise ValidationError(f"Please, fill constant'
                ' HOST/USER/PASSWD/DB_NAME into files {__file__}")'
            )

    def code_write_hook_inherit(self, cw, module, method_name):
        super().code_write_hook_inherit(cw, module, method_name)

        if (
            not module.migrate_from_db_server
            and method_name != "post_init_hook"
        ):
            return
        # TODO duplicate data, maybe
        table_ids = module.migrate_db_server_relation_table_ids
        cw.emit('_logger.info("Start migration")')
        cw.emit("migration = Migration(cr)")
        cw.emit()
        cw.emit("# General configuration")
        cw.emit("migration.setup_configuration()")
        if table_ids:
            cw.emit()
            cw.emit("# Migration method for each table")
        for table_id in table_ids:
            cw.emit(f"migration.migrate_{table_id.name}()")
        cw.emit()
        cw.emit("# Show information about computing migration.")
        cw.emit("if migration.lst_generic_email:")
        with cw.indent():
            cw.emit('print("Got generic mail :")')
            cw.emit("for mail in migration.lst_generic_email:")
            with cw.indent():
                cw.emit('print(f"\\t{mail}")')
                cw.emit()
        cw.emit("# Print warning")
        cw.emit("if migration.lst_warning:")
        with cw.indent():
            cw.emit('print("Got warning :")')
            cw.emit("for warn in migration.lst_warning:")
            with cw.indent():
                cw.emit('print(f"\\t{warn}")')
                cw.emit()
        cw.emit("# Print error")
        cw.emit("if migration.lst_error:")
        with cw.indent():
            cw.emit('print("Got error :")')
            cw.emit("for err in migration.lst_error:")
            with cw.indent():
                cw.emit('print(f"\\t{err}")')

    def write_extra_extra_function_hook(self, module, cw):
        super(CodeGeneratorWriter, self).write_extra_extra_function_hook(
            module, cw
        )
        if not module.migrate_db_server_relation_table_ids:
            return
        db_id = module.migrate_db_server_relation_table_ids[0].m2o_db
        prefix_database = (
            ".dbo" if db_id.m2o_dbtype_name == "SQLServer" else ""
        )

        # Get all table with data
        table_ids = module.migrate_db_server_relation_table_ids

        cw.emit("class Struct(object):")
        with cw.indent():
            cw.emit("def __init__(self, **entries):")
            with cw.indent():
                cw.emit("self.__dict__.update(entries)")
        cw.emit()
        cw.emit()
        cw.emit("class Migration:")
        with cw.indent():
            cw.emit("def __init__(self, cr):")
            with cw.indent():
                cw.emit("# Generic variable")
                cw.emit("self.cr = cr")
                cw.emit("self.lst_generic_email = []")
                cw.emit("self.lst_used_email = []")
                cw.emit("self.lst_error = []")
                cw.emit("self.lst_warning = []")
                cw.emit()
                cw.emit("# Path of the backup")
                cw.emit("self.source_code_path = BACKUP_PATH")
                cw.emit(
                    'self.logo_path = f"{self.source_code_path}/images/logo"'
                )
                cw.emit("# Table into cache")
                for table_id in table_ids:
                    cw.emit(f"self.dct_{table_id.model_name} = {{}}")
                cw.emit("# Model into cache")
                cw.emit("self.dct_partner_id = {}")
                cw.emit("# Database information")
                cw.emit(f"assert {module.migrate_db_server_param_python_lib}")
                cw.emit("self.host = HOST")
                cw.emit("self.user = USER")
                cw.emit("self.port = PORT")
                cw.emit("self.passwd = PASSWD")
                cw.emit("self.db_name = DB_NAME")
                cw.emit(
                    "self.conn ="
                    f" {module.migrate_db_server_param_python_lib}.connect("
                )
                with cw.indent():
                    cw.emit("server=self.host,")
                    cw.emit("user=self.user,")
                    cw.emit("port=self.port,")
                    cw.emit("password=self.passwd,")
                    cw.emit("database=self.db_name,")
                    cw.emit('# charset="utf8",')
                    cw.emit("# use_unicode=True,")
                cw.emit(")")
                cw.emit("self.dct_tbl = self._fill_tbl()")
        cw.emit()
        cw.emit()
        # Fill table database
        with cw.indent():
            cw.emit("def _fill_tbl(self):")
            with cw.indent():
                cw.emit('"""')
                cw.emit("Fill all database in self.dct_tbl")
                cw.emit(":return:")
                cw.emit('"""')
                cw.emit("cur = self.conn.cursor()")
                cw.emit("# Get all tables")
                cw.emit("str_query = (")
                with cw.indent():
                    cw.emit(
                        'f"""SELECT * FROM'
                        ' {self.db_name}.INFORMATION_SCHEMA.TABLES;"""'
                    )
                cw.emit(")")
                cw.emit("cur.nextset()")
                cw.emit("cur.execute(str_query)")
                cw.emit("tpl_result = cur.fetchall()")
                cw.emit()
                cw.emit("lst_whitelist_table = [")
                with cw.indent():
                    for table_id in table_ids:
                        cw.emit(f'"{table_id.name}",')
                cw.emit("]")
                cw.emit()
                cw.emit("dct_tbl = {")
                with cw.indent():
                    cw.emit('f"{a[0]}.{a[1]}.{a[2]}": []')
                    cw.emit("for a in tpl_result")
                cw.emit("}")
                cw.emit("dct_short_tbl = {")
                with cw.indent():
                    cw.emit('f"{a[0]}.{a[1]}.{a[2]}": a[2]')
                    cw.emit("for a in tpl_result")
                cw.emit("}")
                cw.emit()
                cw.emit("for table_name, lst_column in dct_tbl.items():")
                with cw.indent():
                    cw.emit("table = dct_short_tbl[table_name]")
                    cw.emit("if table not in lst_whitelist_table:")
                    with cw.indent():
                        cw.emit("msg = f\"Skip table '{table}'\"")
                        cw.emit("_logger.warning(msg)")
                        cw.emit("self.lst_warning.append(msg)")
                        cw.emit("continue")
                    cw.emit()
                    cw.emit(
                        "_logger.info(f\"Import in cache table '{table}'\")"
                    )
                    cw.emit(
                        'str_query = f"""SELECT COLUMN_NAME FROM'
                        " {self.db_name}.INFORMATION_SCHEMA.COLUMNS WHERE"
                        ' TABLE_NAME = N\'{table}\';"""'
                    )
                    cw.emit("cur.nextset()")
                    cw.emit("cur.execute(str_query)")
                    cw.emit("tpl_result = cur.fetchall()")
                    cw.emit("lst_column_name = [a[0] for a in tpl_result]")
                    cw.emit('str_query = f"""SELECT * FROM {table_name};"""')
                    cw.emit("cur.nextset()")
                    cw.emit("cur.execute(str_query)")
                    cw.emit("tpl_result = cur.fetchall()")
                    cw.emit()
                    cw.emit("for lst_result in tpl_result:")
                    with cw.indent():
                        cw.emit("i = -1")
                        cw.emit("dct_value = {}")
                        cw.emit("for result in lst_result:")
                        with cw.indent():
                            cw.emit("i += 1")
                            cw.emit("dct_value[lst_column_name[i]] = result")
                        cw.emit("lst_column.append(Struct(**dct_value))")
                    cw.emit()
                cw.emit("return dct_tbl")
                cw.emit()
                # Fill setup configuration
            cw.emit("def setup_configuration(self, dry_run=False):")
            with cw.indent():
                cw.emit('_logger.info("Setup configuration")')
                cw.emit()
                cw.emit("with api.Environment.manage():")
                cw.emit()
                with cw.indent():
                    cw.emit("env = api.Environment(self.cr, SUPERUSER_ID, {})")
                    cw.emit("# General configuration")
                    cw.emit("values = {")
                    with cw.indent():
                        cw.emit("# 'use_quotation_validity_days': True,")
                        cw.emit("# 'quotation_validity_days': 30,")
                        cw.emit("# 'portal_confirmation_sign': True,")
                        cw.emit("# 'portal_invoice_confirmation_sign': True,")
                        cw.emit("# 'group_sale_delivery_address': True,")
                        cw.emit("# 'group_sale_order_template': True,")
                        cw.emit("# 'default_sale_order_template_id': True,")
                    cw.emit("}")
                    cw.emit("if not dry_run:")
                    with cw.indent():
                        cw.emit(
                            "event_config ="
                            ' env["res.config.settings"].sudo().create([values])'
                        )
                        cw.emit("event_config.execute()")
                cw.emit()
            for table_id in table_ids:
                var_lst_tbl = f"lst_tbl_{table_id.model_name}"

                cw.emit(f"def migrate_{table_id.name}(self):")
                with cw.indent():
                    cw.emit('"""')
                    cw.emit(":return:")
                    cw.emit('"""')
                    cw.emit(f'_logger.info("Migrate {table_id.name}")')
                    cw.emit("env = api.Environment(self.cr, SUPERUSER_ID, {})")
                    cw.emit(f"if self.dct_{table_id.model_name}:")
                    with cw.indent():
                        cw.emit("return")
                    cw.emit(f"dct_{table_id.model_name} = {{}}")
                    cw.emit(
                        "table_name ="
                        f" f'{{self.db_name}}{prefix_database}.{table_id.name}'"
                    )
                    cw.emit(f"{var_lst_tbl} = self.dct_tbl.get(table_name)")
                    cw.emit('model_name = "res.partner"')
                    cw.emit()
                    cw.emit(
                        f"for i, {table_id.model_name} in"
                        f" enumerate({var_lst_tbl}):"
                    )
                    with cw.indent():
                        cw.emit("if DEBUG_LIMIT and i > LIMIT:")
                        with cw.indent():
                            cw.emit("break")
                        cw.emit()
                        cw.emit(f'pos_id = f"{{i}}/{{len({var_lst_tbl})}}"')
                        cw.emit(
                            "# TODO update variable name from database table"
                        )
                        cw.emit(f"obj_id_i = {table_id.model_name}.ID")
                        cw.emit(f"# name = {table_id.model_name}.Name")
                        cw.emit(f"name = ''")
                        cw.emit()
                        cw.emit("value = {")
                        with cw.indent():
                            cw.emit('"name": name,')
                        cw.emit("}")
                        cw.emit()
                        cw.emit(
                            "obj_res_partner_id ="
                            " env[model_name].create([value])"
                        )
                        cw.emit()
                        cw.emit(
                            f"dct_{table_id.model_name}[obj_id_i]"
                            " = obj_res_partner_id"
                        )
                        cw.emit("_logger.info(")
                        with cw.indent():
                            cw.emit(
                                'f"{pos_id} - {model_name} - table'
                                ' {table_name} - ADDED"'
                            )
                            cw.emit(f"f\" '{{name}}' id {{obj_id_i}}\"")
                        cw.emit(")")
                    cw.emit()
                    cw.emit(
                        f"self.dct_{table_id.model_name} ="
                        f" dct_{table_id.model_name}"
                    )
