#!/usr/bin/env python3
# © 2021-2025 TechnoLibre (http://www.technolibre.ca)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)
from odoo import fields, models


class ResGroups(models.Model):
    _inherit = "res.groups"

    m2o_module = fields.Many2one(
        comodel_name="code.generator.module",
        string="Module",
        help="Module",
        ondelete="cascade",
    )
