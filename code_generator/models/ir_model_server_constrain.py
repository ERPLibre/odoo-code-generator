# !/usr/bin/env python3
# © 2021-2025 TechnoLibre (http://www.technolibre.ca)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)
import re

from odoo import _, api, fields, models
from odoo.addons.base.models.ir_model import SAFE_EVAL_BASE
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval, wrap_module

CONSTRAINEDLS = (
    "The field Constrained lists the fields that the server constrain will"
    " check. It is a comma-separated list of field names, like name, size."
)
SERVERCONSTRAIN = "%s Server constrain "
SYNTAXERRORMSG = "There is a syntax error in your %scode definition."

# The evaluation context of the code of a server constrain: a copy of the
# one of Odoo, which every manual computed field of the server evaluates
# its code with, so that nothing added here reaches it. safe_eval refuses
# a raw module in its context: each module is a wrap_module that exposes
# the names a constrain uses.
SAFE_EVAL_4FUNCTION = dict(
    SAFE_EVAL_BASE,
    re=wrap_module(
        re,
        [
            "compile",
            "escape",
            "findall",
            "finditer",
            "fullmatch",
            "match",
            "search",
            "split",
            "sub",
            "subn",
            "error",
            "A",
            "ASCII",
            "I",
            "IGNORECASE",
            "M",
            "MULTILINE",
            "S",
            "DOTALL",
            "X",
            "VERBOSE",
        ],
    ),
    ValidationError=ValidationError,
    api=wrap_module(api, ["constrains", "depends", "model", "onchange"]),
    models=wrap_module(models, ["AbstractModel", "Model", "TransientModel"]),
    fields=wrap_module(fields, ["Date", "Datetime"]),
    _=_,
)
PREDEFINEDVARS = (
    "You specified a non predefined variable. The predefined variables are"
    " self, datetime, dateutil, time, re, ValidationError and the ones"
    " accessible through self, like self.env."
)


def common_4constrains(el_self, code, message=SYNTAXERRORMSG):
    """

    :param el_self:
    :param code:
    :param message:
    :return:
    """

    try:
        safe_eval(code, SAFE_EVAL_4FUNCTION, {"self": el_self}, mode="exec")

    except ValueError:
        raise ValidationError(PREDEFINEDVARS)

    except SyntaxError:
        raise ValidationError(message)


class IrModelServerConstrain(models.Model):
    _name = "ir.model.server_constrain"
    _description = "Code Generator Model Server Constrains"
    _rec_name = "constrained"

    constrained = fields.Char(
        required=True,
        help="Constrained fields, ej: name, age",
    )

    m2o_ir_model = fields.Many2one(
        comodel_name="ir.model",
        domain=[("transient", "=", False)],
        string="Code generator Model",
        required=True,
        help="Model that will hold this server constrain",
        ondelete="cascade",
    )

    txt_code = fields.Text(
        string="Code",
        required=True,
        help="Code to execute",
    )

    @api.onchange("constrained")
    @api.constrains("constrained")
    def _check_constrained(self):
        if self.constrained:
            splitted = self.constrained.split(",")
            if list(
                filter(
                    lambda e: e.strip()
                    not in self.env[self.m2o_ir_model.model]._fields.keys(),
                    splitted,
                )
            ):
                raise ValidationError(CONSTRAINEDLS)

    @api.onchange("txt_code")
    @api.constrains("txt_code")
    def _check_txt_code(self):
        if self.txt_code:
            constrain_detail = SERVERCONSTRAIN % self.constrained
            common_4constrains(
                self.env[self.m2o_ir_model.model],
                self.txt_code,
                SYNTAXERRORMSG % constrain_detail,
            )
