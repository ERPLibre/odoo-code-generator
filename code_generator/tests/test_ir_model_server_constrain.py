# © 2026 TechnoLibre (http://www.technolibre.ca)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)
import types

from odoo.addons.base.models import ir_model
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged
from odoo.tools import safe_eval

from ..models import ir_model_server_constrain


@tagged("post_install", "-at_install")
class TestIrModelServerConstrain(TransactionCase):
    """The code of a server constrain is checked with its own evaluation
    context, and Odoo's context of the manual computed fields stays as
    Odoo defines it."""

    def test_odoo_safe_eval_base_left_untouched(self):
        """Once code_generator is loaded, SAFE_EVAL_BASE of Odoo holds none
        of the names of the constrain context, keeps its wrapped modules,
        and safe_eval takes it. Another module may add its own wrapped
        entries."""
        base = ir_model.SAFE_EVAL_BASE
        self.assertIsNot(ir_model_server_constrain.SAFE_EVAL_4FUNCTION, base)
        self.assertFalse(
            {"re", "ValidationError", "api", "models", "fields", "_"} & set(base)
        )
        self.assertIs(base["datetime"], safe_eval.datetime)
        self.assertIs(base["dateutil"], safe_eval.dateutil)
        self.assertIs(base["time"], safe_eval.time)
        safe_eval.check_values(base)

    def test_manual_computed_field(self):
        """A manual computed field evaluates its code with Odoo's context:
        a raw module there makes safe_eval refuse every one of them."""
        self.addCleanup(self.registry.reset_changes)
        self.env["ir.model.fields"].create(
            {
                "model_id": self.env["ir.model"]._get_id("res.partner"),
                "name": "x_cg_name_size",
                "field_description": "Name size",
                "ttype": "integer",
                "store": False,
                "depends": "name",
                "compute": "for record in self:\n"
                "    record['x_cg_name_size'] = len(record.name or '')",
            }
        )
        partner = self.env["res.partner"].create({"name": "Four"})
        self.assertEqual(partner.x_cg_name_size, 4)

    def test_constrain_context_has_no_raw_module(self):
        context = ir_model_server_constrain.SAFE_EVAL_4FUNCTION
        self.assertFalse(
            [k for k, v in context.items() if isinstance(v, types.ModuleType)]
        )
        safe_eval.check_values(context)

    def test_constrain_code_checked(self):
        """The code of a constrain runs on the model with re (its short
        flags and its error included), fields and ValidationError; a syntax
        error is refused in words."""
        model = self.env["ir.model"]._get("res.partner")
        code = (
            "digit = re.compile(r'\\d', re.I | re.M | re.S | re.X | re.A)\n"
            "for record in self:\n"
            "    if digit.search(record.name or ''):\n"
            "        raise ValidationError('No digit in a name.')\n"
            "try:\n"
            "    re.compile('(')\n"
            "except re.error:\n"
            "    pass\n"
            "today = fields.Date.today()\n"
        )
        constrain = self.env["ir.model.server_constrain"].create(
            {"m2o_ir_model": model.id, "constrained": "name", "txt_code": code}
        )
        self.assertEqual(constrain.txt_code, code)
        with self.assertRaises(ValidationError):
            self.env["ir.model.server_constrain"].create(
                {
                    "m2o_ir_model": model.id,
                    "constrained": "name",
                    "txt_code": "for record in self\n    pass\n",
                }
            )
