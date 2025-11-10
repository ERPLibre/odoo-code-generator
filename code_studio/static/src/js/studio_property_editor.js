/** @odoo-module **/

import {Component, useState, onWillStart, onWillUpdateProps} from "@odoo/owl";
import {useService} from "@web/core/utils/hooks";
import {_t} from "@web/core/l10n/translation";
import {Dialog} from "@web/core/dialog/dialog";
import {SelectCreateDialog} from "@web/views/view_dialogs/select_create_dialog";

export class StudioPropertyEditor extends Component {
    static template = "code_studio.PropertyEditor";
    static props = {
        element: {type: Object, optional: true},
        elementType: {type: String},
        onSave: {type: Function},
        onDelete: {type: Function, optional: true},
        close: {type: Function},
    };

    setup() {
        this.orm = useService("orm");
        this.dialog = useService("dialog");
        this.notification = useService("notification");

        this.state = useState({
            properties: {},
            availableFields: [],
            availableModels: [],
            selectionValues: [],
            isLoading: true,
            errors: {},
        });

        onWillStart(() => this.loadInitialData());
        onWillUpdateProps((nextProps) => {
            if (nextProps.element !== this.props.element) {
                this.loadElementProperties(nextProps.element);
            }
        });
    }

    async loadInitialData() {
        try {
            await Promise.all([
                this.loadElementProperties(this.props.element),
                this.loadAvailableFields(),
                this.loadAvailableModels(),
            ]);
        } catch (error) {
            this.notification.add(_t("Error loading property editor"), {
                type: "danger",
            });
        } finally {
            this.state.isLoading = false;
        }
    }

    async loadElementProperties(element) {
        if (!element) {
            this.state.properties = this.getDefaultProperties();
            return;
        }

        // Load properties based on element type
        switch (this.props.elementType) {
            case "field":
                this.state.properties = {
                    name: element.name || "",
                    string: element.string || "",
                    type: element.type || "char",
                    required: element.required || false,
                    readonly: element.readonly || false,
                    invisible: element.invisible || false,
                    help: element.help || "",
                    placeholder: element.placeholder || "",
                    widget: element.widget || "",
                    domain: element.domain || "",
                    context: element.context || "{}",
                    options: element.options || "{}",
                };
                break;
            case "button":
                this.state.properties = {
                    name: element.name || "",
                    string: element.string || "",
                    type: element.type || "object",
                    icon: element.icon || "",
                    class: element.class || "btn-primary",
                    invisible: element.invisible || false,
                    confirm: element.confirm || "",
                    context: element.context || "{}",
                };
                break;
            case "group":
                this.state.properties = {
                    string: element.string || "",
                    col: element.col || "2",
                    colspan: element.colspan || "2",
                    invisible: element.invisible || false,
                };
                break;
            case "notebook":
                this.state.properties = {
                    invisible: element.invisible || false,
                };
                break;
            case "page":
                this.state.properties = {
                    string: element.string || "",
                    invisible: element.invisible || false,
                };
                break;
            default:
                this.state.properties = {...element};
        }
    }

    getDefaultProperties() {
        switch (this.props.elementType) {
            case "field":
                return {
                    name: "",
                    string: "",
                    type: "char",
                    required: false,
                    readonly: false,
                    invisible: false,
                    help: "",
                };
            case "button":
                return {
                    name: "",
                    string: "",
                    type: "object",
                    icon: "",
                    class: "btn-primary",
                };
            case "group":
                return {
                    string: "",
                    col: "2",
                    colspan: "2",
                };
            default:
                return {};
        }
    }

    async loadAvailableFields() {
        if (this.props.elementType !== "field") return;

        const modelName = this.env.model || "studio.model";
        const fields = await this.orm.call(modelName, "fields_get");

        this.state.availableFields = Object.entries(fields).map(([name, field]) => ({
            id: name,
            name: name,
            string: field.string,
            type: field.type,
        }));
    }

    async loadAvailableModels() {
        const models = await this.orm.searchRead("ir.model", [], ["model", "name"], {limit: 100, order: "name"});

        this.state.availableModels = models.map((model) => ({
            id: model.model,
            name: model.name,
            model: model.model,
        }));
    }

