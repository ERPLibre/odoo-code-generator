from odoo import _, api, fields, models


class StudioAutomation(models.Model):
    _name = "studio.automation"
    _description = "Studio Automation"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = "name"

    name = fields.Char(string="Automation Name", required=True)

    description = fields.Text(string="Automation Description")

    studio_model_id = fields.Many2one(
        "studio.model",
        string="Studio Model",
        required=True,
        ondelete="cascade",
    )

    automation_id = fields.Many2one(
        "base.automation",
        string="Automation",
        readonly=True,
        ondelete="cascade",
    )

    trigger = fields.Selection(
        [
            ("on_create", "On Creation"),
            ("on_write", "On Update"),
            ("on_create_or_write", "On Creation & Update"),
            ("on_unlink", "On Deletion"),
            ("on_state_set", "On State Change"),
            ("on_time", "Based on Time Condition"),
        ],
        string="Trigger",
        required=True,
        default="on_create",
    )

    # Trigger conditions
    trigger_field_ids = fields.Many2many(
        "ir.model.fields",
        string="Trigger Fields",
        domain="[('model_id', '=', model_id)]",
        help="Fields that trigger the automation when updated",
    )

    filter_domain = fields.Char(
        string="Before Update Domain",
        default="[]",
        help="Domain to filter records before update",
    )

    filter_pre_domain = fields.Char(
        string="After Update Domain",
        default="[]",
        help="Domain to filter records after update",
    )

    # Time-based triggers
    trg_date_field_id = fields.Many2one(
        "ir.model.fields",
        string="Trigger Date Field",
        domain="[('model_id', '=', model_id), ('ttype', 'in', ['date', 'datetime'])]",
        ondelete="cascade",
    )

    trg_date_range = fields.Integer(string="Delay After Trigger Date")
    trg_date_range_type = fields.Selection(
        [
            ("minutes", "Minutes"),
            ("hours", "Hours"),
            ("days", "Days"),
            ("months", "Months"),
        ],
        string="Delay Type",
        default="days",
    )

    # Actions
    action_server_id = fields.Many2one(
        "ir.actions.server", string="Server Action", help="Action to execute"
    )

    state = fields.Selection(
        [
            ("code", "Execute Python Code"),
            ("object_create", "Create a new Record"),
            ("object_write", "Update the Record"),
            ("multi", "Execute several actions"),
            ("email", "Send Email"),
            ("followers", "Add Followers"),
            ("next_activity", "Create Next Activity"),
        ],
        string="Action To Do",
        default="code",
    )

    code = fields.Text(
        string="Python Code",
        default="""# Available variables:
#  - env: Odoo Environment
#  - model: Current model
#  - record: Current record(s)
#  - records: Current recordset
#  - time, datetime, dateutil, timezone: useful Python libraries
#  - float_compare: utility function to compare floats
#  - Command: x2many commands namespace
#  - log: log(message, level='info')

# Example:
# record.message_post(body='Automation triggered!')
""",
    )

    # Email action fields
    template_id = fields.Many2one(
        "mail.template",
        string="Email Template",
        domain="[('model_id', '=', model_id)]",
    )

    # Activity action fields
    activity_type_id = fields.Many2one(
        "mail.activity.type", string="Activity Type"
    )
    activity_summary = fields.Char(string="Activity Summary")
    activity_note = fields.Html(string="Activity Note")
    activity_date_deadline_range = fields.Integer(string="Due Date In")
    activity_date_deadline_range_type = fields.Selection(
        [
            ("days", "Days"),
            ("weeks", "Weeks"),
            ("months", "Months"),
        ],
        string="Due Date Type",
        default="days",
    )
    activity_user_id = fields.Many2one("res.users", string="Assigned To")

    model_id = fields.Many2one(
        "ir.model", related="studio_model_id.model_id", store=True
    )

    active = fields.Boolean(default=True)

    def action_create_automation(self):
        """Create the actual base.automation record"""
        for record in self:
            if record.automation_id:
                continue

            vals = {
                "name": record.name,
                "model_id": record.model_id.id,
                "trigger": record.trigger,
                "active": record.active,
                "filter_domain": record.filter_domain,
                "filter_pre_domain": record.filter_pre_domain,
            }

            # Handle trigger fields
            if record.trigger_field_ids:
                vals["trigger_field_ids"] = [
                    (6, 0, record.trigger_field_ids.ids)
                ]

            # Handle time-based triggers
            if record.trigger == "on_time":
                vals["trg_date_field_id"] = record.trg_date_field_id.id
                vals["trg_date_range"] = record.trg_date_range
                vals["trg_date_range_type"] = record.trg_date_range_type

            # Create or update server action
            action_vals = {
                "name": f"{record.name} - Action",
                "model_id": record.model_id.id,
                "state": record.state,
            }

            if record.state == "code":
                action_vals["code"] = record.code
            elif record.state == "email":
                action_vals["template_id"] = record.template_id.id
            elif record.state == "next_activity":
                action_vals["activity_type_id"] = record.activity_type_id.id
                action_vals["activity_summary"] = record.activity_summary
                action_vals["activity_note"] = record.activity_note
                action_vals["activity_date_deadline_range"] = (
                    record.activity_date_deadline_range
                )
                action_vals["activity_date_deadline_range_type"] = (
                    record.activity_date_deadline_range_type
                )
                if record.activity_user_id:
                    action_vals["activity_user_id"] = (
                        record.activity_user_id.id
                    )

            if record.action_server_id:
                record.action_server_id.write(action_vals)
            else:
                action = self.env["ir.actions.server"].create(action_vals)
                record.action_server_id = action

            vals["action_server_id"] = record.action_server_id.id

            automation = self.env["base.automation"].create(vals)
            record.automation_id = automation

    def action_test_automation(self):
        """Test the automation on sample records"""
        self.ensure_one()

        # Get sample records
        Model = self.env[self.studio_model_id.name]
        records = Model.search([], limit=5)

        if not records:
            raise UserWarning(_("No records found to test the automation."))

        # Execute the action
        if self.action_server_id:
            self.action_server_id.with_context(
                active_model=self.studio_model_id.name,
                active_ids=records.ids,
                active_id=records[0].id if records else False,
            ).run()

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Automation Test"),
                "message": _("Automation executed successfully on %s records.")
                % len(records),
                "type": "success",
                "sticky": False,
            },
        }

    def action_view_logs(self):
        self.ensure_one()
        # action = self.env.ref('code_studio.action_studio_automation_logs').read()[0]
        # # Filtrer sur l’automation courante
        # action['domain'] = [('automation_id', '=', self.id)]
        # # Pré-remplir le M2O à la création
        # action['context'] = {'default_automation_id': self.id}
        # return action


