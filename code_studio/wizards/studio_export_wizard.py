import base64
import io
import json
import zipfile

from lxml import etree
from odoo import _, api, fields, models


class StudioExportWizard(models.TransientModel):
    _name = "studio.export.wizard"
    _description = "Studio Export Wizard"

    name = fields.Char(
        string="Export Name", required=True, default="studio_customizations"
    )
    studio_model_ids = fields.Many2many(
        "studio.model",
        string="Models to Export",
        required=True,
        default=lambda self: self._default_studio_model_ids(),
    )

    export_type = fields.Selection(
        [
            ("module", "Odoo Module"),
            ("json", "JSON Format"),
            ("xml", "XML Data Files"),
        ],
        string="Export Format",
        required=True,
        default="module",
    )

    include_data = fields.Boolean(string="Include Sample Data", default=False)
    include_demo = fields.Boolean(string="Include Demo Data", default=False)
    include_security = fields.Boolean(
        string="Include Security Rules", default=True
    )
    include_translations = fields.Boolean(
        string="Include Translations", default=True
    )

    file_data = fields.Binary(string="Export File", readonly=True)
    file_name = fields.Char(string="File Name", readonly=True)
    state = fields.Selection(
        [
            ("draft", "Configure"),
            ("done", "Done"),
        ],
        default="draft",
    )

    @api.model
    def _default_studio_model_ids(self):
        """Get selected models from context"""
        active_ids = self.env.context.get("active_ids", [])
        if active_ids:
            return self.env["studio.model"].browse(active_ids)
        return self.env["studio.model"]

    def action_export(self):
        """Export the selected models"""
        self.ensure_one()

        if self.export_type == "module":
            file_data, file_name = self._export_as_module()
        elif self.export_type == "json":
            file_data, file_name = self._export_as_json()
        else:  # xml
            file_data, file_name = self._export_as_xml()

        self.write(
            {
                "file_data": file_data,
                "file_name": file_name,
                "state": "done",
            }
        )

        return {
            "type": "ir.actions.act_window",
            "res_model": "studio.export.wizard",
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def _export_as_module(self):
        """Export as a complete Odoo module"""
        # Create a zip file in memory
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(
            zip_buffer, "w", zipfile.ZIP_DEFLATED
        ) as zip_file:
            module_name = self.name.replace(" ", "_").lower()

            # Create __manifest__.py
            manifest_content = self._generate_manifest(module_name)
            zip_file.writestr(
                f"{module_name}/__manifest__.py", manifest_content
            )

            # Create __init__.py
            zip_file.writestr(
                f"{module_name}/__init__.py", "from . import models\n"
            )
            zip_file.writestr(
                f"{module_name}/models/__init__.py",
                self._generate_models_init(),
            )

            # Create model files
            for model in self.studio_model_ids:
                model_content = self._generate_model_py(model)
                model_filename = model.name.replace("x_", "").replace(".", "_")
                zip_file.writestr(
                    f"{module_name}/models/{model_filename}.py", model_content
                )

            # Create view files
            views_content = self._generate_views_xml()
            zip_file.writestr(f"{module_name}/views/views.xml", views_content)

            # Create menu files
            menus_content = self._generate_menus_xml()
            zip_file.writestr(f"{module_name}/views/menus.xml", menus_content)

            # Create security files
            if self.include_security:
                security_csv = self._generate_security_csv()
                zip_file.writestr(
                    f"{module_name}/security/ir.model.access.csv", security_csv
                )

            # Create data files
            if self.include_data:
                data_content = self._generate_data_xml()
                zip_file.writestr(f"{module_name}/data/data.xml", data_content)

            # Create demo files
            if self.include_demo:
                demo_content = self._generate_demo_xml()
                zip_file.writestr(f"{module_name}/demo/demo.xml", demo_content)

        zip_buffer.seek(0)
        file_data = base64.b64encode(zip_buffer.read())
        file_name = f"{module_name}.zip"

        return file_data, file_name

    def _generate_manifest(self, module_name):
        """Generate __manifest__.py content"""
        depends = ["base"]
        for model in self.studio_model_ids:
            if model.is_mail_thread:
                depends.append("mail")
                break

        manifest = {
            "name": self.name,
            "version": "18.0.1.0.0",
            "category": "Customization",
            "summary": f"Custom module created with Studio Community",
            "description": f"""
                {self.name}
                {'=' * len(self.name)}

                This module was generated by Studio Community.

                Models:
                {chr(10).join('- ' + m.description for m in self.studio_model_ids)}
            """,
            "author": "Studio Community",
            "depends": list(set(depends)),
            "data": [
                "security/ir.model.access.csv",
                "views/views.xml",
                "views/menus.xml",
            ],
            "demo": [],
            "installable": True,
            "application": True,
            "license": "LGPL-3",
        }

        if self.include_data:
            manifest["data"].append("data/data.xml")

        if self.include_demo:
            manifest["demo"].append("demo/demo.xml")

        return repr(manifest)

    def _generate_models_init(self):
        """Generate models/__init__.py content"""
        imports = []
        for model in self.studio_model_ids:
            model_filename = model.name.replace("x_", "").replace(".", "_")
            imports.append(f"from . import {model_filename}")
        return "\n".join(imports) + "\n"

    def _generate_model_py(self, model):
        """Generate Python code for a model"""
        # Get inherit list
        inherit = []
        if model.is_mail_thread:
            inherit.append("mail.thread")
        if model.is_mail_activity:
            inherit.append("mail.activity.mixin")

        inherit_str = repr(inherit) if inherit else ""

        # Start building the model code
        code = f"""from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class {self._get_class_name(model.name)}(models.Model):
    _name = '{model.name}'
    _description = '{model.description}'
"""

        if inherit:
            code += f"    _inherit = {inherit_str}\n"

        code += "    _rec_name = 'x_name'\n"
        code += "    _order = 'id desc'\n\n"

        # Add fields
        for field in model.field_ids.sorted("sequence"):
            field_code = self._generate_field_code(field)
            code += f"    {field_code}\n"

        # Add methods for server actions
        for action in self.env["studio.action"].search(
            [
                ("studio_model_id", "=", model.id),
                ("type", "=", "ir.actions.server"),
            ]
        ):
            if action.state == "code" and action.code:
                method_name = action.name.lower().replace(" ", "_")
                code += f"\n    def action_{method_name}(self):\n"
                code += "        self.ensure_one()\n"
                # Indent the code
                indented_code = "\n".join(
                    "        " + line for line in action.code.split("\n")
                )
                code += indented_code + "\n"

        return code

    def _get_class_name(self, model_name):
        """Convert model name to class name"""
        # x_custom_model -> XCustomModel
        parts = model_name.split("_")
        return "".join(part.capitalize() for part in parts)

    def _generate_field_code(self, field):
        """Generate Python code for a field"""
        field_type = field.ttype
        params = []

        # Add string parameter
        params.append(f"string='{field.field_description}'")

        # Add common parameters
        if field.required:
            params.append("required=True")
        if field.readonly:
            params.append("readonly=True")
        if field.help:
            params.append(f"help='{field.help}'")
        if field.tracking and field.ttype not in ("one2many", "many2many"):
            params.append("tracking=True")
        if not field.store:
            params.append("store=False")
        if field.index:
            params.append("index=True")
        if not field.copy:
            params.append("copy=False")

        # Handle specific field types
        if field_type == "selection":
            selection_values = []
            for sel in field.selection_ids:
                selection_values.append(f"('{sel.value}', '{sel.name}')")
            params.insert(0, f"selection=[{', '.join(selection_values)}]")

        elif field_type in ("many2one", "many2many"):
            params.insert(0, f"'{field.relation}'")

        elif field_type == "one2many":
            params.insert(0, f"'{field.relation}'")
            params.insert(1, f"'{field.relation_field}'")

        # Handle computed fields
        if field.compute:
            params.append(f"compute='_compute_{field.name}'")
            if field.inverse:
                params.append(f"inverse='_inverse_{field.name}'")
            if not field.store:
                params.append("store=False")

        # Handle default value
        if field.default_value:
            if field_type == "boolean":
                default = field.default_value.lower() in ("true", "1", "yes")
                params.append(f"default={default}")
            elif field_type in ("integer", "float", "monetary"):
                params.append(f"default={field.default_value}")
            else:
                params.append(f"default='{field.default_value}'")

        # Map field types to Odoo field classes
        field_class_map = {
            "char": "Char",
            "text": "Text",
            "html": "Html",
            "integer": "Integer",
            "float": "Float",
            "monetary": "Monetary",
            "boolean": "Boolean",
            "date": "Date",
            "datetime": "Datetime",
            "selection": "Selection",
            "many2one": "Many2one",
            "one2many": "One2many",
            "many2many": "Many2many",
            "binary": "Binary",
        }

        field_class = field_class_map.get(field_type, "Char")
        params_str = ", ".join(params)

        return f"{field.name} = fields.{field_class}({params_str})"

    def _generate_views_xml(self):
        """Generate views XML content"""
        xml_content = '<?xml version="1.0" encoding="utf-8"?>\n<odoo>\n'

        for model in self.studio_model_ids:
            for view in model.view_ids:
                xml_content += f"""
    <record id="{model.name.replace('.', '_')}_{view.type}_view" model="ir.ui.view">
        <field name="name">{view.name}</field>
        <field name="model">{model.name}</field>
        <field name="arch" type="xml">
{view.arch_base}
        </field>
    </record>
"""

        xml_content += "</odoo>\n"
        return xml_content

    def _generate_menus_xml(self):
        """Generate menus XML content"""
        xml_content = '<?xml version="1.0" encoding="utf-8"?>\n<odoo>\n'

        # Create main menu if needed
        has_root_menu = any(
            not menu.parent_id
            for model in self.studio_model_ids
            for menu in model.menu_ids
        )
        if has_root_menu:
            xml_content += f"""
    <menuitem id="menu_root_{self.name.replace(' ', '_').lower()}"
        name="{self.name}"
        sequence="50"/>
"""

        # Create actions and menus
        for model in self.studio_model_ids:
            # Create action
            xml_content += f"""
    <record id="action_{model.name.replace('.', '_')}" model="ir.actions.act_window">
        <field name="name">{model.description}</field>
        <field name="res_model">{model.name}</field>
        <field name="view_mode">list,form</field>
    </record>
"""

            # Create menus
            for menu in model.menu_ids:
                parent_ref = (
                    f"menu_root_{self.name.replace(' ', '_').lower()}"
                    if not menu.parent_id
                    else f"menu_{menu.parent_id.id}"
                )
                xml_content += f"""
    <menuitem id="menu_{model.name.replace('.', '_')}"
        name="{menu.name}"
        parent="{parent_ref}"
        action="action_{model.name.replace('.', '_')}"
        sequence="{menu.sequence}"/>
"""

        xml_content += "</odoo>\n"
        return xml_content

    def _generate_security_csv(self):
        """Generate security CSV content"""
        csv_lines = [
            "id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink"
        ]

        for model in self.studio_model_ids:
            model_external_id = f"model_{model.name.replace('.', '_')}"
            # User access
            csv_lines.append(
                f"access_{model.name.replace('.', '_')}_user,{model.name}.user,{model_external_id},base.group_user,1,1,1,1"
            )
            # System access
            csv_lines.append(
                f"access_{model.name.replace('.', '_')}_system,{model.name}.system,{model_external_id},base.group_system,1,1,1,1"
            )

        return "\n".join(csv_lines) + "\n"

    def _generate_data_xml(self):
        """Generate data XML content"""
        xml_content = (
            '<?xml version="1.0" encoding="utf-8"?>\n<odoo>\n    <data>\n'
        )
        xml_content += "        <!-- Add your data here -->\n"
        xml_content += "    </data>\n</odoo>\n"
        return xml_content

    def _generate_demo_xml(self):
        """Generate demo XML content"""
        xml_content = (
            '<?xml version="1.0" encoding="utf-8"?>\n<odoo>\n    <data>\n'
        )

        for model in self.studio_model_ids:
            xml_content += (
                f"        <!-- Demo data for {model.description} -->\n"
            )
            for i in range(3):
                xml_content += f"""        <record id="demo_{model.name.replace('.', '_')}_{i}" model="{model.name}">
            <field name="x_name">Demo {model.description} {i + 1}</field>
        </record>\n"""

        xml_content += "    </data>\n</odoo>\n"
        return xml_content

    def _export_as_json(self):
        """Export as JSON format"""
        export_data = {
            "studio_version": "18.0",
            "export_date": fields.Datetime.now().isoformat(),
            "models": [],
        }

        for model in self.studio_model_ids:
            model_data = {
                "name": model.name,
                "description": model.description,
                "is_mail_thread": model.is_mail_thread,
                "is_mail_activity": model.is_mail_activity,
                "fields": [],
                "views": [],
                "menus": [],
                "actions": [],
                "automations": [],
            }

            # Export fields
            for field in model.field_ids:
                field_data = {
                    "name": field.name,
                    "field_description": field.field_description,
                    "ttype": field.ttype,
                    "required": field.required,
                    "readonly": field.readonly,
                    "tracking": field.tracking,
                    "help": field.help,
                    "sequence": field.sequence,
                }

                if field.ttype == "selection":
                    field_data["selection_values"] = [
                        {"value": sel.value, "name": sel.name}
                        for sel in field.selection_ids
                    ]
                elif field.ttype in ("many2one", "one2many", "many2many"):
                    field_data["relation"] = field.relation
                    if field.ttype == "one2many":
                        field_data["relation_field"] = field.relation_field

                model_data["fields"].append(field_data)

            # Export views
            for view in model.view_ids:
                view_data = {
                    "name": view.name,
                    "type": view.type,
                    "arch_base": view.arch_base,
                    "priority": view.priority,
                }
                model_data["views"].append(view_data)

            # Export menus
            for menu in model.menu_ids:
                menu_data = {
                    "name": menu.name,
                    "sequence": menu.sequence,
                    "parent_name": (
                        menu.parent_id.name if menu.parent_id else None
                    ),
                }
                model_data["menus"].append(menu_data)

            export_data["models"].append(model_data)

        json_str = json.dumps(export_data, indent=2)
        file_data = base64.b64encode(json_str.encode("utf-8"))
        file_name = f"{self.name}.json"

        return file_data, file_name

    def _export_as_xml(self):
        """Export as XML data files"""
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(
            zip_buffer, "w", zipfile.ZIP_DEFLATED
        ) as zip_file:
            # Export each model's data
            for model in self.studio_model_ids:
                xml_content = self._generate_model_xml(model)
                filename = f"{model.name.replace('.', '_')}_data.xml"
                zip_file.writestr(filename, xml_content)

        zip_buffer.seek(0)
        file_data = base64.b64encode(zip_buffer.read())
        file_name = f"{self.name}_xml_export.zip"

        return file_data, file_name

    def _generate_model_xml(self, model):
        """Generate XML data for a specific model"""
        xml_content = '<?xml version="1.0" encoding="utf-8"?>\n<odoo>\n'

        # Export model definition
        xml_content += f"""
    <!-- Model: {model.description} -->
    <record id="model_{model.name.replace('.', '_')}" model="ir.model">
        <field name="name">{model.description}</field>
        <field name="model">{model.name}</field>
        <field name="state">manual</field>
    </record>
"""

        # Export fields
        for field in model.field_ids:
            xml_content += f"""
    <record id="field_{model.name.replace('.', '_')}_{field.name}" model="ir.model.fields">
        <field name="name">{field.name}</field>
        <field name="field_description">{field.field_description}</field>
        <field name="model_id" ref="model_{model.name.replace('.', '_')}"/>
        <field name="ttype">{field.ttype}</field>
        <field name="required">{field.required}</field>
        <field name="readonly">{field.readonly}</field>
        <field name="tracking">{field.tracking}</field>
    </record>
"""

        xml_content += "</odoo>\n"
        return xml_content
