# © 2026 TechnoLibre (http://www.technolibre.ca)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)
from odoo import Command
from odoo.tests import tagged

from .common import CodeGeneratorCase


@tagged("post_install", "-at_install")
class TestIrModelRecName(CodeGeneratorCase):
    """The record label of a custom model built from its ir.model row."""

    def setUp(self):
        super().setUp()
        # A custom model joins the registry: back to the database state
        # once the test is rolled back.
        self.addCleanup(self.registry.reset_changes)

    def _custom_model(self, model, field_name, **values):
        return self.env["ir.model"].create(
            [
                {
                    "name": "Code generator test item",
                    "model": model,
                    "state": "manual",
                    "field_id": [
                        Command.create(
                            {
                                "name": field_name,
                                "field_description": "Name",
                                "ttype": "char",
                            }
                        )
                    ],
                    **values,
                }
            ]
        )

    def test_custom_model_with_x_name_only(self):
        """The default « name » of the column is not forced on a model
        that has no such field: Odoo picks x_name."""
        record = self._custom_model("x_test_cg_fix_rec_name", "x_name")
        self.assertEqual(record.rec_name, "name")
        self.assertEqual(
            self.env["x_test_cg_fix_rec_name"]._rec_name, "x_name"
        )

    def test_custom_model_rec_name_kept(self):
        self._custom_model(
            "x_test_cg_fix_rec_label", "x_label", rec_name="x_label"
        )
        self.assertEqual(
            self.env["x_test_cg_fix_rec_label"]._rec_name, "x_label"
        )
