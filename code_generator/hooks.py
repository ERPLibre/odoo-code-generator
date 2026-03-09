#!/usr/bin/env python3
# © 2021-2025 TechnoLibre (http://www.technolibre.ca)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)
import logging

from odoo import _, tools

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    if not tools.config["dev_mode"]:
        raise RuntimeError(
            _(
                "Cancel installation module code_generator, please"
                " specify --dev [options] in your instance."
            )
        )

    system_user = env["res.users"].browse(2)
    system_user.groups_id = [
        (4, env.ref("code_generator.code_generator_manager").id, False)
    ]

    # Drop the core Odoo constraint that prevents programmatic field
    # creation with names starting with 'x_'. The code generator needs
    # to create fields with arbitrary names. This is safe because this
    # module requires --dev mode and should only run in development.
    _logger.info(
        "Dropping constraint 'ir_model_fields_name_manual_field'"
        " to allow code generator field creation"
    )
    env.cr.execute(
        """
        DO $$
        BEGIN
          IF EXISTS (
            SELECT 1
            FROM information_schema.table_constraints
            WHERE constraint_name = 'ir_model_fields_name_manual_field'
              AND table_name = 'ir_model_fields'
          ) THEN
            ALTER TABLE ir_model_fields
            DROP CONSTRAINT ir_model_fields_name_manual_field;
          END IF;
        END$$;
        """
    )
