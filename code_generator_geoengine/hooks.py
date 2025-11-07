#!/usr/bin/env python3
# © 2021-2025 TechnoLibre (http://www.technolibre.ca)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)
from odoo import SUPERUSER_ID, _, api, fields, models


def post_init_hook(env):
    system_user = env["res.users"].browse(2)
    system_user.groups_id = [
        (4, env.ref("base_geoengine.group_geoengine_admin").id, False)
    ]
