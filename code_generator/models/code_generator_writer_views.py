#!/usr/bin/env python3
# © 2021-2025 TechnoLibre (http://www.technolibre.ca)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

import logging
import os
import uuid

from lxml import etree as ET
from lxml.builder import E
from PIL import Image

from odoo import models

from .. import code_generator_data
from .code_generator_writer_constants import (
    BLANK_LINE,
    BREAK_LINE_OFF,
    MAGIC_FIELDS,
    XML_HEAD,
    XML_ODOO_CLOSING_TAG,
    XML_VERSION_HEADER,
    XML_VERSION_STR,
)

_logger = logging.getLogger(__name__)


class CodeGeneratorWriterViewsMixin(models.AbstractModel):
    _name = "code.generator.writer.views.mixin"
    _description = "Code Generator Writer Views Mixin"

    def _get_id_view_model_data(self, record, model=None, is_internal=False):
        """
        Function to obtain the model data from a record
        :param record:
        :param is_internal: if False, add module name for external reference
        :return:
        """

        # special trick for some record
        xml_id = getattr(record, "xml_id")
        if xml_id:
            if is_internal:
                return xml_id.split(".")[1]
            return xml_id

        if model:
            record_model = model
        else:
            record_model = record.model

        ir_model_data = self.env["ir.model.data"].search(
            [
                ("model", "=", record_model),
                ("res_id", "=", record.id),
            ]
        )
        if not ir_model_data:
            return

        if is_internal:
            return ir_model_data[0].name
        return f"{ir_model_data[0].module}.{ir_model_data[0].name}"

    def _get_ir_model_data(
        self,
        record,
        give_a_default=False,
        module_name="",
        force_field_name=None,
    ):
        """
        Function to obtain the model data from a record
        :param record:
        :param give_a_default:
        :param module_name:
        :return:
        """

        ir_model_data = self.env["ir.model.data"].search(
            [
                # TODO: Opción por valorar
                # ('module', '!=', '__export__'),
                ("model", "=", record._name),
                ("res_id", "=", record.id),
            ]
        )

        if ir_model_data:
            if module_name and module_name == ir_model_data[0].module:
                result = ir_model_data[0].name
            else:
                result = f"{ir_model_data[0].module}.{ir_model_data[0].name}"
        elif give_a_default:
            if force_field_name:
                name_v = getattr(record, force_field_name)
                second = self._lower_replace(name_v)
            elif record._rec_name:
                rec_name_v = getattr(record, record._rec_name)
                if not rec_name_v:
                    rec_name_v = uuid.uuid1().int
                second = self._lower_replace(rec_name_v)
            else:
                second = uuid.uuid1().int
            result = self._set_limit_4xmlid(
                f"{self._get_model_model(record._name)}_{second}"
            )
            # Check if name already exist
            model_data_exist = self.env["ir.model.data"].search(
                [("name", "=", result)]
            )
            new_result = result
            i = 0
            while model_data_exist:
                i += 1
                new_result = f"{result}_{i}"
                model_data_exist = self.env["ir.model.data"].search(
                    [("name", "=", new_result)]
                )

            self.env["ir.model.data"].create(
                [
                    {
                        "name": new_result,
                        "model": record._name,
                        "module": module_name,
                        "res_id": record.id,
                        "noupdate": True,  # If it's False, target record (res_id) will be removed while module update
                    }
                ]
            )
            result = new_result
        else:
            result = False

        # Need to limit to 128 char, else can crash like when loading i18n po and id is too long
        if type(result) is str:
            # Remove strange char
            # TODO find another way to remove not alpha numeric char, but accept '_'
            result = (
                result.replace(",", "")
                .replace("'", "")
                .replace('"', "")
                .replace("(", "")
                .replace(")", "")
            )
            # TODO maybe check duplicate
            return result[:120]
        return result

    def _get_group_data_name(self, group):
        """
        Function to obtain the res_id-like group name (Code Generator / Manager -> code_generator_manager)
        :param group:
        :return:
        """

        return (
            self._get_ir_model_data(group)
            if self._get_ir_model_data(group)
            else self._lower_replace(group.name.replace(" /", ""))
        )

    def _get_model_data_name(self, model, module_name=""):
        """
        Function to obtain the res_id-like model name (code.generator.module -> code_generator_module)
        :param model:
        :return:
        """

        return (
            self._get_ir_model_data(model, module_name=module_name)
            if self._get_ir_model_data(model, module_name=module_name)
            else "model_%s" % self._get_model_model(model.model)
        )

    def _get_view_data_name(self, view):
        """
        Function to obtain the res_id-like view name
        :param view:
        :return:
        """

        return (
            self._get_ir_model_data(view)
            if self._get_ir_model_data(view)
            else "%s_%sview" % (self._get_model_model(view.model), view.type)
        )

    def _get_action_data_name(
        self, action, server=False, creating=False, module=None
    ):
        """
        Function to obtain the res_id-like action name
        :param action:
        :param server:
        :param creating:
        :return:
        """

        if not creating and self._get_ir_model_data(
            action, module_name=module.name
        ):
            action_name = self._get_ir_model_data(
                action, module_name=module.name
            )
            if not module or "." not in action_name:
                return action_name
            lst_action = action_name.split(".")
            if module.name == lst_action[0]:
                # remove internal name
                return lst_action[1]
            # link is external
            return action_name

        else:
            model = (
                getattr(action, "res_model")
                if not server
                else getattr(action, "model_id").model
            )
            model_model = self._get_model_model(model)
            action_type = "action_window" if not server else "server_action"

            new_action_name = action.name
            # TODO No need to support limit of 64, why this code?
            # new_action_name = self._set_limit_4xmlid(
            #     "%s" % action.name[: 64 - len(model_model) - len(action_type)]
            # )

            result_name = f"{model_model}_{self._lower_replace(new_action_name)}_{action_type}"

            # if new_action_name != action.name:
            #     _logger.warning(
            #         f"Slice action name {action.name} to"
            #         f" {new_action_name} because length is upper than 63."
            #         f" Result: {result_name}."
            #     )

            return result_name

    def _get_action_act_url_name(self, action):
        """
        Function to obtain the res_id-like action name
        :param action:
        :return:
        """
        return f"action_{self._lower_replace(action.name)}"

    def _get_menu_data_name(
        self, menu, ignore_module=False, ignore_module_name=None, module=None
    ):
        """
        Function to obtain the res_id-like menu name
        :param menu:
        :return:
        """

        menu_name = self._get_ir_model_data(menu, module_name=module.name)
        if menu_name:
            if "." in menu_name:
                module_name, menu_name_short = menu_name.split(".")
                if ignore_module or (
                    ignore_module_name and ignore_module_name == module_name
                ):
                    return menu_name_short
            return menu_name
        return self._lower_replace(menu.name)

    def _set_module_menus(self, module):
        """
        Function to set the module menus file
        :param module:
        :return:
        """

        cg_data = code_generator_data.get_code_generator_data(self.env)

        application_icon = None
        menus = module.with_context({"ir.ui.menu.full_list": True}).o2m_menus
        if not menus:
            return ""

        # Group by parent_id
        lst_menu_root = menus.filtered(lambda x: not x.parent_id).sorted(
            key=lambda x: self._get_menu_data_name(x, module=module).split(
                "."
            )[-1]
        )
        lst_menu_item = menus.filtered(lambda x: x.parent_id and x.child_id)
        lst_menu_last_child = menus.filtered(lambda x: not x.child_id).sorted(
            key=lambda x: self._get_menu_data_name(x, module=module).split(
                "."
            )[-1]
        )
        nb_root = len(lst_menu_root)
        nb_item = len(lst_menu_item)
        nb_last_child = len(lst_menu_last_child)
        has_add_root = False
        has_item = False
        has_last_child = False

        # Order by id_name
        lst_menu = [a for a in lst_menu_root]

        # Be sure parent is added
        lst_menu_item = [a for a in lst_menu_item]

        while lst_menu_item:
            lst_menu_to_order = []
            len_start = len(lst_menu_item)
            for menu_item in lst_menu_item[:]:
                # Remove item and add it
                if menu_item.parent_id in lst_menu:
                    lst_menu_item.remove(menu_item)
                    lst_menu_to_order.append(menu_item)

            if lst_menu_to_order:
                lst_menu_ordered = sorted(
                    lst_menu_to_order,
                    key=lambda x: self._get_menu_data_name(
                        x, module=module
                    ).split(".")[-1],
                )
                for menu_ordered in lst_menu_ordered:
                    lst_menu.append(menu_ordered)

            len_end = len(lst_menu_item)
            if len_start == len_end:
                # Find no parent
                for menu_item in lst_menu_item:
                    lst_menu.append(menu_item)

        # Order by id_name
        for menu_child in lst_menu_last_child:
            lst_menu.append(menu_child)

        lst_menu_xml = []

        for i, menu in enumerate(lst_menu):

            menu_id = self._get_menu_data_name(
                menu, ignore_module=True, module=module
            )
            dct_menu_item = {"id": menu_id}
            if menu.name != menu_id:
                dct_menu_item["name"] = menu.name

            if not menu.ignore_act_window:
                try:
                    menu.action
                except Exception as e:
                    # missing action on menu
                    _logger.error(
                        f"Missing action window on menu {menu.name}."
                    )
                    continue

                if menu.action:
                    dct_menu_item["action"] = self._get_action_data_name(
                        menu.action, module=module
                    )

            if not menu.active:
                dct_menu_item["active"] = "False"

            if len(lst_menu) == 1 and menu.sequence != 10 or len(lst_menu) > 1:
                dct_menu_item["sequence"] = str(menu.sequence)

            if menu.parent_id:
                dct_menu_item["parent"] = self._get_menu_data_name(
                    menu.parent_id,
                    ignore_module_name=module.name,
                    module=module,
                )

            if menu.groups_id:
                dct_menu_item["groups"] = self._get_m2m_groups(menu.groups_id)

            if menu.web_icon:
                # TODO move application_icon in code_generator_data
                application_icon = menu.web_icon
                # ignore actual icon, force a new icon
                new_icon = f"{module.name},static/description/icon.png"
                dct_menu_item["web_icon"] = new_icon
                if new_icon != menu.web_icon:
                    _logger.warning(
                        f"Difference between menu icon '{menu.web_icon}' and"
                        f" new icon '{new_icon}'"
                    )

            if not has_add_root and nb_root:
                has_add_root = True
                lst_menu_xml.append(ET.Comment("end line"))
                lst_menu_xml.append(ET.Comment("Root menu"))

            if not has_item and nb_item and i >= nb_root:
                has_item = True
                lst_menu_xml.append(ET.Comment("end line"))
                lst_menu_xml.append(ET.Comment("Sub menu"))

            if not has_last_child and nb_last_child and i >= nb_root + nb_item:
                has_last_child = True
                lst_menu_xml.append(ET.Comment("end line"))
                lst_menu_xml.append(ET.Comment("Child menu"))

            menu_xml = E.menuitem(dct_menu_item)
            lst_menu_xml.append(ET.Comment("end line"))
            lst_menu_xml.append(menu_xml)

        lst_menu_xml.append(ET.Comment("end line"))
        module_menus_file = E.odoo({}, *lst_menu_xml)
        menu_file_path = os.path.join(cg_data.views_path, "menu.xml")
        result = XML_VERSION_HEADER.encode("utf-8") + ET.tostring(
            module_menus_file, pretty_print=True
        )

        new_result = result.decode().replace("  <!--end line-->\n", "\n")[:-1]

        cg_data.write_file_str(menu_file_path, new_result, data_file=True)

        return application_icon

    def _set_model_xmlview_file(self, module, model, model_model):
        """
        Function to set the model xml files
        :param module:
        :param model:
        :param model_model:
        :return:
        """

        cg_data = code_generator_data.get_code_generator_data(self.env)

        # view_ids = model.view_ids
        # TODO model.view_ids not working when add inherit view from wizard... what is different? Force values
        view_ids = self.env["ir.ui.view"].search([("model", "=", model.model)])
        act_window_ids = (
            self.env["ir.actions.act_window"]
            .search([("res_model", "=", model.model)])
            .with_context(lang=None)
        )
        server_action_ids = model.o2m_server_action.with_context(lang=None)

        # Remove all field when in inherit if not in whitelist
        is_whitelist = any([a.is_show_whitelist_write_view for a in view_ids])
        view_filtered_ids = view_ids.filtered(
            lambda field: field.name not in MAGIC_FIELDS
            and not field.is_hide_blacklist_write_view
            and (
                not is_whitelist
                or (is_whitelist and field.is_show_whitelist_write_view)
            )
        )

        if not (view_filtered_ids or act_window_ids or server_action_ids):
            return

        dct_replace = {}
        dct_replace_template = {}
        lst_id = []
        lst_item_xml = []
        lst_item_template = []

        #
        # Views
        #
        for view in view_filtered_ids:

            view_type = view.type

            lst_view_type = list(
                dict(
                    self.env["code.generator.view"]
                    ._fields["view_type"]
                    .selection
                ).keys()
            )
            if view_type in lst_view_type:

                str_id_system = self._get_id_view_model_data(
                    view, model="ir.ui.view", is_internal=True
                )
                if not str_id_system:
                    str_id = f"{model_model}_view_{view_type}"
                else:
                    str_id = str_id_system
                if str_id in lst_id:
                    count_id = lst_id.count(str_id)
                    str_id += str(count_id)
                lst_id.append(str_id)

                cg_data.add_view_id(view.name, str_id)

                lst_field = []

                if view.name:
                    lst_field.append(E.field({"name": "name"}, view.name))

                lst_field.append(E.field({"name": "model"}, view.model))

                if view.key:
                    lst_field.append(E.field({"name": "key"}, view.key))

                if view.priority != 16:
                    lst_field.append(
                        E.field({"name": "priority"}, str(view.priority))
                    )

                if view.inherit_id:
                    lst_field.append(
                        E.field(
                            {
                                "name": "inherit_id",
                                "ref": self._get_view_data_name(
                                    view.inherit_id
                                ),
                            }
                        )
                    )

                    if view.mode == "primary":
                        lst_field.append(E.field({"name": "mode"}, "primary"))

                if not view.active:
                    lst_field.append(
                        E.field({"name": "active", "eval": "False"})
                    )

                if view.arch_base:
                    uid = str(uuid.uuid1())
                    str_arch_base = (
                        view.arch_base
                        if not view.arch_base.startswith(XML_VERSION_STR)
                        else view.arch_base[len(XML_VERSION_STR) :]
                    )
                    if str_arch_base.startswith(XML_VERSION_STR):
                        str_arch_base = str_arch_base[len(XML_VERSION_STR) :]
                    # TODO retransform xml to format correctly
                    # TODO check where put data
                    str_data_begin = "<data>\n"
                    str_data_end = "</data>\n"
                    if str_arch_base.startswith(
                        str_data_begin
                    ) and str_arch_base.endswith(str_data_end):
                        str_arch_base = str_arch_base[
                            len(str_data_begin) : -len(str_data_end)
                        ]
                    dct_replace[uid] = self._setup_xml_indent(
                        str_arch_base, indent=3
                    )
                    lst_field.append(
                        E.field({"name": "arch", "type": "xml"}, uid)
                    )

                if view.groups_id:
                    lst_field.append(
                        self._get_m2m_groups_etree(view.groups_id)
                    )

                info = E.record(
                    {"id": str_id, "model": "ir.ui.view"}, *lst_field
                )
                lst_item_xml.append(ET.Comment("end line"))
                lst_item_xml.append(info)

            elif view_type == "qweb":
                template_value = {"id": view.key, "name": view.name}
                if view.inherit_id:
                    template_value["inherit_id"] = view.inherit_id.key

                uid = str(uuid.uuid1())
                dct_replace_template[uid] = self._setup_xml_indent(
                    view.arch, indent=2, is_end=True
                )
                info = E.template(template_value, uid)
                # lst_item_xml.append(ET.Comment("end line"))
                # lst_item_xml.append(info)
                lst_item_template.append(ET.Comment("end line"))
                lst_item_template.append(info)

            else:
                _logger.error(
                    f"View type {view_type} of {view.name} not supported."
                )

        #
        # Action Windows
        #
        for act_window in act_window_ids:
            # Use descriptive method when contain this attributes, not supported in simplify view

            record_id = self._get_id_view_model_data(
                act_window, model="ir.actions.act_window", is_internal=True
            )
            if not record_id:
                record_id = self._get_action_data_name(
                    act_window, creating=True
                )

            cg_act_window_id = (
                self.env["code.generator.act_window"]
                .search([("id_name", "=", record_id)], limit=1)
                .exists()
            )

            # has_menu = bool(
            #     module.with_context({"ir.ui.menu.full_list": True}).o2m_menus
            # )
            view_mode = (
                cg_act_window_id.view_mode
                if cg_act_window_id and cg_act_window_id.view_mode
                else act_window.view_mode
            )
            lst_field = []

            if act_window.name:
                lst_field.append(E.field({"name": "name"}, act_window.name))

            if act_window.res_model or act_window.m2o_res_model:
                lst_field.append(
                    E.field(
                        {"name": "res_model"},
                        act_window.res_model or act_window.m2o_res_model.model,
                    )
                )

            if act_window.binding_model_id:
                binding_model = self._get_model_data_name(
                    act_window.binding_model_id, module_name=module.name
                )
                lst_field.append(
                    E.field({"name": "binding_model_id", "ref": binding_model})
                )

            if act_window.view_id:
                lst_field.append(
                    E.field(
                        {
                            "name": "view_id",
                            "ref": self._get_view_data_name(
                                act_window.view_id
                            ),
                        }
                    )
                )

            if act_window.domain != "[]" and act_window.domain:
                lst_field.append(
                    E.field({"name": "domain"}, act_window.domain)
                )

            if act_window.context != "{}":
                lst_field.append(
                    E.field({"name": "context"}, act_window.context)
                )

            # src_model = (
            #     act_window.binding_model_id.model
            #     if act_window.binding_model_id
            #     else False
            # )
            # if src_model:
            #     lst_field.append(
            #         E.field(
            #             {"name": "src_model"},
            #             act_window.src_model or act_window.m2o_src_model.model,
            #         )
            #     )

            if act_window.target != "current":
                lst_field.append(
                    E.field({"name": "target"}, act_window.target)
                )

            if view_mode != "list,form" and view_mode != "form,list":
                lst_field.append(E.field({"name": "view_mode"}, view_mode))

            if act_window.usage:
                lst_field.append(E.field({"name": "usage", "eval": "True"}))

            if act_window.limit != 80 and act_window.limit != 0:
                lst_field.append(
                    E.field({"name": "limit"}, str(act_window.limit))
                )

            if act_window.search_view_id:
                lst_field.append(
                    E.field(
                        {
                            "name": "search_view_id",
                            "ref": self._get_view_data_name(
                                act_window.search_view_id
                            ),
                        }
                    )
                )

            if act_window.filter:
                lst_field.append(E.field({"name": "filter", "eval": "True"}))

            if act_window.help:
                lst_field.append(
                    E.field({"name": "name", "type": "html"}, act_window.help)
                )

            if act_window.groups_id:
                lst_field.append(
                    self._get_m2m_groups_etree(act_window.groups_id)
                )

            info = E.record(
                {"id": record_id, "model": "ir.actions.act_window"},
                *lst_field,
            )
            lst_item_xml.append(ET.Comment("end line"))
            lst_item_xml.append(info)

        #
        # Server Actions
        #
        for server_action in server_action_ids:

            lst_field = [
                E.field({"name": "name"}, server_action.name),
                E.field(
                    {
                        "name": "model_id",
                        "ref": self._get_model_data_name(
                            server_action.model_id, module_name=module.name
                        ),
                    }
                ),
                E.field(
                    {
                        "name": "binding_model_id",
                        "ref": self._get_model_data_name(
                            model, module_name=module.name
                        ),
                    }
                ),
            ]

            if server_action.state == "code":
                lst_field.append(E.field({"name": "state"}, "code"))

                lst_field.append(E.field({"name": "code"}, server_action.code))

            else:
                lst_field.append(E.field({"name": "state"}, "multi"))

                if server_action.child_ids:
                    child_obj = ", ".join(
                        server_action.child_ids.mapped(
                            lambda child: "ref(%s)"
                            % self._get_action_data_name(child, server=True)
                        )
                    )
                    lst_field.append(
                        E.field(
                            {
                                "name": "child_ids",
                                "eval": f"[(6,0, [{child_obj}])]",
                            }
                        )
                    )

            record_id = self._get_id_view_model_data(
                server_action, model="ir.actions.server", is_internal=True
            )
            if not record_id:
                record_id = self._get_action_data_name(
                    server_action, server=True, creating=True
                )
            info = E.record(
                {"id": record_id, "model": "ir.actions.server"}, *lst_field
            )
            lst_item_xml.append(ET.Comment("end line"))

            if server_action.comment:
                lst_item_xml.append(
                    ET.Comment(text=f" {server_action.comment} ")
                )

            lst_item_xml.append(info)

        lst_item_xml.append(ET.Comment("end line"))
        root = E.odoo({}, *lst_item_xml)

        content = XML_VERSION_HEADER.encode("utf-8") + ET.tostring(
            root, pretty_print=True
        )
        str_content = content.decode()

        str_content = str_content.replace("  <!--end line-->\n", "\n")
        for key, value in dct_replace.items():
            str_content = str_content.replace(key, value)
        str_content = self._change_xml_2_to_4_spaces(str_content)[:-1]
        # Patch, because xml domain is better with <>
        str_content = str_content.replace("'&gt;'", "'>'")
        str_content = str_content.replace("'&lt;'", "'<'")

        wizards_path = cg_data.wizards_path
        views_path = cg_data.views_path
        xml_file_path = os.path.join(
            wizards_path if model.transient else views_path,
            f"{model_model}.xml",
        )
        cg_data.write_file_str(xml_file_path, str_content, data_file=True)

        if dct_replace_template:
            root_template = E.odoo({}, *lst_item_template)
            content_template = XML_VERSION_HEADER.encode(
                "utf-8"
            ) + ET.tostring(root_template, pretty_print=True)
            str_content_template = content_template.decode()

            str_content_template = str_content_template.replace(
                "  <!--end line-->\n", "\n"
            )
            for key, value in dct_replace_template.items():
                str_content_template = str_content_template.replace(key, value)
            str_content_template = self._change_xml_2_to_4_spaces(
                str_content_template
            )[:-1]

            views_path = cg_data.views_path
            xml_file_path = os.path.join(
                views_path,
                f"{module.name}_templates.xml",
            )
            cg_data.write_file_str(
                xml_file_path, str_content_template, data_file=True
            )

    def _set_model_xmlreport_file(self, module, model, model_model):
        """

        :param module:
        :param model:
        :param model_model:
        :return:
        """

        cg_data = code_generator_data.get_code_generator_data(self.env)

        if not model.o2m_reports:
            return

        l_model_report_file = XML_HEAD + BLANK_LINE

        for report in model.o2m_reports.with_context(lang=None):

            if report.m2o_template and report.m2o_template.arch_base:
                l_model_report_file.append(
                    '<template id="%s">' % report.report_name
                )

                str_arch_base = (
                    report.m2o_template.arch_base
                    if not report.m2o_template.arch_base.startswith(
                        XML_VERSION_STR
                    )
                    else report.m2o_template.arch_base[
                        len(XML_VERSION_STR) :
                    ]
                )
                l_model_report_file.append(
                    '<field name="arch" type="xml">'
                    f"{str_arch_base}</field>"
                )

                l_model_report_file.append("</template>\n")
            else:
                _logger.warning(
                    "Report '%s' has no QWeb template linked,"
                    " generating report action only.",
                    report.report_name,
                )

            l_model_report_file.append(
                '<record model="ir.actions.report" id="%s_actionreport">'
                % report.report_name
            )

            l_model_report_file.append(
                '<field name="model">%s</field>' % report.model
            )

            l_model_report_file.append(
                '<field name="name">%s</field>' % report.report_name
            )

            l_model_report_file.append(
                '<field name="file">%s</field>' % report.report_name
            )

            l_model_report_file.append(
                '<field name="string">%s</field>' % report.name
            )

            l_model_report_file.append(
                '<field name="report_type">%s</field>' % report.report_type
            )

            if report.print_report_name:
                l_model_report_file.append(
                    '<field name="print_report_name">%s</field>'
                    % report.print_report_name
                )

            if report.multi:
                l_model_report_file.append(
                    '<field name="multi">%s</field>' % report.multi
                )

            if report.attachment_use:
                l_model_report_file.append(
                    '<field name="attachment_use">%s</field>'
                    % report.attachment_use
                )

            if report.attachment:
                l_model_report_file.append(
                    '<field name="attachment">%s</field>' % report.attachment
                )

            if report.binding_model_id:
                l_model_report_file.append(
                    '<field name="binding_model_id" ref="%s" />'
                    % self._get_model_data_name(
                        report.binding_model_id, module_name=module.name
                    )
                )

            if report.groups_id:
                l_model_report_file.append(
                    self._get_m2m_groups(report.groups_id)
                )

            if report.paperformat_id:
                l_model_report_file.append(
                    '<field name="paperformat_id"'
                    ' ref="%s" />'
                    % self._get_id_view_model_data(
                        report.paperformat_id
                    )
                )

            l_model_report_file.append("</record>")

            l_model_report_file += XML_ODOO_CLOSING_TAG

        xmlreport_file_path = os.path.join(
            cg_data.reports_path, f"{model_model}.xml"
        )
        cg_data.write_file_lst_content(
            xmlreport_file_path, l_model_report_file, data_file=True
        )