    validateProperties() {
        const errors = {};

        if (this.props.elementType === "field" && !this.state.properties.name) {
            errors.name = _t("Field name is required");
        }

        if (!this.state.properties.string) {
            errors.string = _t("Label is required");
        }

        // Validate domain
        if (this.state.properties.domain) {
            try {
                JSON.parse(this.state.properties.domain || "[]");
            } catch (e) {
                errors.domain = _t("Invalid domain format");
            }
        }

        // Validate context
        if (this.state.properties.context) {
            try {
                JSON.parse(this.state.properties.context || "{}");
            } catch (e) {
                errors.context = _t("Invalid context format");
            }
        }

        this.state.errors = errors;
        return Object.keys(errors).length === 0;
    }

    async saveProperties() {
        if (!this.validateProperties()) {
            return;
        }

        try {
            await this.props.onSave(this.state.properties);
            this.notification.add(_t("Properties saved successfully"), {
                type: "success",
            });
            this.props.close();
        } catch (error) {
            this.notification.add(_t("Error saving properties"), {
                type: "danger",
            });
        }
    }

    deleteElement() {
        this.dialog.add(ConfirmationDialog, {
            body: _t("Are you sure you want to delete this element?"),
            confirm: async () => {
                try {
                    await this.props.onDelete();
                    this.props.close();
                } catch (error) {
                    this.notification.add(_t("Error deleting element"), {
                        type: "danger",
                    });
                }
            },
        });
    }

    onPropertyChange(property, value) {
        this.state.properties[property] = value;

        // Special handling for field type changes
        if (property === "type" && this.props.elementType === "field") {
            this.updateFieldTypeDefaults(value);
        }
    }

    updateFieldTypeDefaults(fieldType) {
        switch (fieldType) {
            case "selection":
                if (!this.state.properties.selection) {
                    this.state.selectionValues = [
                        {value: "draft", string: "Draft"},
                        {value: "done", string: "Done"},
                    ];
                }
                break;
            case "many2one":
            case "many2many":
            case "one2many":
                if (!this.state.properties.relation) {
                    this.state.properties.relation = "";
                }
                break;
        }
    }

    addSelectionValue() {
        this.state.selectionValues.push({
            value: "",
            string: "",
        });
    }

    removeSelectionValue(index) {
        this.state.selectionValues.splice(index, 1);
    }

    updateSelectionValue(index, field, value) {
        this.state.selectionValues[index][field] = value;
    }

    selectRelationModel() {
        this.dialog.add(SelectCreateDialog, {
            resModel: "ir.model",
            title: _t("Select Related Model"),
            noCreate: true,
            multiSelect: false,
            onSelected: (records) => {
                if (records.length) {
                    this.state.properties.relation = records[0].model;
                }
            },
        });
    }

    getFieldTypeOptions() {
        return [
            {value: "char", label: _t("Text")},
            {value: "text", label: _t("Multiline Text")},
            {value: "html", label: _t("HTML")},
            {value: "integer", label: _t("Integer")},
            {value: "float", label: _t("Float")},
            {value: "monetary", label: _t("Monetary")},
            {value: "boolean", label: _t("Boolean")},
            {value: "date", label: _t("Date")},
            {value: "datetime", label: _t("Datetime")},
            {value: "selection", label: _t("Selection")},
            {value: "many2one", label: _t("Many2one")},
            {value: "one2many", label: _t("One2many")},
            {value: "many2many", label: _t("Many2many")},
            {value: "binary", label: _t("Binary")},
        ];
    }

    getButtonTypeOptions() {
        return [
            {value: "object", label: _t("Object")},
            {value: "action", label: _t("Action")},
        ];
    }

    getButtonClassOptions() {
        return [
            {value: "btn-primary", label: _t("Primary")},
            {value: "btn-secondary", label: _t("Secondary")},
            {value: "btn-success", label: _t("Success")},
            {value: "btn-danger", label: _t("Danger")},
            {value: "btn-warning", label: _t("Warning")},
            {value: "btn-info", label: _t("Info")},
            {value: "btn-link", label: _t("Link")},
        ];
    }
}

