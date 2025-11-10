from odoo import _, api, fields, models


class StudioAction(models.Model):
    _name = "studio.action"
    _description = "Studio Action"
    _inherit = ["mail.thread"]
    _rec_name = "name"

    name = fields.Char(string="Action Name", required=True)
    studio_model_id = fields.Many2one(
        "studio.model",
        string="Studio Model",
        required=True,
        ondelete="cascade",
    )

    type = fields.Selection(
        [
            ("ir.actions.act_window", "Window Action"),
            ("ir.actions.server", "Server Action"),
            ("ir.actions.report", "Report Action"),
            ("ir.actions.act_url", "URL Action"),
        ],
        string="Action Type",
        required=True,
        default="ir.actions.act_window",
    )

    action_id = fields.Reference(
        selection=[
            ("ir.actions.act_window", "Window Action"),
            ("ir.actions.server", "Server Action"),
            ("ir.actions.report", "Report Action"),
            ("ir.actions.act_url", "URL Action"),
        ],
        string="Action Reference",
        readonly=True,
    )

    # Window action fields
    view_mode = fields.Char(string="View Mode", default="list,form")
    target = fields.Selection(
        [
            ("current", "Current Window"),
            ("new", "New Window"),
            ("inline", "Inline"),
            ("fullscreen", "Full Screen"),
        ],
        string="Target",
        default="current",
    )

    domain = fields.Char(string="Domain", default="[]")
    context = fields.Char(string="Context", default="{}")
    limit = fields.Integer(string="Record Limit", default=80)

    # Server action fields
    state = fields.Selection(
        [
            ("code", "Execute Python Code"),
            ("object_create", "Create a new Record"),
            ("object_write", "Update the Record"),
            ("multi", "Execute several actions"),
        ],
        string="Action To Do",
        default="code",
    )

    code = fields.Text(string="Python Code")

    # Button fields
    button_name = fields.Char(string="Button Name")
    button_type = fields.Selection(
        [
            ("action", "Action"),
            ("object", "Object"),
        ],
        string="Button Type",
        default="object",
    )
    button_icon = fields.Char(string="Button Icon")
    button_classes = fields.Char(
        string="Button Classes", default="btn-primary"
    )

    groups_id = fields.Many2many("res.groups", string="Groups")

    def action_create_action(self):
        """Create the actual action record"""
        for record in self:
            if record.action_id:
                continue

            if record.type == "ir.actions.act_window":
                vals = {
                    "name": record.name,
                    "res_model": record.studio_model_id.name,
                    "view_mode": record.view_mode,
                    "target": record.target,
                    "domain": record.domain,
                    "context": record.context,
                    "limit": record.limit,
                }

                if record.groups_id:
                    vals["groups_id"] = [(6, 0, record.groups_id.ids)]

                action = self.env["ir.actions.act_window"].create(vals)
                record.action_id = f"ir.actions.act_window,{action.id}"

            elif record.type == "ir.actions.server":
                vals = {
                    "name": record.name,
                    "model_id": record.studio_model_id.model_id.id,
                    "state": record.state,
                    "code": record.code or "",
                }

                if record.groups_id:
                    vals["groups_id"] = [(6, 0, record.groups_id.ids)]

                action = self.env["ir.actions.server"].create(vals)
                record.action_id = f"ir.actions.server,{action.id}"
