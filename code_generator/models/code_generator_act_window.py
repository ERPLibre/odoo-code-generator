from odoo import api, fields, models, modules, tools


class CodeGeneratorActWindow(models.Model):
    _name = "code.generator.act_window"
    _description = "Code Generator Act Window"

    name = fields.Char(string="name")

    code_generator_id = fields.Many2one(
        comodel_name="code.generator.module",
        string="Code Generator",
        required=True,
        ondelete="cascade",
    )

    # TODO use ir.model.data instead if id_name
    id_name = fields.Char(
        string="Action id",
        help="Specify id name of this action window.",
    )

    is_wizard = fields.Boolean()

    model_name = fields.Char(
        help="The associate model, if empty, no association."
    )

    target = fields.Selection(
        selection=[
            ("current", "Current Window"),
            ("new", "New Window"),
            ("inline", "Inline Edit"),
            ("fullscreen", "Full Screen"),
            ("main", "Main action of Current Window"),
        ],
        string="Target Window",
        default="current",
    )

    view_mode = fields.Char(help="The sequence of view mode.")

    view_type = fields.Char(
        default="form",
        help="The default view for this action window.",
    )
