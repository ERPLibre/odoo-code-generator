import re

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class StudioField(models.Model):
    _name = "studio.field"
    _description = "Studio Field"
    _inherit = ["mail.thread"]
    _rec_name = "field_description"
    _order = "sequence, id"

    name = fields.Char(
        string="Field Name", required=True, help="Technical name of the field"
    )
    field_description = fields.Char(
        string="Field Label", required=True, translate=True
    )
    studio_model_id = fields.Many2one(
        "studio.model",
        string="Studio Model",
        required=True,
        ondelete="cascade",
    )
    model_id = fields.Many2one(
        "ir.model", related="studio_model_id.model_id", store=True
    )
    field_id = fields.Many2one(
        "ir.model.fields", string="Field", readonly=True, ondelete="cascade"
    )

    ttype = fields.Selection(
        [
            ("char", "Text"),
            ("text", "Multiline Text"),
            ("html", "Html"),
            ("integer", "Integer"),
            ("float", "Float"),
            ("monetary", "Monetary"),
            ("boolean", "Boolean"),
            ("date", "Date"),
            ("datetime", "Datetime"),
            ("selection", "Selection"),
            ("many2one", "Many2one"),
            ("one2many", "One2many"),
            ("many2many", "Many2many"),
            ("binary", "Binary"),
        ],
        string="Field Type",
        required=True,
        default="char",
    )

    # Field attributes
    required = fields.Boolean(string="Required")
    readonly = fields.Boolean(string="Readonly")
    store = fields.Boolean(string="Store", default=True)
    index = fields.Boolean(string="Index")
    copy = fields.Boolean(string="Copy", default=True)
    tracking = fields.Boolean(string="Track Changes")

    # For selection fields
    selection_ids = fields.One2many(
        "studio.field.selection", "field_id", string="Selection Values"
    )

    # For relational fields
    relation = fields.Char(string="Related Model")
    relation_field = fields.Char(string="Related Field")

    # Computed fields
    depends = fields.Char(string="Dependencies")
    compute = fields.Text(string="Compute Method")
    inverse = fields.Text(string="Inverse Method")

    help = fields.Text(string="Help Text", translate=True)
    default_value = fields.Char(string="Default Value")

    sequence = fields.Integer(string="Sequence", default=10)

    @api.constrains("name")
    def _check_name(self):
        for record in self:
            if not re.match(r"^x_[a-z0-9_]+$", record.name):
                raise ValidationError(
                    _(
                        "Field name must start with 'x_' and contain only lowercase letters, numbers, and underscores."
                    )
                )

    def action_create_field(self):
        """Create the actual ir.model.fields record"""
        for record in self:
            if record.field_id:
                continue

            vals = {
                "name": record.name,
                "field_description": record.field_description,
                "model_id": record.model_id.id,
                "ttype": record.ttype,
                "required": record.required,
                "readonly": record.readonly,
                "store": record.store,
                "index": record.index,
                # "copy": record.copy,
                "tracking": record.tracking
                and record.ttype not in ("one2many", "many2many"),
                "help": record.help,
                "state": "manual",
            }

            # Handle selection fields
            if record.ttype == "selection":
                selection = []
                for sel in record.selection_ids:
                    selection.append((sel.value, sel.name))
                vals["selection"] = str(selection)

            # Handle relational fields
            if record.ttype in ("many2one", "one2many", "many2many"):
                vals["relation"] = record.relation
                if record.ttype == "one2many":
                    vals["relation_field"] = record.relation_field

            # Handle computed fields
            if record.compute:
                vals["compute"] = record.compute
                vals["depends"] = record.depends
                if record.inverse:
                    vals["inverse"] = record.inverse

            # Handle default value
            if record.default_value:
                if record.ttype == "boolean":
                    vals["default"] = record.default_value.lower() in (
                        "true",
                        "1",
                        "yes",
                    )
                elif record.ttype in ("integer", "float", "monetary"):
                    vals["default"] = float(record.default_value)
                else:
                    vals["default"] = record.default_value

            field = self.env["ir.model.fields"].create(vals)
            record.field_id = field


class StudioFieldSelection(models.Model):
    _name = "studio.field.selection"
    _description = "Studio Field Selection"
    _order = "sequence, id"

    field_id = fields.Many2one(
        "studio.field", string="Field", required=True, ondelete="cascade"
    )
    value = fields.Char(string="Value", required=True)
    name = fields.Char(string="Label", required=True, translate=True)
    sequence = fields.Integer(string="Sequence", default=10)
