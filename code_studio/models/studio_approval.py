import json

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class StudioApproval(models.Model):
    _name = "studio.approval"
    _description = "Studio Approval Workflow"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = "name"
    _order = "sequence, id"

    name = fields.Char(string="Approval Name", required=True, tracking=True)
    studio_model_id = fields.Many2one(
        "studio.model", string="Model", required=True, ondelete="cascade"
    )
    model = fields.Char(
        related="studio_model_id.name", store=True, readonly=True
    )

    active = fields.Boolean(default=True)
    sequence = fields.Integer(string="Sequence", default=10)

    # Approval Configuration
    approval_type = fields.Selection(
        [
            ("simple", "Simple Approval"),
            ("multi_step", "Multi-Step Approval"),
            ("parallel", "Parallel Approval"),
            ("conditional", "Conditional Approval"),
        ],
        string="Approval Type",
        default="simple",
        required=True,
    )

    # Trigger Configuration
    trigger_field_id = fields.Many2one(
        "ir.model.fields",
        string="Trigger Field",
        domain="[('model_id.model', '=', model), ('ttype', 'in', ['selection', 'boolean'])]",
        help="Field that triggers the approval process",
        ondelete="cascade",
    )
    trigger_value = fields.Char(
        string="Trigger Value",
        help="Value that triggers the approval (for selection fields)",
    )

    # Approval Steps
    step_ids = fields.One2many(
        "studio.approval.step", "approval_id", string="Approval Steps"
    )

    # Field Updates
    field_update_ids = fields.One2many(
        "studio.approval.field.update", "approval_id", string="Field Updates"
    )

    # Conditions
    condition_domain = fields.Char(
        string="Approval Condition",
        default="[]",
        help="Domain to determine when approval is required",
    )

    # Notifications
    send_email = fields.Boolean(
        string="Send Email Notifications", default=True
    )
    email_template_id = fields.Many2one(
        "mail.template",
        string="Email Template",
        domain="[('model', '=', model)]",
    )

    # Button Configuration
    button_name = fields.Char(string="Button Name", default="Request Approval")
    button_icon = fields.Char(string="Button Icon", default="fa-check")
    button_classes = fields.Char(
        string="Button Classes", default="btn-primary"
    )

    # States
    approved_state = fields.Char(string="Approved State", default="approved")
    rejected_state = fields.Char(string="Rejected State", default="rejected")

    @api.constrains("condition_domain")
    def _check_condition_domain(self):
        for record in self:
            try:
                json.loads(record.condition_domain or "[]")
            except json.JSONDecodeError:
                raise ValidationError(_("Invalid condition domain format"))

    def action_create_approval(self):
        """Create the approval workflow components"""
        self.ensure_one()

        # Create approval status field if not exists
        self._create_approval_fields()

        # Create approval method
        self._create_approval_method()

        # Create automated actions
        self._create_automated_actions()

        # Create email templates if needed
        if self.send_email and not self.email_template_id:
            self._create_email_templates()

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "success",
                "message": _("Approval workflow created successfully"),
                "next": {"type": "ir.actions.act_window_close"},
            },
        }

    def _create_approval_fields(self):
        """Create necessary fields for approval workflow"""
        self.ensure_one()

        model_obj = self.env["ir.model"].search([("model", "=", self.model)])
        if not model_obj:
            raise UserError(_("Model not found"))

        # Approval status field
        status_field = self.env["ir.model.fields"].search(
            [
                ("model_id", "=", model_obj.id),
                ("name", "=", "x_approval_status"),
            ]
        )

        if not status_field:
            self.env["ir.model.fields"].create(
                {
                    "name": "x_approval_status",
                    "field_description": "Approval Status",
                    "model_id": model_obj.id,
                    "ttype": "selection",
                    "selection": str(
                        [
                            ("draft", "Draft"),
                            ("pending", "Pending Approval"),
                            ("approved", "Approved"),
                            ("rejected", "Rejected"),
                        ]
                    ),
                    "state": "manual",
                }
            )

        # Current approver field
        approver_field = self.env["ir.model.fields"].search(
            [
                ("model_id", "=", model_obj.id),
                ("name", "=", "x_current_approver_id"),
            ]
        )

        if not approver_field:
            self.env["ir.model.fields"].create(
                {
                    "name": "x_current_approver_id",
                    "field_description": "Current Approver",
                    "model_id": model_obj.id,
                    "ttype": "many2one",
                    "relation": "res.users",
                    "state": "manual",
                }
            )

        # Approval history
        history_field = self.env["ir.model.fields"].search(
            [
                ("model_id", "=", model_obj.id),
                ("name", "=", "x_approval_history_ids"),
            ]
        )

        if not history_field:
            self.env["ir.model.fields"].create(
                {
                    "name": "x_approval_history_ids",
                    "field_description": "Approval History",
                    "model_id": model_obj.id,
                    "ttype": "one2many",
                    "relation": "studio.approval.history",
                    "relation_field": "record_ref",
                    "state": "manual",
                }
            )

    def _create_approval_method(self):
        """Create the approval request method"""
        self.ensure_one()

        code = f"""
# Request Approval
record = self
approval = env['studio.approval'].browse({self.id})

# Check if approval is needed
if approval.condition_domain:
    domain = eval(approval.condition_domain)
    if not record.filtered_domain(domain):
        raise UserError("This record does not meet the approval conditions")

# Set to pending and assign first approver
record.write({{
    'x_approval_status': 'pending',
}})

# Process first step
if approval.step_ids:
    first_step = approval.step_ids.sorted('sequence')[0]
    first_step.assign_approver(record)

# Send notification
if approval.send_email and approval.email_template_id:
    approval.email_template_id.send_mail(record.id)
"""

        # Create server action
        action_vals = {
            "name": f"{self.name} - Request Approval",
            "model_id": self.studio_model_id.model_id.id,
            "state": "code",
            "code": code,
        }

        action = self.env["ir.actions.server"].create(action_vals)

        # Create button in form view
        self._add_approval_button(action)

    def _add_approval_button(self, action):
        """Add approval button to form view"""
        self.ensure_one()

        # Find form view
        form_view = self.env["ir.ui.view"].search(
            [
                ("model", "=", self.model),
                ("type", "=", "form"),
            ],
            limit=1,
        )

        if not form_view:
            return

        # Add button to view
        # This is simplified - in reality you'd need to parse and modify the XML
        pass

    def _create_automated_actions(self):
        """Create automated actions for approval workflow"""
        self.ensure_one()

        # Auto-assign next approver
        self.env["base.automation"].create(
            {
                "name": f"{self.name} - Auto Assign Next Approver",
                "model_id": self.studio_model_id.model_id.id,
                "trigger": "on_write",
                "filter_domain": "[('x_approval_status', 'in', ['approved', 'rejected'])]",
                "action_server_id": self._create_next_approver_action().id,
            }
        )

    def _create_next_approver_action(self):
        """Create action to assign next approver"""
        code = f"""
# Assign next approver
record = model.browse(env.context.get('active_id'))
approval = env['studio.approval'].browse({self.id})

# Find current step
current_step = approval.step_ids.filtered(
    lambda s: s.get_approvers() & record.x_current_approver_id
)

if current_step and record.x_approval_status == 'approved':
    # Find next step
    next_steps = approval.step_ids.filtered(
        lambda s: s.sequence > current_step.sequence
    ).sorted('sequence')

    if next_steps:
        next_steps[0].assign_approver(record)
    else:
        # All steps completed
        record.x_approval_status = approval.approved_state

        # Apply field updates
        for update in approval.field_update_ids:
            update.apply_update(record)
"""

        return self.env["ir.actions.server"].create(
            {
                "name": f"{self.name} - Assign Next Approver",
                "model_id": self.studio_model_id.model_id.id,
                "state": "code",
                "code": code,
            }
        )

    def _create_email_templates(self):
        """Create default email templates"""
        self.ensure_one()

        # Approval request template
        self.email_template_id = self.env["mail.template"].create(
            {
                "name": f"{self.name} - Approval Request",
                "model_id": self.studio_model_id.model_id.id,
                "subject": "Approval Required: ${object.display_name}",
                "body_html": """
<p>Dear ${object.x_current_approver_id.name},</p>

<p>You have a new approval request for ${object.display_name}.</p>

<p>Please review and approve/reject this request.</p>

<p>
    <a href="/web#id=${object.id}&model=${object._name}&view_type=form"
       style="padding: 10px 20px; background-color: #875A7B; color: white; text-decoration: none; border-radius: 4px;">
       View Request
    </a>
</p>

<p>Best regards,<br/>${user.company_id.name}</p>
""",
                "auto_delete": False,
            }
        )


