import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class StudioModel(models.Model):
    _name = "studio.model"
    _description = "Studio Model"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = "name"
    _order = "name"

    name = fields.Char(
        string="Model Name",
        required=True,
        tracking=True,
        help="Technical name of the model (e.g., 'x_custom_model')",
    )
    description = fields.Char(
        string="Description",
        required=True,
        tracking=True,
        help="User-friendly description of the model",
    )
    model_id = fields.Many2one(
        "ir.model", string="Model", readonly=True, ondelete="cascade"
    )
    field_ids = fields.One2many(
        "studio.field", "studio_model_id", string="Fields"
    )
    view_ids = fields.One2many(
        "studio.view", "studio_model_id", string="Views"
    )
    menu_ids = fields.One2many(
        "studio.menu", "studio_model_id", string="Menus"
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("active", "Active"),
        ],
        default="draft",
        tracking=True,
    )

    is_mail_thread = fields.Boolean(
        string="Mail Thread",
        default=True,
        help="Enable mail thread functionality",
    )
    is_mail_activity = fields.Boolean(
        string="Activities",
        default=True,
        help="Enable activities functionality",
    )

    @api.constrains("name")
    def _check_name(self):
        for record in self:
            if not re.match(r"^x_[a-z0-9_]+$", record.name):
                raise ValidationError(
                    _(
                        "Model name must start with 'x_' and contain only lowercase letters, numbers, and underscores."
                    )
                )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            record._create_model()
        return records

    def _create_model(self):
        """Create the actual ir.model record"""
        self.ensure_one()

        inherit = []
        if self.is_mail_thread:
            inherit.append("mail.thread")
        if self.is_mail_activity:
            inherit.append("mail.activity.mixin")

        model_vals = {
            "name": self.description,
            "model": self.name,
            "state": "manual",
            "transient": False,
        }

        model = self.env["ir.model"].create(model_vals)
        self.model_id = model

        # Create default fields
        self._create_default_fields()

        # Create default views
        self._create_default_views()

        return model

    def _create_default_fields(self):
        """Create default fields for the model"""
        self.ensure_one()

        # Name field
        self.env["studio.field"].create(
            {
                "name": "x_name_x",
                "field_description": "Name",
                "ttype": "char",
                "required": True,
                "studio_model_id": self.id,
            }
        )

        # Active field
        self.env["studio.field"].create(
            {
                "name": "x_active_x",
                "field_description": "Active",
                "ttype": "boolean",
                "studio_model_id": self.id,
            }
        )

    def _create_default_views(self):
        """Create default views for the model"""
        self.ensure_one()

        # Form view
        form_view = self.env["studio.view"].create(
            {
                "name": f"{self.description} Form",
                "type": "form",
                "studio_model_id": self.id,
                "arch_base": """<?xml version="1.0"?>
<form string="{description}">
    <sheet>
        <group>
            <field name="x_name_x"/>
            <field name="x_active_x"/>
        </group>
    </sheet>
</form>""".format(
                    description=self.description
                ),
            }
        )
        # <div class="oe_chatter">
        #     <field name="message_follower_ids"/>
        #     <field name="activity_ids"/>
        #     <field name="message_ids"/>
        # </div>

        # List view
        list_view = self.env["studio.view"].create(
            {
                "name": f"{self.description} List",
                "type": "list",
                "studio_model_id": self.id,
                "arch_base": """<?xml version="1.0"?>
<list string="{description}">
    <field name="x_name_x"/>
    <field name="x_active_x"/>
</list>""".format(
                    description=self.description
                ),
            }
        )

        # Search view
        search_view = self.env["studio.view"].create(
            {
                "name": f"{self.description} Search",
                "type": "search",
                "studio_model_id": self.id,
                "arch_base": """<?xml version="1.0"?>
<search string="{description}">
    <field name="x_name_x"/>
    <filter name="active" string="Active" domain="[('x_active_x', '=', True)]"/>
    <filter name="inactive" string="Archived" domain="[('x_active_x', '=', False)]"/>
</search>""".format(
                    description=self.description
                ),
            }
        )

    def action_activate(self):
        """Activate the model"""
        self.ensure_one()
        if self.state == "active":
            return

        # Activate all fields
        self.field_ids.action_create_field()

        # Activate all views
        self.view_ids.action_create_view()

        self.state = "active"

        # Clear caches
        # self.env.registry.clear_caches()

        return {
            "type": "ir.actions.client",
            "tag": "reload",
        }

    def action_open_model(self):
        """Open the model in a new action"""
        self.ensure_one()

        action = {
            "name": self.description,
            "type": "ir.actions.act_window",
            "res_model": self.name,
            "view_mode": "list,form",
            "target": "current",
            "context": {"studio_mode": True},
        }

        return action
