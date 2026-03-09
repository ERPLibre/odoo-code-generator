#!/usr/bin/env python3
# © 2021-2025 TechnoLibre (http://www.technolibre.ca)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)
import logging
import time
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


class CodeGeneratorGenerateViewsWizard(models.TransientModel):
    _name = "code.generator.generate.views.wizard"
    _inherit = [
        "code.generator.views.standard.mixin",
        "code.generator.views.xml.helpers.mixin",
    ]
    _description = "Code Generator Generate Views Wizard"

    # def default_get(self, fields):
    #     result = super(CodeGeneratorGenerateViewsWizard, self).default_get(fields)
    #     code_generator_id = self.env["code.generator.module"].browse(result.get("code_generator_id"))
    #     lst_model_id = [a.id for a in code_generator_id.o2m_models]
    # Don't need that solution
    #     result["selected_model_list_view_ids"] = [(6, 0, lst_model_id)]
    #     result["selected_model_form_view_ids"] = [(6, 0, lst_model_id)]
    #     return result

    name = fields.Char()

    all_model = fields.Boolean(
        string="All models",
        default=True,
        help="Generate with all existing model, or select manually.",
    )

    clear_all_access = fields.Boolean(
        string="Clear access",
        default=True,
        help="Clear all access/permission before execute.",
    )

    clear_all_act_window = fields.Boolean(
        string="Clear actions windows",
        default=True,
        help="Clear all actions windows before execute.",
    )

    clear_all_menu = fields.Boolean(
        string="Clear menus",
        default=True,
        help="Clear all menus before execute.",
    )

    clear_all_view = fields.Boolean(
        string="Clear views",
        default=True,
        help="Clear all views before execute.",
    )

    code_generator_id = fields.Many2one(
        comodel_name="code.generator.module",
        string="Code Generator",
        required=True,
        ondelete="cascade",
    )

    code_generator_view_ids = fields.Many2many(
        comodel_name="code.generator.view",
        string="Code Generator View",
    )

    date = fields.Date(
        required=True,
        default=fields.Date.context_today,
    )

    disable_generate_access = fields.Boolean(
        help="Disable security access generation."
    )

    disable_generate_menu = fields.Boolean(help="Disable menu generation.")

    enable_generate_all = fields.Boolean(
        string="Enable all feature",
        default=True,
        help="Generate with all feature.",
    )

    selected_model_calendar_view_ids = fields.Many2many(
        comodel_name="ir.model",
        relation="selected_model_calendar_view_ids_ir_model",
        string="Selected Model Calendar View",
    )

    selected_model_diagram_view_ids = fields.Many2many(
        comodel_name="ir.model",
        relation="selected_model_diagram_view_ids_ir_model",
        string="Selected Model Diagram View",
    )

    selected_model_form_view_ids = fields.Many2many(
        comodel_name="ir.model",
        relation="selected_model_form_view_ids_ir_model",
        string="Selected Model Form View",
    )

    selected_model_graph_view_ids = fields.Many2many(
        comodel_name="ir.model",
        relation="selected_model_graph_view_ids_ir_model",
        string="Selected Model Graph View",
    )

    selected_model_kanban_view_ids = fields.Many2many(
        comodel_name="ir.model",
        relation="selected_model_kanban_view_ids_ir_model",
        string="Selected Model Kanban View",
    )

    selected_model_pivot_view_ids = fields.Many2many(
        comodel_name="ir.model",
        relation="selected_model_pivot_view_ids_ir_model",
        string="Selected Model Pivot View",
    )

    selected_model_search_view_ids = fields.Many2many(
        comodel_name="ir.model",
        relation="selected_model_search_view_ids_ir_model",
        string="Selected Model Search View",
    )

    selected_model_timeline_view_ids = fields.Many2many(
        comodel_name="ir.model",
        relation="selected_model_timeline_view_ids_ir_model",
        string="Selected Model Timeline View",
    )

    selected_model_list_view_ids = fields.Many2many(
        comodel_name="ir.model",
        relation="selected_model_list_view_ids_ir_model",
        string="Selected Model List View",
    )

    user_id = fields.Many2one(
        comodel_name="res.users",
        string="User",
        required=True,
        default=lambda s: s.env.user.id,
    )

    def clear_all(self):
        # if self.clear_all_view and self.code_generator_id.o2m_model_views:
        #     self.code_generator_id.o2m_model_views.unlink()
        if self.clear_all_access and self.code_generator_id.o2m_model_access:
            self.code_generator_id.o2m_model_access.unlink()
        if self.clear_all_menu and self.code_generator_id.o2m_menus:
            self.code_generator_id.o2m_menus.unlink()
        if self.clear_all_act_window:
            if self.code_generator_id.o2m_model_act_window:
                self.code_generator_id.o2m_model_act_window.unlink()
            if self.code_generator_id.o2m_model_act_todo:
                self.code_generator_id.o2m_model_act_todo.unlink()
            if self.code_generator_id.o2m_model_act_url:
                self.code_generator_id.o2m_model_act_url.unlink()

    def button_generate_views(self):
        self.ensure_one()

        # Add dependencies
        self._add_dependencies()

        self.clear_all()

        # TODO refactor this part to control generation
        dct_value_to_create = defaultdict(list)

        before_time = time.process_time()

        if not self.code_generator_view_ids:
            status = self.generic_generate_view(dct_value_to_create)
        else:
            model_id = None
            lst_view_generated = []
            lst_model_id = []
            for code_generator_view_id in self.code_generator_view_ids:
                view_id = self._generate_specific_form_views_models(
                    code_generator_view_id, dct_value_to_create
                )
                if not view_id:
                    _logger.error(
                        "Cannot create view_id or find existing. Skip for"
                        f" '{code_generator_view_id.id_name}'"
                    )
                else:
                    lst_view_generated.append(view_id.type)
                    lst_model_id.append(view_id.m2o_model)
            lst_model_id = list(set(lst_model_id))
            for model_id in lst_model_id:
                self._generate_model_access(model_id)
            if model_id:
                self._generate_menu(
                    model_id,
                    model_id.m2o_module,
                    lst_view_generated,
                    self.code_generator_id.o2m_models,
                )
            status = True
        # Accelerate creation in batch
        for model_name, lst_value in dct_value_to_create.items():
            self.env[model_name].create(lst_value)

        after_time = time.process_time()
        _logger.info(
            "DEBUG time execution button_generate_views"
            f" {after_time - before_time}"
        )
        return status

    def generic_generate_view(self, dct_value_to_create):
        # before_time = time.process_time()
        o2m_models_view_list = (
            self.code_generator_id.o2m_models
            if self.all_model
            else self.selected_model_list_view_ids
        ).filtered(lambda x: not x.blacklist_all_ir_ui_view)
        o2m_models_view_form = (
            self.code_generator_id.o2m_models
            if self.all_model
            else self.selected_model_form_view_ids
        ).filtered(lambda x: not x.blacklist_all_ir_ui_view)
        o2m_models_view_kanban = (
            self.code_generator_id.o2m_models
            if self.all_model
            else self.selected_model_kanban_view_ids
        ).filtered(lambda x: not x.blacklist_all_ir_ui_view)
        o2m_models_view_search = (
            self.code_generator_id.o2m_models
            if self.all_model
            else self.selected_model_search_view_ids
        ).filtered(lambda x: not x.blacklist_all_ir_ui_view)
        o2m_models_view_pivot = (
            self.code_generator_id.o2m_models
            if self.all_model
            else self.selected_model_pivot_view_ids
        ).filtered(lambda x: not x.blacklist_all_ir_ui_view)
        o2m_models_view_calendar = (
            self.code_generator_id.o2m_models
            if self.all_model
            else self.selected_model_calendar_view_ids
        ).filtered(lambda x: not x.blacklist_all_ir_ui_view)
        o2m_models_view_graph = (
            self.code_generator_id.o2m_models
            if self.all_model
            else self.selected_model_graph_view_ids
        ).filtered(lambda x: not x.blacklist_all_ir_ui_view)
        o2m_models_view_timeline = (
            self.code_generator_id.o2m_models
            if self.all_model
            else self.selected_model_timeline_view_ids
        ).filtered(lambda x: not x.blacklist_all_ir_ui_view)
        o2m_models_view_diagram = (
            self.code_generator_id.o2m_models.filtered(
                lambda model: model.diagram_node_object
                and model.diagram_arrow_object
                and model.diagram_node_xpos_field
                and model.diagram_node_ypos_field
                and model.diagram_arrow_src_field
                and model.diagram_arrow_dst_field
            )
            if self.all_model
            else self.selected_model_diagram_view_ids
        ).filtered(lambda x: not x.blacklist_all_ir_ui_view)
        # Get unique list order by name of all model to generate
        lst_model = sorted(
            set(
                o2m_models_view_list
                + o2m_models_view_form
                + o2m_models_view_kanban
                + o2m_models_view_search
                + o2m_models_view_pivot
                + o2m_models_view_calendar
                + o2m_models_view_graph
                + o2m_models_view_timeline
            ),
            key=lambda model: model.name,
        )
        lst_model_id = self.env["ir.model"].browse([a.id for a in lst_model])

        for model_id in lst_model_id:
            lst_view_generated = []

            # Support enable_activity
            if model_id.enable_activity:
                model_id.add_model_inherit(
                    ["mail.thread", "mail.activity.mixin"]
                )
                # inherit_model_ids
                lst_view_generated.append("activity")

            # Different view
            if model_id in o2m_models_view_list:
                is_whitelist = any(
                    [a.is_show_whitelist_list_view for a in model_id.field_id]
                )
                # model_created_fields_list = list(
                #     filter(
                #         lambda x: x.name not in MAGIC_FIELDS
                #                   and not x.is_hide_blacklist_list_view
                #                   and (
                #                           not is_whitelist
                #                           or (is_whitelist and x.is_show_whitelist_list_view)
                #                   ),
                #         [a for a in model_id.field_id],
                #     )
                # )
                model_created_fields_list = model_id.field_id.filtered(
                    lambda field: field.name not in MAGIC_FIELDS
                    and not field.is_hide_blacklist_list_view
                    and (
                        not is_whitelist
                        or (is_whitelist and field.is_show_whitelist_list_view)
                    )
                )
                model_created_fields_list = self._update_model_field_list_view(
                    model_created_fields_list
                )
                self._generate_list_views_models(
                    model_id,
                    model_created_fields_list,
                    model_id.m2o_module,
                    dct_value_to_create,
                )
                lst_view_generated.append("list")

            if model_id in o2m_models_view_form:
                is_whitelist = any(
                    [
                        a.is_show_whitelist_form_view
                        for b in model_id
                        for a in b.field_id
                    ]
                )
                # model_created_fields_form = list(
                #     filter(
                #         lambda x: x.name not in MAGIC_FIELDS
                #                   and not x.is_hide_blacklist_form_view
                #                   and (
                #                           not is_whitelist
                #                           or (is_whitelist and x.is_show_whitelist_form_view)
                #                   ),
                #         [a for a in model_id.field_id],
                #     )
                # )
                model_created_fields_form = model_id.field_id.filtered(
                    lambda field: field.name not in MAGIC_FIELDS
                    and not field.is_hide_blacklist_form_view
                    and (
                        not is_whitelist
                        or (is_whitelist and field.is_show_whitelist_form_view)
                    )
                )
                self._generate_form_views_models(
                    model_id,
                    model_created_fields_form,
                    model_id.m2o_module,
                    dct_value_to_create,
                )
                lst_view_generated.append("form")

            if model_id in o2m_models_view_kanban:
                is_whitelist = any(
                    [
                        a.is_show_whitelist_kanban_view
                        for b in model_id
                        for a in b.field_id
                    ]
                )
                # model_created_fields_kanban = list(
                #     filter(
                #         lambda x: x.name not in MAGIC_FIELDS
                #                   and not x.is_hide_blacklist_kanban_view
                #                   and (
                #                           not is_whitelist
                #                           or (is_whitelist and x.is_show_whitelist_kanban_view)
                #                   ),
                #         [a for a in model_id.field_id],
                #     )
                # )
                model_created_fields_kanban = model_id.field_id.filtered(
                    lambda field: field.name not in MAGIC_FIELDS
                    and not field.is_hide_blacklist_kanban_view
                    and (
                        not is_whitelist
                        or (
                            is_whitelist
                            and field.is_show_whitelist_kanban_view
                        )
                    )
                )
                self._generate_kanban_views_models(
                    model_id,
                    model_created_fields_kanban,
                    model_id.m2o_module,
                    dct_value_to_create,
                )
                lst_view_generated.append("kanban")

            if model_id in o2m_models_view_search:
                is_whitelist = any(
                    [
                        a.is_show_whitelist_search_view
                        for b in model_id
                        for a in b.field_id
                    ]
                )
                # model_created_fields_search = list(
                #     filter(
                #         lambda x: x.name not in MAGIC_FIELDS
                #                   and not x.is_hide_blacklist_search_view
                #                   and (
                #                           not is_whitelist
                #                           or (is_whitelist and x.is_show_whitelist_search_view)
                #                   ),
                #         [a for a in model_id.field_id],
                #     )
                # )
                model_created_fields_search = model_id.field_id.filtered(
                    lambda field: field.name not in MAGIC_FIELDS
                    and not field.is_hide_blacklist_search_view
                    and (
                        not is_whitelist
                        or (
                            is_whitelist
                            and field.is_show_whitelist_search_view
                        )
                    )
                )
                status = self._generate_search_views_models(
                    model_id,
                    model_created_fields_search,
                    model_id.m2o_module,
                    dct_value_to_create,
                )
                if status:
                    lst_view_generated.append("search")

            if model_id in o2m_models_view_pivot:
                is_whitelist = any(
                    [
                        a.is_show_whitelist_pivot_view
                        for b in model_id
                        for a in b.field_id
                    ]
                )
                # model_created_fields_pivot = list(
                #     filter(
                #         lambda x: x.name not in MAGIC_FIELDS
                #                   and not x.is_hide_blacklist_pivot_view
                #                   and (
                #                           not is_whitelist
                #                           or (is_whitelist and x.is_show_whitelist_pivot_view)
                #                   ),
                #         [a for a in model_id.field_id],
                #     )
                # )
                model_created_fields_pivot = model_id.field_id.filtered(
                    lambda field: field.name not in MAGIC_FIELDS
                    and not field.is_hide_blacklist_pivot_view
                    and (
                        not is_whitelist
                        or (
                            is_whitelist and field.is_show_whitelist_pivot_view
                        )
                    )
                )
                self._generate_pivot_views_models(
                    model_id,
                    model_created_fields_pivot,
                    model_id.m2o_module,
                    dct_value_to_create,
                )
                lst_view_generated.append("pivot")

            if model_id in o2m_models_view_calendar:
                is_whitelist = any(
                    [
                        a.is_show_whitelist_calendar_view
                        for b in model_id
                        for a in b.field_id
                    ]
                )
                # model_created_fields_calendar = list(
                #     filter(
                #         lambda x: x.name not in MAGIC_FIELDS
                #                   and not x.is_hide_blacklist_calendar_view
                #                   and (
                #                           not is_whitelist
                #                           or (is_whitelist and x.is_show_whitelist_calendar_view)
                #                   ),
                #         [a for a in model_id.field_id],
                #     )
                # )
                model_created_fields_calendar = model_id.field_id.filtered(
                    lambda field: field.name not in MAGIC_FIELDS
                    and not field.is_hide_blacklist_calendar_view
                    and (
                        not is_whitelist
                        or (
                            is_whitelist
                            and field.is_show_whitelist_calendar_view
                        )
                    )
                )
                has_start_date = any(
                    [
                        a.is_date_start_view
                        for a in model_created_fields_calendar
                    ]
                )
                if has_start_date:
                    self._generate_calendar_views_models(
                        model_id,
                        model_created_fields_calendar,
                        model_id.m2o_module,
                        dct_value_to_create,
                    )
                    lst_view_generated.append("calendar")

            if model_id in o2m_models_view_graph:
                is_whitelist = any(
                    [
                        a.is_show_whitelist_graph_view
                        for b in model_id
                        for a in b.field_id
                    ]
                )
                # model_created_fields_graph = list(
                #     filter(
                #         lambda x: x.name not in MAGIC_FIELDS
                #                   and not x.is_hide_blacklist_graph_view
                #                   and (
                #                           not is_whitelist
                #                           or (is_whitelist and x.is_show_whitelist_graph_view)
                #                   ),
                #         [a for a in model_id.field_id],
                #     )
                # )
                model_created_fields_graph = model_id.field_id.filtered(
                    lambda field: field.name not in MAGIC_FIELDS
                    and not field.is_hide_blacklist_graph_view
                    and (
                        not is_whitelist
                        or (
                            is_whitelist and field.is_show_whitelist_graph_view
                        )
                    )
                )
                self._generate_graph_views_models(
                    model_id,
                    model_created_fields_graph,
                    model_id.m2o_module,
                    dct_value_to_create,
                )
                lst_view_generated.append("graph")

            if model_id in o2m_models_view_timeline:
                model_created_fields_timeline = model_id.field_id.filtered(
                    lambda field: field.name not in MAGIC_FIELDS
                    and field.ttype in ("date", "datetime")
                    and (field.is_date_start_view or field.is_date_end_view)
                )

                if model_created_fields_timeline:
                    self._generate_timeline_views_models(
                        model_id,
                        model_created_fields_timeline,
                        model_id.m2o_module,
                        dct_value_to_create,
                    )
                    lst_view_generated.append("timeline")

            if model_id in o2m_models_view_diagram:
                lst_view_generated.append("diagram")

            # Menu and action_windows
            self._generate_menu(
                model_id,
                model_id.m2o_module,
                lst_view_generated,
                lst_model_id,
            )

        # Need form to be created before create diagram
        for model_id in o2m_models_view_diagram:
            self._generate_diagram_views_models(
                model_id,
                model_id.m2o_module,
                dct_value_to_create,
            )

        # for model_id in o2m_models_view_form:
        #     print(model_id)
        # model_created_fields = model_id.field_id.filtered(lambda field: field.name not in MAGIC_FIELDS).mapped(
        #     'name')
        #

        for model_id in self.code_generator_id.o2m_models:
            self._generate_model_access(model_id)

        # after_time = time.process_time()
        # _logger.info(
        #     "DEBUG time execution generic_generate_view"
        #     f" {after_time - before_time}"
        # )
        return True

    def _add_dependencies(self):
        # Check if need to add mail dependency
        for code_generator in self.code_generator_id:
            need_mail_depend = any(
                [a.enable_activity for a in code_generator.o2m_models]
            )
            if not need_mail_depend:
                continue

            code_generator.add_module_dependency("mail")

    def _generate_model_access(self, model_created):
        if self.disable_generate_access:
            return
        # Unique access
        # group_id = self.env['res.groups'].search([('name', '=', 'Code Generator / Manager')])
        # group_id = self.env['res.groups'].search([('name', '=', 'Internal User')])
        # TODO search system lang
        lang = "en_US"
        group_id = self.env.ref("base.group_user").with_context(lang=lang)
        model_name = model_created.model
        model_name_str = model_name.replace(".", "_")
        name = "%s Access %s" % (model_name_str, group_id.full_name)
        # TODO maybe search by permission and model, ignore the name
        existing_access = self.env["ir.model.access"].search(
            [
                ("model_id", "=", model_created.id),
                ("group_id", "=", group_id.id),
                ("name", "=", name),
            ]
        )
        if existing_access:
            return

        v = {
            "name": name,
            "model_id": model_created.id,
            "group_id": group_id.id,
            "perm_read": True,
            "perm_create": True,
            "perm_write": True,
            "perm_unlink": True,
        }

        access_value = self.env["ir.model.access"].create([v])

    def _create_ir_model_data(
        self, module, model, res_id, name, prefix_name="", suffix_name=""
    ):
        # TODO check function _get_action_data_name in code_generator_writer.py
        def _create_name(name, count=0, prefix_name="", suffix_name=""):
            # TODO wait after cg refactoring to support this feature
            # so ignore suffix_name menu
            if suffix_name in ["root"]:
                suffix_name = ""
            # Accept prefix_name group
            if suffix_name in ["group", "parent"]:
                # TODO revert it when menu will be refactor
                prefix_name = suffix_name
                suffix_name = ""
            if prefix_name in ["menu"]:
                prefix_name = ""
            create_name = ""
            if prefix_name:
                create_name = prefix_name + "_"
            create_name += name
            if count:
                create_name += f"_{count}"
            if suffix_name:
                create_name += f"_{suffix_name}"
            return (
                unidecode.unidecode(create_name)
                .replace(" ", "_")
                .replace("'", "_")
                .replace("-", "_")
                .lower()
            )

        data = self.env["ir.model.data"].search(
            [
                ("module", "=", module.name),
                ("model", "=", model),
                ("res_id", "=", res_id),
            ]
        )
        if data:
            _logger.warning(
                f"Cannot create xml_id for model '{model}', id '{res_id}',"
                f" name '{data.name}'. Already exist!"
            )
            return

        # check if exist
        new_name = ""
        i = 0
        while not new_name:
            new_name = _create_name(
                name, count=i, prefix_name=prefix_name, suffix_name=suffix_name
            )
            i += 1
            data = self.env["ir.model.data"].search(
                [
                    ("module", "=", module.name),
                    ("model", "=", model),
                    ("name", "=", new_name),
                ]
            )
            if data:
                new_name = ""

        return self.env["ir.model.data"].create(
            [
                {
                    "name": new_name,
                    "model": model,
                    "module": module.name,
                    "res_id": res_id,
                    "noupdate": True,
                    # If it's False, target record (res_id) will be removed while module update
                }
            ]
        )

    def _generate_menu(
        self, model_created, module, lst_view_generated, model_ids
    ):
        if self.disable_generate_menu:
            return

        generated_root_menu = None
        generated_parent_menu = None
        dct_group_generated_menu = {}
        dct_parent_generated_menu = {}
        lst_group_generated_menu_name = []
        lst_parent_generated_menu_name = []
        nb_sub_menu = 0

        # TODO no menu is generated in case of module is not an application
        #  and it creates new views, because cannot find views to attach it.
        #  Need a configuration to attach a root if not create it.
        #  Can have multiple menu
        # group_id = self.env['res.groups'].search([('name', '=', 'Code Generator / Manager')])
        # group_id = self.env['res.groups'].search([('name', '=', 'Internal User')])
        is_generic_menu = not model_created.m2o_module.code_generator_menus_id
        group_id = self.env.ref("base.group_user")
        model_name = model_created.model
        menu_group = model_created.menu_group
        menu_parent = model_created.menu_parent
        model_name_str = model_name.replace(".", "_")
        module_name = module.name
        menu_group_id = None
        menu_parent_id = None
        if module.application and is_generic_menu:
            # Create root if not exist
            if not generated_root_menu:
                v = {
                    "name": module_name.replace("_", " ").title(),
                    "sequence": 20,
                    "web_icon": f"code_generator,static/description/icon_new_application.png",
                    # 'group_id': group_id.id,
                    "m2o_module": module.id,
                }
                generated_root_menu = self.env["ir.ui.menu"].create([v])
            if not generated_parent_menu:
                v = {
                    "name": _("Menu"),
                    "sequence": 1,
                    "parent_id": generated_root_menu.id,
                    # 'group_id': group_id.id,
                    "m2o_module": module.id,
                }
                generated_parent_menu = self.env["ir.ui.menu"].create([v])

        # Create list of menu_parent
        if not lst_parent_generated_menu_name:
            lst_parent_generated_menu_name = sorted(
                list(set([a.menu_parent for a in model_ids if a.menu_parent]))
            )

        # Create list of menu_group
        if not lst_group_generated_menu_name:
            lst_group_generated_menu_name = sorted(
                list(set([a.menu_group for a in model_ids if a.menu_group]))
            )

        # Create menu_parent item
        if is_generic_menu and menu_parent:
            menu_parent_id = dct_parent_generated_menu.get(menu_parent)
            if menu_parent == "Configuration":
                sequence = 99
            else:
                sequence = (
                    lst_parent_generated_menu_name.index(menu_parent) + 1
                )

            if not menu_parent_id:
                v = {
                    "name": menu_parent,
                    "sequence": sequence,
                    # 'group_id': group_id.id,
                    "m2o_module": module.id,
                    "parent_id": generated_root_menu.id,
                }

                menu_parent_id = self.env["ir.ui.menu"].create([v])
                dct_parent_generated_menu[menu_parent] = menu_parent_id

                # Create id name
                self._create_ir_model_data(
                    module,
                    "ir.ui.menu",
                    menu_parent_id.id,
                    menu_parent,
                    prefix_name="menu",
                    suffix_name="parent",
                )

        # Create menu_group item
        if is_generic_menu and menu_group:
            menu_group_id = dct_group_generated_menu.get(menu_group)
            sequence = lst_group_generated_menu_name.index(menu_group)
            if not menu_group_id:
                v = {
                    "name": menu_group,
                    "sequence": sequence,
                    # 'group_id': group_id.id,
                    "m2o_module": module.id,
                }
                if menu_parent_id:
                    v["parent_id"] = menu_parent_id.id
                elif generated_parent_menu:
                    v["parent_id"] = generated_parent_menu.id
                else:
                    v["parent_id"] = generated_root_menu.id

                menu_group_id = self.env["ir.ui.menu"].create([v])
                dct_group_generated_menu[menu_group] = menu_group_id

                # Create id name
                self._create_ir_model_data(
                    module,
                    "ir.ui.menu",
                    menu_group_id.id,
                    menu_group,
                    prefix_name="menu",
                    suffix_name="group",
                )

        help_str = f"""<p class="o_view_nocontent_empty_folder">
        Add a new {model_name_str}
          </p>
          <p>
            Databases whose tables could be imported to Odoo and then be exported into code
          </p>
        """

        # TODO change sequence of view mode
        # Kanban first by default
        if "kanban" in lst_view_generated:
            lst_first_view_generated = ["kanban"]
            lst_second_view_generated = list(set(lst_view_generated[:]))
            lst_second_view_generated.remove("kanban")
        else:
            lst_first_view_generated = []
            lst_second_view_generated = list(set(lst_view_generated))

        # Special case, cannot support search view type in action_view
        try:
            lst_second_view_generated.remove("search")
        except ValueError:
            pass

        view_mode = ",".join(
            lst_first_view_generated
            + sorted(lst_second_view_generated, reverse=True)
        )
        view_type = (
            "form" if "form" in lst_view_generated else lst_view_generated[0]
        )

        # Create menu
        if module.application and is_generic_menu:
            # Compute menu name
            menu_name = model_name_str
            if "." in model_name:
                application_name, sub_model_name = model_name.split(
                    ".", maxsplit=1
                )
                if model_created.menu_label:
                    menu_name = model_created.menu_label
                elif (
                    not model_created.menu_name_keep_application
                    and sub_model_name
                    and menu_name.lower().startswith(application_name.lower())
                ):
                    menu_name = (
                        sub_model_name.capitalize()
                        .replace(".", " ")
                        .replace("_", " ")
                    )
                else:
                    menu_name = f"{application_name} {sub_model_name.replace('.', ' ')}".capitalize().replace(
                        "_", " "
                    )
            else:
                menu_name = model_name

            action_data_value = self.env["ir.actions.act_window"].search(
                [
                    ("name", "=", menu_name),
                    ("res_model", "=", model_name),
                    ("type", "=", "ir.actions.act_window"),
                ]
            )

            if not action_data_value:
                # Create action
                v = {
                    "name": menu_name,
                    "res_model": model_name,
                    "type": "ir.actions.act_window",
                    "view_mode": view_mode,
                    # "view_type": view_type,
                    # 'help': help_str,
                    # 'search_view_id': self.search_view_id.id,
                    "context": {},
                    "m2o_res_model": model_created.id,
                }
                action_id = self.env["ir.actions.act_window"].create([v])
            else:
                s_more_info = ""
                if len(action_data_value) > 1:
                    s_more_info = " Detect 2 act_window."
                elif action_data_value.view_mode != view_mode:
                    s_more_info = (
                        f" Detect new view_mode '{view_mode}'. Old view_mode"
                        f" '{action_data_value.view_mode}'"
                    )
                _logger.warning(
                    f"Ir Actions Act_window '{menu_name}' of model"
                    f" '{model_name}' already exist.{s_more_info}"
                )
                action_id = action_data_value[0]

            self._create_ir_model_data(
                module,
                "ir.actions.act_window",
                action_id.id,
                menu_name,
                prefix_name=model_name_str,
                suffix_name="action_window",
            )

            nb_sub_menu += 1

            v = {
                "name": menu_name,
                "sequence": nb_sub_menu,
                "action": "ir.actions.act_window,%s" % action_id.id,
                # 'group_id': group_id.id,
                "m2o_module": module.id,
            }

            if menu_group_id:
                v["parent_id"] = menu_group_id.id
            elif menu_parent_id:
                v["parent_id"] = menu_parent_id.id
            elif generated_parent_menu:
                v["parent_id"] = generated_parent_menu.id

            new_menu_id = self.env["ir.ui.menu"].create([v])

            self._create_ir_model_data(
                module,
                "ir.ui.menu",
                new_menu_id.id,
                menu_name,
                prefix_name="menu",
            )
        elif not is_generic_menu:
            cg_menu_ids = model_created.m2o_module.code_generator_menus_id
            # TODO check different case, with act_window, without, multiple menu, single menu
            # Sort parent first

            lst_menu_to_sort = [a for a in cg_menu_ids]
            lst_menu = []
            lst_inserted_menu_name = []
            i = -1
            while lst_menu_to_sort:
                i += 1
                lst_added_menu = []
                if len(lst_menu_to_sort) <= i:
                    # Re loop
                    i = 0
                menu_id = lst_menu_to_sort[i]
                menu_name = menu_id.id_name
                if not menu_id.parent_id_name:
                    lst_inserted_menu_name.append(menu_name)
                    lst_added_menu.append(menu_id)
                else:
                    parent_module_name = None
                    if "." in menu_id.parent_id_name:
                        (
                            parent_module_name,
                            parent_menu_name,
                        ) = menu_id.parent_id_name.split(".")
                    else:
                        parent_menu_name = menu_id.parent_id_name
                    if (
                        parent_module_name != module.name
                        or parent_menu_name in lst_inserted_menu_name
                    ):
                        lst_inserted_menu_name.append(menu_name)
                        lst_added_menu.append(menu_id)
                for added_menu in lst_added_menu:
                    lst_menu.append(added_menu)
                    lst_menu_to_sort.remove(added_menu)
                    i = -1

            for menu_id in lst_menu:
                action_id = None
                if menu_id.m2o_act_window:
                    # Create action
                    v = {
                        "name": menu_id.m2o_act_window.name,
                        "type": "ir.actions.act_window",
                        "view_mode": view_mode,
                        # "view_type": view_type,
                        # 'help': help_str,
                        # 'search_view_id': self.search_view_id.id,
                        "context": {},
                        "m2o_res_model": model_created.id,
                    }
                    if menu_id.m2o_act_window.model_name:
                        v["res_model"] = menu_id.m2o_act_window.model_name
                    else:
                        _logger.warning(
                            "Missing model_name into m2o_act_window"
                            f" '{menu_id.m2o_act_window.name}', force another"
                            f" model name '{model_name}'"
                        )
                        v["res_model"] = model_name

                    lst_action = [
                        (a, "=", b)
                        for a, b in v.items()
                        if a != "m2o_res_model"
                    ]
                    action_id = self.env["ir.actions.act_window"].search(
                        lst_action
                    )
                    if not action_id:
                        action_id = self.env["ir.actions.act_window"].create(
                            [v]
                        )
                    else:
                        action_id.m2o_res_model = model_created.id
                    if menu_id.m2o_act_window.id_name:
                        ir_model_data_id = self.env["ir.model.data"].search(
                            [
                                ("name", "=", menu_id.m2o_act_window.id_name),
                                ("model", "=", "ir.actions.act_window"),
                                (
                                    "module",
                                    "=",
                                    module.name,
                                ),
                            ]
                        )
                        if ir_model_data_id:
                            ir_model_data_id.res_id = action_id.id
                        else:
                            # Write id name
                            self.env["ir.model.data"].create(
                                [
                                    {
                                        "name": menu_id.m2o_act_window.id_name,
                                        "model": "ir.actions.act_window",
                                        "module": module.name,
                                        "res_id": action_id.id,
                                        "noupdate": True,
                                        # If it's False, target record (res_id) will be removed while module update
                                    }
                                ]
                            )
                elif not menu_id.ignore_act_window:
                    # Create action
                    v = {
                        "name": f"{model_name_str}_action_view",
                        "res_model": model_name,
                        "type": "ir.actions.act_window",
                        "view_mode": view_mode,
                        # "view_type": view_type,
                        # 'help': help_str,
                        # 'search_view_id': self.search_view_id.id,
                        "context": {},
                        "m2o_res_model": model_created.id,
                    }
                    action_id = self.env["ir.actions.act_window"].create([v])

                v = {
                    "name": menu_id.name,
                    # 'group_id': group_id.id,
                    "m2o_module": module.id,
                }
                if menu_id.ignore_act_window:
                    v["ignore_act_window"] = True
                else:
                    v["action"] = "ir.actions.act_window,%s" % action_id.id

                v["sequence"] = menu_id.sequence

                if menu_id.web_icon:
                    v["web_icon"] = menu_id.web_icon

                if menu_id.parent_id_name:
                    # TODO wait after cg refactoring to support this feature
                    # menu_id.parent_id doesn't exist, we try to find the parent with
                    # ir_model_data_parent_id = self.env["ir.model.data"].search(
                    #     [
                    #         ("module", "=", module.name),
                    #         ("model", "=", "ir.ui.menu"),
                    #         ("res_id", "=", menu_id.parent_id.id),
                    #     ]
                    # )
                    # TODO crash when create empty module and template to read this empty module
                    try:
                        v["parent_id"] = self.env.ref(
                            menu_id.parent_id_name
                        ).id
                    except Exception:
                        _logger.error(
                            f"Cannot find ref {menu_id.parent_id_name} of menu"
                            f" {menu_id.id_name} to associate parent_id."
                        )

                new_menu_id = self.env["ir.ui.menu"].create([v])

                ir_model_data_id = self.env["ir.model.data"].search(
                    [
                        ("name", "=", menu_id.id_name),
                        ("model", "=", "ir.ui.menu"),
                        (
                            "module",
                            "=",
                            module.name,
                        ),
                    ]
                )
                if ir_model_data_id:
                    # This is because the module is already installed
                    ir_model_data_id.res_id = new_menu_id.id
                    _logger.warning(
                        f"Force change menu id for {menu_id.id_name}"
                    )
                else:
                    suffix = ""
                    if not menu_id.parent_id_name:
                        suffix = "root"
                    self._create_ir_model_data(
                        module,
                        "ir.ui.menu",
                        new_menu_id.id,
                        menu_id.id_name,
                        prefix_name="menu",
                        suffix_name=suffix,
                    )
