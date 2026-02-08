#!/usr/bin/env python3
# © 2021-2025 TechnoLibre (http://www.technolibre.ca)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)
import logging

from odoo import _, api, fields, models, tools

_logger = logging.getLogger(__name__)


class IrModelConstraint(models.Model):
    _inherit = "ir.model.constraint"

    code_generator_id = fields.Many2one(
        comodel_name="code.generator.module",
        string="Code Generator",
        ondelete="cascade",
    )

    message = fields.Char()

    model_state = fields.Selection(related="model.state")

    module = fields.Many2one(
        default=lambda self: self.env["ir.module.module"]
        .search([("name", "=", "base")])[0]
        .id,
    )
