import ast
import base64
import glob
import hashlib
import io
import logging
import os
import shutil
import tempfile
import types
import uuid
from collections import defaultdict

import unidecode
from code_writer import CodeWriter
from lxml import etree as ET
from lxml.builder import E
from odoo import api, fields, models
from odoo.models import MAGIC_COLUMNS
from odoo.tools.misc import mute_logger
from PIL import Image

from .. import code_generator_data
from ..extractor_controller import ExtractorController
from ..extractor_module import ExtractorModule
from ..extractor_view import ExtractorView
from ..python_controller_writer import PythonControllerWriter

_logger = logging.getLogger(__name__)

from .code_generator_writer_constants import (
    UNDEFINEDMESSAGE,
    MAGIC_FIELDS,
    MODULE_NAME,
    BLANK_LINE,
    BREAK_LINE_OFF,
    BREAK_LINE,
    XML_VERSION_HEADER,
    XML_VERSION,
    XML_VERSION_STR,
    XML_ODOO_OPENING_TAG,
    XML_HEAD,
    XML_ODOO_CLOSING_TAG,
    FROM_ODOO_IMPORTS,
    MODEL_HEAD,
    FROM_ODOO_IMPORTS_SUPERUSER,
    MODEL_SUPERUSER_HEAD,
)


