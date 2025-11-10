import uuid

from lxml import etree
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class StudioView(models.Model):
    _name = "studio.view"
    _description = "Studio View"
    _inherit = ["mail.thread"]
    _rec_name = "name"
    _order = "priority, id"

    name = fields.Char(string="View Name", required=True)
    type = fields.Selection(
        [
            ("form", "Form"),
            ("list", "List"),
            ("kanban", "Kanban"),
            ("calendar", "Calendar"),
            ("graph", "Graph"),
            ("pivot", "Pivot"),
            ("search", "Search"),
        ],
        string="View Type",
        required=True,
        default="form",
    )

    studio_model_id = fields.Many2one(
        "studio.model",
        string="Studio Model",
        required=True,
        ondelete="cascade",
    )
    model = fields.Char(related="studio_model_id.name", store=True)
    view_id = fields.Many2one(
        "ir.ui.view", string="View", readonly=True, ondelete="cascade"
    )

    arch_base = fields.Text(
        string="View Architecture",
        required=True,
        default='<?xml version="1.0"?>\n<form>\n    <sheet>\n        <group>\n        </group>\n    </sheet>\n</form>',
    )
    arch_studio = fields.Text(
        string="Studio Modifications",
        help="Studio-specific modifications to the view",
    )

    priority = fields.Integer(string="Priority", default=16)
    mode = fields.Selection(
        [
            ("primary", "Primary"),
            ("extension", "Extension"),
        ],
        string="Mode",
        default="primary",
    )

    inherit_id = fields.Many2one("ir.ui.view", string="Inherited View")

    groups_id = fields.Many2many("res.groups", string="Groups")

    active = fields.Boolean(default=True)

    def action_create_view(self):
        """Create the actual ir.ui.view record"""
        for record in self:
            if record.view_id:
                continue

            arch = record._get_final_arch()

            vals = {
                "name": record.name,
                "model": record.model,
                "type": record.type,
                "arch": arch,
                "priority": record.priority,
                "mode": record.mode,
                "active": record.active,
            }

            if record.inherit_id:
                vals["inherit_id"] = record.inherit_id.id

            if record.groups_id:
                vals["groups_id"] = [(6, 0, record.groups_id.ids)]

            view = self.env["ir.ui.view"].create(vals)
            record.view_id = view

    def _get_final_arch(self):
        """Get the final architecture combining base and studio modifications"""
        self.ensure_one()

        if not self.arch_studio:
            return self.arch_base

        # Parse both architectures
        base_tree = etree.fromstring(self.arch_base)

        # Apply studio modifications
        # This is a simplified version - you would need more complex logic here
        # to properly merge the modifications

        return etree.tostring(base_tree, encoding="unicode")

    def action_edit_view(self):
        """Open the view editor"""
        self.ensure_one()

        return {
            "type": "ir.actions.client",
            "tag": "studio_view_editor",
            "params": {
                "studio_view_id": self.id,
                "view_type": self.type,
                "model": self.model,
            },
            "target": "new",
        }

    @api.model
    def get_view_fields(self):
        """Get available fields for the view"""
        model = self.studio_model_id.name
        fields = self.env[model].fields_get()

        return [
            {
                "name": fname,
                "type": fdata["type"],
                "string": fdata["string"],
                "required": fdata.get("required", False),
                "readonly": fdata.get("readonly", False),
            }
            for fname, fdata in fields.items()
        ]
