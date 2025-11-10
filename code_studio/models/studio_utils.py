import ast
import re

from odoo import _, api, models
from odoo.tools.safe_eval import safe_eval


class StudioUtils(models.AbstractModel):
    _name = "studio.utils"
    _description = "Studio Utilities"

    @api.model
    def validate_python_code(self, code):
        """Validate Python code syntax"""
        try:
            ast.parse(code)
            return {"valid": True}
        except SyntaxError as e:
            return {
                "valid": False,
                "error": str(e),
                "line": e.lineno,
                "offset": e.offset,
            }

    @api.model
    def validate_domain(self, domain_string):
        """Validate domain syntax"""
        try:
            domain = safe_eval(domain_string)
            if not isinstance(domain, list):
                return {"valid": False, "error": "Domain must be a list"}
            return {"valid": True, "domain": domain}
        except Exception as e:
            return {"valid": False, "error": str(e)}

    @api.model
    def suggest_field_name(self, label):
        """Suggest a field name based on label"""
        # Convert to lowercase and replace spaces/special chars
        name = label.lower()
        name = re.sub(r"[^a-z0-9_]", "_", name)
        name = re.sub(r"_+", "_", name)
        name = name.strip("_")

        # Ensure it starts with x_
        if not name.startswith("x_"):
            name = "x_" + name

        return name

    @api.model
    def get_available_models(self):
        """Get list of models available for relations"""
        models = self.env["ir.model"].search(
            [
                ("transient", "=", False),
                ("model", "not like", "ir.%"),
                ("model", "not like", "base_%"),
            ]
        )

        return [
            {
                "id": model.id,
                "model": model.model,
                "name": model.name,
            }
            for model in models
        ]

    @api.model
    def analyze_view_usage(self, model_name):
        """Analyze how views are used for a model"""
        views = self.env["ir.ui.view"].search(
            [("model", "=", model_name), ("active", "=", True)]
        )

        analysis = {
            "total_views": len(views),
            "view_types": {},
            "inherited_views": 0,
            "custom_views": 0,
        }

        for view in views:
            vtype = view.type
            if vtype not in analysis["view_types"]:
                analysis["view_types"][vtype] = 0
            analysis["view_types"][vtype] += 1

            if view.inherit_id:
                analysis["inherited_views"] += 1
            else:
                analysis["custom_views"] += 1

        return analysis

    @api.model
    def generate_sample_data(self, model_name, count=10):
        """Generate sample data for a model"""
        Model = self.env[model_name]
        fields = Model.fields_get()

        created_records = self.env[model_name]

        for i in range(count):
            vals = {}

            for fname, fdata in fields.items():
                if fname in (
                    "id",
                    "create_date",
                    "write_date",
                    "create_uid",
                    "write_uid",
                ):
                    continue

                ftype = fdata["type"]

                if ftype == "char":
                    vals[fname] = (
                        f"Sample {fdata.get('string', fname)} {i + 1}"
                    )
                elif ftype == "text":
                    vals[fname] = (
                        f"Sample text for {fdata.get('string', fname)} {i + 1}"
                    )
                elif ftype == "integer":
                    vals[fname] = i + 1
                elif ftype == "float":
                    vals[fname] = (i + 1) * 1.5
                elif ftype == "boolean":
                    vals[fname] = i % 2 == 0
                elif ftype == "date":
                    vals[fname] = fields.Date.today()
                elif ftype == "datetime":
                    vals[fname] = fields.Datetime.now()
                elif ftype == "selection" and fdata.get("selection"):
                    vals[fname] = fdata["selection"][0][0]

            try:
                record = Model.create(vals)
                created_records |= record
            except Exception:
                # Skip if required fields are missing
                pass

        return created_records