// Property Editor Template
StudioPropertyEditor.template = /* xml */ `
<Dialog size="'md'" title="'Edit Properties'" t-on-close="props.close">
    <div class="o_studio_property_editor">
        <div t-if="state.isLoading" class="text-center p-5">
            <i class="fa fa-spinner fa-spin fa-3x"/>
        </div>

        <div t-else="" class="o_form_sheet">
            <!-- Field Properties -->
            <div t-if="props.elementType === 'field'">
                <group>
                    <group>
                        <label for="name">Technical Name</label>
                        <input type="text" class="o_input" id="name"
                               t-model="state.properties.name"
                               t-att-class="{'is-invalid': state.errors.name}"
                               placeholder="x_field_name"/>
                        <div t-if="state.errors.name" class="invalid-feedback" t-esc="state.errors.name"/>

                        <label for="string">Label</label>
                        <input type="text" class="o_input" id="string"
                               t-model="state.properties.string"
                               t-att-class="{'is-invalid': state.errors.string}"/>
                        <div t-if="state.errors.string" class="invalid-feedback" t-esc="state.errors.string"/>

                        <label for="type">Field Type</label>
                        <select class="o_input" id="type" t-model="state.properties.type">
                            <t t-foreach="getFieldTypeOptions()" t-as="option" t-key="option.value">
                                <option t-att-value="option.value" t-esc="option.label"/>
                            </t>
                        </select>
                    </group>

                    <group>
                        <label class="o_form_label">
                            <input type="checkbox" t-model="state.properties.required"/>
                            Required
                        </label>

                        <label class="o_form_label">
                            <input type="checkbox" t-model="state.properties.readonly"/>
                            Readonly
                        </label>

                        <label class="o_form_label">
                            <input type="checkbox" t-model="state.properties.invisible"/>
                            Invisible
                        </label>
                    </group>
                </group>

                <!-- Selection Values -->
                <div t-if="state.properties.type === 'selection'" class="mt-3">
                    <label>Selection Values</label>
                    <div class="o_list_view">
                        <table class="o_list_table table table-sm">
                            <thead>
                                <tr>
                                    <th>Value</th>
                                    <th>Label</th>
                                    <th width="50"/>
                                </tr>
                            </thead>
                            <tbody>
                                <tr t-foreach="state.selectionValues" t-as="sel" t-key="sel_index">
                                    <td>
                                        <input type="text" class="o_input"
                                               t-model="sel.value"
                                               t-on-change="() => updateSelectionValue(sel_index, 'value', sel.value)"/>
                                    </td>
                                    <td>
                                        <input type="text" class="o_input"
                                               t-model="sel.string"
                                               t-on-change="() => updateSelectionValue(sel_index, 'string', sel.string)"/>
                                    </td>
                                    <td>
                                        <button class="btn btn-sm btn-danger"
                                                t-on-click="() => removeSelectionValue(sel_index)">
                                            <i class="fa fa-trash"/>
                                        </button>
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                        <button class="btn btn-link" t-on-click="addSelectionValue">
                            <i class="fa fa-plus"/> Add Value
                        </button>
                    </div>
                </div>

                <!-- Relational Fields -->
                <div t-if="state.properties.type in ['many2one', 'one2many', 'many2many']" class="mt-3">
                    <group>
                        <label for="relation">Related Model</label>
                        <div class="o_row">
                            <input type="text" class="o_input" id="relation"
                                   t-model="state.properties.relation" readonly=""/>
                            <button class="btn btn-secondary" t-on-click="selectRelationModel">
                                <i class="fa fa-search"/> Select
                            </button>
                        </div>

                        <label for="domain" t-if="state.properties.type !== 'one2many'">Domain</label>
                        <input type="text" class="o_input" id="domain"
                               t-model="state.properties.domain"
                               t-att-class="{'is-invalid': state.errors.domain}"
                               placeholder="[]"
                               t-if="state.properties.type !== 'one2many'"/>
                        <div t-if="state.errors.domain" class="invalid-feedback" t-esc="state.errors.domain"/>
                    </group>
                </div>

                <group>
                    <label for="help">Help Text</label>
                    <textarea class="o_input" id="help" rows="3" t-model="state.properties.help"/>

                    <label for="placeholder">Placeholder</label>
                    <input type="text" class="o_input" id="placeholder" t-model="state.properties.placeholder"/>
                </group>
            </div>

            <!-- Button Properties -->
            <div t-if="props.elementType === 'button'">
                <group>
                    <group>
                        <label for="name">Method Name</label>
                        <input type="text" class="o_input" id="name"
                               t-model="state.properties.name"
                               placeholder="action_do_something"/>

                        <label for="string">Label</label>
                        <input type="text" class="o_input" id="string"
                               t-model="state.properties.string"
                               t-att-class="{'is-invalid': state.errors.string}"/>

                        <label for="type">Button Type</label>
                        <select class="o_input" id="type" t-model="state.properties.type">
                            <t t-foreach="getButtonTypeOptions()" t-as="option" t-key="option.value">
                                <option t-att-value="option.value" t-esc="option.label"/>
                            </t>
                        </select>
                    </group>

                    <group>
                        <label for="icon">Icon</label>
                        <input type="text" class="o_input" id="icon"
                               t-model="state.properties.icon"
                               placeholder="fa-check"/>

                        <label for="class">Style</label>
                        <select class="o_input" id="class" t-model="state.properties.class">
                            <t t-foreach="getButtonClassOptions()" t-as="option" t-key="option.value">
                                <option t-att-value="option.value" t-esc="option.label"/>
                            </t>
                        </select>

                        <label class="o_form_label">
                            <input type="checkbox" t-model="state.properties.invisible"/>
                            Invisible
                        </label>
                    </group>
                </group>

                <group>
                    <label for="confirm">Confirmation Message</label>
                    <input type="text" class="o_input" id="confirm"
                           t-model="state.properties.confirm"
                           placeholder="Are you sure?"/>
                </group>
            </div>

            <!-- Group Properties -->
            <div t-if="props.elementType === 'group'">
                <group>
                    <label for="string">Label</label>
                    <input type="text" class="o_input" id="string" t-model="state.properties.string"/>

                    <label for="col">Columns</label>
                    <input type="number" class="o_input" id="col" t-model="state.properties.col" min="1" max="4"/>

                    <label for="colspan">Column Span</label>
                    <input type="number" class="o_input" id="colspan" t-model="state.properties.colspan" min="1" max="4"/>

                    <label class="o_form_label">
                        <input type="checkbox" t-model="state.properties.invisible"/>
                        Invisible
                    </label>
                </group>
            </div>

            <!-- Page Properties -->
            <div t-if="props.elementType === 'page'">
                <group>
                    <label for="string">Tab Title</label>
                    <input type="text" class="o_input" id="string"
                           t-model="state.properties.string"
                           t-att-class="{'is-invalid': state.errors.string}"/>

                    <label class="o_form_label">
                        <input type="checkbox" t-model="state.properties.invisible"/>
                        Invisible
                    </label>
                </group>
            </div>

            <!-- Advanced Properties -->
            <notebook>
                <page string="Advanced" name="advanced">
                    <group>
                        <label for="context">Context</label>
                        <input type="text" class="o_input" id="context"
                               t-model="state.properties.context"
                               t-att-class="{'is-invalid': state.errors.context}"
                               placeholder="{}"/>
                        <div t-if="state.errors.context" class="invalid-feedback" t-esc="state.errors.context"/>

                        <label for="options" t-if="props.elementType === 'field'">Widget Options</label>
                        <input type="text" class="o_input" id="options"
                               t-model="state.properties.options"
                               placeholder="{}"
                               t-if="props.elementType === 'field'"/>

                        <label for="widget" t-if="props.elementType === 'field'">Widget</label>
                        <input type="text" class="o_input" id="widget"
                               t-model="state.properties.widget"
                               placeholder="e.g., many2many_tags"
                               t-if="props.elementType === 'field'"/>
                    </group>
                </page>
            </notebook>
        </div>
    </div>

    <t t-set-slot="footer">
        <button class="btn btn-primary" t-on-click="saveProperties">Save</button>
        <button class="btn btn-secondary" t-on-click="props.close">Cancel</button>
        <button t-if="props.onDelete" class="btn btn-danger float-start" t-on-click="deleteElement">Delete</button>
    </t>
</Dialog>
`;

export class ConfirmationDialog extends Component {
    static template = "code_studio.ConfirmationDialog";
    static components = {Dialog};
    static props = {
        body: String,
        confirm: Function,
        cancel: {type: Function, optional: true},
        close: Function,
    };
}

ConfirmationDialog.template = /* xml */ `
<Dialog title="'Confirm'" size="'sm'" t-on-close="props.close">
    <div t-esc="props.body"/>
    <t t-set-slot="footer">
        <button class="btn btn-primary" t-on-click="() => { props.confirm(); props.close(); }">Confirm</button>
        <button class="btn btn-secondary" t-on-click="props.close">Cancel</button>
    </t>
</Dialog>
`;