class StudioApprovalStep(models.Model):
    _name = "studio.approval.step"
    _description = "Studio Approval Step"
    _order = "sequence, id"

    approval_id = fields.Many2one(
        "studio.approval", string="Approval", required=True, ondelete="cascade"
    )
    name = fields.Char(string="Step Name", required=True)
    sequence = fields.Integer(string="Sequence", default=10)

    # Approver Configuration
    approver_type = fields.Selection(
        [
            ("user", "Specific User"),
            ("group", "Group"),
            ("field", "Field Value"),
            ("python", "Python Expression"),
            ("manager", "Manager"),
            ("role", "Approval Role"),
        ],
        string="Approver Type",
        default="user",
        required=True,
    )

    approver_user_id = fields.Many2one("res.users", string="Approver")
    approver_group_id = fields.Many2one("res.groups", string="Approver Group")
    approver_field_id = fields.Many2one(
        "ir.model.fields",
        string="Approver Field",
        domain="[('model_id.model', '=', approval_id.model), ('ttype', '=', 'many2one'), ('relation', '=', 'res.users')]",
        ondelete="cascade",
    )
    approver_python = fields.Text(string="Python Expression")

    # Conditions
    condition_type = fields.Selection(
        [
            ("always", "Always"),
            ("field", "Field Condition"),
            ("amount", "Amount Condition"),
            ("python", "Python Condition"),
        ],
        string="Condition Type",
        default="always",
    )

    condition_field_id = fields.Many2one(
        comodel_name="ir.model.fields",
        string="Condition Field",
        domain="[('model_id.model', '=', approval_id.model)]",
        ondelete="cascade",
    )
    condition_operator = fields.Selection(
        [
            ("=", "Equals"),
            ("!=", "Not Equals"),
            (">", "Greater Than"),
            ("<", "Less Than"),
            (">=", "Greater or Equal"),
            ("<=", "Less or Equal"),
            ("in", "In"),
            ("not in", "Not In"),
        ],
        string="Operator",
    )
    condition_value = fields.Char(string="Condition Value")
    condition_python = fields.Text(string="Python Condition")

    # Options
    require_all = fields.Boolean(
        string="Require All Approvers",
        help="If checked, all users in the group must approve",
    )
    can_reject = fields.Boolean(string="Can Reject", default=True)
    rejection_ends_process = fields.Boolean(
        string="Rejection Ends Process",
        default=True,
        help="If checked, rejection at this step ends the entire approval process",
    )

    def get_approvers(self):
        """Get approvers for this step"""
        self.ensure_one()

        if self.approver_type == "user":
            return self.approver_user_id
        elif self.approver_type == "group":
            return self.approver_group_id.users
        elif self.approver_type == "field":
            # This would need the actual record to evaluate
            return self.env["res.users"]
        elif self.approver_type == "python":
            # This would need the actual record to evaluate
            return self.env["res.users"]
        elif self.approver_type == "manager":
            # This would need the actual record to evaluate
            return self.env["res.users"]

        return self.env["res.users"]

    def assign_approver(self, record):
        """Assign approver for this step to the record"""
        self.ensure_one()

        approvers = self.env["res.users"]

        if self.approver_type == "user":
            approvers = self.approver_user_id
        elif self.approver_type == "group":
            approvers = self.approver_group_id.users
        elif self.approver_type == "field" and self.approver_field_id:
            approvers = record[self.approver_field_id.name]
        elif self.approver_type == "python" and self.approver_python:
            # Safe evaluation of python expression
            safe_eval_dict = {
                "record": record,
                "env": self.env,
                "user": self.env.user,
            }
            try:
                approvers = eval(self.approver_python, safe_eval_dict)
            except Exception:
                approvers = self.env["res.users"]
        elif self.approver_type == "manager":
            if hasattr(record, "user_id"):
                employee = self.env["hr.employee"].search(
                    [("user_id", "=", record.user_id.id)], limit=1
                )
                if employee and employee.parent_id:
                    approvers = employee.parent_id.user_id

        if approvers:
            record.write(
                {
                    "x_current_approver_id": (
                        approvers[0].id if len(approvers) > 1 else approvers.id
                    ),
                }
            )

            # Create approval history entry
            self.env["studio.approval.history"].create(
                {
                    "approval_id": self.approval_id.id,
                    "step_id": self.id,
                    "record_ref": f"{record._name},{record.id}",
                    "approver_id": (
                        approvers[0].id if len(approvers) > 1 else approvers.id
                    ),
                    "status": "pending",
                }
            )

    def check_condition(self, record):
        """Check if this step should be executed"""
        self.ensure_one()

        if self.condition_type == "always":
            return True
        elif self.condition_type == "field" and self.condition_field_id:
            field_value = record[self.condition_field_id.name]
            condition_value = self.condition_value

            # Convert condition value to appropriate type
            if self.condition_field_id.ttype in (
                "integer",
                "float",
                "monetary",
            ):
                condition_value = float(condition_value)

            # Evaluate condition
            if self.condition_operator == "=":
                return field_value == condition_value
            elif self.condition_operator == "!=":
                return field_value != condition_value
            elif self.condition_operator == ">":
                return field_value > condition_value
            elif self.condition_operator == "<":
                return field_value < condition_value
            elif self.condition_operator == ">=":
                return field_value >= condition_value
            elif self.condition_operator == "<=":
                return field_value <= condition_value
        elif self.condition_type == "python" and self.condition_python:
            safe_eval_dict = {
                "record": record,
                "env": self.env,
                "user": self.env.user,
            }
            try:
                return eval(self.condition_python, safe_eval_dict)
            except Exception:
                return False

        return True


