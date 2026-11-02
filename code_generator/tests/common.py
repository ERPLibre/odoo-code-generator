# © 2026 TechnoLibre (http://www.technolibre.ca)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)
import ast
import os
import shutil
from unittest.mock import patch

from odoo.tests import TransactionCase


class CodeGeneratorCase(TransactionCase):
    """Generation of throwaway modules: the files go to the temporary
    directory of the writer, never synchronised into a repository, and
    the directory is removed at the end of the test."""

    def _new_generator(self, name, **values):
        vals = {
            "name": name,
            "shortdesc": name.replace("_", " ").title(),
            "license": "AGPL-3",
            "enable_sync_code": False,
        }
        vals.update(values)
        return self.env["code.generator.module"].create([vals])

    def _new_constraint(
        self, model, generator, name, definition, message, **values
    ):
        """An ir.model.constraint of ``generator``, as the writer reads it;
        ``values`` overrides the other columns of the row.

        Only the record matters to the writer: the SQL constraint that
        the create of code_generator adds to the table is left out.
        """
        with patch(
            "odoo.addons.code_generator.models.ir_model_constraint"
            ".sql_constraint",
            return_value=True,
        ):
            return self.env["ir.model.constraint"].create(
                [
                    {
                        "name": name,
                        "definition": definition,
                        "message": message,
                        "type": "u",
                        "model": model.id,
                        "code_generator_id": generator.id,
                        **values,
                    }
                ]
            )

    def _generate(self, generator):
        writer = self.env["code.generator.writer"].create(
            [{"code_generator_ids": generator.ids}]
        )
        self.addCleanup(
            shutil.rmtree, os.path.dirname(writer.rootdir), ignore_errors=True
        )
        return writer

    @staticmethod
    def _read(writer, relative_path):
        with open(
            os.path.join(writer.rootdir, relative_path), encoding="utf-8"
        ) as file:
            return file.read()

    def _parse_class(self, writer, relative_path):
        """The first class of the generated Python file, parsed: a syntax
        error in the file fails the test here."""
        tree = ast.parse(self._read(writer, relative_path))
        return next(n for n in tree.body if isinstance(n, ast.ClassDef))

    @staticmethod
    def _class_attributes(class_node):
        """{name: value} of the literal class attributes of the class."""
        result = {}
        for node in class_node.body:
            if (
                isinstance(node, ast.Assign)
                and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
            ):
                try:
                    result[node.targets[0].id] = ast.literal_eval(node.value)
                except ValueError:
                    result[node.targets[0].id] = ast.unparse(node.value)
        return result

    @staticmethod
    def _field_keywords(class_node, field_name):
        """{keyword: value} of the literal arguments of a field."""
        for node in class_node.body:
            if (
                isinstance(node, ast.Assign)
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == field_name
            ):
                return {
                    kw.arg: ast.literal_eval(kw.value)
                    for kw in node.value.keywords
                    if isinstance(kw.value, ast.Constant)
                }
        raise AssertionError(f"Field {field_name} is not generated.")
