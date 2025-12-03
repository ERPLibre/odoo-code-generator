#!/usr/bin/env python3
# © 2021-2025 TechnoLibre (http://www.technolibre.ca)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)
from odoo import api, fields, models, modules, tools


class IrUiMenu(models.Model):
    _inherit = "ir.ui.menu"

    ignore_act_window = fields.Boolean(
        help="Set True to force no act_window, like a parent menu."
    )

    m2o_module = fields.Many2one(
        comodel_name="code.generator.module",
        string="Module",
        help="Module",
        ondelete="cascade",
    )