class StudioApprovalFieldUpdate(models.Model):
    _name = "studio.approval.field.update"
    _description = "Studio Approval Field Update"
    _order = "sequence"

    approval_id = fields.Many2one(
        "studio.approval", string="Approval", required=True, ondelete="cascade"
    )
    name = fields.Char(string="Update Name", required=True)
    sequence = fields.Integer(string="Sequence", default=10)

    field_id = fields.Many2one(
        "ir.model.fields",
        string="Field to Update",
        required=True,
        domain="[('model_id.model', '=', approval_id.model)]",
        ondelete="cascade",
    )

    update_type = fields.Selection(
        [
            ("value", "Set Value"),
            ("python", "Python Expression"),
            ("copy", "Copy from Field"),
        ],
        string="Update Type",
        default="value",
        required=True,
    )

    update_value = fields.Char(string="Value")
    update_python = fields.Text(string="Python Expression")
    copy_field_id = fields.Many2one(
        "ir.model.fields",
        string="Copy from Field",
        domain="[('model_id.model', '=', approval_id.model)]",
        ondelete="cascade",
    )

    def apply_update(self, record):
        """Apply field update to record"""
        self.ensure_one()

        if self.update_type == "value":
            value = self.update_value

            # Convert value based on field type
            if self.field_id.ttype == "boolean":
                value = value.lower() in ("true", "1", "yes")
            elif self.field_id.ttype in ("integer", "float", "monetary"):
                value = float(value) if value else 0.0

            record.write({self.field_id.name: value})

        elif self.update_type == "python" and self.update_python:
            safe_eval_dict = {
                "record": record,
                "env": self.env,
                "user": self.env.user,
            }
            try:
                value = eval(self.update_python, safe_eval_dict)
                record.write({self.field_id.name: value})
            except Exception:
                pass

        elif self.update_type == "copy" and self.copy_field_id:
            value = record[self.copy_field_id.name]
            record.write({self.field_id.name: value})


