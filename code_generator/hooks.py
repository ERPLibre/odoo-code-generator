from odoo import SUPERUSER_ID, _, api, fields, models, tools


def post_init_hook(env):
    if not tools.config["dev_mode"]:
        raise Exception(
            _(
                "Cancel installation module code_generator, please specify"
                " --dev [options] in your instance."
            )
        )

    system_user = env["res.users"].browse(2)
    system_user.groups_id = [
        (4, env.ref("code_generator.code_generator_manager").id, False)
    ]
