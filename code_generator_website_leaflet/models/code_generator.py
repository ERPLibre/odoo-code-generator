#!/usr/bin/env python3
# © 2021-2025 TechnoLibre (http://www.technolibre.ca)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)
from odoo import api, fields, models, modules, tools


class CodeGenerator(models.Model):
    _inherit = "code.generator.module"

    enable_generate_website_leaflet = fields.Boolean(
        string="Enable website leaflet feature",
        default=False,
        help=(
            "This variable need to be True to generate website leaflet if"
            " enable_generate_all is False"
        ),
    )
