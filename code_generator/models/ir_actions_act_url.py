# !/usr/bin/env python3
# © 2021-2025 TechnoLibre (http://www.technolibre.ca)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)
from odoo import api, fields, models, modules, tools


class IrActionsActUrl(models.Model):
    _inherit = "ir.actions.act_url"

    m2o_code_generator = fields.Many2one(
        comodel_name="code.generator.module",
        string="Code Generator",
        store=True,
        help="Code Generator relation",
        ondelete="cascade",
    )
