#!/usr/bin/env python3
# © 2021-2025 TechnoLibre (http://www.technolibre.ca)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)
from odoo import api, fields, models, modules, tools


class CodeGeneratorPyclass(models.Model):
    _name = "code.generator.pyclass"
    _description = "Code Generator Python Class"

    name = fields.Char(
        string="Class name",
        required=True,
        help="Class name",
    )

    module = fields.Char(
        string="Class path",
        help="Class path",
    )
