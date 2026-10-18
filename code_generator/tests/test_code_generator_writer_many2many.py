# © 2026 TechnoLibre (http://www.technolibre.ca)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)
from odoo.tests import tagged

from .common import CodeGeneratorCase

MODEL = "x_test_cg_m2m.house"
NAMED_TABLE = "x_test_cg_m2m_house_tag_rel"
SELF_TABLE = "x_test_cg_m2m_house_parent_rel"


@tagged("post_install", "-at_install")
class TestCodeGeneratorWriterMany2many(CodeGeneratorCase):
    """The relation table and the columns of a many2many: written in the
    generated field whenever one of them differs from the names the ORM
    gives a Python many2many that names none, so that the module uses the
    table of the database."""

    def test_names_of_the_relation(self):
        generator = self._new_generator("test_cg_fix_many2many")
        generator.add_update_model(
            MODEL,
            model_name="House",
            dct_field={
                "x_name": {"ttype": "char", "field_description": "Name"},
                # The table differs from the default, the columns do not.
                "x_tag_ids": {
                    "ttype": "many2many",
                    "field_description": "Tags",
                    "relation": "res.partner.category",
                    "relation_table": NAMED_TABLE,
                    "column1": "x_test_cg_m2m_house_id",
                    "column2": "res_partner_category_id",
                },
                # Every name is the default one.
                "x_country_ids": {
                    "ttype": "many2many",
                    "field_description": "Countries",
                    "relation": "res.country",
                    "relation_table": "res_country_x_test_cg_m2m_house_rel",
                    "column1": "x_test_cg_m2m_house_id",
                    "column2": "res_country_id",
                },
                # A relation of the model to itself has no default names.
                "x_parent_ids": {
                    "ttype": "many2many",
                    "field_description": "Parents",
                    "relation": MODEL,
                    "relation_table": SELF_TABLE,
                    "column1": "id1",
                    "column2": "id2",
                },
            },
        )
        writer = self._generate(generator)
        class_node = self._parse_class(writer, "models/x_test_cg_m2m_house.py")
        tags = self._field_keywords(class_node, "x_tag_ids")
        self.assertEqual(
            (tags["relation"], tags["column1"], tags["column2"]),
            (NAMED_TABLE, "x_test_cg_m2m_house_id", "res_partner_category_id"),
        )
        countries = self._field_keywords(class_node, "x_country_ids")
        self.assertNotIn("relation", countries)
        self.assertNotIn("column1", countries)
        self.assertNotIn("column2", countries)
        parents = self._field_keywords(class_node, "x_parent_ids")
        self.assertEqual(
            (parents["relation"], parents["column1"], parents["column2"]),
            (SELF_TABLE, "id1", "id2"),
        )
