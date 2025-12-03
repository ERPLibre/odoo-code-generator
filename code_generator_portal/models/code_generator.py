#!/usr/bin/env python3
# © 2021-2025 TechnoLibre (http://www.technolibre.ca)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)
from odoo import api, fields, models, modules, tools


class CodeGeneratorModule(models.Model):
    _inherit = "code.generator.module"

    selected_model_portal_ids = fields.Many2many(comodel_name="ir.model")

    def has_field_type_date(self):
        for ir_model in self.o2m_models:
            for ir_model_field in ir_model.field_id:
                if ir_model_field.ttype in ("date", "datetime"):
                    return True
        return False
