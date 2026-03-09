#!/usr/bin/env python3
# © 2021-2025 TechnoLibre (http://www.technolibre.ca)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestCodeGeneratorModule(TransactionCase):
    """Basic tests for code.generator.module CRUD operations."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.module = cls.env["code.generator.module"].create([{
            "name": "test_generated_module",
            "shortdesc": "Test Generated Module",
        }])

    def test_module_creation(self):
        self.assertTrue(self.module.id)
        self.assertEqual(self.module.name, "test_generated_module")

    def test_module_add_dependency(self):
        base_module = self.env["ir.module.module"].search(
            [("name", "=", "base")], limit=1
        )
        dep = self.env["code.generator.module.dependency"].create([{
            "module_id": self.module.id,
            "depend_id": base_module.id,
            "name": base_module.display_name,
        }])
        self.assertTrue(dep.id)
        self.assertIn(
            dep, self.module.dependencies_id
        )


class TestCodeGeneratorWriter(TransactionCase):
    """Tests for writer utility methods."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.writer = cls.env["code.generator.writer"]

    def test_fmt_underscores(self):
        self.assertEqual(
            self.writer._fmt_underscores("res.partner"),
            "res_partner",
        )

    def test_fmt_camel(self):
        result = self.writer._fmt_camel("res.partner")
        self.assertEqual(result, "ResPartner")

    def test_fmt_title(self):
        result = self.writer._fmt_title("res.partner")
        self.assertEqual(result, "Res Partner")


class TestModelAttributes(TransactionCase):
    """Tests for new model attributes (_inherits, _parent_store)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.module = cls.env["code.generator.module"].create([{
            "name": "test_model_attrs",
            "shortdesc": "Test Model Attributes",
        }])

    def test_inherits_field(self):
        model_id = self.module.add_update_model(
            "x_test.inherits.model",
            dct_field={
                "partner_id": {
                    "ttype": "many2one",
                    "relation": "res.partner",
                    "required": True,
                },
            },
        )
        model_id.inherits_model = "res.partner:partner_id"
        self.assertEqual(
            model_id.inherits_model, "res.partner:partner_id"
        )

    def test_parent_store_field(self):
        model_id = self.module.add_update_model(
            "x_test.parent.store",
            dct_field={
                "parent_id": {
                    "ttype": "many2one",
                    "relation": "x_test.parent.store",
                },
            },
        )
        model_id.parent_store = True
        self.assertTrue(model_id.parent_store)


class TestAccessRuleHelper(TransactionCase):
    """Tests for the add_access_rule helper."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.module = cls.env["code.generator.module"].create([{
            "name": "test_access_rules",
            "shortdesc": "Test Access Rules",
        }])
        cls.model_id = cls.env["ir.model"].search(
            [("model", "=", "res.partner")], limit=1
        )

    def test_add_access_rule_user(self):
        rule = self.module.add_access_rule(
            self.model_id,
            "base.group_user",
            domain_force="[(1, '=', 1)]",
        )
        self.assertTrue(rule.id)
        self.assertEqual(rule.domain_force, "[(1, '=', 1)]")
        self.assertTrue(rule.perm_read)

    def test_add_access_rule_auto_name(self):
        rule = self.module.add_access_rule(
            self.model_id,
            "base.group_user",
        )
        self.assertIn("res_partner", rule.name)
        self.assertIn("group_user", rule.name)


class TestOnchangeHelper(TransactionCase):
    """Tests for the add_onchange_method helper."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.module = cls.env["code.generator.module"].create([{
            "name": "test_onchange",
            "shortdesc": "Test Onchange",
        }])
        cls.model_id = cls.env["ir.model"].search(
            [("model", "=", "res.partner")], limit=1
        )

    def test_add_onchange_method(self):
        self.module.add_onchange_method(
            self.model_id,
            field_names="name",
            code="self.display_name = self.name",
        )
        code_rec = self.env["code.generator.model.code"].search([
            ("m2o_module", "=", self.module.id),
            ("name", "=", "_onchange_name"),
        ])
        self.assertTrue(code_rec)
        self.assertIn("@api.onchange", code_rec.decorator)

    def test_add_onchange_multiple_fields(self):
        self.module.add_onchange_method(
            self.model_id,
            field_names=["name", "email"],
        )
        code_rec = self.env["code.generator.model.code"].search([
            ("m2o_module", "=", self.module.id),
            ("name", "=", "_onchange_name_email"),
        ])
        self.assertTrue(code_rec)
        self.assertIn('"name"', code_rec.decorator)
        self.assertIn('"email"', code_rec.decorator)


class TestAddControllerWizard(TransactionCase):
    """Tests for the add controller wizard."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.module = cls.env["code.generator.module"].create([{
            "name": "test_controller_module",
            "shortdesc": "Test Controller Module",
        }])

    def test_wizard_no_model_raises_error(self):
        wizard = self.env[
            "code.generator.add.controller.wizard"
        ].create([{
            "code_generator_id": self.module.id,
        }])
        with self.assertRaises(UserError):
            wizard.button_generate_add_controller()

    def test_wizard_links_model(self):
        model_id = self.env["ir.model"].search(
            [("model", "=", "res.partner")], limit=1
        )
        wizard = self.env[
            "code.generator.add.controller.wizard"
        ].create([{
            "code_generator_id": self.module.id,
            "model_ids": [(6, 0, [model_id.id])],
        }])
        result = wizard.button_generate_add_controller()
        self.assertEqual(result["type"], "ir.actions.client")
        self.assertEqual(model_id.m2o_module, self.module)