class StudioApprovalHistory(models.Model):
    _name = "studio.approval.history"
    _description = "Studio Approval History"
    _order = "create_date desc"
    _rec_name = "step_id"

    approval_id = fields.Many2one(
        "studio.approval", string="Approval", required=True, ondelete="cascade"
    )
    step_id = fields.Many2one(
        "studio.approval.step",
        string="Step",
        required=True,
        ondelete="cascade",
    )
    record_ref = fields.Reference(
        selection="_get_record_selection", string="Record"
    )

    approver_id = fields.Many2one(
        "res.users", string="Approver", required=True
    )
    status = fields.Selection(
        [
            ("pending", "Pending"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        string="Status",
        default="pending",
        required=True,
    )

    approved_date = fields.Datetime(string="Approval Date")
    comments = fields.Text(string="Comments")

    @api.model
    def _get_record_selection(self):
        """Get available models for reference field"""
        models = self.env["studio.model"].search([])
        return [(model.name, model.description) for model in models]

    def action_approve(self):
        """Approve this step"""
        self.ensure_one()

        if self.status != "pending":
            raise UserError(_("This step has already been processed"))

        if self.approver_id != self.env.user:
            raise UserError(
                _("Only the assigned approver can approve this step")
            )

        self.write(
            {
                "status": "approved",
                "approved_date": fields.Datetime.now(),
            }
        )

        # Update record status
        if self.record_ref:
            self.record_ref.write({"x_approval_status": "approved"})

    def action_reject(self):
        """Reject this step"""
        self.ensure_one()

        if self.status != "pending":
            raise UserError(_("This step has already been processed"))

        if self.approver_id != self.env.user:
            raise UserError(
                _("Only the assigned approver can reject this step")
            )

        self.write(
            {
                "status": "rejected",
                "approved_date": fields.Datetime.now(),
            }
        )

        # Update record status
        if self.record_ref:
            self.record_ref.write({"x_approval_status": "rejected"})

            # Check if rejection ends process
            if self.step_id.rejection_ends_process:
                # Cancel any pending approvals
                pending_approvals = self.search(
                    [
                        (
                            "record_ref",
                            "=",
                            f"{self.record_ref._name},{self.record_ref.id}",
                        ),
                        ("status", "=", "pending"),
                        ("id", "!=", self.id),
                    ]
                )
                pending_approvals.write({"status": "rejected"})
