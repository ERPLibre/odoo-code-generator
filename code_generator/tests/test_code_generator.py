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
