# © 2026 TechnoLibre (http://www.technolibre.ca)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)
import ast

from code_writer import CodeWriter
from odoo.tests import tagged

from ..models.code_generator_writer import py_str, py_str_multiline
from .common import CodeGeneratorCase

# Strings that a naive quoting breaks: quotes, backslashes, triple
# quotes, line breaks other than \n, a quote or a backslash at the end.
TRICKY_STRINGS = [
    "",
    "plain",
    "it's",
    'say "hi"',
    "back\\slash",
    "trailing backslash\\",
    "trailing quote'",
    "\\'already escaped",
    'triple """ inside\nand a line',
    "triple ''' inside\nand a line",
    "both \"\"\" and '''\nlines",
    "line 1\nline 2",
    'ends with a quote\n"',
    "ends with a quote\n'",
    "tab\tand\nnewline",
    "carriage\r\nreturn",
    "accents é à ç\nline",
    "separator here\nline",
    "back\\slash\nline\\",
]

TRICKY_HELP = "It's a \"quoted\" help\nwith a back\\slash \\n and '''"
TRICKY_MESSAGE = 'It\'s "taken" \\ already'


@tagged("post_install", "-at_install")
class TestCodeGeneratorWriterLiteral(CodeGeneratorCase):
    def test_py_str_round_trip(self):
        for value in TRICKY_STRINGS:
            with self.subTest(value=value):
                literal = py_str(value)
                self.assertNotIn("\n", literal)
                self.assertEqual(ast.literal_eval(literal), value)

    def test_py_str_multiline_round_trip_through_code_writer(self):
        for value in TRICKY_STRINGS:
            with self.subTest(value=value):
                literal = py_str_multiline(value)
                self.assertEqual(ast.literal_eval(literal), value)
                # The literal survives emit_raw, which splits on every
                # line break str.splitlines knows.
                cw = CodeWriter()
                with cw.indent():
                    cw.emit_raw(f"{cw.mk_indent()}value = {literal}\n")
                namespace = {}
                exec(compile(cw.render().strip(), "<cw>", "exec"), namespace)
                self.assertEqual(namespace["value"], value)

    def test_py_str_multiline_keeps_lines_visible(self):
        literal = py_str_multiline("line 1\nline 2")
        self.assertEqual(literal, '"""line 1\nline 2"""')
        self.assertEqual(py_str_multiline("one line"), "'one line'")

    def test_manifest_strings(self):
        generator = self._new_generator(
            "test_cg_fix_manifest",
            shortdesc='It\'s "the" module \\',
            summary="Summary with ' and \"",
            author="O'Brien, Back\\slash",
            description="First line\nIt's the 'second' \\ line",
            website="https://example.org/a'b",
        )
        writer = self._generate(generator)
        manifest = ast.literal_eval(self._read(writer, "__manifest__.py"))
        self.assertEqual(manifest["name"], 'It\'s "the" module \\')
        self.assertEqual(manifest["summary"], "Summary with ' and \"")
        self.assertEqual(manifest["author"], "O'Brien, Back\\slash")
        self.assertEqual(
            manifest["description"], "First line\nIt's the 'second' \\ line"
        )
        self.assertEqual(manifest["website"], "https://example.org/a'b")

    def test_model_strings_and_sql_constraints(self):
        generator = self._new_generator("test_cg_fix_model")
        model = generator.add_update_model(
            "x_test_cg_fix.house",
            model_name='House "quoted" it\'s',
            dct_field={
                "x_name": {"ttype": "char", "field_description": "Name"},
                "x_note": {
                    "ttype": "char",
                    "field_description": 'Note\'s "label"',
                    "help": TRICKY_HELP,
                },
            },
        )
        self._new_constraint(
            model, generator, "name_uniq", "unique(x_name)", TRICKY_MESSAGE
        )
        writer = self._generate(generator)
        class_node = self._parse_class(writer, "models/x_test_cg_fix_house.py")
        attributes = self._class_attributes(class_node)
        self.assertEqual(attributes["_description"], 'House "quoted" it\'s')
        self.assertEqual(
            attributes["_sql_constraints"],
            [("name_uniq", "unique(x_name)", TRICKY_MESSAGE)],
        )
        keywords = self._field_keywords(class_node, "x_note")
        self.assertEqual(keywords["help"], TRICKY_HELP)
        self.assertEqual(keywords["string"], 'Note\'s "label"')

    def test_extension_keeps_only_its_own_class_attributes(self):
        """An _inherit class of res.partner carries neither the core
        constraints nor the core _order, only what the generator adds."""
        generator = self._new_generator("test_cg_fix_partner")
        model = generator.add_update_model(
            "res.partner",
            dct_field={
                "x_cg_fix_code": {
                    "ttype": "char",
                    "field_description": "Code",
                },
            },
            lst_depend_model=["res.partner"],
        )
        self.assertIn(
            "res_partner_check_name", model.o2m_constraints.mapped("name")
        )
        self.assertEqual(model.order, self.env["res.partner"]._order)
        self._new_constraint(
            model,
            generator,
            "res_partner_x_cg_fix_code_uniq",
            "unique(x_cg_fix_code)",
            TRICKY_MESSAGE,
        )
        writer = self._generate(generator)
        class_node = self._parse_class(writer, "models/res_partner.py")
        attributes = self._class_attributes(class_node)
        self.assertEqual(attributes["_inherit"], "res.partner")
        self.assertNotIn("_name", attributes)
        self.assertNotIn("_order", attributes)
        self.assertNotIn("_description", attributes)
        self.assertEqual(
            attributes["_sql_constraints"],
            [("x_cg_fix_code_uniq", "unique(x_cg_fix_code)", TRICKY_MESSAGE)],
        )
        self.assertEqual(
            self._field_keywords(class_node, "x_cg_fix_code")["string"], "Code"
        )

    def _partner_extension(self, name):
        generator = self._new_generator(name)
        model = generator.add_update_model(
            "res.partner",
            dct_field={
                "x_cg_fix_code": {
                    "ttype": "char",
                    "field_description": "Code",
                },
            },
            lst_depend_model=["res.partner"],
        )
        return generator, model

    def _ir_module(self, name):
        return self.env["ir.module.module"].create(
            [{"name": name, "state": "uninstalled"}]
        )

    def _generated_sql_constraints(self, generator):
        writer = self._generate(generator)
        class_node = self._parse_class(writer, "models/res_partner.py")
        return self._class_attributes(class_node).get("_sql_constraints")

    def test_extension_keeps_its_reflected_override_of_a_core_key(self):
        """A row of check_name that Odoo reflected for the module (an
        installed version, or the template module) is the override of
        the module: emitted once, and the row of base stays out."""
        generator, model = self._partner_extension(
            "test_cg_fix_partner_override"
        )
        self._new_constraint(
            model,
            generator,
            "res_partner_check_name",
            "CHECK(name IS NOT NULL)",
            TRICKY_MESSAGE,
            code_generator_id=False,
            module=self._ir_module(generator.name).id,
        )
        self.assertEqual(
            len(
                model.o2m_constraints.filtered(
                    lambda c: c.name == "res_partner_check_name"
                )
            ),
            2,
        )
        self.assertEqual(
            self._generated_sql_constraints(generator),
            [("check_name", "CHECK(name IS NOT NULL)", TRICKY_MESSAGE)],
        )

    def test_extension_keeps_its_generator_override_of_a_core_key(self):
        """A row of check_name that the generator created is the override
        of the module, whatever module the row names."""
        generator, model = self._partner_extension(
            "test_cg_fix_partner_override_cg"
        )
        self._new_constraint(
            model,
            generator,
            "res_partner_check_name",
            "CHECK(name IS NOT NULL)",
            TRICKY_MESSAGE,
            module=self._ir_module("test_cg_fix_other_owner").id,
        )
        self.assertEqual(
            self._generated_sql_constraints(generator),
            [("check_name", "CHECK(name IS NOT NULL)", TRICKY_MESSAGE)],
        )

    def test_extension_emits_one_row_per_key(self):
        """A key with a reflected row and a generator row of the module is
        emitted once, from the row of the generator."""
        generator, model = self._partner_extension(
            "test_cg_fix_partner_override_both"
        )
        self._new_constraint(
            model,
            generator,
            "res_partner_check_name",
            "CHECK(name IS NOT NULL)",
            "Reflected message",
            code_generator_id=False,
            module=self._ir_module(generator.name).id,
        )
        self._new_constraint(
            model,
            generator,
            "res_partner_check_name",
            "CHECK(name IS NOT NULL)",
            TRICKY_MESSAGE,
            module=self._ir_module("test_cg_fix_other_owner").id,
        )
        self.assertEqual(
            self._generated_sql_constraints(generator),
            [("check_name", "CHECK(name IS NOT NULL)", TRICKY_MESSAGE)],
        )
