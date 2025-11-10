/** @odoo-module **/

import {Component, useState} from "@odoo/owl";
import {Dialog} from "@web/core/dialog/dialog";
import {useService} from "@web/core/utils/hooks";

export class StudioFieldSelector extends Component {
    static template = "code_studio.StudioFieldSelector";
    static components = {Dialog};

    setup() {
        this.rpc = useService("rpc");

        this.state = useState({
            fields: [],
            selectedField: null,
            searchTerm: "",
            isLoading: false,
        });

        this.loadFields();
    }

    async loadFields() {
        this.state.isLoading = true;
        try {
            const result = await this.rpc("/web/dataset/call_kw", {
                model: "studio.field",
                method: "search_read",
                args: [[["studio_model_id", "=", this.props.modelId]]],
                kwargs: {
                    fields: ["name", "field_description", "ttype"],
                },
            });
            this.state.fields = result;
        } catch (error) {
            console.error("Error loading fields:", error);
        } finally {
            this.state.isLoading = false;
        }
    }

    get filteredFields() {
        if (!this.state.searchTerm) {
            return this.state.fields;
        }
        const term = this.state.searchTerm.toLowerCase();
        return this.state.fields.filter(
            (field) => field.name.toLowerCase().includes(term) || field.field_description.toLowerCase().includes(term)
        );
    }

    selectField(field) {
        this.state.selectedField = field;
    }

    confirm() {
        if (this.state.selectedField) {
            this.props.close(this.state.selectedField);
        }
    }

    cancel() {
        this.props.close();
    }
}
