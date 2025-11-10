/** @odoo-module **/

import {Component, useState} from "@odoo/owl";
import {Dropdown} from "@web/core/dropdown/dropdown";
import {DropdownItem} from "@web/core/dropdown/dropdown_item";

export class StudioSidebar extends Component {
    static template = "code_studio.StudioSidebar";
    static components = {Dropdown, DropdownItem};

    setup() {
        this.state = useState({
            activeTab: "add", // add, properties, view
            searchTerm: "",
        });

        this.availableWidgets = [
            {type: "field", label: "Field", icon: "fa-tag"},
            {type: "group", label: "Group", icon: "fa-object-group"},
            {type: "notebook", label: "Notebook", icon: "fa-book"},
            {type: "page", label: "Page", icon: "fa-file"},
            {type: "button", label: "Button", icon: "fa-square"},
            {type: "separator", label: "Separator", icon: "fa-minus"},
            {type: "label", label: "Label", icon: "fa-font"},
            {type: "html", label: "HTML", icon: "fa-code"},
        ];

        this.fieldTypes = [
            {value: "char", label: "Text"},
            {value: "text", label: "Multiline Text"},
            {value: "html", label: "HTML"},
            {value: "integer", label: "Integer"},
            {value: "float", label: "Float"},
            {value: "monetary", label: "Monetary"},
            {value: "boolean", label: "Checkbox"},
            {value: "date", label: "Date"},
            {value: "datetime", label: "Date & Time"},
            {value: "selection", label: "Selection"},
            {value: "many2one", label: "Many2One"},
            {value: "one2many", label: "One2Many"},
            {value: "many2many", label: "Many2Many"},
            {value: "binary", label: "File"},
        ];
    }

    get filteredWidgets() {
        if (!this.state.searchTerm) {
            return this.availableWidgets;
        }
        const term = this.state.searchTerm.toLowerCase();
        return this.availableWidgets.filter((widget) => widget.label.toLowerCase().includes(term));
    }

    selectTab(tab) {
        this.state.activeTab = tab;
    }

    onDragStart(ev, widget) {
        ev.dataTransfer.effectAllowed = "copy";
        ev.dataTransfer.setData("widget-type", widget.type);
        this.props.onDragStart(widget);
    }

    async createNewField() {
        // Open field creation dialog
        const result = await this.env.services.dialog.add(FieldCreationDialog, {
            fieldTypes: this.fieldTypes,
            modelId: this.props.currentModel.id,
        });

        if (result) {
            // Refresh fields list
            this.props.onFieldCreated(result);
        }
    }
}
