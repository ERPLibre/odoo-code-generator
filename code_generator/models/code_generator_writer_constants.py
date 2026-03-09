#!/usr/bin/env python3
# © 2021-2025 TechnoLibre (http://www.technolibre.ca)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from odoo.models import MAGIC_COLUMNS

UNDEFINEDMESSAGE = "Restriction message not yet define."
MAGIC_FIELDS = MAGIC_COLUMNS + [
    "display_name",
    "__last_update",
    "access_url",
    "access_token",
    "access_warning",
]
MODULE_NAME = "code_generator"
BLANK_LINE = [""]
BREAK_LINE_OFF = "\n"
BREAK_LINE = ["\n"]
XML_VERSION_HEADER = '<?xml version="1.0" encoding="utf-8"?>' + BREAK_LINE_OFF
XML_VERSION = ['<?xml version="1.0" encoding="utf-8"?>']
XML_VERSION_STR = '<?xml version="1.0"?>\n'
XML_ODOO_OPENING_TAG = ["<odoo>"]
XML_HEAD = XML_VERSION + XML_ODOO_OPENING_TAG
XML_ODOO_CLOSING_TAG = ["</odoo>"]
FROM_ODOO_IMPORTS = ["from odoo import _, api, models, fields"]
MODEL_HEAD = FROM_ODOO_IMPORTS + BREAK_LINE
FROM_ODOO_IMPORTS_SUPERUSER = [
    "from odoo import _, api, models, fields, SUPERUSER_ID"
]
MODEL_SUPERUSER_HEAD = FROM_ODOO_IMPORTS_SUPERUSER + BREAK_LINE