class StudioApproval(models.Model):
    _name = "studio.approval"
    _description = "Studio Approval"
    _inherit = ["mail.thread"]
    _rec_name = "name"

    name = fields.Char(string="Approval Name", required=True)
    studio_model_id = fields.Many2one(
        "studio.model",
        string="Studio Model",
        required=True,
        ondelete="cascade",
    )

    approval_type = fields.Selection(
        [
            ("simple", "Simple Approval"),
            ("multiple", "Multiple Approvals"),
            ("hierarchical", "Hierarchical Approval"),
        ],
        string="Approval Type",
        default="simple",
        required=True,
    )

    # Approval configuration
    approval_minimum = fields.Integer(
        string="Minimum Approvals",
        default=1,
        help="Minimum number of approvals required",
    )

    approval_authorized_ids = fields.Many2many(
        "res.users",
        "studio_approval_authorized_rel",
        "approval_id",
        "user_id",
        string="Authorized Approvers",
    )

    approval_manager_ids = fields.Many2many(
        "res.users",
        "studio_approval_manager_rel",
        "approval_id",
        "user_id",
        string="Approval Managers",
    )

    # Approval rules
    rule_ids = fields.One2many(
        "studio.approval.rule", "approval_id", string="Approval Rules"
    )

    # Field configuration
    state_field_id = fields.Many2one(
        "ir.model.fields",
        string="State Field",
        domain="[('model_id', '=', model_id), ('ttype', '=', 'selection')]",
        ondelete="cascade",
    )

    approved_state = fields.Char(
        string="Approved State",
        default="approved",
        help="State value when approved",
    )

    refused_state = fields.Char(
        string="Refused State",
        default="refused",
        help="State value when refused",
    )

    model_id = fields.Many2one(
        "ir.model", related="studio_model_id.model_id", store=True
    )

    active = fields.Boolean(default=True)

    def action_setup_approval(self):
        """Setup approval workflow on the model"""
        self.ensure_one()

        # Create approval fields on the model
        self._create_approval_fields()

        # Create approval views
        self._create_approval_views()

        # Create approval actions
        self._create_approval_actions()

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Approval Setup"),
                "message": _(
                    "Approval workflow has been set up successfully."
                ),
                "type": "success",
                "sticky": False,
            },
        }

    def _create_approval_fields(self):
        """Create approval-related fields on the model"""
        self.ensure_one()

        # Create state field if not exists
        if not self.state_field_id:
            state_field = self.env["studio.field"].create(
                {
                    "name": "x_approval_state",
                    "field_description": "Approval State",
                    "ttype": "selection",
                    "studio_model_id": self.studio_model_id.id,
                    "selection_ids": [
                        (
                            0,
                            0,
                            {"value": "draft", "name": "Draft", "sequence": 1},
                        ),
                        (
                            0,
                            0,
                            {
                                "value": "to_approve",
                                "name": "To Approve",
                                "sequence": 2,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "value": "approved",
                                "name": "Approved",
                                "sequence": 3,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "value": "refused",
                                "name": "Refused",
                                "sequence": 4,
                            },
                        ),
                    ],
                    "tracking": True,
                }
            )
            state_field.action_create_field()
            self.state_field_id = state_field.field_id

        # Create approval fields
        approval_fields = [
            {
                "name": "x_approval_user_ids",
                "field_description": "Approvers",
                "ttype": "many2many",
                "relation": "res.users",
            },
            {
                "name": "x_approval_date",
                "field_description": "Approval Date",
                "ttype": "datetime",
                "readonly": True,
            },
            {
                "name": "x_approval_notes",
                "field_description": "Approval Notes",
                "ttype": "text",
            },
        ]

        for field_vals in approval_fields:
            field_vals["studio_model_id"] = self.studio_model_id.id
            field = self.env["studio.field"].create(field_vals)
            field.action_create_field()

    def _create_approval_views(self):
        """Add approval elements to existing views"""
        # This would modify existing views to add approval buttons and fields
        pass

    def _create_approval_actions(self):
        """Create approval server actions"""
        # Create approve action
        approve_action = self.env["studio.action"].create(
            {
                "name": "Approve",
                "studio_model_id": self.studio_model_id.id,
                "type": "ir.actions.server",
                "state": "code",
                "code": """
# Approve the record
record.write({
    'x_approval_state': 'approved',
    'x_approval_date': fields.Datetime.now(),
    'x_approval_user_ids': [(4, env.user.id)],
})
record.message_post(body='Document approved by %s' % env.user.name)
""",
            }
        )
        approve_action.action_create_action()

        # Create refuse action
        refuse_action = self.env["studio.action"].create(
            {
                "name": "Refuse",
                "studio_model_id": self.studio_model_id.id,
                "type": "ir.actions.server",
                "state": "code",
                "code": """
# Refuse the record
record.write({
    'x_approval_state': 'refused',
    'x_approval_date': fields.Datetime.now(),
    'x_approval_user_ids': [(4, env.user.id)],
})
record.message_post(body='Document refused by %s' % env.user.name)
""",
            }
        )
        refuse_action.action_create_action()


class StudioApprovalRule(models.Model):
    _name = "studio.approval.rule"
    _description = "Studio Approval Rule"
    _order = "sequence, id"

    approval_id = fields.Many2one(
        "studio.approval", string="Approval", required=True, ondelete="cascade"
    )

    name = fields.Char(string="Rule Name", required=True)
    sequence = fields.Integer(string="Sequence", default=10)

    domain = fields.Char(
        string="Domain",
        default="[]",
        help="Domain to determine when this rule applies",
    )

    user_ids = fields.Many2many(
        "res.users",
        string="Approvers",
        help="Users who can approve when this rule applies",
    )

    group_ids = fields.Many2many(
        "res.groups", string="Groups", help="Groups whose members can approve"
    )

    minimum_approvals = fields.Integer(
        string="Minimum Approvals",
        default=1,
        help="Minimum number of approvals required for this rule",
    )

    active = fields.Boolean(default=True)
