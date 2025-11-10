/** @odoo-module **/

import {registry} from "@web/core/registry";
import {Component, useState, onWillStart} from "@odoo/owl";
import {useService} from "@web/core/utils/hooks";
import {StudioSidebar} from "./studio_sidebar";
import {StudioViewEditor} from "./studio_view_editor";

export class StudioEditor extends Component {
    static template = "code_studio.StudioEditor";
    static components = {StudioSidebar, StudioViewEditor};

    setup() {
        this.rpc = useService("rpc");
        this.action = useService("action");
        this.notification = useService("notification");

        this.state = useState({
            mode: "edit", // edit, preview
            currentView: null,
            currentModel: null,
            selectedElement: null,
            isDragging: false,
            isLoading: false,
        });

        onWillStart(async () => {
            await this.loadStudioData();
        });
    }

    async loadStudioData() {
        this.state.isLoading = true;
        try {
            const modelId = this.props.action.context.studio_model_id;
            if (modelId) {
                const result = await this.rpc("/web/dataset/call_kw", {
                    model: "studio.model",
                    method: "read",
                    args: [[modelId]],
                    kwargs: {},
                });
                this.state.currentModel = result[0];
            }
        } catch (error) {
            this.notification.add("Error loading studio data", {type: "danger"});
        } finally {
            this.state.isLoading = false;
        }
    }

    toggleMode() {
        this.state.mode = this.state.mode === "edit" ? "preview" : "edit";
    }

    async saveChanges() {
        this.state.isLoading = true;
        try {
            // Save current view changes
            if (this.state.currentView) {
                await this.rpc("/web/dataset/call_kw", {
                    model: "studio.view",
                    method: "write",
                    args: [
                        [this.state.currentView.id],
                        {
                            arch_studio: this.state.currentView.arch_studio,
                        },
                    ],
                    kwargs: {},
                });
            }

            this.notification.add("Changes saved successfully", {type: "success"});
        } catch (error) {
            this.notification.add("Error saving changes", {type: "danger"});
        } finally {
            this.state.isLoading = false;
        }
    }

    exitStudio() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: this.state.currentModel.name,
            view_mode: "list,form",
            target: "current",
        });
    }
}

registry.category("actions").add("studio_editor", StudioEditor);
