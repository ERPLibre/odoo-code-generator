#!/usr/bin/env python3
# © 2021-2025 TechnoLibre (http://www.technolibre.ca)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class CodeGeneratorAddControllerWizard(models.TransientModel):
    _name = "code.generator.add.controller.wizard"
    _description = "Code Generator Add Controller Wizard"

    code_generator_id = fields.Many2one(
        comodel_name="code.generator.module",
        string="Code Generator",
        required=True,
        ondelete="cascade",
    )

    field_ids = fields.Many2many(
        comodel_name="ir.model.fields",
        string="Fields",
        help="Select the fields to expose in controller routes.",
    )

    model_ids = fields.Many2many(
        comodel_name="ir.model",
        string="Models",
        help="Select models to generate controller routes for.",
    )

    user_id = fields.Many2one(
        comodel_name="res.users",
        string="User",
        required=True,
        default=lambda s: s.env.user.id,
    )

    @api.onchange("model_ids")
    def _onchange_model_ids(self):
        field_ids = [
            field_id.id
            for model_id in self.model_ids
            for field_id in model_id.field_id
        ]
        self.field_ids = [(6, 0, field_ids)]

    def button_generate_add_controller(self):
        if not self.model_ids:
            raise UserError(
                _("Please select at least one model to generate"
                  " controller routes.")
            )

        module = self.code_generator_id
        lst_model_linked = []

        for model_id in self.model_ids:
            # Link model to code generator module if not already linked
            if model_id.m2o_module != module:
                model_id.m2o_module = module.id

            # Add module dependency if needed
            module_name = model_id.modules
            if module_name:
                for mod_name in [
                    a.strip() for a in module_name.split(",")
                ]:
                    if not mod_name:
                        continue
                    dep_module = self.env["ir.module.module"].search(
                        [("name", "=", mod_name)], limit=1
                    )
                    if dep_module:
                        existing = self.env[
                            "code.generator.module.dependency"
                        ].search_count([
                            ("module_id", "=", module.id),
                            ("depend_id", "=", dep_module.id),
                        ])
                        if not existing:
                            self.env[
                                "code.generator.module.dependency"
                            ].create([{
                                "module_id": module.id,
                                "depend_id": dep_module.id,
                                "name": dep_module.display_name,
                            }])

            lst_model_linked.append(model_id.model)

        _logger.info(
            "Linked %d model(s) to module '%s' for controller"
            " generation: %s",
            len(lst_model_linked),
            module.name,
            ", ".join(lst_model_linked),
        )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Controller Models Linked"),
                "message": _(
                    "%d model(s) linked to module '%s': %s. "
                    "Use PythonControllerWriter programmatically "
                    "to generate the controller code."
                ) % (
                    len(lst_model_linked),
                    module.name,
                    ", ".join(lst_model_linked),
                ),
                "sticky": False,
                "type": "info",
            },
        }