class CodeGeneratorWriter(models.Model):
    _name = "code.generator.writer"
    _inherit = [
        "code.generator.writer.xml.mixin",
        "code.generator.writer.views.mixin",
        "code.generator.writer.python.mixin",
    ]
    _description = "Code Generator Writer"

    basename = fields.Char(string="Base name")

    code_generator_ids = fields.Many2many(
        comodel_name="code.generator.module",
        string="Code Generator",
    )

    list_path_file = fields.Char(
        string="List path file",
        help="Value are separated by ;",
    )

    rootdir = fields.Char(string="Root dir")

    @staticmethod
    def _fmt_underscores(word):
        return word.lower().replace(".", "_")

    @staticmethod
    def _fmt_camel(word):
        return word.replace(".", "_").title().replace("_", "")

    @staticmethod
    def _fmt_title(word):
        return word.replace(".", " ").title()

    @staticmethod
    def _get_l_map(fn, collection):
        """
        Util function to get a list of a map operation
        :param fn:
        :param collection:
        :return:
        """

        return list(map(fn, collection))

    def _get_class_name(self, model):
        """
        Util function to get a model class name representation from a model name (code.generator -> CodeGenerator)
        :param model:
        :return:
        """

        result = []
        bypoint = model.split(".")
        for byp in bypoint:
            result += byp.split("_")
        return "".join(self._get_l_map(lambda e: e.capitalize(), result))

    @staticmethod
    def _lower_replace(string, replacee=" ", replacer="_"):
        """
        Util function to replace and get the lower content of a string
        :param string:
        :return:
        """

        v = (
            str(string)
            .lower()
            .replace(replacee, replacer)
            .replace("-", "_")
            .replace(".", "_")
            .replace("'", "_")
            .replace("`", "_")
            .replace("^", "_")
        )
        new_v = v.strip("_")

        while new_v.count("__"):
            new_v = new_v.replace("__", "_")
        return unidecode.unidecode(new_v)

    def _get_model_model(self, model_model, replacee="."):
        """
        Util function to get a model res_id-like representation (code.generator -> code_generator)
        :param model_model:
        :param replacee:
        :return:
        """
        return self._lower_replace(model_model, replacee=replacee)

    @staticmethod
    def _get_python_class_4inherit(model):
        """
        Util function to get the Python Classes for inheritance
        :param model:
        :return:
        """

        class_4inherit = (
            "models.TransientModel"
            if model.transient
            else (
                "models.AbstractModel" if model._abstract else "models.Model"
            )
        )
        if model.m2o_inherit_py_class.name:
            class_4inherit += ", %s" % model.m2o_inherit_py_class.name

        return class_4inherit

    def _get_odoo_ttype_class(self, ttype):
        """
        Util function to get a field class name from a field type (char -> Char, many2one -> Many2one)
        :param ttype:
        :return:
        """

        return f"fields.{self._get_class_name(ttype)}"

    @staticmethod
    def _get_starting_spaces(compute_line):
        """
        Util function to count the starting spaces of a string
        :param compute_line:
        :return:
        """

        space_counter = 0
        for character in compute_line:
            if character.isspace():
                space_counter += 1

            else:
                break

        return space_counter

    @staticmethod
    def _set_limit_4xmlid(xmlid):
        """
        Util function to truncate (to 64 characters) an xml_id
        :param xmlid:
        :return:
        """

        # if 64 - len(xmlid) < 0:
        #     new_xml_id = "%s..." % xmlid[: 61 - len(xmlid)]
        #     _logger.warning(
        #         f"Slice xml_id {xmlid} to {new_xml_id} because length is upper"
        #         " than 63."
        #     )
        # else:
        #     new_xml_id = xmlid
        # return new_xml_id
        return xmlid

    @staticmethod
    def _prepare_compute_constrained_fields(l_fields):
        """

        :param l_fields:
        :return:
        """

        counter = 1
        prepared = ""
        for field in l_fields:
            prepared += "'%s'%s" % (
                field,
                ", " if counter < len(l_fields) else "",
            )
            counter += 1

        return prepared

    def _get_model_constrains(self, cw, model, module):
        """
        Function to obtain the model constrains
        :param model:
        :return:
        """

        if model.o2m_server_constrains:

            cw.emit()

            for sconstrain in model.o2m_server_constrains:
                l_constrained = self._get_l_map(
                    lambda e: e.strip(), sconstrain.constrained.split(",")
                )

                cw.emit(
                    f"@api.constrains({self._prepare_compute_constrained_fields(l_constrained)})"
                )
                cw.emit(f"def _check_{'_'.join(l_constrained)}(self):")

                l_code = sconstrain.txt_code.split("\n")
                with cw.indent():
                    for line in l_code:
                        cw.emit(line.rstrip())
                # starting_spaces = 2
                # for line in l_code:
                #     if self._get_starting_spaces(line) == 2:
                #         starting_spaces += 1
                #     l_model_constrains.append('%s%s' % (TAB4 * starting_spaces, line.strip()))
                #     starting_spaces = 2

                cw.emit()

            cw.emit()

        constraints_id = None
        if model.o2m_constraints:
            # TODO how to use this way? binding model not working
            constraints_id = model.o2m_constraints
        elif module.o2m_model_constraints:
            constraints_id = module.o2m_model_constraints

        if constraints_id:
            lst_constraint = []
            for constraint in constraints_id:
                constraint_name = constraint.name.replace(
                    "%s_" % self._get_model_model(model.model), ""
                )
                constraint_definition = constraint.definition
                constraint_message = (
                    constraint.message
                    if constraint.message
                    else UNDEFINEDMESSAGE
                )

                lst_constraint.append(
                    f"('{constraint_name}', '{constraint_definition}',"
                    f" '{constraint_message}')"
                )

            cw.emit()
            cw.emit_list(
                lst_constraint, ("[", "]"), before="_sql_constraints = "
            )
            cw.emit()

    def _set_static_description_file(self, module, application_icon):
        """
        Function to set the static descriptions files
        :param module:
        :param application_icon:
        :return:
        """

        cg_data = code_generator_data.get_code_generator_data(self.env)
        static_description_icon_path = os.path.join(
            cg_data.static_description_path, "icon.png"
        )
        static_description_icon_code_generator_path = os.path.join(
            cg_data.static_description_path,
            "code_generator_icon.png",
        )
        # TODO hack to force icon or True
        if module.icon_child_image or module.icon_real_image:
            if module.icon_real_image:
                cg_data.write_file_binary(
                    static_description_icon_path,
                    base64.b64decode(module.icon_real_image),
                )
            if module.icon_child_image:
                cg_data.write_file_binary(
                    static_description_icon_code_generator_path,
                    base64.b64decode(module.icon_child_image),
                )
        else:
            # elif module.icon_image:

            # TODO use this when fix loading picture, now temporary disabled and force use icon from menu
            # cg_data.write_file_binary(static_description_icon_path,
            # base64.b64decode(module.icon_image))
            # TODO temp solution with icon from menu
            icon_path = ""
            if module.icon and os.path.isfile(module.icon):
                with open(module.icon, "rb") as file:
                    content = file.read()
                icon_path = module.icon
            else:
                if application_icon:
                    icon_path = application_icon[
                        application_icon.find(",") + 1 :
                    ]
                    # icon_path = application_icon.replace(",", "/")
                else:
                    icon_path = "static/description/icon_new_application.png"
                icon_path = os.path.normpath(
                    os.path.join(os.path.dirname(__file__), "..", icon_path)
                )
                with open(icon_path, "rb") as file:
                    content = file.read()
            if hasattr(module, "template_module_id") and hasattr(
                module.template_module_id, "icon_image"
            ):
                if not icon_path:
                    _logger.error("Icon path is empty.")
                    return ""
                if not os.path.exists(icon_path):
                    _logger.error(f"Icon path {icon_path} doesn't exist.")
                    return ""
                # It's a template generator
                minimal_size_width = 350
                # Add logo in small corner
                if module.template_module_id.icon_image:
                    logo = Image.open(
                        io.BytesIO(
                            base64.b64decode(
                                module.template_module_id.icon_image
                            )
                        )
                    )
                    icon = Image.open(icon_path)
                    # Change original size for better quality
                    if logo.width < minimal_size_width:
                        new_h = int(
                            logo.height / logo.width * minimal_size_width
                        )
                        new_w = minimal_size_width
                        logo = logo.resize(
                            (new_w, new_h), Image.Resampling.LANCZOS
                        )
                    ratio = 0.3
                    w = int(logo.width * ratio)
                    if icon.width != icon.height:
                        h = int(logo.height / logo.width * w)
                    else:
                        h = w
                    size = w, h
                    icon.thumbnail(size, Image.Resampling.LANCZOS)
                    x = logo.width - w
                    logo.paste(icon, (x, 0))
                    img_byte_arr = io.BytesIO()
                    logo.save(img_byte_arr, format="PNG")
                    img_byte_arr = img_byte_arr.getvalue()

                    # image = base64.b64decode(module.template_module_id.icon_image)
                    cg_data.write_file_binary(
                        static_description_icon_path, img_byte_arr
                    )
                    module.icon_real_image = base64.b64encode(img_byte_arr)
                if module.template_module_id.icon_image:
                    code_generator_image = base64.b64decode(
                        module.template_module_id.icon_image
                    )
                    module.icon_child_image = (
                        module.template_module_id.icon_image
                    )
                    cg_data.write_file_binary(
                        static_description_icon_code_generator_path,
                        code_generator_image,
                    )
            else:
                cg_data.write_file_binary(
                    static_description_icon_path, content
                )
                module.icon_real_image = base64.b64encode(content)
        # else:
        #     static_description_icon_path = ""

        return static_description_icon_path

    @staticmethod
    def _get_from_rec_name(record, model):
        """
        Util function to handle the _rec_name / rec_name access
        :param record:
        :param model:
        :return:
        """

        return (
            getattr(record, model._rec_name)
            if getattr(record, model._rec_name)
            else getattr(record, model.rec_name)
        )

    def set_module_init_file_extra(self, module):
        pass

    def set_module_translator(self, module_name, module_path):
        module_id = self.env["ir.module.module"].search(
            [("name", "=", module_name), ("state", "=", "installed")]
        )
        if not module_id:
            return

        i18n_path = os.path.join(module_path, "i18n")
        # TODO can be move to util
        data = code_generator_data.CodeGeneratorData(module_id, module_path)
        data.check_mkdir_and_create(i18n_path, is_file=False)

        # Create pot
        export = self.env["base.language.export"].create(
            [{"format": "po", "modules": [(6, 0, [module_id.id])]}]
        )

        export.act_getfile()
        po_file = export.data
        data = base64.b64decode(po_file).decode("utf-8")
        translation_file = os.path.join(i18n_path, f"{module_name}.pot")

        with open(translation_file, "w") as file:
            file.write(data)

        # Create po
        # TODO get this info from configuration/module
        # lst_lang = [
        #     ("fr_CA", "fr_CA"),
        #     ("fr_FR", "fr"),
        #     ("en_US", "en"),
        #     ("en_CA", "en_CA"),
        # ]
        lst_lang = [("fr_CA", "fr_CA")]
        for lang_local, lang_ISO in lst_lang:
            translation_file = os.path.join(i18n_path, f"{lang_ISO}.po")

            if not self.env["ir.translation"].search(
                [("lang", "=", lang_local)]
            ):
                with mute_logger("odoo.addons.base.models.ir_translation"):
                    self.env["base.language.install"].create(
                        [{"lang": lang_local, "overwrite": True}]
                    ).lang_install()
                self.env["base.update.translations"].create(
                    [{"lang": lang_local}]
                ).act_update()

            # Load existing translations
            # translations = self.env["ir.translation"].search([
            #     ('lang', '=', lang),
            #     ('module', '=', module_name)
            # ])

            export = self.env["base.language.export"].create(
                [
                    {
                        "lang": lang_local,
                        "format": "po",
                        "modules": [(6, 0, [module_id.id])],
                    }
                ]
            )
            export.act_getfile()
            po_file = export.data
            data = base64.b64decode(po_file).decode("utf-8").strip() + "\n"

            # Special replace for lang fr_CA
            if lang_ISO in ["fr_CA", "fr", "en", "en_CA"]:
                data = data.replace(
                    '"Plural-Forms: \\n"',
                    '"Plural-Forms: nplurals=2; plural=(n > 1);\\n"',
                )

            with open(translation_file, "w") as file:
                file.write(data)

    def copy_missing_file(
        self, module_name, module_path, template_dir, lst_file_extra=None
    ):
        """
        This function will create and copy file into template module.
        :param module_name:
        :param module_path:
        :param template_dir:
        :param lst_file_extra:
        :return:
        """
        # TODO bad conception, this method not suppose to be here, move this before generate code
        module_id = self.env["ir.module.module"].search(
            [("name", "=", module_name), ("state", "=", "installed")]
        )
        if not module_id:
            return

        template_copied_dir = os.path.join(template_dir, "not_supported_files")

        # Copy i18n files
        i18n_po_path = os.path.join(module_path, "i18n", "*.po")
        i18n_pot_path = os.path.join(module_path, "i18n", "*.pot")
        target_i18n_path = os.path.join(template_copied_dir, "i18n")
        lst_file = glob.glob(i18n_po_path) + glob.glob(i18n_pot_path)
        if lst_file:
            code_generator_data.CodeGeneratorData.os_make_dirs(
                target_i18n_path
            )
            for file_name in lst_file:
                shutil.copy(file_name, target_i18n_path)

        # Copy readme file
        readme_file_path = os.path.join(module_path, "README.rst")
        target_readme_file_path = os.path.join(template_copied_dir)
        shutil.copy(readme_file_path, target_readme_file_path)

        # Copy readme dir
        readme_dir_path = os.path.join(module_path, "readme")
        target_readme_dir_path = os.path.join(template_copied_dir, "readme")
        shutil.copytree(readme_dir_path, target_readme_dir_path)

        # Copy tests dir
        tests_dir_path = os.path.join(module_path, "tests")
        target_tests_dir_path = os.path.join(template_copied_dir, "tests")
        shutil.copytree(tests_dir_path, target_tests_dir_path)

        if lst_file_extra:
            for file_extra in lst_file_extra:
                # Special if existing, mail_message_subtype.xml
                mail_data_xml_path = os.path.join(module_path, file_extra)
                target_mail_data_xml_path = os.path.join(
                    template_copied_dir, file_extra
                )
                if os.path.isfile(mail_data_xml_path):
                    code_generator_data.CodeGeneratorData.check_mkdir_and_create(
                        target_mail_data_xml_path
                    )
                    shutil.copy(mail_data_xml_path, target_mail_data_xml_path)

    def _set_manifest_file(self, module):
        """
        Function to set the module manifest file
        :param module:
        :return:
        """

        cg_data = code_generator_data.get_code_generator_data(self.env)
        lang = "en_US"

        cw = CodeWriter()

        has_header = False
        if module.header_manifest:
            lst_header = module.header_manifest.split("\n")
            for line in lst_header:
                s_line = line.strip()
                if s_line:
                    cw.emit(s_line)
                    has_header = True
        if has_header:
            cw.emit()

        with cw.block(delim=("{", "}")):
            cw.emit(f"'name': '{module.shortdesc}',")

            if module.category_id:
                cw.emit(
                    "'category':"
                    f" '{module.category_id.with_context(lang=lang).name}',"
                )

            if module.summary and module.summary != "false":
                cw.emit(f"'summary': '{module.summary}',")

            if module.description:
                description = module.description.strip()
                lst_description = description.split("\n")
                if len(lst_description) == 1:
                    cw.emit(f"'description': '{description}',")
                else:
                    cw.emit("'description': '''")
                    for desc in lst_description:
                        cw.emit_raw(desc)
                    cw.emit("''',")

            if module.installed_version:
                cw.emit(f"'version': '{module.installed_version}',")

            if module.author:
                author = module.author.strip()
                lst_author = author.split(",")
                if len(lst_author) == 1:
                    cw.emit(f"'author': '{author}',")
                else:
                    cw.emit(f"'author': (")
                    with cw.indent():
                        for auth in lst_author[:-1]:
                            s_auth = auth.strip()
                            cw.emit(f"'{s_auth}, '")
                    cw.emit(f"'{lst_author[-1].strip()}'),")

            if module.contributors:
                cw.emit(f"'contributors': '{module.contributors}',")

            # if module.maintener:
            #     cw.emit(f"'maintainers': '{module.maintener}',")

            if module.license != "LGPL-3":
                cw.emit(f"'license': '{module.license}',")

            if module.sequence != 100:
                cw.emit(f"'sequence': {module.sequence},")

            if module.website:
                cw.emit(f"'website': '{module.website}',")

            if module.auto_install:
                cw.emit(f"'auto_install': True,")

            if module.demo:
                cw.emit(f"'demo': True,")

            if module.application:
                cw.emit(f"'application': True,")

            if module.dependencies_id:
                lst_depend = module.dependencies_id.mapped(
                    lambda did: f"'{did.depend_id.name}'"
                )
                lst_depend = sorted(lst_depend)
                # Remove exclude_dependencies_str
                if module.exclude_dependencies_str:
                    lst_exclude_depend = [
                        f"'{a}'"
                        for a in module.exclude_dependencies_str.split(";")
                    ]
                    lst_depend = list(
                        set(lst_depend) - set(lst_exclude_depend)
                    )
                cw.emit_list(
                    lst_depend, ("[", "]"), before="'depends': ", after=","
                )

            if module.external_dependencies_id and [
                a for a in module.external_dependencies_id if not a.is_template
            ]:
                with cw.block(
                    before="'external_dependencies':",
                    delim=("{", "}"),
                    after=",",
                ):
                    dct_depend = defaultdict(list)
                    for depend in module.external_dependencies_id:
                        if depend.is_template:
                            continue
                        dct_depend[depend.application_type].append(
                            f"'{depend.depend}'"
                        )
                    for application_type, lst_value in dct_depend.items():
                        cw.emit_list(
                            lst_value,
                            ("[", "]"),
                            before=f"'{application_type}': ",
                            after=",",
                        )

            lst_data = self._get_l_map(
                lambda dfile: f"'{dfile}'",
                cg_data.lst_manifest_data_files,
            )
            if lst_data:
                cw.emit_list(
                    lst_data, ("[", "]"), before="'data': ", after=","
                )

            if module.assets:
                try:
                    import json

                    dct_assets = json.loads(module.assets)
                    if dct_assets:
                        with cw.block(
                            before="'assets':",
                            delim=("{", "}"),
                            after=",",
                        ):
                            for bundle_name, lst_files in (
                                dct_assets.items()
                            ):
                                lst_quoted = [
                                    f"'{f}'" for f in lst_files
                                ]
                                cw.emit_list(
                                    lst_quoted,
                                    ("[", "]"),
                                    before=f"'{bundle_name}': ",
                                    after=",",
                                )
                except (json.JSONDecodeError, TypeError):
                    _logger.warning(
                        "Invalid JSON in assets field for"
                        " module '%s'",
                        module.name,
                    )

            cw.emit(f"'installable': True,")

            self.set_manifest_file_extra(cw, module)

        manifest_file_path = "__manifest__.py"
        cg_data.write_file_str(manifest_file_path, cw.render())

    def set_manifest_file_extra(self, cw, module):
        pass

    def create(self, vals_list):
        """
        Create log of code generator writer
        :return:
        """
        new_list = []
        for vals in vals_list:
            new_list.append(self.generate_writer(vals))

        return super(CodeGeneratorWriter, self).create(new_list)

    def get_lst_file_generate(self, module, python_controller_writer):
        cg_data = code_generator_data.get_code_generator_data(self.env)

        l_model_csv_access = []
        l_model_rules = []
        dct_model_model_xmldata = {}

        if module.template_model_name or module.template_inherit_model_name:
            lst_model = f"{module.template_model_name};{module.template_inherit_model_name}".strip(
                ";"
            ).split(
                ";"
            )
            lst_unique_model = list(set(lst_model))
            last_extractor_view = None
            last_extractor_view_with_cg = None
            for model in lst_unique_model:
                model = model.strip()
                if model:
                    last_extractor_view = ExtractorView(module, model)
                    cg_data.view_file_sync[model] = last_extractor_view
                    if last_extractor_view.code_generator_id:
                        last_extractor_view_with_cg = last_extractor_view
                    cg_data.module_file_sync[model] = ExtractorModule(
                        module, model, cg_data.view_file_sync[model]
                    )
                    # TODO no need to keep memory
                    ExtractorController(
                        module, model, cg_data.module_file_sync[model]
                    )
            if last_extractor_view_with_cg:
                # TODO this seems an hack to extract menu, need another method
                last_extractor_view_with_cg.parse_menu()

        for model in module.o2m_models:

            model_model = self._get_model_model(model.model)

            if not module.nomenclator_only:
                # Wizard
                self._set_model_py_file(module, model, model_model)
                self._set_model_xmlview_file(module, model, model_model)

                # Report
                self._set_model_xmlreport_file(module, model, model_model)

            parameters = self.env["ir.config_parameter"].sudo()
            s_data2export = parameters.get_param(
                "code_generator.s_data2export", default="nomenclator"
            )
            if s_data2export != "nomenclator" or (
                s_data2export == "nomenclator" and model.nomenclator
            ):
                dct_result_xmldata = self._set_model_xmldata_file(
                    module, model, model_model
                )
                if dct_result_xmldata:
                    dct_model_model_xmldata.update(dct_result_xmldata)

            if not module.nomenclator_only:
                l_model_csv_access += self._get_model_access(module, model)

                l_model_rules += self._get_model_rules(module, model)

        l_model_csv_access = sorted(
            list(set(l_model_csv_access)),
            key=lambda x: x,
        )
        self._compute_xml_data_file(module, dct_model_model_xmldata)
        self._write_xml_data_file(dct_model_model_xmldata)

        if not module.nomenclator_only:
            application_icon = self._set_module_menus(module)

            self.set_xml_data_file(module)

            self.set_xml_views_file(module)

            self.set_module_python_file(module)

            self.set_module_css_file(module)

            self.set_module_js_file(module)

            self._set_module_security(
                module, l_model_rules, l_model_csv_access
            )

            self._set_static_description_file(module, application_icon)

            # TODO info Moved in template module
            # self.set_module_translator(module)

        python_controller_writer.generate()

        self.set_extra_get_lst_file_generate(module)

        cg_data.reorder_manifest_data_files()

        self._set_manifest_file(module)

        self.set_module_init_file_extra(module)

        cg_data.generate_python_init_file(module)

        cg_data.auto_format()
        if module.enable_pylint_check:
            # cg_data.flake8_check()
            cg_data.pylint_check()

    def set_xml_data_file(self, module):
        pass

    def set_xml_views_file(self, module):
        pass

    def set_module_css_file(self, module):
        pass

    def set_module_js_file(self, module):
        pass

    def set_module_python_file(self, module):
        pass

    def set_extra_get_lst_file_generate(self, module):
        pass

    def write_extra_pre_init_hook(self, module, cw):
        # Depend on code_generator_hook
        pass

    def write_extra_post_init_hook(self, module, cw):
        # Depend on code_generator_hook
        if module.list_scss_process_hook:
            lst_scss_process_hook = [
                a.strip() for a in module.list_scss_process_hook.split(";")
            ]
            for scss_process_hook in lst_scss_process_hook:
                cw.emit(f'xml_id = "{scss_process_hook}"')
                cw.emit("update_datas_ir_attachment_from_xmlid(env, xml_id)")
            cw.emit()

    def write_extra_uninstall_hook(self, module, cw):
        # Depend on code_generator_hook
        pass

    def write_extra_extra_function_hook(self, module, cw):
        # Depend on code_generator_hook
        if module.list_scss_process_hook:
            cw.emit("def update_datas_ir_attachment_from_xmlid(env, xml_id):")
            with cw.indent():
                cw.emit(
                    "dir_path ="
                    " os.path.normpath(os.path.join(os.path.dirname(__file__),"
                    ' ".."))'
                )
                cw.emit(
                    'ir_attach_id_name = env["ir.model.data"].search([("name",'
                    ' "=", xml_id)])'
                )
                cw.emit("if not ir_attach_id_name:")
                with cw.indent():
                    cw.emit(
                        """_logger.warning(f"Cannot find ir.attachment id '{xml_id}'")"""
                    )
                    cw.emit("return")
                cw.emit(
                    "ir_attach_id ="
                    ' env["ir.attachment"].browse(ir_attach_id_name.res_id)'
                )
                cw.emit("file_path = dir_path + ir_attach_id.url")
                cw.emit("if not os.path.isfile(file_path):")
                with cw.indent():
                    cw.emit(
                        """_logger.warning(f"File not exist '{file_path}'")"""
                    )
                    cw.emit("return")
                cw.emit(
                    'datas = base64.b64encode(open(file_path, "rb").read())'
                )
                cw.emit('ir_attach_id.write({"datas": datas})')

    def generate_writer(self, vals):
        modules = self.env["code.generator.module"].browse(
            vals.get("code_generator_ids")
        )

        # path = tempfile.gettempdir()
        path = tempfile.mkdtemp()
        _logger.info(f"Temporary path for code generator: {path}")
        morethanone = len(modules.ids) > 1
        if morethanone:
            # TODO validate it's working
            path += "/modules"
            code_generator_data.CodeGeneratorData.os_make_dirs(path)

        # TODO is it necessary? os.chdir into sync_code to be back to normal
        # os.chdir(path=path)

        basename = (
            "modules" if morethanone else modules[0].name.lower().strip()
        )
        vals["basename"] = basename
        rootdir = (
            path
            if morethanone
            else path + "/" + modules[0].name.lower().strip()
        )
        vals["rootdir"] = rootdir

        lst_path_file = []
        # TODO this will crash if generate multiple modules
        for module in modules:
            cg_data = code_generator_data.get_code_generator_data(
                self.env, module, path
            )
            python_controller_writer = PythonControllerWriter(module, cg_data)
            self.get_lst_file_generate(module, python_controller_writer)

            if module.enable_sync_code:
                cg_data.sync_code(module.path_sync_code, module.name)
            lst_path_file.extend(cg_data.lst_path_file)

        vals["list_path_file"] = ";".join(list(set(lst_path_file)))

        return vals

    def get_list_path_file(self):
        return self.list_path_file.split(";")
