# !/usr/bin/env python3
# © 2021-2025 TechnoLibre (http://www.technolibre.ca)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)
from odoo import api, fields, models, modules, tools


class CodeGeneratorModuleTemplateDependency(models.Model):
    _name = "code.generator.module.template.dependency"
    _inherit = "ir.module.module.dependency"
    _description = (
        "Code Generator Module Template Dependency, set by"
        " code_generator_template"
    )

    depend_id = fields.Many2one(compute=None)

    module_id = fields.Many2one(comodel_name="code.generator.module")
