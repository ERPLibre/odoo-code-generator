#!/usr/bin/env python3
# © 2021-2025 TechnoLibre (http://www.technolibre.ca)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    s_data2export = fields.Selection(
        selection=[
            (
                "nonomenclator",
                "Include the data of all of the selected models to export.",
            ),
            (
                "nomenclator",
                "Include the data of the selected models to export set it as"
                " nomenclator.",
            ),
        ],
        string="Model data to export",
        default="nomenclator",
        config_parameter="code_generator.s_data2export",
        help="Model data to export",
    )
