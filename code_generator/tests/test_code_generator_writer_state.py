# © 2026 TechnoLibre (http://www.technolibre.ca)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)
import ast
import os
import shutil
import tempfile
from unittest.mock import patch

from odoo.tests import tagged

from .. import code_generator_data
from .common import CodeGeneratorCase


@tagged("post_install", "-at_install")
class TestCodeGeneratorWriterState(CodeGeneratorCase):
    def _generator_with_model(self, name):
        generator = self._new_generator(name)
        generator.add_update_model(
            f"x_{name}.item",
            dct_field={
                "x_name": {"ttype": "char", "field_description": "Name"}
            },
        )
        return generator

    def test_two_writers_on_one_cursor(self):
        """The second generation of a cursor writes its own module, under
        its own directory, and the cursor keeps no state afterwards."""
        first = self._generate(self._generator_with_model("test_cg_fix_one"))
        self.assertFalse(hasattr(self.env.cr, "_code_generator_data"))
        second = self._generate(self._generator_with_model("test_cg_fix_two"))
        self.assertFalse(hasattr(self.env.cr, "_code_generator_data"))

        self.assertNotEqual(
            os.path.dirname(first.rootdir), os.path.dirname(second.rootdir)
        )
        self.assertEqual(os.path.basename(second.rootdir), "test_cg_fix_two")
        for path in second.get_list_path_file():
            with self.subTest(path=path):
                self.assertTrue(path.startswith(second.rootdir + os.sep))
        self.assertTrue(
            os.path.isfile(
                os.path.join(
                    second.rootdir, "models", "x_test_cg_fix_two_item.py"
                )
            )
        )
        self.assertFalse(
            os.path.exists(
                os.path.join(
                    first.rootdir, "models", "x_test_cg_fix_two_item.py"
                )
            )
        )
        manifest = ast.literal_eval(self._read(second, "__manifest__.py"))
        self.assertEqual(manifest["name"], "Test Cg Fix Two")

    def test_writer_run_closes_state_on_error(self):
        generator = self._generator_with_model("test_cg_fix_error")
        writer_class = type(self.env["code.generator.writer"])

        def failing(writer, module, python_controller_writer):
            raise ValueError("generation failed")

        path = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, path, ignore_errors=True)
        with patch.object(
            writer_class, "get_lst_file_generate", failing
        ), patch.object(tempfile, "mkdtemp", return_value=path):
            with self.assertRaises(ValueError):
                self.env["code.generator.writer"].create(
                    [{"code_generator_ids": generator.ids}]
                )
        self.assertFalse(hasattr(self.env.cr, "_code_generator_data"))

    def test_no_state_outside_a_writer_run(self):
        with self.assertRaises(RuntimeError):
            code_generator_data.get_code_generator_data(self.env)
