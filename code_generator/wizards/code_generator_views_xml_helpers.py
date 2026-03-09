#!/usr/bin/env python3
# © 2021-2025 TechnoLibre (http://www.technolibre.ca)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)
import logging
import uuid
from collections import defaultdict

import unidecode
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


class CodeGeneratorViewsXmlHelpersMixin(models.AbstractModel):
    _name = "code.generator.views.xml.helpers.mixin"
    _description = "Code Generator Views XML Helpers Mixin"

    def _generate_xml_button(self, item, model_id, lst_child_update=None):
        button_attributes = {
            "name": item.action_name,
        }
        if item.label:
            button_attributes["string"] = item.label
        # TODO can have others type
        button_attributes["type"] = "object"
        if item.button_type:
            button_attributes["class"] = item.button_type
        if item.binding_type:
            button_attributes["type"] = item.binding_type
        if item.icon:
            button_attributes["icon"] = item.icon
        if item.domain:
            button_attributes["domain"] = item.domain
        if item.tabindex:
            button_attributes["tabindex"] = item.tabindex
        if item.context:
            button_attributes["context"] = item.context
        if item.attrs:
            button_attributes["attrs"] = item.attrs
        if item.groups:
            button_attributes["groups"] = item.groups

        # Create method
        items = self.env["code.generator.model.code"].search(
            [
                ("name", "=", item.action_name),
                ("m2o_model", "=", model_id),
                ("m2o_module", "=", self.code_generator_id.id),
            ]
        )
        # TODO get this list from module base
        lst_ignore_code = ["toggle_active"]
        if (
            not items
            and item.action_name not in lst_ignore_code
            and item.binding_type == "object"
            and not item.action_name.isdigit()
        ):
            value = {
                "code": '''"""TODO what to run"""
pass''',
                "name": item.action_name,
                "param": "self",
                "m2o_module": self.code_generator_id.id,
                "m2o_model": model_id,
                "is_wip": True,
            }
            self.env["code.generator.model.code"].create([value])
        button_attributes = self._order_attributes_item(button_attributes)
        if lst_child_update:
            return E.button(button_attributes, *lst_child_update)

        return E.button(button_attributes)

    @staticmethod
    def _generate_xml_html_help(item, lst_child, dct_replace):
        """

        :param item:
        :param lst_child: list of item to add more in some context
        :param dct_replace: need it to replace html in xml without validation
        :return:
        """
        dct_item = {"string": "Help"}
        if item.colspan > 1:
            dct_item["colspan"] = str(item.colspan)
        dct_item = dict(sorted(dct_item.items(), key=lambda kv: kv[0]))
        item_xml = E.separator(dct_item)
        lst_child.append(item_xml)

        uid = str(uuid.uuid1())
        dct_replace[uid] = item.label
        item_xml = E.div({}, uid)
        return item_xml

    def _generate_xml_object(self, item, model_id, lst_child=None):
        lst_child_update = [] if not lst_child else lst_child
        item_xml = None
        dct_item = {}
        # TODO duplicate code here with function _generate_xml_title_field
        if not item.item_type == "html":
            if item.name:
                dct_item["name"] = item.name
            elif item.action_name:
                # TODO this is maybe the bug where name is a number
                dct_item["name"] = item.action_name

            if item.t_name:
                dct_item["t-name"] = item.t_name
            if item.t_attf_class:
                dct_item["t-attf-class"] = item.t_attf_class
            if item.t_if:
                dct_item["t-if"] = item.t_if
            if item.title:
                dct_item["title"] = item.title
            if item.aria_label:
                dct_item["aria-label"] = item.aria_label
            if item.role:
                dct_item["role"] = item.role
            if item.type:
                dct_item["type"] = item.type
            if item.widget:
                dct_item["widget"] = item.widget
            if item.label:
                dct_item["string"] = item.label
            if item.domain:
                dct_item["domain"] = item.domain
            if item.context:
                dct_item["context"] = item.context
            if item.class_attr:
                dct_item["class"] = item.class_attr
            if item.invisible:
                dct_item["invisible"] = item.invisible
            if item.groups:
                dct_item["groups"] = item.groups
            if item.options:
                dct_item["options"] = item.options
            if item.filter_domain:
                dct_item["filter_domain"] = item.filter_domain
            if item.nolabel:
                dct_item["nolabel"] = item.nolabel
            if item.clickable:
                dct_item["clickable"] = item.clickable
            if item.help:
                dct_item["help"] = item.help
            if item.attrs:
                dct_item["attrs"] = item.attrs
            if item.expand:
                # TODO change 1 to True and 0 to False
                dct_item["expand"] = item.expand

        if item.item_type == "field":
            if item.placeholder:
                dct_item["placeholder"] = item.placeholder
            if item.password:
                dct_item["password"] = "True"
            dct_item = self._order_attributes_item(dct_item)
            item_xml = E.field(dct_item)
        elif item.item_type == "filter":
            dct_item = self._order_attributes_item(dct_item)
            item_xml = E.filter(dct_item)
        elif item.item_type == "button":
            return self._generate_xml_button(
                item, model_id, lst_child_update=lst_child_update
            )
        elif item.item_type == "html":
            lst_html_child = []
            if item.background_type:
                old_class = dct_item.get("class")
                if old_class and old_class != item.background_type:
                    _logger.error(
                        "Duplicate class, old class: {old_class},"
                        " background_type {item.background_type}"
                    )
                dct_item["class"] = item.background_type
                if item.background_type.startswith("bg-warning"):
                    lst_html_child.append(E.h3({}, "Warning:"))
                elif item.background_type.startswith("bg-success"):
                    lst_html_child.append(E.h3({}, "Success:"))
                elif item.background_type.startswith("bg-info"):
                    lst_html_child.append(E.h3({}, "Info:"))
                elif item.background_type.startswith("bg-danger"):
                    lst_html_child.append(E.h3({}, "Danger:"))
            lst_html_child.append(item.label)
            dct_item = self._order_attributes_item(dct_item)
            item_xml = E.div(dct_item, *lst_html_child)
        elif item.item_type == "group":
            if item.label:
                dct_item["string"] = item.label
            if item.attrs:
                dct_item["attrs"] = item.attrs
            dct_item = self._order_attributes_item(dct_item)
            item_xml = E.group(dct_item, *lst_child_update)
        elif item.item_type == "li":
            dct_item = self._order_attributes_item(dct_item)
            item_xml = E.li(dct_item, *lst_child_update)
        elif item.item_type == "ul":
            dct_item = self._order_attributes_item(dct_item)
            item_xml = E.ul(dct_item, *lst_child_update)
        elif item.item_type == "i":
            dct_item = self._order_attributes_item(dct_item)
            item_xml = E.i(dct_item, *lst_child_update)
        elif item.item_type == "t":
            dct_item = self._order_attributes_item(dct_item)
            item_xml = E.t(dct_item, *lst_child_update)
        elif item.item_type == "strong":
            dct_item = self._order_attributes_item(dct_item)
            item_xml = E.strong(dct_item, *lst_child_update)
        elif item.item_type == "xpath":
            if not item.expr:
                _logger.error(
                    f"Missing expr for item action_name {item.action_name}"
                )
            elif not item.position:
                _logger.error(
                    f"Missing position for item action_name {item.action_name}"
                )
            else:
                dct_item["expr"] = item.expr
                dct_item["position"] = item.position
                dct_item = self._order_attributes_item(dct_item)
                item_xml = E.xpath(dct_item, *lst_child_update)
        elif item.item_type == "div":
            if item.attrs:
                dct_item["attrs"] = item.attrs
            dct_item = self._order_attributes_item(dct_item)
            item_xml = E.div(dct_item, *lst_child_update)
        elif item.item_type == "p":
            if item.attrs:
                dct_item["attrs"] = item.attrs
            dct_item = self._order_attributes_item(dct_item)
            item_xml = E.p(dct_item, *lst_child_update)
        elif item.item_type == "h1":
            if item.attrs:
                dct_item["attrs"] = item.attrs
            dct_item = self._order_attributes_item(dct_item)
            item_xml = E.h1(dct_item, *lst_child_update)
        elif item.item_type == "h2":
            if item.attrs:
                dct_item["attrs"] = item.attrs
            dct_item = self._order_attributes_item(dct_item)
            item_xml = E.h2(dct_item, *lst_child_update)
        elif item.item_type == "h3":
            if item.attrs:
                dct_item["attrs"] = item.attrs
            dct_item = self._order_attributes_item(dct_item)
            item_xml = E.h3(dct_item, *lst_child_update)
        elif item.item_type == "h4":
            if item.attrs:
                dct_item["attrs"] = item.attrs
            dct_item = self._order_attributes_item(dct_item)
            item_xml = E.h4(dct_item, *lst_child_update)
        elif item.item_type == "h5":
            if item.attrs:
                dct_item["attrs"] = item.attrs
            dct_item = self._order_attributes_item(dct_item)
            item_xml = E.h5(dct_item, *lst_child_update)
        elif item.item_type == "page":
            if item.attrs:
                dct_item["attrs"] = item.attrs
            dct_item = self._order_attributes_item(dct_item)
            item_xml = E.page(dct_item, *lst_child_update)
        elif item.item_type == "notebook":
            if item.attrs:
                dct_item["attrs"] = item.attrs
            dct_item = self._order_attributes_item(dct_item)
            item_xml = E.notebook(dct_item, *lst_child_update)
        elif item.item_type == "templates":
            if item.attrs:
                dct_item["attrs"] = item.attrs
            dct_item = self._order_attributes_item(dct_item)
            item_xml = E.templates(dct_item, *lst_child_update)
        elif item.item_type == "#text":
            item_xml = item.inner_text
        else:
            _logger.warning(f"View item '{item.item_type}' is not supported.")
        return item_xml

    def _order_attributes_item(self, dct_item):
        # Force sequence. name/string/type/class ... in order ... context/attrs
        dct_item_copy = dct_item.copy()
        dct_item_begin = {}
        dct_item_end = {}
        lst_key_begin = ["name", "string", "type", "class", "widget"]
        lst_key_end = ["options", "context", "groups", "attrs", "help"]
        for key in lst_key_begin:
            if key in dct_item_copy.keys():
                dct_item_begin[key] = dct_item_copy[key]
                del dct_item_copy[key]
        for key in lst_key_end:
            if key in dct_item_copy.keys():
                dct_item_end[key] = dct_item_copy[key]
                del dct_item_copy[key]
        dct_item_middle = dict(
            sorted(dct_item_copy.items(), key=lambda kv: kv[0])
        )
        dct_item_result = dct_item_begin
        dct_item_result.update(dct_item_middle)
        dct_item_result.update(dct_item_end)
        return dct_item_result

    def _generate_xml_group_div(self, item, lst_xml, dct_replace, model_id):
        """

        :param item:
        :param lst_xml: list of item to add more in some context
        :param dct_replace: need it to replace html in xml without validation
        :return:
        """
        lst_child = sorted(item.child_id, key=lambda a: a.sequence)
        lst_item_child = []
        if lst_child:
            for item_child_id in lst_child:
                item_child = self._generate_xml_group_div(
                    item_child_id, lst_xml, dct_replace, model_id
                )
                if item_child is not None:
                    lst_item_child.append(item_child)
                else:
                    _logger.warning(
                        "Missing item xml group div about view item"
                        f" '{item_child_id.item_type}'"
                    )
            item_xml = self._generate_xml_object(
                item, model_id, lst_child=lst_item_child
            )
        else:
            item_xml = self._generate_xml_object(item, model_id)

        if item_xml is None:
            _logger.error(f"Cannot generate view for item {item.action_name}")

        return item_xml

    @staticmethod
    def _generate_xml_title_field(item, lst_child, level=0):
        """

        :param item: type odoo.api.code.generator.view.item
        :param lst_child: list of item to add more in some context
        :param level: 0 is bigger level (H1), >=4 is H5
        :return:
        """
        if item.edit_only or item.has_label:
            dct_item_label = {"for": item.action_name}
            if item.edit_only:
                dct_item_label["class"] = "oe_edit_only"
            item_label = E.label(dct_item_label)
            lst_child.append(item_label)
        dct_item_field = {}
        if item.name:
            dct_item_field["name"] = item.name
        else:
            dct_item_field["name"] = item.action_name

        if item.type:
            dct_item_field["type"] = item.type

        if item.is_required:
            dct_item_field["required"] = "1"
        if item.is_readonly:
            dct_item_field["readonly"] = "1"
        dct_item_field = dict(
            sorted(dct_item_field.items(), key=lambda kv: kv[0])
        )
        item_field = E.field(dct_item_field)
        if level == 0:
            result = E.h1({}, item_field)
        elif level == 1:
            result = E.h2({}, item_field)
        elif level == 2:
            result = E.h3({}, item_field)
        elif level == 3:
            result = E.h4({}, item_field)
        else:
            result = E.h5({}, item_field)
        return result

    def _generate_specific_form_views_models(
        self, code_generator_view_id, dct_value_to_create
    ):
        view_type = code_generator_view_id.view_type
        model_name = code_generator_view_id.m2o_model.model
        model_id = code_generator_view_id.m2o_model.id
        dct_replace = {}
        lst_item_header = []
        lst_item_footer = []
        lst_item_body = []
        lst_item_title = []
        for view_item in code_generator_view_id.view_item_ids:
            if view_item.section_type == "body":
                lst_item_body.append(view_item)
            elif view_item.section_type == "header":
                lst_item_header.append(view_item)
            elif view_item.section_type == "footer":
                lst_item_footer.append(view_item)
            elif view_item.section_type == "title":
                lst_item_title.append(view_item)
            else:
                _logger.warning(
                    f"View item section '{view_item.section_type}' is not"
                    " supported."
                )

        lst_item_form = []
        lst_item_form_sheet = []

        if lst_item_header:
            lst_item_header = sorted(lst_item_header, key=lambda a: a.sequence)
            lst_child = []
            for item_header in lst_item_header:
                if item_header.item_type in ("field", "button"):
                    item = self._generate_xml_object(item_header, model_id)
                else:
                    _logger.warning(
                        f"Item header type '{item_header.item_type}' is not"
                        " supported."
                    )
                    continue
                if item is not None:
                    lst_child.append(item)
            if lst_child:
                header_xml = E.header({}, *lst_child)
                lst_item_form.append(header_xml)

        if lst_item_title:
            lst_item_title = sorted(lst_item_title, key=lambda a: a.sequence)
            lst_child = []
            i = 0
            for item_title in lst_item_title:
                if item_title.item_type == "field":
                    item = self._generate_xml_title_field(
                        item_title, lst_child, level=i
                    )
                elif item_title.item_type == "button":
                    _logger.warning(
                        f"Button is not supported in title section."
                    )
                    continue
                else:
                    _logger.warning(
                        f"Item title type '{item_title.item_type}' is not"
                        " supported."
                    )
                    continue
                i += 1
                lst_child.append(item)
            title_xml = E.div({"class": "oe_title"}, *lst_child)
            lst_item_form_sheet.append(title_xml)

        if lst_item_body:
            lst_item_root_body = [a for a in lst_item_body if not a.parent_id]
            lst_item_root_body = sorted(
                lst_item_root_body, key=lambda a: a.sequence
            )
            for item_body in lst_item_root_body:
                if item_body.is_help:
                    item_xml = self._generate_xml_html_help(
                        item_body, lst_item_form_sheet, dct_replace
                    )
                    lst_item_form_sheet.append(item_xml)
                elif item_body.item_type in ("button", "html"):
                    if not item_body.child_id:
                        # Nothing inside
                        item_xml = self._generate_xml_object(
                            item_body, model_id
                        )
                    else:
                        # Something inside
                        item_xml = self._generate_xml_group_div(
                            item_body,
                            lst_item_form_sheet,
                            dct_replace,
                            model_id,
                        )
                    if item_xml is not None:
                        lst_item_form_sheet.append(item_xml)
                elif item_body.item_type in (
                    "div",
                    "group",
                    "templates",
                    "h1",
                    "h2",
                    "h3",
                    "h4",
                    "h5",
                    "notebook",
                    "page",
                ):
                    if not item_body.child_id:
                        _logger.warning(
                            f"Item type '{item_body.item_type}' missing child."
                        )
                        continue
                    item_xml = self._generate_xml_group_div(
                        item_body, lst_item_form_sheet, dct_replace, model_id
                    )
                    if item_xml is not None:
                        lst_item_form_sheet.append(item_xml)
                elif item_body.item_type in ("xpath",):
                    # TODO maybe move this in lst_item_xpath with view_item.section_type == 'xpath'
                    if not item_body.child_id:
                        _logger.warning(f"Item type xpath missing child.")
                        continue
                    item_xml = self._generate_xml_group_div(
                        item_body, lst_item_form_sheet, dct_replace, model_id
                    )
                    if item_xml is not None:
                        lst_item_form_sheet.append(item_xml)
                elif item_body.item_type in ("field", "filter"):
                    item_xml = self._generate_xml_object(item_body, model_id)
                    if item_xml is not None:
                        lst_item_form_sheet.append(item_xml)
                else:
                    _logger.warning(f"Unknown type xml {item_body.item_type}")

        if lst_item_footer:
            lst_item_footer = sorted(lst_item_footer, key=lambda a: a.sequence)
            lst_child = []
            for item_footer in lst_item_footer:
                if item_footer.item_type == "field":
                    item = E.field()
                    # TODO field in footer
                elif item_footer.item_type == "button":
                    item = self._generate_xml_button(item_footer, model_id)
                else:
                    _logger.warning(
                        f"Item footer type '{item_footer.item_type}' is not"
                        " supported."
                    )
                    continue
                if item:
                    lst_child.append(item)
            footer_xml = E.footer({}, *lst_child)
            lst_item_form.append(footer_xml)

        if lst_item_form_sheet:
            if code_generator_view_id.has_body_sheet:
                sheet_xml = E.sheet({}, *lst_item_form_sheet)
                lst_item_form.append(sheet_xml)
            else:
                lst_item_form += lst_item_form_sheet

        if (
            code_generator_view_id.m2o_model.enable_activity
            and view_type == "form"
        ):
            # TODO duplicate
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

        dct_attr_view = {}
        if code_generator_view_id.view_attr_string:
            dct_attr_view["string"] = code_generator_view_id.view_attr_string

        if code_generator_view_id.view_attr_class:
            dct_attr_view["class"] = code_generator_view_id.view_attr_class

        if code_generator_view_id.view_attr_decoration_danger:
            dct_attr_view["decoration-danger"] = (
                code_generator_view_id.view_attr_decoration_danger
            )

        if code_generator_view_id.view_attr_decoration_success:
            dct_attr_view["decoration-success"] = (
                code_generator_view_id.view_attr_decoration_success
            )

        if code_generator_view_id.view_attr_decoration_primary:
            dct_attr_view["decoration-primary"] = (
                code_generator_view_id.view_attr_decoration_primary
            )

        if code_generator_view_id.view_attr_decoration_bf:
            dct_attr_view["decoration-bf"] = (
                code_generator_view_id.view_attr_decoration_bf
            )

        if code_generator_view_id.view_attr_decoration_it:
            dct_attr_view["decoration-it"] = (
                code_generator_view_id.view_attr_decoration_it
            )

        if code_generator_view_id.view_attr_decoration_info:
            dct_attr_view["decoration-info"] = (
                code_generator_view_id.view_attr_decoration_info
            )

        if code_generator_view_id.view_attr_decoration_warning:
            dct_attr_view["decoration-warning"] = (
                code_generator_view_id.view_attr_decoration_warning
            )

        if code_generator_view_id.view_attr_decoration_muted:
            dct_attr_view["decoration-muted"] = (
                code_generator_view_id.view_attr_decoration_muted
            )

        dct_attr_view = dict(
            sorted(dct_attr_view.items(), key=lambda kv: kv[0])
        )
        if code_generator_view_id.inherit_view_name:
            if len(lst_item_form) > 1:

                form_xml = E.data(dct_attr_view, *lst_item_form)
            else:
                form_xml = lst_item_form[0] if len(lst_item_form) else None
        elif view_type == "form":
            form_xml = E.form(dct_attr_view, *lst_item_form)
        elif view_type == "search":
            form_xml = E.search(dct_attr_view, *lst_item_form)
        elif view_type == "list":
            form_xml = E.list(dct_attr_view, *lst_item_form)
        elif view_type == "kanban":
            form_xml = E.kanban(dct_attr_view, *lst_item_form)
        elif view_type == "graph":
            form_xml = E.graph(dct_attr_view, *lst_item_form)
        elif view_type == "pivot":
            form_xml = E.pivot(dct_attr_view, *lst_item_form)
        else:
            _logger.warning(
                f"Unknown xml view_type {view_type}, attribute {dct_attr_view}"
            )
            return

        if form_xml is not None:
            str_arch = ET.tostring(form_xml, pretty_print=True)
            str_content = str_arch.decode()
        else:
            _logger.error(
                f"Cannot find view type of id '{model_id}' and model"
                f" '{model_name}'"
            )
            str_content = ""

        for key, value in dct_replace.items():
            str_content = str_content.replace(key, value)

        view_name = (
            code_generator_view_id.view_name
            if code_generator_view_id.view_name
            else f"{model_name.replace('.', '_')}_{view_type}"
        )
        dct_view_value = {
            "name": view_name,
            "type": view_type,
            "model": model_name,
            "arch": str_content,
            "m2o_model": code_generator_view_id.m2o_model.id,
        }
        if code_generator_view_id.inherit_view_name:
            # TODO validate module is installed before assign inherit_id
            dct_view_value["inherit_id"] = self.env.ref(
                code_generator_view_id.inherit_view_name
            ).id
            dct_view_value["is_show_whitelist_write_view"] = True
        lst_search = [
            (a, "=", b)
            for a, b in dct_view_value.items()
            if a not in ("m2o_model", "arch")
        ]
        view_value = self.env["ir.ui.view"].search(lst_search)
        if not view_value:
            if not dct_view_value:
                view_value = None
            elif not dct_view_value.get("arch"):
                _logger.error(f"Cannot generate view name '{dct_view_value}'")
            else:
                view_value = self.env["ir.ui.view"].create([dct_view_value])
        else:
            view_value.m2o_model = code_generator_view_id.m2o_model.id
            # dct_value_to_create["ir.ui.view"].append(ir_ui_view_value)

        if not view_value:
            _logger.error(f"Cannot create view '{view_name}'")
        elif code_generator_view_id.id_name:
            ir_model_data_id = self.env["ir.model.data"].search(
                [
                    ("name", "=", code_generator_view_id.id_name),
                    ("model", "=", "ir.ui.view"),
                    (
                        "module",
                        "=",
                        code_generator_view_id.code_generator_id.name,
                    ),
                ]
            )
            if ir_model_data_id:
                ir_model_data_id.res_id = view_value.id
            else:
                self._create_ir_model_data(
                    code_generator_view_id.code_generator_id,
                    "ir.ui.view",
                    view_value.id,
                    code_generator_view_id.id_name,
                )

        return view_value
