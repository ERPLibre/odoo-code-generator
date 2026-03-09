#!/usr/bin/env python3
# © 2021-2025 TechnoLibre (http://www.technolibre.ca)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

import ast
import base64
import hashlib
import logging
import os
import uuid
from collections import defaultdict

from lxml import etree as ET
from lxml.builder import E
from odoo import models

from .. import code_generator_data
from .code_generator_writer_constants import MAGIC_FIELDS, XML_VERSION_HEADER

_logger = logging.getLogger(__name__)


class CodeGeneratorWriterXmlMixin(models.AbstractModel):
    _name = "code.generator.writer.xml.mixin"
    _description = "Code Generator Writer XML Mixin"

    def _set_model_xmldata_file(self, module, model, model_model):
        """
        Function to set the module data file
        :param module:
        :param model:
        :param model_model:
        :return:
        """

        cg_data = code_generator_data.get_code_generator_data(self.env)

        expression_export_data = model.expression_export_data
        if not expression_export_data:
            search = []
        elif expression_export_data[0] == "[":
            search = ast.literal_eval(expression_export_data)
        else:
            search = [ast.literal_eval(expression_export_data)]
        # Search with active_test to support when active is False
        nomenclador_data = (
            self.env[model.model]
            .sudo()
            .with_context(active_test=False)
            .search(search)
        )
        if not nomenclador_data:
            return

        ignore_name_export_data = model.ignore_name_export_data
        if ignore_name_export_data:
            lst_ignore_name_export_data = ignore_name_export_data.strip(
                ";"
            ).split(";")
            if lst_ignore_name_export_data:
                new_nomenclator_data_list = [
                    a.id
                    for b in lst_ignore_name_export_data
                    for a in nomenclador_data
                    if not a.name.split("/")[-1].endswith(b.strip())
                    and not a.name == b.strip()
                ]
                if len(new_nomenclator_data_list) != len(nomenclador_data):
                    nomenclador_data = self.env[model.model].browse(
                        new_nomenclator_data_list
                    )

        lst_data_xml = []
        lst_id = []
        lst_depend = []
        lst_field_id_blacklist = [
            a.m2o_fields.id
            for a in model.m2o_module.o2m_nomenclator_blacklist_fields
        ]
        lst_field_id_whitelist = [
            a.m2o_fields.id
            for a in model.m2o_module.o2m_nomenclator_whitelist_fields
        ]
        lst_record = []
        lst_new_data_to_write = []
        dct_search_and_replace_in_file = defaultdict(list)
        lst_scss_process_hook = []
        for record in nomenclador_data:
            add_scss_hook = False
            new_data_to_write = None
            force_field_name_xml_id = None
            f2exports = model.field_id.filtered(
                lambda field: field.name not in MAGIC_FIELDS
            ).with_context(lang=None)
            lst_field = []
            lst_end_field = []
            lst_ignore_field_name = []
            for rfield in f2exports:
                # whitelist check
                if (
                    lst_field_id_whitelist
                    and rfield.id not in lst_field_id_whitelist
                ):
                    continue
                # blacklist check
                if rfield.id in lst_field_id_blacklist:
                    continue
                if rfield.name in lst_ignore_field_name:
                    continue
                record_value = getattr(record, rfield.name)
                child = None
                if record_value or (
                    not record_value
                    and rfield.ttype == "boolean"
                    and rfield.default == "True"
                ):
                    delete_node = False
                    if rfield.ttype == "many2one":
                        ref = self._get_ir_model_data(
                            record_value,
                            give_a_default=True,
                            module_name=module.name,
                        )
                        if not ref:
                            # This will cause an error at installation
                            _logger.error(
                                "Cannot find reference for field"
                                f" {rfield.name} model {model_model}"
                            )
                            continue
                        child = E.field({"name": rfield.name, "ref": ref})

                        if "." not in ref:
                            lst_depend.append(ref)

                    elif rfield.ttype == "one2many":
                        # TODO do we need to export one2many relation data, it's better to export many2one
                        # TODO maybe check if many2one is exported or export this one
                        continue
                        # field_eval = ", ".join(
                        #     record_value.mapped(
                        #         lambda rvalue: "(4, ref('%s'))"
                        #         % self._get_ir_model_data(
                        #             rvalue, give_a_default=True, module_name=module.name
                        #         )
                        #     )
                        # )
                        # child = E.field(
                        #     {"name": rfield.name, "eval": f"[{field_eval}]"}
                        # )

                    elif rfield.ttype == "many2many":
                        # TODO add dependencies id in lst_depend
                        field_eval = ", ".join(
                            record_value.mapped(
                                lambda rvalue: "ref(%s)"
                                % self._get_ir_model_data(
                                    rvalue,
                                    give_a_default=True,
                                    module_name=module.name,
                                )
                            )
                        )
                        child = E.field(
                            {
                                "name": rfield.name,
                                "eval": f"[(6,0, [{field_eval}])]",
                            }
                        )

                    elif rfield.ttype == "binary":
                        add_in_search_and_replace_file = False
                        manage_scss = False
                        sub_dir = "img"
                        # Create file if image, else create binary
                        if record.index_content == "image":
                            manage_scss = True
                        elif record.mimetype in ["text/css", "text/scss"]:
                            force_field_name_xml_id = "datas_fname"
                            manage_scss = True
                            sub_dir = "scss"
                        elif (
                            record.mimetype in ["application/octet-stream"]
                            and ".custom." in record.name
                            and record.name.endswith(".scss")
                        ):
                            manage_scss = True
                            add_scss_hook = True
                            add_in_search_and_replace_file = True
                            sub_dir = "scss"
                        # Check record.index_content or record.mimetype
                        if manage_scss:
                            new_filename = (
                                record.datas_fname
                                if not add_scss_hook
                                else record.name.rsplit("/", maxsplit=1)[1]
                            )
                            url_path_file_module = os.path.join(
                                "static",
                                "src",
                                sub_dir,
                                new_filename,
                            )
                            url_path_file = os.path.join(
                                "/",
                                module.name,
                                "static",
                                "src",
                                sub_dir,
                                new_filename,
                            )
                            child_end = E.field({"name": "type"}, "url")
                            lst_end_field.append(child_end)
                            lst_ignore_field_name.append("type")

                            child_end = E.field({"name": "url"}, url_path_file)
                            lst_end_field.append(child_end)
                            lst_ignore_field_name.append("url")

                            new_data_to_write = [
                                record_value,
                                url_path_file_module,
                            ]
                            # decode_record = base64.b64decode(record_value)
                            # cg_data.write_file_binary(
                            #     url_path_file_module,
                            #     decode_record,
                            # )
                            if add_in_search_and_replace_file:
                                pattern_str = (
                                    '<attribute name="href">%s</attribute>'
                                )
                                str_to_search = pattern_str % record.name
                                str_to_replace = pattern_str % url_path_file
                                dct_search_and_replace_in_file[
                                    "data/ir_ui_view.xml"
                                ].append((str_to_search, str_to_replace))
                        else:
                            # Transform binary in string and remove b''
                            child = E.field(
                                {"name": rfield.name},
                                str(record_value)[2:-1],
                            )
                    elif rfield.ttype == "boolean":
                        # Don't show boolean if same value of default
                        if str(record_value) != rfield.default:
                            child = E.field(
                                {"name": rfield.name},
                                str(record_value),
                            )
                        else:
                            delete_node = True
                    elif rfield.related == "view_id.arch" or (
                        rfield.name == "arch" and rfield.model == "ir.ui.view"
                    ):
                        root = ET.fromstring(record_value)
                        child = E.field(
                            {"name": rfield.name, "type": "xml"}, root
                        )

                    else:
                        child = E.field(
                            {"name": rfield.name}, str(record_value)
                        )

                    if not delete_node and child is not None:
                        lst_field.append(child)

            # TODO delete this comment, check why no need anymore rec_name
            # rec_name_v = self._get_from_rec_name(record, model)
            # if rec_name_v:
            #     rec_name_v = self._lower_replace(rec_name_v)
            #     id_record = self._set_limit_4xmlid(f"{model_model}_{rec_name_v}")
            # else:
            #     rec_name_v = uuid.uuid1().int
            id_record = self._get_ir_model_data(
                record,
                give_a_default=True,
                module_name=module.name,
                force_field_name=force_field_name_xml_id,
            )
            lst_id.append(id_record)
            lst_total_field = lst_field + lst_end_field
            record_xml = E.record(
                {"id": id_record, "model": model.model}, *lst_total_field
            )
            lst_data_xml.append(record_xml)
            lst_record.append(record)
            lst_new_data_to_write.append(new_data_to_write)

            if add_scss_hook:
                lst_scss_process_hook.append(id_record)

        # Do xml update for attachment later
        if model_model == "ir_attachment":
            result = ""
        else:
            # TODO find when is noupdate and not noupdate
            # <data noupdate="1">
            # xml_no_update = E.data({"noupdate": "1"}, *lst_data_xml)
            # module_file = E.odoo({}, xml_no_update)
            #
            # result = XML_VERSION_HEADER.encode("utf-8") + ET.tostring(
            #     module_file, pretty_print=True
            # )
            # TODO bug some character is missing, check code_generator_demo_website_attachments_data, use this method instead
            result = (
                XML_VERSION_HEADER.encode("utf-8")
                + b"<odoo>\n"
                + ET.tostring(E.data({"noupdate": "1"}, *lst_data_xml))
                + b"\n</odoo>\n"
            )

        return {
            model_model: [
                result,
                lst_data_xml,
                lst_id,
                lst_depend,
                lst_record,
                lst_new_data_to_write,
                dct_search_and_replace_in_file,
                lst_scss_process_hook,
            ]
        }

    def _compute_xml_data_file(self, module, dct_result):
        if "ir_attachment" in dct_result.keys():
            dct_ir_attachment = dct_result.get("ir_attachment")
            lst_scss_process_hook = dct_ir_attachment[7]
            if lst_scss_process_hook:
                str_scss_process_hook = ";".join(lst_scss_process_hook)
                # self.write({"list_scss_process_hook":str_scss_process_hook})
                module.post_init_hook_show = True
                module.list_scss_process_hook = str_scss_process_hook
                module.hook_constant_code = """import logging
import base64
_logger = logging.getLogger(__name__)"""

        # filter ir_attachment with ir_ui_view from website export data
        if (
            "website_page" not in dct_result.keys()
            or "ir_attachment" not in dct_result.keys()
            or "ir_ui_view" not in dct_result.keys()
        ):
            return
        # lst_attach_image_index_keep = []
        dct_replace_view = {}
        lst_attachment_id_to_keep = []
        lst_attachment_id_check = []
        result_view = dct_result.get("ir_ui_view")[0]
        lst_view_id = dct_result.get("ir_ui_view")[4]
        lst_ele_attach_xml = dct_ir_attachment[1]
        lst_attach_xml_id = dct_ir_attachment[2]
        lst_attach_id = dct_ir_attachment[4]
        lst_new_data_to_write = dct_ir_attachment[5]
        dct_associate_duplicate_attach_id = {}  # ref to master
        dct_associate_duplicate_attach_id_index = {}  # ref to master
        lst_attachment_id_index_has_rename = []

        # TODO do algorithme to detect duplicate image reference. To test it, upload 2 same image and add it in html
        # Detect duplicate and create association with master
        if module.export_website_optimize_binary_image:
            i = -1
            for attach_id in lst_attach_id:
                i += 1
                for i_attach, attach_id_iter in enumerate(lst_attach_id):
                    if i_attach == i:
                        # same file...
                        continue

                    if (
                        i not in dct_associate_duplicate_attach_id_index.keys()
                        and attach_id.datas_fname == attach_id_iter.datas_fname
                    ):
                        if attach_id.datas == attach_id_iter.datas:
                            dct_associate_duplicate_attach_id[
                                attach_id_iter.id
                            ] = attach_id.id
                            dct_associate_duplicate_attach_id_index[
                                i_attach
                            ] = i
                        else:
                            # Support rename for picture, the name is the same, but it's a different picture
                            new_data_to_write = lst_new_data_to_write[i_attach]
                            if (
                                new_data_to_write
                                and attach_id_iter.index_content == "image"
                                and i_attach
                                not in lst_attachment_id_index_has_rename
                            ):
                                (
                                    record_value,
                                    url_path_file_module,
                                ) = new_data_to_write
                                unique_str = hashlib.md5(
                                    str(i_attach).encode("utf-8")
                                ).hexdigest()[:6]

                                new_data_to_write[1] = (
                                    self.rename_filename_with_uuid(
                                        url_path_file_module, unique_str
                                    )
                                )

                                element = ET.tostring(
                                    lst_ele_attach_xml[i_attach]
                                ).decode("utf-8")
                                new_name = self.rename_filename_with_uuid(
                                    attach_id.name, unique_str
                                )
                                new_datas_fname = (
                                    self.rename_filename_with_uuid(
                                        attach_id.datas_fname, unique_str
                                    )
                                )
                                new_element = element.replace(
                                    attach_id.name, new_name
                                ).replace(
                                    attach_id.datas_fname, new_datas_fname
                                )
                                lst_ele_attach_xml[i_attach] = ET.fromstring(
                                    new_element
                                )
                                lst_attachment_id_index_has_rename.append(
                                    i_attach
                                )

        # Detect /web/image/ in views, change attachment_id.id to his xml_id
        for view_id in lst_view_id:
            str_view = view_id.arch
            iter_find = self.findall("/web/image/", str_view)
            lst_find = list(iter_find)
            for index in lst_find:
                preview_char_find = str_view[index - 1]
                if preview_char_find == '"':
                    keyword_str = '"'
                elif preview_char_find == ";":
                    # extract &quot;
                    if index > 6 and str_view[index - 6 : index] == "&quot;":
                        keyword_str = "&quot;"
                    else:
                        _logger.warning(
                            "Cannot extract /web/image/ in view name"
                            f" {view_id.name},"
                            f" ...'{str_view[index-30:index+30]}'..."
                        )
                        continue
                else:
                    _logger.warning(
                        "Cannot extract /web/image/ in view name"
                        f" {view_id.name},"
                        f" ...'{str_view[index-30:index+30]}'..."
                    )
                    continue
                # TODO this will not work if the filename include the keyword_str, need to detect it
                last_index = view_id.arch.find(keyword_str, index + 1)
                attach_link = view_id.arch[index:last_index]
                if attach_link.count("/") != 4:
                    _logger.warning(
                        f"Not support attach_link web/image of '{attach_link}'"
                    )
                    continue
                lst_attach = attach_link.split("/")
                i_attach_id = lst_attach[3]
                if i_attach_id.isdigit():
                    i_attach_id = int(i_attach_id)
                else:
                    # Support only id
                    _logger.warning(f"Ignore attach_link '{attach_link}'")
                    continue
                # Ignore processing if already got this information
                if i_attach_id in lst_attachment_id_check:
                    continue
                lst_attachment_id_check.append(i_attach_id)
                # Search this picture if exist
                i = -1
                for attach_id in lst_attach_id:
                    i += 1
                    if attach_id.id == i_attach_id:
                        # lst_attach_image_index_keep.append(i)
                        break
                else:
                    _logger.warning(
                        f"Not found attachment for attach_link '{attach_link}'"
                        f" into {view_id.name}"
                    )
                    continue
                if (
                    module.export_website_optimize_binary_image
                    and i in dct_associate_duplicate_attach_id_index.keys()
                ):
                    # change link, to the master
                    new_i = dct_associate_duplicate_attach_id_index[i]
                    new_i_attach_id = dct_associate_duplicate_attach_id[
                        i_attach_id
                    ]
                else:
                    new_i = i
                    new_i_attach_id = i_attach_id

                # Rewrite link
                xml_id_link = f"{module.name}.{lst_attach_xml_id[new_i]}"
                new_lst_attach = lst_attach[:]
                new_lst_attach[3] = xml_id_link
                new_attach_link = "/".join(new_lst_attach)
                dct_replace_view[attach_link] = new_attach_link
                if new_i_attach_id not in lst_attachment_id_to_keep:
                    lst_attachment_id_to_keep.append(new_i_attach_id)

        # Replace all link
        if dct_replace_view:
            str_result_view = result_view.decode("utf-8")
            for attach_link, new_attach_link in dct_replace_view.items():
                str_result_view = str_result_view.replace(
                    attach_link, new_attach_link
                )
            dct_result.get("ir_ui_view")[0] = str_result_view.encode("utf-8")

        # Remove unused image, missing from /web/image/ link
        if module.export_website_optimize_binary_image:
            lst_index_to_delete = []
            i = -1
            for attach_id in lst_attach_id:
                i += 1
                if (
                    attach_id.id in lst_attachment_id_to_keep
                    or attach_id.index_content != "image"
                ):
                    continue
                lst_index_to_delete.append(i)
            # Add slave attachment in the list
            for slave_index in dct_associate_duplicate_attach_id_index:
                if slave_index not in lst_index_to_delete:
                    lst_index_to_delete.append(slave_index)
            lst_index_to_delete.sort(reverse=True)
            for index_to_delete in lst_index_to_delete:
                attach_id = lst_attach_id[index_to_delete]
                attach_xml_id = lst_attach_xml_id[index_to_delete]
                _logger.info(
                    "Ignore export attachment id"
                    f" {attach_id.id} '{attach_id.datas_fname}', xml_id"
                    f" '{attach_xml_id}'."
                )
                dct_ir_attachment[1].pop(index_to_delete)
                dct_ir_attachment[2].pop(index_to_delete)
                dct_ir_attachment[4].pop(index_to_delete)
                dct_ir_attachment[5].pop(index_to_delete)

    @staticmethod
    def findall(p, s):
        """Yields all the positions of
        the pattern p in the string s."""
        i = s.find(p)
        while i != -1:
            yield i
            i = s.find(p, i + 1)

    @staticmethod
    def rename_filename_with_uuid(name, s_uuid):
        if "." in name:
            lst_new_name = name.rsplit(".", maxsplit=1)
            new_url_path = f"{lst_new_name[0]}_{s_uuid}.{lst_new_name[1]}"
        else:
            new_url_path = f"{name}_{s_uuid}"
        return new_url_path

    def _write_xml_data_file(self, dct_result):
        cg_data = code_generator_data.get_code_generator_data(self.env)
        dct_search_and_replace_in_file_global = defaultdict(list)
        for model_model, tpl_result in dct_result.items():
            (
                result,
                lst_data_xml,
                lst_id,
                lst_depend,
                lst_record,
                lst_new_data_to_write,
                dct_search_and_replace_in_file,
                lst_scss_process_hook,
            ) = tpl_result
            if dct_search_and_replace_in_file:
                for (
                    file_name,
                    lst_value,
                ) in dct_search_and_replace_in_file.items():
                    dct_search_and_replace_in_file_global[file_name].extend(
                        lst_value
                    )
        for model_model, tpl_result in dct_result.items():
            (
                result,
                lst_data_xml,
                lst_id,
                lst_depend,
                lst_record,
                lst_new_data_to_write,
                dct_search_and_replace_in_file,
                lst_scss_process_hook,
            ) = tpl_result
            if not any(tpl_result):
                # it's empty
                continue
            data_file_path = os.path.join(
                cg_data.data_path, f"{model_model}.xml"
            )

            for new_data_to_write in lst_new_data_to_write:
                if not new_data_to_write:
                    continue
                record_value, url_path_file_module = new_data_to_write
                decode_record = base64.b64decode(record_value)
                cg_data.write_file_binary(
                    url_path_file_module,
                    decode_record,
                )

            if not result:
                # Need to recompute the result
                # TODO find when is noupdate and not noupdate
                # <data noupdate="1">
                xml_no_update = E.data({"noupdate": "1"}, *lst_data_xml)
                module_file = E.odoo({}, xml_no_update)

                new_result = XML_VERSION_HEADER.encode("utf-8") + ET.tostring(
                    module_file, pretty_print=True
                )
            else:
                new_result = result
            lst_to_replace = dct_search_and_replace_in_file_global.get(
                data_file_path
            )
            if lst_to_replace:
                for str_search, str_replace in lst_to_replace:
                    new_result = new_result.replace(
                        str_search.encode(), str_replace.encode()
                    )

            cg_data.write_file_binary(
                data_file_path, new_result, data_file=True
            )

            abs_path_file = os.path.join("data", f"{model_model}.xml")

            cg_data.dct_data_metadata_file[abs_path_file] = lst_id
            if lst_depend:
                cg_data.dct_data_depend[abs_path_file] = lst_depend

    @staticmethod
    def _setup_xml_indent(content, indent=0, is_end=False):
        # return "\n".join([f"{'    ' * indent}{a}" for a in content.split("\n")])
        str_content = content.rstrip().replace("\n", f"\n{'  ' * indent}")
        super_content = f"\n{'  ' * indent}{str_content}"
        if is_end:
            super_content += f"\n{'  ' * 1}"
        else:
            super_content += f"\n{'  ' * (indent - 1)}"
        return super_content

    @staticmethod
    def _change_xml_2_to_4_spaces(content):
        new_content = ""
        # Change 2 space for 4 space
        for line in content.split("\n"):
            # count first space
            if line.strip():
                new_content += f'{"  " * (len(line) - len(line.lstrip()))}{line.strip()}\n'
            else:
                new_content += "\n"
        return new_content
