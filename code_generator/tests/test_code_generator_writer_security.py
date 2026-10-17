# © 2026 TechnoLibre (http://www.technolibre.ca)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)
import csv
import io

from lxml import etree
from odoo.tests import tagged

from .common import CodeGeneratorCase

MODULE = "test_cg_fix_security"
MODEL = "x_test_cg_fix_security.item"


@tagged("post_install", "-at_install")
class TestCodeGeneratorWriterSecurity(CodeGeneratorCase):
    """The access rights and record rules a generated module carries:
    the CSV of the access rights and the XML of the rules."""

    def setUp(self):
        super().setUp()
        # A custom model joins the registry: back to the database state
        # once the test is rolled back.
        self.addCleanup(self.registry.reset_changes)
        self.generator = self._new_generator(MODULE)
        self.generator.add_update_model(
            MODEL,
            dct_field={
                "x_name": {"ttype": "char", "field_description": "Name"}
            },
        )
        self.model = self.env["ir.model"]._get(MODEL)
        self.group = self.env.ref("base.group_user")

    def _bind(self, record, name):
        self.env["ir.model.data"].create(
            [
                {
                    "module": MODULE,
                    "name": name,
                    "model": record._name,
                    "res_id": record.id,
                }
            ]
        )

    def test_access_csv_columns(self):
        """Each value goes under its header, and a name with a comma is
        quoted."""
        bound = self.env["ir.model.access"].create(
            [
                {
                    "name": "Items, internal users",
                    "model_id": self.model.id,
                    "group_id": self.group.id,
                    "perm_read": True,
                    "perm_write": True,
                    "perm_create": False,
                    "perm_unlink": False,
                }
            ]
        )
        self._bind(bound, "access_item_user")
        self.env["ir.model.access"].create(
            [
                {
                    "name": "item_public",
                    "model_id": self.model.id,
                    "perm_read": True,
                    "perm_write": False,
                    "perm_create": True,
                    "perm_unlink": True,
                }
            ]
        )
        writer = self._generate(self.generator)
        rows = list(
            csv.DictReader(
                io.StringIO(self._read(writer, "security/ir.model.access.csv"))
            )
        )
        by_id = {row["id"]: row for row in rows}
        self.assertEqual(
            by_id["access_item_user"],
            {
                "id": "access_item_user",
                "name": "Items, internal users",
                "model_id:id": "model_x_test_cg_fix_security_item",
                "group_id:id": "base.group_user",
                "perm_read": "1",
                "perm_write": "1",
                "perm_create": "0",
                "perm_unlink": "0",
            },
        )
        self.assertEqual(
            by_id["item_public"],
            {
                "id": "item_public",
                "name": "item_public",
                "model_id:id": "model_x_test_cg_fix_security_item",
                "group_id:id": "",
                "perm_read": "1",
                "perm_write": "0",
                "perm_create": "1",
                "perm_unlink": "1",
            },
        )

    def test_model_reference(self):
        """A model of the module is referenced by its local external id,
        another model by the external id of the module that defines it."""
        Writer = self.env["code.generator.writer"]
        self.assertEqual(
            Writer._get_model_xmlid_ref(self.model, self.generator),
            "model_x_test_cg_fix_security_item",
        )
        category = self.env["ir.model"]._get("res.partner.category")
        self.assertEqual(
            Writer._get_model_xmlid_ref(category, self.generator),
            "base.model_res_partner_category",
        )

    def test_rule_xml(self):
        """The rule keeps the external id it has under the module, its name
        and its domain round-trip through XML, and its groups are a valid
        eval on ``groups``."""
        name = 'Own items & "drafts" <first>'
        domain = "[('id', '<', 1000), ('x_name', '!=', '&')]"
        rule = self.env["ir.rule"].create(
            [
                {
                    "name": name,
                    "model_id": self.model.id,
                    "domain_force": domain,
                    "groups": [(6, 0, self.group.ids)],
                    "perm_create": False,
                }
            ]
        )
        self._bind(rule, "rule_item_own")
        writer = self._generate(self.generator)
        root = etree.fromstring(
            self._read(writer, f"security/{MODULE}.xml").encode()
        )
        record = root.find(".//record[@model='ir.rule']")
        self.assertEqual(record.get("id"), "rule_item_own")
        self.assertEqual(record.find("field[@name='name']").text, name)
        self.assertEqual(
            record.find("field[@name='domain_force']").text, domain
        )
        self.assertEqual(
            record.find("field[@name='model_id']").get("ref"),
            "model_x_test_cg_fix_security_item",
        )
        self.assertIsNone(record.find("field[@name='groups_id']"))
        self.assertEqual(
            record.find("field[@name='groups']").get("eval"),
            "[(6, 0, [ref('base.group_user')])]",
        )
        self.assertEqual(
            record.find("field[@name='perm_create']").get("eval"), "False"
        )
        self.assertIsNone(record.find("field[@name='perm_read']"))

    def test_rule_id_and_long_texts(self):
        """A quote in the external id of a rule stays inside its attribute,
        and a name or a domain longer than a line keeps its value: the
        security file is formatted without wrapping."""
        name = "Items of the user " + "and of the followers " * 6
        domain = (
            "['|', ('create_uid', '=', user.id), "
            "('x_name', 'in', ['" + "', '".join(["value"] * 20) + "'])]"
        )
        rule = self.env["ir.rule"].create(
            [
                {
                    "name": name,
                    "model_id": self.model.id,
                    "domain_force": domain,
                }
            ]
        )
        self._bind(rule, 'rule_item_"quoted"')
        writer = self._generate(self.generator)
        root = etree.fromstring(
            self._read(writer, f"security/{MODULE}.xml").encode()
        )
        records = root.findall(".//record[@model='ir.rule']")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].get("id"), 'rule_item_"quoted"')
        self.assertEqual(records[0].find("field[@name='name']").text, name)
        self.assertEqual(
            records[0].find("field[@name='domain_force']").text, domain
        )

    def test_groups_etree_quoted(self):
        node = self.env["code.generator.writer"]._get_m2m_groups_etree(
            self.group
        )
        self.assertEqual(node.get("name"), "groups_id")
        self.assertEqual(
            node.get("eval"), "[(6, 0, [ref('base.group_user')])]"
        )
