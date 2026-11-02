# © 2026 TechnoLibre (http://www.technolibre.ca)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)
from odoo.tests import tagged

from .common import CodeGeneratorCase


@tagged("post_install", "-at_install")
class TestCodeGeneratorModuleUnlink(CodeGeneratorCase):
    def test_foreign_key_is_set_null(self):
        self.env.cr.execute(
            """
            SELECT c.confdeltype
              FROM pg_constraint c
              JOIN pg_attribute a
                ON a.attrelid = c.conrelid AND a.attnum = ANY (c.conkey)
             WHERE c.contype = 'f'
               AND c.conrelid = 'ir_model'::regclass
               AND a.attname = 'm2o_module'
            """
        )
        self.assertEqual(self.env.cr.fetchall(), [("n",)])

    def test_unlink_keeps_existing_models(self):
        """Deleting a generator linked to res.partner keeps its ir.model,
        and still deletes the manual model the generator created."""
        generator = self._new_generator("test_cg_fix_unlink")
        partner_model = generator.add_update_model(
            "res.partner", lst_depend_model=["res.partner"]
        )
        owned_model = generator.add_update_model(
            "x_test_cg_fix_unlink.item",
            dct_field={
                "x_name": {"ttype": "char", "field_description": "Name"}
            },
        )
        self.assertEqual(partner_model.m2o_module, generator)
        self.assertEqual(owned_model.m2o_module, generator)

        generator.unlink()

        self.assertTrue(partner_model.exists())
        self.assertFalse(partner_model.m2o_module)
        self.assertEqual(
            self.env["ir.model"]._get_id("res.partner"), partner_model.id
        )
        self.assertFalse(owned_model.exists())
        self.assertNotIn("x_test_cg_fix_unlink.item", self.env.registry)
