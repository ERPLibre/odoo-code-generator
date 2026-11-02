# © 2026 TechnoLibre (http://www.technolibre.ca)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)
import os
import shutil

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
