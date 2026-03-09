#!/usr/bin/env python3
# © 2021-2025 TechnoLibre (http://www.technolibre.ca)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)
import logging
import uuid
from collections import defaultdict

from lxml import etree as ET
from lxml.builder import E
from odoo import _, api, fields, models
from odoo.models import MAGIC_COLUMNS

_logger = logging.getLogger(__name__)

MAGIC_FIELDS = MAGIC_COLUMNS + [
    "display_name",
    "__last_update",
    "access_url",
    "access_token",
    "access_warning",
]


class CodeGeneratorViewsStandardMixin(models.AbstractModel):
    _name = "code.generator.views.standard.mixin"
    _description = "Code Generator Views Standard Mixin"

    def _update_model_field_list_view(self, model_created_fields_list):
        return model_created_fields_list

    def _generate_list_views_models(
        self, model_created, model_created_fields, module, dct_value_to_create
    ):
        model_name = model_created.model
        model_name_str = model_name.replace(".", "_")

        lst_field_to_remove = ("active",)

        has_sequence = False
        for field_id in model_created_fields:
            if field_id.code_generator_list_view_sequence >= 0:
                has_sequence = True
                break

        if not has_sequence:
            lst_order_field_id = [[], [], []]
            # code_generator_list_view_sequence all -1, default value
            # Move rec_name in beginning
            # Move one2many at the end
            for field_id in model_created_fields:
                if field_id.name == model_created.rec_name:
                    # TODO write this value
                    lst_order_field_id[0].append(field_id.id)
                    # field_id.code_generator_list_view_sequence = 0
                elif field_id.ttype == "one2many":
                    lst_order_field_id[2].append(field_id.id)
                    # field_id.code_generator_list_view_sequence = 2
                else:
                    lst_order_field_id[1].append(field_id.id)
                    # field_id.code_generator_list_view_sequence = 1
            new_lst_order_field_id = (
                lst_order_field_id[0]
                + lst_order_field_id[1]
                + lst_order_field_id[2]
            )
            # TODO this can slow, can we accumulate this data for the end?
            # field_sorted_sequence_0 = self.env["ir.model.fields"].browse(
            #     lst_order_field_id[0]
            # )
            # field_sorted_sequence_1 = self.env["ir.model.fields"].browse(
            #     lst_order_field_id[1]
            # )
            # field_sorted_sequence_2 = self.env["ir.model.fields"].browse(
            #     lst_order_field_id[2]
            # )
            # field_sorted_sequence_0.write(
            #     {"code_generator_form_simple_view_sequence": 0}
            # )
            # field_sorted_sequence_1.write(
            #     {"code_generator_form_simple_view_sequence": 1}
            # )
            # field_sorted_sequence_2.write(
            #     {"code_generator_form_simple_view_sequence": 2}
            # )
            # field_sorted_ids = (
            #     field_sorted_sequence_0
            #     + field_sorted_sequence_1
            #     + field_sorted_sequence_2
            # )
            lst_field_sorted = (
                self.env["ir.model.fields"]
                .browse(new_lst_order_field_id)
                .filtered(
                    lambda field: not field.ignore_on_code_generator_writer
                )
            )
        else:
            # Use list view sequence, or generic sequence
            lst_field_sorted = model_created_fields.filtered(
                lambda field: not field.ignore_on_code_generator_writer
            ).sorted(lambda field: field.code_generator_list_view_sequence)

        # lst_field = [E.field({"name": a.name}) for a in model_created_fields]
        lst_field = []
        for field_id in lst_field_sorted:
            if field_id.name in lst_field_to_remove:
                continue
            # TODO validate code_generator_list_view_sequence is supported
            # if a.code_generator_list_view_sequence >= 0
            if field_id.ttype == "monetary":
                dct_value = {
                    "name": field_id.name,
                    "widget": "monetary",
                    "sum": f"Total {field_id.field_description}",
                    "avg": f"{field_id.field_description} moyen",
                }
            elif field_id.ttype == "many2one" and field_id.relation in [
                "res.currency"
            ]:
                dct_value = {"name": field_id.name, "invisible": "1"}
            else:
                dct_value = {"name": field_id.name}
            if field_id.force_widget:
                dct_value["widget"] = field_id.force_widget
            dct_value = dict(sorted(dct_value.items(), key=lambda kv: kv[0]))
            lst_field.append(E.field(dct_value))
        arch_xml = E.list(
            {
                # TODO enable this when missing form
                # "editable": "top",
            },
            *lst_field,
        )
        str_arch = ET.tostring(arch_xml, pretty_print=True)
        str_arch = b'<?xml version="1.0"?>\n' + str_arch
        # ir_ui_view_value = {
        #     "name": f"{model_name_str}_list",
        #     "type": "list",
        #     "model": model_name,
        #     "arch": str_arch,
        #     "m2o_model": model_created.id,
        # }
        # dct_value_to_create["ir.ui.view"].append(ir_ui_view_value)
        view_value = self.env["ir.ui.view"].search(
            [
                # ("name", "=", f"{model_name_str}_list"),
                ("type", "=", "list"),
                ("model", "=", model_name),
                # ("arch", "=", str_arch),
                # ("m2o_model", "=", model_created.id),
            ]
        )
        if not view_value:
            view_value = self.env["ir.ui.view"].create(
                [
                    {
                        "name": f"{model_name_str}_list",
                        "type": "list",
                        "model": model_name,
                        "arch": str_arch,
                        "m2o_model": model_created.id,
                    }
                ]
            )
        else:
            _logger.warning(
                f"View '{model_name_str}_list' of model '{model_name}' already"
                " exist."
            )

        return view_value

    def _generate_form_views_models(
        self, model_created, model_created_fields, module, dct_value_to_create
    ):
        model_name = model_created.model
        model_name_str = model_name.replace(".", "_")
        lst_item_sheet = []

        lst_field_to_transform_button_box = ("active",)

        has_sequence = False
        for field_id in model_created_fields:
            if field_id.code_generator_form_simple_view_sequence >= 0:
                has_sequence = True
                break

        if not has_sequence:
            lst_order_field_id = [[], [], []]
            # code_generator_form_simple_view_sequence all -1, default value
            # Move rec_name in beginning
            # Move one2many at the end
            for field_id in model_created_fields:
                if field_id.name == model_created.rec_name:
                    # TODO write this value
                    lst_order_field_id[0].append(field_id.id)
                    # field_id.code_generator_form_simple_view_sequence = 0
                elif field_id.ttype == "one2many":
                    lst_order_field_id[2].append(field_id.id)
                    # field_id.code_generator_form_simple_view_sequence = 2
                else:
                    lst_order_field_id[1].append(field_id.id)
                    # field_id.code_generator_form_simple_view_sequence = 1
            new_lst_order_field_id = (
                lst_order_field_id[0]
                + lst_order_field_id[1]
                + lst_order_field_id[2]
            )

            # TODO this can slow, can we accumulate this data for the end?
            # field_sorted_sequence_0 = self.env["ir.model.fields"].browse(
            #     lst_order_field_id[0]
            # )
            # field_sorted_sequence_1 = self.env["ir.model.fields"].browse(
            #     lst_order_field_id[1]
            # )
            # field_sorted_sequence_2 = self.env["ir.model.fields"].browse(
            #     lst_order_field_id[2]
            # )
            # field_sorted_sequence_0.write(
            #     {"code_generator_form_simple_view_sequence": 0}
            # )
            # field_sorted_sequence_1.write(
            #     {"code_generator_form_simple_view_sequence": 1}
            # )
            # field_sorted_sequence_2.write(
            #     {"code_generator_form_simple_view_sequence": 2}
            # )
            # field_sorted_ids = (
            #     field_sorted_sequence_0
            #     + field_sorted_sequence_1
            #     + field_sorted_sequence_2
            # )
            field_sorted_ids = (
                self.env["ir.model.fields"]
                .browse(new_lst_order_field_id)
                .filtered(
                    lambda field: not field.ignore_on_code_generator_writer
                )
            )
        else:
            field_sorted_ids = model_created_fields.filtered(
                lambda field: not field.ignore_on_code_generator_writer
            ).sorted(
                lambda x: x.code_generator_form_simple_view_sequence,
            )

        lst_button_box = []
        for field_id in field_sorted_ids:
            if field_id.name in lst_field_to_transform_button_box:
                item_field = E.field(
                    {"name": field_id.name, "widget": "boolean_button"}
                )
                item_button = E.button(
                    {
                        "class": "oe_stat_button",
                        "icon": "fa-archive",
                        "name": "toggle_active",
                        "type": "object",
                    },
                    item_field,
                )
                lst_button_box.append(item_button)

        if lst_button_box:
            item = E.div(
                {"class": "oe_button_box", "name": "button_box"},
                *lst_button_box,
            )
            lst_item_sheet.append(item)

        # First is title
        lst_field_continue = [
            a
            for a in field_sorted_ids
            if a.name not in lst_field_to_transform_button_box
        ]
        if len(lst_field_continue) > 0:
            field_sorted_first_id = lst_field_continue[0]
        else:
            field_sorted_first_id = None
        if len(lst_field_continue) > 1:
            lst_field_sorted_group_id = lst_field_continue[1:]
        else:
            lst_field_sorted_group_id = []

        if field_sorted_first_id:
            value = self._create_form_field_views(field_sorted_first_id)
            # TODO add second title
            lst_item_sheet.append(
                E.div(
                    {"class": "oe_title"},
                    E.label(
                        {
                            "for": field_sorted_first_id.name,
                            "class": "oe_edit_only",
                        }
                    ),
                    E.h1({}, E.field(value)),
                )
            )

        lst_value_group = []
        for field_id in lst_field_sorted_group_id:
            value = self._create_form_field_views(field_id)
            lst_value_group.append(E.field(value))
        lst_item_sheet.append(E.group({}, *lst_value_group))

        lst_item_form = [E.sheet({}, *lst_item_sheet)]

        if model_created.enable_activity:
            # xml_activity = E.div(
            #     {"class": "oe_chatter"},
            #     E.field(
            #         {
            #             # "groups": "base.group_user",
            #             # "help": "",
            #             "name": "message_follower_ids",
            #             "widget": "mail_followers",
            #         }
            #     ),
            #     E.field({"name": "activity_ids", "widget": "mail_activity"}),
            #     E.field(
            #         {
            #             "name": "message_ids",
            #             "options": "{'post_refresh': 'recipients'}",
            #             "widget": "mail_thread",
            #         }
            #     ),
            # )
            xml_activity = E.chatter()
            lst_item_form.append(xml_activity)

        arch_xml = E.form(
            {
                "string": "Titre",
            },
            *lst_item_form,
        )
        str_arch = ET.tostring(arch_xml, pretty_print=True)
        str_arch = b'<?xml version="1.0"?>\n' + str_arch
        # ir_ui_view_value = {
        #     "name": f"{model_name_str}_form",
        #     "type": "form",
        #     "model": model_name,
        #     "arch": str_arch,
        #     "m2o_model": model_created.id,
        # }
        # dct_value_to_create["ir.ui.view"].append(ir_ui_view_value)
        view_value = self.env["ir.ui.view"].search(
            [
                # ("name", "=", f"{model_name_str}_form"),
                ("type", "=", "form"),
                ("model", "=", model_name),
                # ("arch", "=", str_arch),
                # ("m2o_model", "=", model_created.id),
            ]
        )

        if not view_value:
            view_value = self.env["ir.ui.view"].create(
                [
                    {
                        "name": f"{model_name_str}_form",
                        "type": "form",
                        "model": model_name,
                        "arch": str_arch,
                        "m2o_model": model_created.id,
                    }
                ]
            )

            self._create_ir_model_data(
                module,
                "ir.ui.view",
                view_value.id,
                model_name_str,
                suffix_name="view_form",
            )
        else:
            _logger.warning(
                f"Cannot generate view '{model_name_str}_form' of model"
                f" '{model_name}'"
            )

        return view_value

    def _create_form_field_views(self, field_id, key_geo="geo_"):
        value = {"name": field_id.name}

        if field_id.force_widget:
            if field_id.force_widget != "link_button":
                # TODO add a configuration to force edible mode, if not editable, choose widget = link button
                # special case, link button is readonly in form,
                value["widget"] = field_id.force_widget
        elif key_geo in field_id.ttype:
            value["widget"] = "geo_edit_map"
            # value["attrs"] = "{'invisible': [('type', '!=', '"f"{model[len(key):]}')]""}"
        return value

    def _generate_kanban_views_models(
        self, model_created, model_created_fields, module, dct_value_to_create
    ):
        model_name = model_created.model
        model_name_str = model_name.replace(".", "_")

        lst_field_to_remove = ("active",)

        has_sequence = False
        for field_id in model_created_fields:
            if field_id.code_generator_kanban_view_sequence >= 0:
                has_sequence = True
                break

        if not has_sequence:
            lst_order_field_id = [[], [], []]
            # code_generator_kanban_view_sequence all -1, default value
            # Move rec_name in beginning
            # Move one2many at the end
            for field_id in model_created_fields:
                if field_id.name == model_created.rec_name:
                    # TODO write this value
                    lst_order_field_id[0].append(field_id.id)
                    # field_id.code_generator_kanban_view_sequence = 0
                elif field_id.ttype == "one2many":
                    lst_order_field_id[2].append(field_id.id)
                    # field_id.code_generator_kanban_view_sequence = 2
                else:
                    lst_order_field_id[1].append(field_id.id)
                    # field_id.code_generator_kanban_view_sequence = 1
            new_lst_order_field_id = (
                lst_order_field_id[0]
                + lst_order_field_id[1]
                + lst_order_field_id[2]
            )
            # TODO this can slow, can we accumulate this data for the end?
            # field_sorted_sequence_0 = self.env["ir.model.fields"].browse(
            #     lst_order_field_id[0]
            # )
            # field_sorted_sequence_1 = self.env["ir.model.fields"].browse(
            #     lst_order_field_id[1]
            # )
            # field_sorted_sequence_2 = self.env["ir.model.fields"].browse(
            #     lst_order_field_id[2]
            # )
            # field_sorted_sequence_0.write(
            #     {"code_generator_form_simple_view_sequence": 0}
            # )
            # field_sorted_sequence_1.write(
            #     {"code_generator_form_simple_view_sequence": 1}
            # )
            # field_sorted_sequence_2.write(
            #     {"code_generator_form_simple_view_sequence": 2}
            # )
            # field_sorted_ids = (
            #     field_sorted_sequence_0
            #     + field_sorted_sequence_1
            #     + field_sorted_sequence_2
            # )
            lst_field_sorted = (
                self.env["ir.model.fields"]
                .browse(new_lst_order_field_id)
                .filtered(
                    lambda field: not field.ignore_on_code_generator_writer
                )
            )
        else:
            # Use kanban view sequence, or generic sequence
            lst_field_sorted = model_created_fields.filtered(
                lambda field: not field.ignore_on_code_generator_writer
            ).sorted(lambda field: field.code_generator_kanban_view_sequence)

        # lst_field = [E.field({"name": a.name}) for a in model_created_fields]
        lst_field = []
        lst_field_template = []
        lst_field_currency_id = [
            a
            for a in lst_field_sorted
            if a.ttype == "many2one" and a.relation == "res.currency"
        ]
        field_currency_id = (
            lst_field_currency_id[0] if lst_field_currency_id else None
        )
        for field_id in lst_field_sorted:
            if field_id.name in lst_field_to_remove:
                continue
            # TODO validate code_generator_kanban_view_sequence is supported
            # if a.code_generator_kanban_view_sequence >= 0
            if (
                field_id.ttype == "many2one"
                and field_id.relation == "res.currency"
            ):
                field_view = E.field({"name": field_id.name, "invisible": "1"})
                lst_field.append(field_view)

            elif field_id.ttype == "boolean":
                lst_field.append(E.field({"name": field_id.name}))
                # TODO detect type success/danger or another type of boolean
                dct_templates_value = E.li(
                    {
                        "class": "text-success float-right mb4",
                        "t-if": f"record.{field_id.name}.raw_value",
                    },
                    E.i(
                        {
                            "aria-label": "Ok",
                            "class": "fa fa-circle",
                            "role": "img",
                            "title": "Ok",
                        }
                    ),
                )
                lst_field_template.append(dct_templates_value)

                dct_templates_value = E.li(
                    {
                        "class": "text-danger float-right mb4",
                        "t-if": f"!record.{field_id.name}.raw_value",
                    },
                    E.i(
                        {
                            "aria-label": "Invalid",
                            "class": "fa fa-circle",
                            "role": "img",
                            "title": "Invalid",
                        }
                    ),
                )
                lst_field_template.append(dct_templates_value)
            else:
                lst_field.append(E.field({"name": field_id.name}))
                dct_value = {"name": field_id.name}
                if field_id.ttype == "monetary":
                    if field_currency_id:
                        dct_value["option"] = (
                            f"{{'currency_field': '{field_currency_id.name}'}}"
                        )
                    dct_value["widget"] = "monetary"
                if field_id.force_widget:
                    dct_value["widget"] = field_id.force_widget
                dct_value = dict(
                    sorted(dct_value.items(), key=lambda kv: kv[0])
                )

                dct_templates_value = E.li(
                    {"class": "mb4"},
                    E.strong(E.field(dct_value)),
                )
                lst_field_template.append(dct_templates_value)

        template_item = E.templates(
            {},
            E.t(
                {"t-name": "card"},
                E.div(
                    {"t-attf-class": "oe_kanban_global_click"},
                    E.div(
                        {"class": "oe_kanban_details"},
                        E.ul({}, *lst_field_template),
                    ),
                ),
            ),
        )
        lst_item_kanban = lst_field + [template_item]
        arch_xml = E.kanban(
            {
                "class": "o_kanban_mobile",
            },
            *lst_item_kanban,
        )
        str_arch = ET.tostring(arch_xml, pretty_print=True)
        str_arch = b'<?xml version="1.0"?>\n' + str_arch
        # ir_ui_view_value = {
        #     "name": f"{model_name_str}_kanban",
        #     "type": "kanban",
        #     "model": model_name,
        #     "arch": str_arch,
        #     "m2o_model": model_created.id,
        # }
        # dct_value_to_create["ir.ui.view"].append(ir_ui_view_value)
        view_value = self.env["ir.ui.view"].search(
            [
                # ("name", "=", f"{model_name_str}_kanban"),
                ("type", "=", "kanban"),
                ("model", "=", model_name),
                # ("arch", "=", str_arch),
                # ("m2o_model", "=", model_created.id),
            ]
        )
        if not view_value:
            view_value = self.env["ir.ui.view"].create(
                [
                    {
                        "name": f"{model_name_str}_kanban",
                        "type": "kanban",
                        "model": model_name,
                        "arch": str_arch,
                        "m2o_model": model_created.id,
                    }
                ]
            )
        else:
            _logger.warning(
                f"View '{model_name_str}_kanban' of model '{model_name}'"
                " already exist."
            )

        return view_value

    def _generate_search_views_models(
        self, model_created, model_created_fields, module, dct_value_to_create
    ):
        model_name = model_created.model
        # Ignore for config.res
        if model_name in ["res.config.settings"]:
            return
        model_name_str = model_name.replace(".", "_")
        model_name_display_str = model_name_str.replace("_", " ").capitalize()

        lst_field_to_remove = ("active",)

        has_sequence = False
        for field_id in model_created_fields:
            if field_id.code_generator_search_view_sequence >= 0:
                has_sequence = True
                break

        if not has_sequence:
            lst_order_field_id = [[], [], []]
            # code_generator_search_view_sequence all -1, default value
            # Move rec_name in beginning
            # Move one2many at the end
            for field_id in model_created_fields:
                if field_id.name == model_created.rec_name:
                    # TODO write this value
                    lst_order_field_id[0].append(field_id.id)
                    # field_id.code_generator_search_view_sequence = 0
                elif field_id.ttype == "one2many":
                    lst_order_field_id[2].append(field_id.id)
                    # field_id.code_generator_search_view_sequence = 2
                else:
                    lst_order_field_id[1].append(field_id.id)
                    # field_id.code_generator_search_view_sequence = 1
            new_lst_order_field_id = (
                lst_order_field_id[0]
                + lst_order_field_id[1]
                + lst_order_field_id[2]
            )
            # TODO this can slow, can we accumulate this data for the end?
            # field_sorted_sequence_0 = self.env["ir.model.fields"].browse(
            #     lst_order_field_id[0]
            # )
            # field_sorted_sequence_1 = self.env["ir.model.fields"].browse(
            #     lst_order_field_id[1]
            # )
            # field_sorted_sequence_2 = self.env["ir.model.fields"].browse(
            #     lst_order_field_id[2]
            # )
            # field_sorted_sequence_0.write(
            #     {"code_generator_form_simple_view_sequence": 0}
            # )
            # field_sorted_sequence_1.write(
            #     {"code_generator_form_simple_view_sequence": 1}
            # )
            # field_sorted_sequence_2.write(
            #     {"code_generator_form_simple_view_sequence": 2}
            # )
            # field_sorted_ids = (
            #     field_sorted_sequence_0
            #     + field_sorted_sequence_1
            #     + field_sorted_sequence_2
            # )
            lst_field_sorted = (
                self.env["ir.model.fields"]
                .browse(new_lst_order_field_id)
                .filtered(
                    lambda field: not field.ignore_on_code_generator_writer
                )
            )
        else:
            # Use search view sequence, or generic sequence
            lst_field_sorted = model_created_fields.filtered(
                lambda field: not field.ignore_on_code_generator_writer
            ).sorted(lambda field: field.code_generator_search_view_sequence)

        lst_field = []
        lst_field_filter = []
        lst_field_searchpanel_field = []
        lst_field_group_field = []
        for field_id in lst_field_sorted:
            if field_id.name in lst_field_to_remove:
                # Add inactive
                dct_templates_value = E.filter(
                    {
                        "domain": f"[('{field_id.name}','=',False)]",
                        "name": "Inactive",
                        "string": f"Inactive {model_name_display_str}",
                    }
                )
                lst_field_filter.append(dct_templates_value)
                continue
            if field_id.ttype in [
                "char",
                "text",
                "many2one",
                "many2many",
                "one2many",
                "html",
                "selection",
            ]:
                if field_id.relation not in ["res.currency"]:
                    field_xml = E.field(
                        {
                            "name": field_id.name,
                            "string": field_id.field_description,
                        }
                    )
                    lst_field.append(field_xml)

            # TODO validate code_generator_search_view_sequence is supported
            # if a.code_generator_search_view_sequence >= 0
            # TODO support many2one/one2many/many2many sur res.partner or res.user
            # <filter name="filter_my_projects"
            #                         string="Mes projets"
            #                         domain="[('project_manager_id', '=', uid)]"/>
            #
            #                 <filter name="filter_my_team"
            #                         string="Projets de mon équipe"
            #                         context="{'search_default_member_ids': [uid]}"/>

            # Detect stage
            # <filter name="filter_draft"
            #                         string="Brouillons"
            #                         domain="[('state', '=', 'draft')]"/>
            #
            #                 <filter name="filter_in_progress"
            #                         string="En cours"
            #                         domain="[('state', '=', 'in_progress')]"/>
            #
            #                 <filter name="filter_done"
            #                         string="Terminés"
            #                         domain="[('state', '=', 'done')]"/>

            # Support selection
            # <filter name="filter_high_priority"
            #                         string="Haute priorité"
            #                         domain="[('priority', '=', '3')]"/>

            # Support date
            # <filter name="filter_this_month"
            #                         string="Ce mois-ci"
            #                         domain="[
            #                             ('start_date', '&gt;=', (context_today() - datetime.timedelta(days=context_today().day-1)).strftime('%%Y-%%m-%%d')),
            #                             ('start_date', '&lt;', (context_today() + datetime.timedelta(days=32-context_today().day)).strftime('%%Y-%%m-%%d'))
            #                         ]"
            #                         help="Projets démarrés ce mois-ci."/>

            # Filter late
            # <filter name="filter_late"
            #                         string="En retard"
            #                         help="Projets avec date de fin dépassée et non terminés."
            #                         domain="[('end_date', '&lt;', context_today()), ('state', 'not in', ('done', 'cancel'))]"/>

            if field_id.ttype == "boolean":
                dct_templates_value = E.filter(
                    {
                        "domain": f"[('{field_id.name}','=',True)]",
                        "name": field_id.name,
                        "string": field_id.field_description,
                    }
                )
                lst_field_filter.append(dct_templates_value)

            field_id_name_no_id = (
                field_id.name[:-3]
                if field_id.name.endswith("_id")
                else field_id.name
            )

            if field_id.ttype in ["date", "datetime"]:
                filter_value = E.filter(
                    {
                        "name": f"group_by_date_{field_id_name_no_id}",
                        "string": f"{field_id.field_description}",
                        "context": f"{{'group_by': '{field_id.name}'}}",
                    }
                )
                lst_field_filter.append(filter_value)

            if field_id.ttype == "many2one":
                if field_id.relation not in ["res.currency"]:
                    search_panel_xml = E.field(
                        {
                            "name": field_id.name,
                            "string": field_id.field_description,
                            "icon": "fa-th-list",
                        }
                    )
                    lst_field_searchpanel_field.append(search_panel_xml)

                    group_field_xml = E.filter(
                        {
                            "string": field_id.field_description,
                            "name": f"groupby_{field_id_name_no_id}",
                            "context": f"{{'group_by':'{field_id.name}'}}",
                        }
                    )
                    lst_field_group_field.append(group_field_xml)

            if field_id.ttype in ["many2many", "one2many"]:
                search_panel_xml = E.field(
                    {
                        "name": field_id.name,
                        "string": field_id.field_description,
                        "icon": "fa-th-list",
                        "domain": "[]",
                        "enable_counters": "1",
                        "select": "multi",
                    }
                )
                lst_field_searchpanel_field.append(search_panel_xml)

            # dct_templates_value = E.filter(
            #     {
            #         "domain": f"[('{field_id.name}','!=',False)]",
            #         "name": field_id.name,
            #         "string": field_id.field_description,
            #     }
            # )
            # lst_field_filter.append(dct_templates_value)

        if lst_field_group_field:
            lst_field_group = [
                E.group(
                    {"expand": "1", "string": "Group by"},
                    *lst_field_group_field,
                )
            ]
        else:
            lst_field_group = []

        if lst_field_searchpanel_field:
            lst_field_searchpanel = [
                E.searchpanel({}, *lst_field_searchpanel_field)
            ]
        else:
            lst_field_searchpanel = []

        lst_item_search = []
        lst_item_search += lst_field
        lst_item_search += lst_field_filter
        lst_item_search += lst_field_group
        lst_item_search += lst_field_searchpanel
        arch_xml = E.search(
            {
                "string": model_name_display_str,
            },
            *lst_item_search,
        )
        str_arch = ET.tostring(arch_xml, pretty_print=True)
        str_arch = b'<?xml version="1.0"?>\n' + str_arch
        # ir_ui_view_value = {
        #     "name": f"{model_name_str}_search",
        #     "type": "search",
        #     "model": model_name,
        #     "arch": str_arch,
        #     "m2o_model": model_created.id,
        # }
        # dct_value_to_create["ir.ui.view"].append(ir_ui_view_value)
        view_value = self.env["ir.ui.view"].search(
            [
                # ("name", "=", f"{model_name_str}_search"),
                ("type", "=", "search"),
                ("model", "=", model_name),
                # ("arch", "=", str_arch),
                # ("m2o_model", "=", model_created.id),
            ]
        )
        if not view_value:
            view_value = self.env["ir.ui.view"].create(
                [
                    {
                        "name": f"{model_name_str}_search",
                        "type": "search",
                        "model": model_name,
                        "arch": str_arch,
                        "m2o_model": model_created.id,
                    }
                ]
            )
        else:
            _logger.warning(
                f"View '{model_name_str}_search' of model '{model_name}'"
                " already exist."
            )

        return view_value

    def _generate_pivot_views_models(
        self, model_created, model_created_fields, module, dct_value_to_create
    ):
        model_name = model_created.model
        model_name_str = model_name.replace(".", "_")
        model_name_display_str = model_name_str.replace("_", " ").capitalize()

        lst_field_to_remove = ("active",)

        has_sequence = False
        for field_id in model_created_fields:
            if field_id.code_generator_pivot_view_sequence >= 0:
                has_sequence = True
                break

        if not has_sequence:
            lst_order_field_id = [[], [], []]
            # code_generator_pivot_view_sequence all -1, default value
            # Move rec_name in beginning
            # Move one2many at the end
            for field_id in model_created_fields:
                if field_id.name == model_created.rec_name:
                    # TODO write this value
                    lst_order_field_id[0].append(field_id.id)
                    # field_id.code_generator_pivot_view_sequence = 0
                elif field_id.ttype == "one2many":
                    lst_order_field_id[2].append(field_id.id)
                    # field_id.code_generator_pivot_view_sequence = 2
                else:
                    lst_order_field_id[1].append(field_id.id)
                    # field_id.code_generator_pivot_view_sequence = 1
            new_lst_order_field_id = (
                lst_order_field_id[0]
                + lst_order_field_id[1]
                + lst_order_field_id[2]
            )
            # TODO this can slow, can we accumulate this data for the end?
            # field_sorted_sequence_0 = self.env["ir.model.fields"].browse(
            #     lst_order_field_id[0]
            # )
            # field_sorted_sequence_1 = self.env["ir.model.fields"].browse(
            #     lst_order_field_id[1]
            # )
            # field_sorted_sequence_2 = self.env["ir.model.fields"].browse(
            #     lst_order_field_id[2]
            # )
            # field_sorted_sequence_0.write(
            #     {"code_generator_form_simple_view_sequence": 0}
            # )
            # field_sorted_sequence_1.write(
            #     {"code_generator_form_simple_view_sequence": 1}
            # )
            # field_sorted_sequence_2.write(
            #     {"code_generator_form_simple_view_sequence": 2}
            # )
            # field_sorted_ids = (
            #     field_sorted_sequence_0
            #     + field_sorted_sequence_1
            #     + field_sorted_sequence_2
            # )
            lst_field_sorted = (
                self.env["ir.model.fields"]
                .browse(new_lst_order_field_id)
                .filtered(
                    lambda field: not field.ignore_on_code_generator_writer
                    and field.ttype not in ("many2many", "one2many", "binary")
                )
            )
        else:
            # Use pivot view sequence, or generic sequence
            lst_field_sorted = model_created_fields.filtered(
                lambda field: not field.ignore_on_code_generator_writer
                and field.ttype not in ("many2many", "one2many", "binary")
            ).sorted(lambda field: field.code_generator_pivot_view_sequence)

        # lst_field = [E.field({"name": a.name}) for a in model_created_fields]
        lst_field = []
        for field_id in lst_field_sorted:
            if field_id.name in lst_field_to_remove:
                continue
            # TODO validate code_generator_pivot_view_sequence is supported
            # if a.code_generator_pivot_view_sequence >= 0

            # TODO detect field_type col, when it's a date?
            if model_created.rec_name == field_id.name:
                field_type = "row"
            elif field_id.ttype in ("integer", "float"):
                field_type = "measure"
            else:
                field_type = "row"

            dct_templates_value = E.field(
                {
                    "name": field_id.name,
                    "type": field_type,
                }
            )
            lst_field.append(dct_templates_value)

        lst_item_pivot = lst_field
        arch_xml = E.pivot(
            {
                "string": model_name_display_str,
            },
            *lst_item_pivot,
        )
        str_arch = ET.tostring(arch_xml, pretty_print=True)
        str_arch = b'<?xml version="1.0"?>\n' + str_arch
        # ir_ui_view_value = {
        #     "name": f"{model_name_str}_pivot",
        #     "type": "pivot",
        #     "model": model_name,
        #     "arch": str_arch,
        #     "m2o_model": model_created.id,
        # }
        # dct_value_to_create["ir.ui.view"].append(ir_ui_view_value)
        view_value = self.env["ir.ui.view"].search(
            [
                # ("name", "=", f"{model_name_str}_pivot"),
                ("type", "=", "pivot"),
                ("model", "=", model_name),
                # ("arch", "=", str_arch),
                # ("m2o_model", "=", model_created.id),
            ]
        )
        if not view_value:
            view_value = self.env["ir.ui.view"].create(
                [
                    {
                        "name": f"{model_name_str}_pivot",
                        "type": "pivot",
                        "model": model_name,
                        "arch": str_arch,
                        "m2o_model": model_created.id,
                    }
                ]
            )
        else:
            _logger.warning(
                f"View '{model_name_str}_pivot' of model '{model_name}'"
                " already exist."
            )

        return view_value

    def _generate_calendar_views_models(
        self, model_created, model_created_fields, module, dct_value_to_create
    ):
        model_name = model_created.model
        model_name_str = model_name.replace(".", "_")
        model_name_display_str = model_name_str.replace("_", " ").capitalize()

        lst_field_to_remove = ("active",)

        has_sequence = False
        for field_id in model_created_fields:
            if field_id.code_generator_calendar_view_sequence >= 0:
                has_sequence = True
                break

        if not has_sequence:
            lst_order_field_id = [[], [], []]
            # code_generator_calendar_view_sequence all -1, default value
            # Move rec_name in beginning
            # Move one2many at the end
            for field_id in model_created_fields:
                if field_id.name == model_created.rec_name:
                    # TODO write this value
                    lst_order_field_id[0].append(field_id.id)
                    # field_id.code_generator_calendar_view_sequence = 0
                elif field_id.ttype == "one2many":
                    lst_order_field_id[2].append(field_id.id)
                    # field_id.code_generator_calendar_view_sequence = 2
                else:
                    lst_order_field_id[1].append(field_id.id)
                    # field_id.code_generator_calendar_view_sequence = 1
            new_lst_order_field_id = (
                lst_order_field_id[0]
                + lst_order_field_id[1]
                + lst_order_field_id[2]
            )
            # TODO this can slow, can we accumulate this data for the end?
            # field_sorted_sequence_0 = self.env["ir.model.fields"].browse(
            #     lst_order_field_id[0]
            # )
            # field_sorted_sequence_1 = self.env["ir.model.fields"].browse(
            #     lst_order_field_id[1]
            # )
            # field_sorted_sequence_2 = self.env["ir.model.fields"].browse(
            #     lst_order_field_id[2]
            # )
            # field_sorted_sequence_0.write(
            #     {"code_generator_form_simple_view_sequence": 0}
            # )
            # field_sorted_sequence_1.write(
            #     {"code_generator_form_simple_view_sequence": 1}
            # )
            # field_sorted_sequence_2.write(
            #     {"code_generator_form_simple_view_sequence": 2}
            # )
            # field_sorted_ids = (
            #     field_sorted_sequence_0
            #     + field_sorted_sequence_1
            #     + field_sorted_sequence_2
            # )
            lst_field_sorted = (
                self.env["ir.model.fields"]
                .browse(new_lst_order_field_id)
                .filtered(
                    lambda field: not field.ignore_on_code_generator_writer
                )
            )
        else:
            # Use calendar view sequence, or generic sequence
            lst_field_sorted = model_created_fields.filtered(
                lambda field: not field.ignore_on_code_generator_writer
            ).sorted(lambda field: field.code_generator_calendar_view_sequence)

        # lst_field = [E.field({"name": a.name}) for a in model_created_fields]
        lst_field = []
        date_start = None
        for field_id in lst_field_sorted:
            if field_id.name in lst_field_to_remove:
                continue
            # TODO validate code_generator_calendar_view_sequence is supported
            # if a.code_generator_calendar_view_sequence >= 0

            dct_value = {"name": field_id.name}
            if field_id.force_widget:
                dct_value["widget"] = field_id.force_widget

            if field_id.is_date_start_view:
                if date_start:
                    _logger.warning(
                        f"Double date_start in model {model_name}."
                    )
                date_start = field_id

            dct_templates_value = E.field(dct_value)
            lst_field.append(dct_templates_value)

        if not date_start:
            _logger.error(
                f"Missing date_start in view calendar for model {model_name}."
            )
            return

        lst_item_calendar = lst_field
        arch_xml = E.calendar(
            {
                "color": model_created.rec_name,
                "date_start": date_start.name,
                "string": model_name_display_str,
            },
            *lst_item_calendar,
        )
        str_arch = ET.tostring(arch_xml, pretty_print=True)
        str_arch = b'<?xml version="1.0"?>\n' + str_arch
        # ir_ui_view_value = {
        #     "name": f"{model_name_str}_calendar",
        #     "type": "calendar",
        #     "model": model_name,
        #     "arch": str_arch,
        #     "m2o_model": model_created.id,
        # }
        # dct_value_to_create["ir.ui.view"].append(ir_ui_view_value)
        view_value = self.env["ir.ui.view"].search(
            [
                # ("name", "=", f"{model_name_str}_calendar"),
                ("type", "=", "calendar"),
                ("model", "=", model_name),
                # ("arch", "=", str_arch),
                # ("m2o_model", "=", model_created.id),
            ]
        )
        if not view_value:
            view_value = self.env["ir.ui.view"].create(
                [
                    {
                        "name": f"{model_name_str}_calendar",
                        "type": "calendar",
                        "model": model_name,
                        "arch": str_arch,
                        "m2o_model": model_created.id,
                    }
                ]
            )
        else:
            _logger.warning(
                f"View '{model_name_str}_calendar' of model '{model_name}'"
                " already exist."
            )

        return view_value

    def _generate_graph_views_models(
        self, model_created, model_created_fields, module, dct_value_to_create
    ):
        model_name = model_created.model
        model_name_str = model_name.replace(".", "_")
        model_name_display_str = model_name_str.replace("_", " ").capitalize()

        lst_field_to_remove = ("active",)

        has_sequence = False
        for field_id in model_created_fields:
            if field_id.code_generator_graph_view_sequence >= 0:
                has_sequence = True
                break

        if not has_sequence:
            lst_order_field_id = [[], [], []]
            # code_generator_graph_view_sequence all -1, default value
            # Move rec_name in beginning
            # Move one2many at the end
            for field_id in model_created_fields:
                if field_id.name == model_created.rec_name:
                    # TODO write this value
                    lst_order_field_id[0].append(field_id.id)
                    # field_id.code_generator_graph_view_sequence = 0
                elif field_id.ttype == "one2many":
                    lst_order_field_id[2].append(field_id.id)
                    # field_id.code_generator_graph_view_sequence = 2
                else:
                    lst_order_field_id[1].append(field_id.id)
                    # field_id.code_generator_graph_view_sequence = 1
            new_lst_order_field_id = (
                lst_order_field_id[0]
                + lst_order_field_id[1]
                + lst_order_field_id[2]
            )
            # TODO this can slow, can we accumulate this data for the end?
            # field_sorted_sequence_0 = self.env["ir.model.fields"].browse(
            #     lst_order_field_id[0]
            # )
            # field_sorted_sequence_1 = self.env["ir.model.fields"].browse(
            #     lst_order_field_id[1]
            # )
            # field_sorted_sequence_2 = self.env["ir.model.fields"].browse(
            #     lst_order_field_id[2]
            # )
            # field_sorted_sequence_0.write(
            #     {"code_generator_form_simple_view_sequence": 0}
            # )
            # field_sorted_sequence_1.write(
            #     {"code_generator_form_simple_view_sequence": 1}
            # )
            # field_sorted_sequence_2.write(
            #     {"code_generator_form_simple_view_sequence": 2}
            # )
            # field_sorted_ids = (
            #     field_sorted_sequence_0
            #     + field_sorted_sequence_1
            #     + field_sorted_sequence_2
            # )
            lst_field_sorted = (
                self.env["ir.model.fields"]
                .browse(new_lst_order_field_id)
                .filtered(
                    lambda field: not field.ignore_on_code_generator_writer
                    and field.ttype not in ("many2many", "one2many")
                )
            )
        else:
            # Use graph view sequence, or generic sequence
            lst_field_sorted = model_created_fields.filtered(
                lambda field: not field.ignore_on_code_generator_writer
                and field.ttype not in ("many2many", "one2many")
            ).sorted(lambda field: field.code_generator_graph_view_sequence)

        # lst_field = [E.field({"name": a.name}) for a in model_created_fields]
        lst_field = []
        for field_id in lst_field_sorted:
            if field_id.name in lst_field_to_remove:
                continue
            # TODO validate code_generator_graph_view_sequence is supported
            # if a.code_generator_graph_view_sequence >= 0

            # TODO detect field_type col, when it's a date?
            if model_created.rec_name == field_id.name:
                field_type = "row"
            elif field_id.ttype in ("integer", "float"):
                field_type = "measure"
            else:
                field_type = "row"

            dct_templates_value = E.field(
                {
                    "name": field_id.name,
                    "type": field_type,
                }
            )
            lst_field.append(dct_templates_value)

        lst_item_graph = lst_field
        arch_xml = E.graph(
            {
                "string": model_name_display_str,
            },
            *lst_item_graph,
        )
        str_arch = ET.tostring(arch_xml, pretty_print=True)
        str_arch = b'<?xml version="1.0"?>\n' + str_arch
        # ir_ui_view_value = {
        #     "name": f"{model_name_str}_graph",
        #     "type": "graph",
        #     "model": model_name,
        #     "arch": str_arch,
        #     "m2o_model": model_created.id,
        # }
        # dct_value_to_create["ir.ui.view"].append(ir_ui_view_value)
        view_value = self.env["ir.ui.view"].search(
            [
                # ("name", "=", f"{model_name_str}_graph"),
                ("type", "=", "graph"),
                ("model", "=", model_name),
                # ("arch", "=", str_arch),
                # ("m2o_model", "=", model_created.id),
            ]
        )
        if not view_value:
            view_value = self.env["ir.ui.view"].create(
                [
                    {
                        "name": f"{model_name_str}_graph",
                        "type": "graph",
                        "model": model_name,
                        "arch": str_arch,
                        "m2o_model": model_created.id,
                    }
                ]
            )
        else:
            _logger.warning(
                f"View '{model_name_str}_graph' of model '{model_name}'"
                " already exist."
            )

        return view_value

    def _generate_timeline_views_models(
        self, model_created, model_created_fields, module, dct_value_to_create
    ):
        model_name = model_created.model
        model_name_str = model_name.replace(".", "_")
        model_name_display_str = model_name_str.replace("_", " ").capitalize()

        start_date = None
        end_date = None
        for field_id in model_created_fields:
            if field_id.is_date_start_view and not start_date:
                start_date = field_id
            if field_id.is_date_end_view and not end_date:
                end_date = field_id

        if not start_date:
            _logger.warning(
                "Missing start date field, need word start in name."
            )
        if not end_date:
            _logger.warning("Missing end date field, need word start in name.")
        if not start_date or not end_date:
            return

        # lst_item_timeline = lst_field
        arch_xml = E.timeline(
            {
                "date_start": start_date.name,
                "date_stop": end_date.name,
                "default_group_by": model_created.rec_name,
                "event_open_popup": "True",
                "string": model_name_display_str,
            }
        )
        str_arch = ET.tostring(arch_xml, pretty_print=True)
        str_arch = b'<?xml version="1.0"?>\n' + str_arch
        # ir_ui_view_value = {
        #     "name": f"{model_name_str}_timeline",
        #     "type": "timeline",
        #     "model": model_name,
        #     "arch": str_arch,
        #     "m2o_model": model_created.id,
        # }
        # dct_value_to_create["ir.ui.view"].append(ir_ui_view_value)
        view_value = self.env["ir.ui.view"].search(
            [
                # ("name", "=", f"{model_name_str}_timeline"),
                ("type", "=", "timeline"),
                ("model", "=", model_name),
                # ("arch", "=", str_arch),
                # ("m2o_model", "=", model_created.id),
            ]
        )
        if not view_value:
            view_value = self.env["ir.ui.view"].create(
                [
                    {
                        "name": f"{model_name_str}_timeline",
                        "type": "timeline",
                        "model": model_name,
                        "arch": str_arch,
                        "m2o_model": model_created.id,
                    }
                ]
            )
        else:
            _logger.warning(
                f"View '{model_name_str}_timeline' of model '{model_name}'"
                " already exist."
            )

        return view_value

    def _generate_diagram_views_models(
        self, model_created, module, dct_value_to_create
    ):
        model_name = model_created.model
        model_name_str = model_name.replace(".", "_")
        model_name_display_str = model_name_str.replace("_", " ").capitalize()

        if (
            not model_created.diagram_node_object
            or not model_created.diagram_node_xpos_field
            or not model_created.diagram_node_ypos_field
            or not model_created.diagram_arrow_object
            or not model_created.diagram_arrow_src_field
            or not model_created.diagram_arrow_dst_field
        ):
            _logger.error(
                "Cannot create diagram view, missing field in model, check"
                " diagram_*"
            )
            return

        model_node = module.env["ir.model"].search(
            [("model", "=", model_created.diagram_node_object)], limit=1
        )
        if not model_node:
            _logger.error(
                f"Diagram model {model_created.diagram_node_object} doesn't"
                " exist."
            )
            return
        model_arrow = module.env["ir.model"].search(
            [("model", "=", model_created.diagram_arrow_object)], limit=1
        )
        if not model_arrow:
            _logger.error(
                f"Diagram model {model_created.diagram_arrow_object} doesn't"
                " exist."
            )
            return

        lst_field_node = [E.field({"name": model_node.rec_name})]
        lst_field_arrow = [
            E.field({"name": model_created.diagram_arrow_src_field}),
            E.field({"name": model_created.diagram_arrow_dst_field}),
            E.field({"name": model_arrow.rec_name}),
        ]

        # Take first
        node_form_view = module.env["ir.ui.view"].search(
            [
                ("model", "=", model_created.diagram_node_object),
                ("type", "=", "form"),
            ],
            limit=1,
        )
        node_xml_id = module.env["ir.model.data"].search(
            [("model", "=", "ir.ui.view"), ("res_id", "=", node_form_view.id)]
        )
        arrow_form_view = module.env["ir.ui.view"].search(
            [
                ("model", "=", model_created.diagram_arrow_object),
                ("type", "=", "form"),
            ],
            limit=1,
        )
        arrow_xml_id = module.env["ir.model.data"].search(
            [("model", "=", "ir.ui.view"), ("res_id", "=", arrow_form_view.id)]
        )

        arch_xml = E.diagram(
            {},
            E.node(
                {
                    # "bgcolor":"",
                    "form_view_ref": node_xml_id.name,
                    "object": model_created.diagram_node_object,
                    "shape": "rectangle:True",
                    "xpos": model_created.diagram_node_xpos_field,
                    "ypos": model_created.diagram_node_ypos_field,
                },
                *lst_field_node,
            ),
            E.arrow(
                {
                    "destination": model_created.diagram_arrow_dst_field,
                    "form_view_ref": arrow_xml_id.name,
                    "label": f"['{model_arrow.rec_name}']",
                    "object": model_created.diagram_arrow_object,
                    "source": model_created.diagram_arrow_src_field,
                },
                *lst_field_arrow,
            ),
            E.label(
                {
                    "for": "",
                    "string": (
                        "Caution, all modification is live. Diagram model:"
                        f" {model_created.model}, node model:"
                        f" {model_created.diagram_node_object} and arrow"
                        f" model: {model_created.diagram_arrow_object}"
                    ),
                }
            ),
        )

        str_arch = ET.tostring(arch_xml, pretty_print=True)
        str_arch = b'<?xml version="1.0"?>\n' + str_arch
        # dct_value_to_create["ir.ui.view"].append(ir_ui_view_value)
        view_value = self.env["ir.ui.view"].search(
            [
                # ("name", "=", f"{model_name_str}_diagram"),
                ("type", "=", "diagram"),
                ("model", "=", model_name),
                # ("arch", "=", str_arch),
                # ("m2o_model", "=", model_created.id),
            ]
        )
        if not view_value:
            view_value = self.env["ir.ui.view"].create(
                [
                    {
                        "name": f"{model_name_str}_diagram",
                        "type": "diagram",
                        "model": model_name,
                        "arch": str_arch,
                        "m2o_model": model_created.id,
                    }
                ]
            )
        else:
            _logger.warning(
                f"View '{model_name_str}_diagram' of model '{model_name}'"
                " already exist."
            )

        return view_value
