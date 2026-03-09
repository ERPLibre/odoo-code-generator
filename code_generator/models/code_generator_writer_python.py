#!/usr/bin/env python3
# © 2021-2025 TechnoLibre (http://www.technolibre.ca)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

import ast
import logging
import os
import types
import uuid
from collections import defaultdict

from code_writer import CodeWriter
from lxml.builder import E
from odoo import api, models

from .. import code_generator_data
from .code_generator_writer_constants import (
    BLANK_LINE,
    BREAK_LINE,
    MAGIC_FIELDS,
    MODEL_HEAD,
    MODEL_SUPERUSER_HEAD,
    UNDEFINEDMESSAGE,
    XML_HEAD,
    XML_ODOO_CLOSING_TAG,
)

_logger = logging.getLogger(__name__)


class CodeGeneratorWriterPythonMixin(models.AbstractModel):
    _name = "code.generator.writer.python.mixin"
    _description = "Code Generator Writer Python Mixin"

    @staticmethod
    def _get_lst_inherit_model(model_id):
        lst_model = []

        def recursive_get_inherit_model(actual_model_id):
            """
            actual_model_id is code.generator.ir.model.dependency
            """
            lst_model_id = [a.id for a in lst_model] + model_id.ids
            if actual_model_id.depend_id.id not in lst_model_id:
                new_model_id = actual_model_id.depend_id
                lst_model.append(new_model_id)
                if new_model_id.inherit_model_ids:
                    for new_inherit_model_id in new_model_id.inherit_model_ids:
                        recursive_get_inherit_model(new_inherit_model_id)

        if model_id.inherit_model_ids:
            for inherit_model_id in model_id.inherit_model_ids:
                recursive_get_inherit_model(inherit_model_id)

        return lst_model

    def _get_rec_name_inherit_model(self, model):
        # search in inherit
        lst_rec_name_inherit = []
        for inherit_model in model.inherit_model_ids:
            model_inherit_id = inherit_model.depend_id
            if model_inherit_id.id != model.id:
                # TODO can remove recursive and use _get_lst_inherit_model to get all rec_name model
                lst_rec_name_inherit.append(
                    self._get_rec_name_inherit_model(model_inherit_id)
                )
        result_rec_name = None
        new_rec_name = self.env[model.model]._rec_name
        if new_rec_name and new_rec_name != "name":
            result_rec_name = new_rec_name
        elif model.rec_name and model.rec_name != "name":
            result_rec_name = model.rec_name
        # Ignore rec_name if same of inherit parent
        if lst_rec_name_inherit and result_rec_name:
            if result_rec_name in lst_rec_name_inherit:
                return None
        return result_rec_name

    def _set_model_py_file(self, module, model, model_model):
        """
        Function to set the model files
        :param model:
        :param model_model:
        :return:
        """

        cg_data = code_generator_data.get_code_generator_data(self.env)

        key_special_endline = str(uuid.uuid1())

        cw = CodeWriter()

        code_ids = model.o2m_codes.filtered(
            lambda x: not x.is_templated
        ).sorted(key=lambda x: x.sequence)
        code_import_ids = model.o2m_code_import.filtered(
            lambda x: not x.is_templated
        ).sorted(key=lambda x: x.sequence)
        if code_import_ids:
            for code in code_import_ids:
                for code_line in code.code.split("\n"):
                    cw.emit(code_line)
        else:
            # search api or contextmanager
            # TODO ignore api, because need to search in code
            has_context_manager = False
            lst_import = MODEL_HEAD
            for code_id in code_ids:
                if (
                    code_id.decorator
                    and "@contextmanager" in code_id.decorator
                ):
                    has_context_manager = True
            if has_context_manager:
                lst_import.insert(1, "from contextlib import contextmanager")

            for line in lst_import:
                str_line = line.strip()
                cw.emit(str_line)

            if (
                model.m2o_inherit_py_class.name
                and model.m2o_inherit_py_class.module
            ):
                cw.emit(
                    f"from {model.m2o_inherit_py_class.module} import"
                    f" {model.m2o_inherit_py_class.name}"
                )

        cw.emit()
        cw.emit(
            "class"
            f" {self._get_class_name(model.model)}({self._get_python_class_4inherit(model)}):"
        )

        with cw.indent():
            """
            _name
            _table =
            _description
            _auto = False
            _log_access = False
            _order = ""
            _rec_name = ""
            _foreign_keys = []
            """
            # Force unique inherit
            lst_inherit = sorted(
                list(set([a.depend_id.model for a in model.inherit_model_ids]))
            )

            add_name = False
            if model.model not in lst_inherit:
                add_name = True
                cw.emit(f"_name = '{model.model}'")

            if lst_inherit:
                if len(lst_inherit) == 1:
                    str_inherit = f"'{lst_inherit[0]}'"
                else:
                    str_inherit_internal = '", "'.join(lst_inherit)
                    str_inherit = f'["{str_inherit_internal}"]'
                cw.emit(f"_inherit = {str_inherit}")

            if model.description:
                new_description = model.description.replace("'", "\\'")
                cw.emit(f"_description = '{new_description}'")
            elif not lst_inherit or add_name:
                cw.emit(f"_description = '{model.name}'")
            rec_name = self._get_rec_name_inherit_model(model)
            if rec_name:
                cw.emit(f"_rec_name = '{rec_name}'")
            if model.order:
                new_order = model.order.replace("'", "\\'")
                cw.emit(f"_order = '{new_order}'")

            if model.inherits_model:
                dct_inherits = {}
                for entry in model.inherits_model.split(";"):
                    entry = entry.strip()
                    if ":" in entry:
                        parent_model, field_name = entry.split(":", 1)
                        dct_inherits[parent_model.strip()] = (
                            field_name.strip()
                        )
                if len(dct_inherits) == 1:
                    k, v = next(iter(dct_inherits.items()))
                    cw.emit(f"_inherits = {{'{k}': '{v}'}}")
                elif dct_inherits:
                    parts = ", ".join(
                        f"'{k}': '{v}'"
                        for k, v in dct_inherits.items()
                    )
                    cw.emit(f"_inherits = {{{parts}}}")

            if model.parent_store:
                cw.emit("_parent_store = True")

            if model.parent_name_field:
                cw.emit(
                    f"_parent_name = '{model.parent_name_field}'"
                )

            # TODO _local_fields, _period_number, _log_access, _auto

            self._get_model_constrains(cw, model, module)

            f2exports = self._get_model_fields_f2export(model, module)

            lst_method_before = []
            # Detect method to move before field
            for ir_model_field_id in f2exports:
                if ir_model_field_id.default_lambda:
                    for code_id in code_ids:
                        if code_id.name == ir_model_field_id.default_lambda:
                            lst_method_before.append(code_id)

            lst_method_after = [
                code_id
                for code_id in code_ids
                if code_id not in lst_method_before
            ]

            self._write_code(
                cw, model, module, lst_method_before, key_special_endline
            )

            self._get_model_fields(cw, model, module, f2exports)

            # code_ids = self.env["code.generator.model.code"].search(
            #     [("m2o_module", "=", module.id)]
            # )

            self._write_code(
                cw, model, module, lst_method_after, key_special_endline
            )

        if model.transient:
            pypath = cg_data.wizards_path
        elif model.o2m_reports and self.env[model.model]._abstract:
            pypath = cg_data.reports_path
        else:
            pypath = cg_data.models_path

        model_file_path = os.path.join(pypath, f"{model_model}.py")

        cg_data.write_file_str(model_file_path, cw.render())

        return model_file_path

    def _set_module_security(self, module, l_model_rules, l_model_csv_access):
        """
        Function to set the module security file
        :param module:
        :param l_model_rules:
        :param l_model_csv_access:
        :return:
        """
        cg_data = code_generator_data.get_code_generator_data(self.env)

        l_model_csv_access.insert(
            0,
            "id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink",
        )

        if module.o2m_groups or l_model_rules:
            l_module_security = ["<data>\n"]

            for group in module.o2m_groups:

                l_module_security += [
                    '<record model="res.groups" id="%s">'
                    % self._get_group_data_name(group)
                ]
                l_module_security += [
                    '<field name="name">%s</field>' % group.name
                ]

                if group.comment:
                    l_module_security += [
                        '<field name="comment">%s</field>' % group.comment
                    ]

                if group.implied_ids:
                    l_module_security += [
                        '<field name="implied_ids" eval="[%s]"/>'
                        % ", ".join(
                            group.implied_ids.mapped(
                                lambda g: "(4, ref('%s'))"
                                % self._get_group_data_name(g)
                            )
                        )
                    ]

                l_module_security += ["</record>\n"]

            l_module_security += l_model_rules

            l_module_security += ["</data>"]

            module_name = module.name.lower().strip()
            security_file_path = os.path.join(
                cg_data.security_path, f"{module_name}.xml"
            )
            cg_data.write_file_lst_content(
                security_file_path,
                XML_HEAD + l_module_security + XML_ODOO_CLOSING_TAG,
                data_file=True,
                insert_first=True,
            )

        if len(l_model_csv_access) > 1:
            model_access_file_path = os.path.join(
                cg_data.security_path, "ir.model.access.csv"
            )
            cg_data.write_file_lst_content(
                model_access_file_path,
                l_model_csv_access,
                data_file=True,
                insert_first=True,
            )

    def _get_model_access(self, module, model):
        """
        Function to obtain the model access
        :param model:
        :return:
        """

        l_model_csv_access = []

        for access in model.access_ids:
            access_name = access.name

            access_model_data = self.env["ir.model.data"].search(
                [
                    ("module", "=", module.name),
                    ("model", "=", "ir.model.access"),
                    ("res_id", "=", access.id),
                ]
            )

            access_id = (
                access_model_data[0].name
                if access_model_data
                else self._lower_replace(access_name)
            )

            access_model = self._get_model_model(access.model_id.model)

            access_group = (
                self._get_group_data_name(access.group_id)
                if access.group_id
                else ""
            )

            access_read, access_create, access_write, access_unlink = (
                1 if access.perm_read else 0,
                1 if access.perm_create else 0,
                1 if access.perm_write else 0,
                1 if access.perm_unlink else 0,
            )

            l_model_csv_access.append(
                "%s,%s,model_%s,%s,%s,%s,%s,%s"
                % (
                    access_id,
                    access_name,
                    access_model,
                    access_group,
                    access_read,
                    access_create,
                    access_write,
                    access_unlink,
                )
            )

        return l_model_csv_access

    def _get_model_rules(self, module, model):
        """
        Function to obtain the model rules
        :param model:
        :return:
        """

        l_model_rules = []

        for rule in model.rule_ids:

            if rule.name:
                l_model_rules.append(
                    '<record model="ir.rule" id="%s">'
                    % self._lower_replace(rule.name)
                )
                l_model_rules.append(
                    '<field name="name">%s</field>' % rule.name
                )

            else:
                l_model_rules.append(
                    '<record model="ir.rule" id="%s_rrule_%s">'
                    % (
                        self._get_model_data_name(
                            rule.model_id, module_name=module.name
                        ),
                        rule.id,
                    )
                )

            l_model_rules.append(
                '<field name="model_id" ref="%s"/>'
                % self._get_model_data_name(
                    rule.model_id, module_name=module.name
                )
            )

            if rule.domain_force:
                l_model_rules.append(
                    '<field name="domain_force">%s</field>' % rule.domain_force
                )

            if not rule.active:
                l_model_rules.append('<field name="active" eval="False" />')

            if rule.groups:
                l_model_rules.append(self._get_m2m_groups(rule.groups))

            if not rule.perm_read:
                l_model_rules.append('<field name="perm_read" eval="False" />')

            if not rule.perm_create:
                l_model_rules.append(
                    '<field name="perm_create" eval="False" />'
                )

            if not rule.perm_write:
                l_model_rules.append(
                    '<field name="perm_write" eval="False" />'
                )

            if not rule.perm_unlink:
                l_model_rules.append(
                    '<field name="perm_unlink" eval="False" />'
                )

            l_model_rules.append("</record>\n")

        return l_model_rules

    def _get_m2m_groups(self, m2m_groups):
        """

        :param m2m_groups:
        :return:
        """

        return '<field name="groups_id" eval="[(6,0, [%s])]" />' % ", ".join(
            m2m_groups.mapped(
                lambda g: "ref(%s)" % self._get_group_data_name(g)
            )
        )

    def _get_m2m_groups_etree(self, m2m_groups):
        """

        :param m2m_groups:
        :return:
        """

        var = ", ".join(
            m2m_groups.mapped(
                lambda g: "ref(%s)" % self._get_group_data_name(g)
            )
        )
        return E.field({"name": "groups_id", "eval": f"[(6,0, [{var}])]"})

    def _generate_field_from_model(
        self, f2export, model_name, lst_field_inherit, dct_field_attr_diff
    ):
        # Documentation to understand how attributes work, check file odoo/odoo/addons/base/models/ir_model.py function _instanciate_attrs
        # Check odoo/odoo/fields.py in documentation
        if lst_field_inherit and not dct_field_attr_diff:
            return [], False, None, False
        has_endline = False
        lst_attribute_to_filter = []
        lst_first_field_attribute = []
        lst_field_attribute = []
        compute = None
        lst_last_field_attribute = []
        extra_info = (
            self.env[f2export.model]
            .fields_get(f2export.name)
            .get(f2export.name)
        )
        dct_field_attribute = {}

        code_generator_compute = f2export.get_code_generator_compute()
        if not code_generator_compute and not f2export.related:
            code_generator_compute = self._get_compute_fct(f2export)

        # TODO not optimal to remove attributes, but more easy ;-)
        if dct_field_attr_diff:
            for attr_key, lst_value in dct_field_attr_diff.items():
                if attr_key == "default":
                    dct_field_attribute[attr_key] = self._get_default(f2export)
                else:
                    dct_field_attribute[attr_key] = getattr(f2export, attr_key)
            # Exception for compute
            if "compute" in dct_field_attr_diff.keys():
                new_value_compute = self._get_compute_fct(f2export)
                if not new_value_compute:
                    dct_field_attribute["compute"] = None
                    if dct_field_attribute.get("store"):
                        # no need to store when no compute
                        del dct_field_attribute["store"]
                    if dct_field_attribute.get("readonly") is False:
                        del dct_field_attribute["readonly"]
                else:
                    dct_field_attribute["compute"] = new_value_compute
            # Rename attribute
            if "relation" in dct_field_attribute.keys():
                dct_field_attribute["comodel_name"] = dct_field_attribute[
                    "relation"
                ]
                del dct_field_attribute["relation"]
            if "field_description" in dct_field_attribute.keys():
                dct_field_attribute["string"] = dct_field_attribute[
                    "field_description"
                ]
                del dct_field_attribute["field_description"]
            if "relation_field" in dct_field_attribute.keys():
                dct_field_attribute["inverse_name"] = dct_field_attribute[
                    "relation_field"
                ]
                del dct_field_attribute["relation_field"]
            if "relation_table" in dct_field_attribute.keys():
                dct_field_attribute["relation"] = dct_field_attribute[
                    "relation_table"
                ]
                del dct_field_attribute["relation_table"]
            if "copied" in dct_field_attribute.keys():
                dct_field_attribute["copy"] = dct_field_attribute["copied"]
                del dct_field_attribute["copied"]
        else:
            # TODO use if cannot find information
            # field_selection = self.env[f2export.model].fields_get(f2export.name).get(f2export.name)

            related_field_id = None
            if f2export.related:
                dct_field_attribute["related"] = f2export.related
                # Get related field if, it works like inherit
                (
                    related_inside_field,
                    related_outside_field,
                ) = f2export.related.split(".")
                # This need to be a many2many
                related_model_name = f2export.model_id.field_id.filtered(
                    lambda field: field.name == related_inside_field
                ).relation
                related_outside_field_id = self.env["ir.model.fields"].search(
                    [
                        ("model", "=", related_model_name),
                        ("name", "=", related_inside_field),
                    ],
                    limit=1,
                )
                if not related_outside_field_id:
                    _logger.error(
                        "Cannot find related field from field"
                        f" '{f2export.name}' and model '{f2export.model}'"
                    )
                else:
                    # Get is model and search outside field
                    related_field_id = (
                        related_outside_field_id.model_id.field_id.filtered(
                            lambda field: field.name == related_outside_field
                        )
                    )

            # Respect sequence in list, order listed by human preference
            if (
                f2export.ttype in ("selection", "reference")
                and not f2export.related
            ):
                # cannot support selection item with related attributes
                str_selection = f2export.get_selection()
                if str_selection:
                    dct_field_attribute["selection"] = str_selection

            if f2export.ttype == "properties":
                if f2export.related:
                    pass
                else:
                    definition_record = extra_info.get(
                        "definition_record"
                    ) if extra_info else None
                    definition_record_field = extra_info.get(
                        "definition_record_field"
                    ) if extra_info else None
                    if definition_record:
                        dct_field_attribute[
                            "definition_record"
                        ] = definition_record
                    if definition_record_field:
                        dct_field_attribute[
                            "definition_record_field"
                        ] = definition_record_field

            if f2export.ttype == "many2one_reference":
                model_field = extra_info.get(
                    "model_field"
                ) if extra_info else None
                if model_field:
                    dct_field_attribute["model_field"] = model_field

            if f2export.ttype in ["many2one", "one2many", "many2many"]:
                if f2export.relation:
                    dct_field_attribute["comodel_name"] = f2export.relation

                if f2export.ttype == "one2many" and f2export.relation_field:
                    dct_field_attribute["inverse_name"] = (
                        f2export.relation_field
                    )

                if f2export.ttype == "many2many":
                    # elif f2export.relation_table.startswith("x_"):
                    #     # TODO why ignore relation when start name with x_? Is it about x_name?
                    #     # A relation who begin with x_ is an automated relation, ignore it
                    #     ignored_relation = True
                    if (
                        f2export.relation_table
                        and f"{f2export.model.replace('.', '_')}_id"
                        != f2export.column1
                        and f"{f2export.relation.replace('.', '_')}_id"
                        != f2export.column2
                        and f"{f2export.model.replace('.', '_')}_{f2export.relation.replace('.', '_')}"
                        != f2export.relation_table
                    ):
                        dct_field_attribute["relation"] = (
                            f2export.relation_table
                        )
                        dct_field_attribute["column1"] = f2export.column1
                        dct_field_attribute["column2"] = f2export.column2
                    elif (
                        dct_field_attribute.get("relation") is None
                        and f2export.relation_table
                        and f2export.relation
                        and len(f2export.relation_table) > 63
                    ):
                        # TODO need to validate it's not exist, the new relation table
                        # relation can be empty, the system will generate it, but crash if highter then 63
                        new_relation_table = f"{f2export.name}_{f2export.model.replace('.', '_')}_rel"
                        if len(new_relation_table) > 63:
                            # again!
                            lst_split_relation_t = f2export.relation_table[
                                :-4
                            ].split("_")
                            if lst_split_relation_t[0] == "x":
                                lst_split_relation_t = lst_split_relation_t[1:]
                            # Take only first later of each word
                            new_relation_table = (
                                "_".join([a[0] for a in lst_split_relation_t])
                                + "_rel"
                            )
                            if len(new_relation_table) > 63:
                                new_relation_table = new_relation_table[
                                    :63
                                ].trim("_")
                        dct_field_attribute["relation"] = new_relation_table
                if extra_info:
                    domain_info = extra_info.get("domain")
                else:
                    domain_info = ""
                if f2export.domain and f2export.domain != "[]":
                    dct_field_attribute["domain"] = f2export.domain
                elif domain_info and domain_info != "[]":
                    dct_field_attribute["domain"] = domain_info
                if f2export.force_domain:
                    try:
                        eval(f2export.force_domain)
                        dct_field_attribute["domain_raw"] = (
                            f2export.force_domain
                        )
                    except Exception as e:
                        # Cannot transform it in string
                        dct_field_attribute["domain"] = f2export.force_domain

                if (
                    f2export.ttype == "many2one"
                    and f2export.on_delete
                    and f2export.on_delete != "set null"
                ):
                    dct_field_attribute["ondelete"] = f2export.on_delete

            if (
                f2export.field_description
                and f2export.name.replace("_", " ").title()
                != f2export.field_description
            ):
                if not (
                    related_field_id
                    and related_field_id.field_description
                    == f2export.field_description
                ):
                    dct_field_attribute["string"] = f2export.field_description

            if f2export.ttype == "monetary":
                dct_field_attribute["currency_field"] = f2export.currency_field

            if (
                f2export.ttype == "char" or f2export.ttype == "reference"
            ) and f2export.size != 0:
                dct_field_attribute["size"] = f2export.size

            if f2export.related:
                dct_field_attribute["related"] = f2export.related

            if f2export.readonly and not code_generator_compute:
                # Note that a computed field without an inverse method is readonly by default.
                if not (
                    related_field_id
                    and related_field_id.readonly == f2export.readonly
                ):
                    dct_field_attribute["readonly"] = True

            if f2export.required:
                dct_field_attribute["required"] = True

            if f2export.index:
                dct_field_attribute["index"] = True

            field_context = f2export.get_field_context()
            if field_context:
                # Extract content from string
                try:
                    dct_field_context = ast.literal_eval(field_context)
                    dct_field_attribute["context"] = dct_field_context
                except Exception as e:
                    _logger.error(
                        f"Cannot extract dict from context '{field_context}'"
                        f" for field '{f2export.name}' in model"
                        f" '{f2export.model}'"
                    )

            tv = getattr(f2export, "tracking", 0)
            if tv:
                if tv == 1:
                    tv = True
                # TODO ignore when store=False
                dct_field_attribute["tracking"] = tv

            # Get default value
            default_lambda = f2export.get_default_lambda()
            if default_lambda:
                dct_field_attribute["default"] = (
                    "noquote",
                    default_lambda.replace("'", '"'),
                )
            else:
                default_value = None
                if f2export.default:
                    default_value = f2export.default
                else:
                    dct_default_value = self.env[model_name].default_get(
                        [f2export.name]
                    )
                    if dct_default_value:
                        default_value = dct_default_value.get(f2export.name)
                if default_value:
                    # TODO support default = None
                    if f2export.ttype == "boolean" and (
                        default_value == "True" or default_value is True
                    ):
                        dct_field_attribute["default"] = True
                    elif f2export.ttype == "boolean" and (
                        default_value == "False" or default_value is False
                    ):
                        # TODO Only if the field inherit, else None it
                        dct_field_attribute["default"] = False
                    elif f2export.ttype == "integer":
                        dct_field_attribute["default"] = int(default_value)
                    elif f2export.ttype in (
                        "char",
                        "selection",
                        "text",
                        "html",
                    ):
                        dct_field_attribute["default"] = default_value
                    else:
                        _logger.warning(
                            f"Not supported default type '{f2export.ttype}',"
                            f" field name '{f2export.name}', model"
                            f" '{f2export.model_id.model}', value"
                            f" '{default_value}'"
                        )
                        dct_field_attribute["default"] = default_value

            # TODO support states
            if f2export.groups:
                dct_field_attribute["groups"] = f2export.groups.mapped(
                    lambda g: self._get_group_data_name(g)
                )

            compute = f2export.compute and f2export.depends

            if code_generator_compute and not isinstance(
                code_generator_compute, types.FunctionType
            ):
                dct_field_attribute["compute"] = code_generator_compute
            elif compute:
                dct_field_attribute["compute"] = f"_compute_{f2export.name}"
            elif f2export.compute:
                dct_field_attribute["compute"] = f2export.compute

            if (
                f2export.ttype == "one2many" or f2export.related or compute
            ) and f2export.copied:
                dct_field_attribute["copy"] = True

            # TODO support oldname

            # TODO support group_operator

            # TODO support inverse

            # TODO support search

            if f2export.precompute:
                dct_field_attribute["precompute"] = True

            # TODO support store
            if f2export.store and code_generator_compute:
                dct_field_attribute["store"] = True
            elif (
                not f2export.store
                and not code_generator_compute
                and not related_field_id
            ):
                # By default, a computed field is not stored to the database, and is computed on-the-fly.
                dct_field_attribute["store"] = False

            # TODO support compute_sudo

            if f2export.translate:
                dct_field_attribute["translate"] = True

            # TODO not working, but no module need it
            # if not f2export.selectable and f2export.ttype == "one2many":
            #     # Default is True
            #     # Check _reflect_field_params in file odoo/odoo/addons/base/models/ir_model.py
            #     dct_field_attribute["selectable"] = False

            # TODO support digits, check dp.get_precision('Account')

            if f2export.help:
                dct_field_attribute["help"] = f2export.help.replace("\\'", '"')

            # Ignore it, by default it's copy=False
            # elif f2export.ttype != 'one2many' and not f2export.related and not compute and not f2export.copied:
            #     dct_field_attribute["copy"] = False

            if (
                f2export.code_generator_ir_model_fields_ids
                and f2export.code_generator_ir_model_fields_ids.filter_field_attribute
            ):
                # Filter list of attribute
                lst_attribute_to_filter = f2export.code_generator_ir_model_fields_ids.filter_field_attribute.split(
                    ";"
                )
                lst_attribute_to_filter = [
                    a.strip() for a in lst_attribute_to_filter if a.strip()
                ]

        for key, value in dct_field_attribute.items():
            if lst_attribute_to_filter and key not in lst_attribute_to_filter:
                continue
            if type(value) is str:
                if key == "domain_raw":
                    lst_last_field_attribute.append(f"domain={value}")
                else:
                    # TODO find another solution than removing \n, this cause error with cw.CodeWriter
                    copy_value = value.replace("'", "\\'")
                    value = value.replace("\n", " ").replace("'", "\\'")
                    if key == "comodel_name":
                        lst_first_field_attribute.append(f"{key}='{value}'")
                    elif key == "ondelete":
                        lst_last_field_attribute.append(f"{key}='{value}'")
                    else:
                        if "\n" in copy_value:
                            has_endline = True
                            if '"""' in copy_value:
                                lst_field_attribute.append(
                                    f"{key}='''{copy_value}'''"
                                )
                            elif "'''" in copy_value:
                                lst_field_attribute.append(
                                    f'{key}="""{copy_value}"""'
                                )
                            else:
                                lst_field_attribute.append(
                                    f'{key}="""{copy_value}"""'
                                )
                        else:
                            lst_field_attribute.append(f"{key}='{copy_value}'")
            elif type(value) is list or type(value) is tuple:
                # TODO find another solution than removing \n, this cause error with cw.CodeWriter
                if key == "default" and value[0] == "noquote":
                    # Exception for lambda
                    lst_field_attribute.append(f"{key}={value[1]}")
                else:
                    new_value = str(value).replace("\n", " ")
                    lst_field_attribute.append(f"{key}={new_value}")
            else:
                lst_field_attribute.append(f"{key}={value}")

        lst_field_attribute = (
            lst_first_field_attribute
            + lst_field_attribute
            + lst_last_field_attribute
        )

        return lst_field_attribute, has_endline, compute, True

    def _get_model_fields_f2export(self, model, module):
        """
        Function to obtain the model fields
        :param model:
        :return:
        """
        # TODO detect if contain code_generator_sequence, else order by name
        # TODO some field.modules containts space, this is why it strip each element
        # the field.modules is full when the module is installed, check file odoo/odoo/addons/base/models/ir_model.py fct _in_modules
        f2exports = (
            model.field_id.filtered(
                lambda field: field.name not in MAGIC_FIELDS
                and (
                    module.name
                    in [a.strip() for a in field.modules.split(",")]
                    or not field.modules
                )
            )
            .sorted(key=lambda r: r.code_generator_sequence)
            .with_context(lang=None)
        )

        if model.inherit_model_ids:
            is_whitelist = any(
                [a.is_show_whitelist_model_inherit_call() for a in f2exports]
            )
            if is_whitelist:
                f2exports = f2exports.filtered(
                    lambda field: field.name not in MAGIC_FIELDS
                    and not field.is_hide_blacklist_model_inherit
                    and (
                        not is_whitelist
                        or (
                            is_whitelist
                            and field.is_show_whitelist_model_inherit_call()
                        )
                    )
                ).with_context(lang=None)
            # else:
            #     father_ids = self.env["ir.model"].browse(
            #         [a.depend_id.id for a in model.inherit_model_ids]
            #     )
            #     set_unique_field = set()
            #     for father_id in father_ids:
            #         fatherfieldnames = father_id.field_id.filtered(
            #             lambda field: field.name not in MAGIC_FIELDS
            #         ).mapped("name")
            #         set_unique_field.update(fatherfieldnames)
            #     f2exports = f2exports.filtered(
            #         lambda field: field.name not in list(set_unique_field)
            #     ).with_context(lang=None)
        return f2exports

    def _write_code(self, cw, model, module, code_ids, key_special_endline):
        # Add function
        for code in code_ids:
            cw.emit()
            if code.decorator:
                for line in code.decorator.split(";"):
                    if line:
                        cw.emit(line)
            return_v = "" if not code.returns else f" -> {code.returns}"
            # TODO Bug from uca, into ucb hook, so patch it
            param_formatted = code.param.replace("='''", '="\'"')
            cw.emit(f"def {code.name}({param_formatted}){return_v}:")

            code_formatted = code.code.replace("\\\n", key_special_endline)
            code_formatted = code_formatted.replace("\\'", "\\\\'")
            code_formatted = code_formatted.replace("\b", "\\b")
            # TODO Bug from uca, into ucb hook, so patch it
            code_formatted = code_formatted.replace("'\\\"'", "'\\\\\"'")
            code_formatted = code_formatted.replace("\"''", "\"\\''")
            code_formatted = code_formatted.replace('}"\'"', '}\\"\'"')
            code_formatted = code_formatted.replace(
                "osascript -e ", "osascript -e \\"
            )
            code_formatted = code_formatted.replace(
                '\\"{cmd}{str_keep_open}\\"',
                '\\\\"{cmd}{str_keep_open}\\\\"',
            )
            code_formatted = code_formatted.replace(
                'grep -nr "{s_value_error}"',
                'grep -nr \\\\"{s_value_error}"\\\\',
            )
            code_formatted = code_formatted.replace(
                'force replace " to "', 'force replace " to \\"'
            )
            code_formatted = code_formatted.replace(
                "{value_error}", "\\{value_error}"
            )
            code_formatted = code_formatted.replace(
                '\\"{s_value_error}\\"', '\\\\"{s_value_error}\\\\"'
            )
            with cw.indent():
                for code_line in code_formatted.split("\n"):
                    if key_special_endline in code_line:
                        code_line = code_line.replace(
                            key_special_endline, "\\\\n"
                        )
                    cw.emit(code_line)

    def _get_model_fields(self, cw, model, module, f2exports):
        """
        Function to obtain the model fields
        :param model:
        :return:
        """
        lst_inherit_model = self._get_lst_inherit_model(model)

        # Force field name first
        field_rec_name = model.get_rec_name()
        if not field_rec_name:
            field_rec_name = "name"
        lst_field_rec_name = f2exports.filtered(
            lambda field: field.name == field_rec_name
        )
        if lst_field_rec_name:
            lst_field_not_name = f2exports.filtered(
                lambda field: field.name != field_rec_name
            )
            lst_id = lst_field_rec_name.ids + lst_field_not_name.ids
            f2exports = (
                self.env["ir.model.fields"]
                .browse(lst_id)
                .with_context(lang=None)
            )

        lst_field_to_write = []
        for f2export in f2exports:
            lst_field_inherit = [
                b
                for a in lst_inherit_model
                for b in a.field_id
                if b.name == f2export.name
            ]
            # TODO update this list
            # Don't use field_description, but name instead, because field_description is transformed
            # Documentation to understand how attributes work, check file odoo/odoo/addons/base/models/ir_model.py function _instanciate_attrs
            lst_attribute_check_diff = [
                "readonly",
                "required",
                # "field_description",  # String
                "name",  # String
                "relation_field",  # inverse_name
                "relation",  # comodel_name
                "relation_table",  # relation
                # "default",
                "help",
                # "context",
                "compute",
                "domain",
                "store",
            ]
            dct_field_attr_diff = defaultdict(list)
            # TODO éviter d'écraser une valeur pour le multi héritage
            for field_inherit in lst_field_inherit:
                for attr_name in lst_attribute_check_diff:
                    actual_value = getattr(f2export, attr_name)
                    inherit_value = getattr(field_inherit, attr_name)
                    if actual_value != inherit_value:
                        dct_field_attr_diff[attr_name].append(inherit_value)
                self._find_field_computed(
                    dct_field_attr_diff, f2export, field_inherit
                )
                self._find_field_default(
                    dct_field_attr_diff, f2export, field_inherit
                )
            (
                lst_field_attribute,
                has_endline,
                compute,
                do_generate,
            ) = self._generate_field_from_model(
                f2export, model.model, lst_field_inherit, dct_field_attr_diff
            )
            if do_generate:
                lst_field_to_write.append(
                    (lst_field_attribute, f2export, has_endline, compute)
                )

        for (
            lst_field_attribute,
            f2export,
            has_endline,
            compute,
        ) in lst_field_to_write:
            # Write comment
            cw.emit()
            str_comment_before = f2export.get_comment_before()
            if str_comment_before:
                for str_comment in str_comment_before.split("\n"):
                    cw.emit(f"# {str_comment}")

            # Write field
            if not has_endline:
                cw.emit_list(
                    lst_field_attribute,
                    ("(", ")"),
                    before=(
                        f"{f2export.name} ="
                        f" {self._get_odoo_ttype_class(f2export.ttype)}"
                    ),
                )
            else:
                cw.emit(
                    f"{f2export.name} ="
                    f" {self._get_odoo_ttype_class(f2export.ttype)}("
                )
                with cw.indent():
                    for item in lst_field_attribute:
                        if "\n" in item:
                            lst_item = item.split("\n")
                            cw.emit(f"{lst_item[0]}")
                            i_last = len(lst_item) - 2
                            for i, inter_item in enumerate(lst_item[1:]):
                                if i == i_last:
                                    cw.emit_raw(f"{inter_item},\n")
                                else:
                                    cw.emit_raw(f"{inter_item}\n")
                        else:
                            cw.emit(f"{item},")
                cw.emit(")")

            # Write comment
            str_comment_after = f2export.get_comment_after()
            if str_comment_after:
                for str_comment in str_comment_after.split("\n"):
                    cw.emit(f"# {str_comment}")
                cw.emit()

            if compute:
                cw.emit()
                l_depends = self._get_l_map(
                    lambda e: e.strip(), f2export.depends.split(",")
                )

                cw.emit(
                    f"@api.depends({self._prepare_compute_constrained_fields(l_depends)})"
                )
                cw.emit(f"def _compute_{f2export.name}(self):")

                l_compute = f2export.compute.split("\n")
                # starting_spaces = 2
                # for line in l_compute:
                #     if self._get_starting_spaces(line) == 2:
                #         starting_spaces += 1
                #     l_model_fields.append('%s%s' % (TAB4 * starting_spaces, line.strip()))
                for line in l_compute:
                    with cw.indent():
                        cw.emit(line.rstrip())

    def _get_compute_fct(self, field_id):
        model_name = field_id.model
        # field.compute
        # field.store
        # field.related
        # field.inverse
        # field.compute_sudo
        computed_fields = [
            field
            for name, field in self.env[model_name]._fields.items()
            if field.compute
        ]
        lst_field = [a for a in computed_fields if a.name == field_id.name]
        if lst_field:
            field_relation = lst_field[0]
            return field_relation.compute
        return False

    def _get_default(self, field_id):
        default_value = field_id.get_default_lambda()
        if not default_value:
            default_value = self.env[field_id.model].default_get(
                [field_id.name]
            )
            if default_value:
                default_value = default_value.get(field_id.name)
        if not default_value:
            default_value = False
        return default_value

    def _find_field_computed(
        self, dct_field_attr_diff, f2export, field_inherit
    ):
        inherit_compute = self._get_compute_fct(field_inherit)
        actual_compute = self._get_compute_fct(f2export)
        if inherit_compute and not actual_compute:
            dct_field_attr_diff["compute"] = inherit_compute

    def _find_field_default(
        self, dct_field_attr_diff, f2export, field_inherit
    ):
        inherit_default = self._get_default(field_inherit)
        actual_default = self._get_default(f2export)
        if inherit_default != actual_default:
            dct_field_attr_diff["default"] = inherit_default
