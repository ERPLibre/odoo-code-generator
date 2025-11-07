#!/usr/bin/env python3
# © 2021-2025 TechnoLibre (http://www.technolibre.ca)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)
from odoo import api, fields, models, modules, tools


class IrModuleModule(models.Model):
    _inherit = "ir.module.module"

    header_manifest = fields.Text(
        string="Header",
        help="Header comment in __manifest__.py file.",
    )
