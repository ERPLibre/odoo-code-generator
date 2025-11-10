from odoo import _, api, fields, models


class StudioMenu(models.Model):
    _name = "studio.menu"
    _description = "Studio Menu"
    _inherit = ["mail.thread"]
    _rec_name = "name"
    _order = "sequence, id"

    name = fields.Char(string="Menu Name", required=True, translate=True)
    studio_model_id = fields.Many2one(
        "studio.model", string="Studio Model", ondelete="cascade"
    )

    menu_id = fields.Many2one(
        "ir.ui.menu", string="Menu", readonly=True, ondelete="cascade"
    )
    parent_id = fields.Many2one("ir.ui.menu", string="Parent Menu")

    sequence = fields.Integer(string="Sequence", default=10)
    active = fields.Boolean(default=True)

    groups_id = fields.Many2many("res.groups", string="Groups")

    action_id = fields.Many2one(
        "ir.actions.act_window", string="Action", readonly=True
    )

    web_icon = fields.Char(string="Web Icon")

    def action_create_menu(self):
        """Create the menu and associated action"""
        for record in self:
            if record.menu_id:
                continue

            # Create action first
            action_vals = {
                "name": record.name,
                "res_model": record.studio_model_id.name,
                "view_mode": "list,form,kanban",
                "context": {},
                "help": f'<p class="o_view_nocontent_smiling_face">Create your first {record.name}</p>',
            }

            action = self.env["ir.actions.act_window"].create(action_vals)
            record.action_id = action

            # Create menu
            menu_vals = {
                "name": record.name,
                "action": f"ir.actions.act_window,{action.id}",
                "sequence": record.sequence,
                "active": record.active,
            }

            if record.parent_id:
                menu_vals["parent_id"] = record.parent_id.id

            if record.groups_id:
                menu_vals["groups_id"] = [(6, 0, record.groups_id.ids)]

            if record.web_icon:
                menu_vals["web_icon"] = record.web_icon

            menu = self.env["ir.ui.menu"].create(menu_vals)
            record.menu_id = menu
