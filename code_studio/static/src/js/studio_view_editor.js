/** @odoo-module **/

import {Component, useState, useRef, onMounted} from "@odoo/owl";
import {useService} from "@web/core/utils/hooks";

export class StudioViewEditor extends Component {
    static template = "code_studio.StudioViewEditor";

    setup() {
        this.rpc = useService("rpc");
        this.notification = useService("notification");
        this.viewRef = useRef("viewContainer");

        this.state = useState({
            viewArch: "",
            selectedElement: null,
            hoveredElement: null,
            dropZones: [],
        });

        onMounted(() => {
            this.initializeEditor();
        });
    }

    initializeEditor() {
        if (this.props.currentView) {
            this.state.viewArch = this.props.currentView.arch_base;
            this.renderView();
        }
    }

    renderView() {
        const container = this.viewRef.el;
        container.innerHTML = this.state.viewArch;

        // Add studio editing capabilities
        this.addStudioListeners(container);
        this.highlightDropZones();
    }

    addStudioListeners(container) {
        // Add click handlers to all elements
        const elements = container.querySelectorAll("*");
        elements.forEach((el) => {
            el.addEventListener("click", (ev) => {
                ev.stopPropagation();
                this.selectElement(el);
            });

            el.addEventListener("mouseenter", () => {
                this.state.hoveredElement = el;
                el.classList.add("studio-hover");
            });

            el.addEventListener("mouseleave", () => {
                this.state.hoveredElement = null;
                el.classList.remove("studio-hover");
            });
        });
    }

    highlightDropZones() {
        const container = this.viewRef.el;
        const dropZones = container.querySelectorAll("group, sheet, notebook, page, div.oe_chatter");

        dropZones.forEach((zone) => {
            zone.classList.add("studio-drop-zone");

            zone.addEventListener("dragover", (ev) => {
                ev.preventDefault();
                ev.dataTransfer.dropEffect = "copy";
                zone.classList.add("studio-drop-active");
            });

            zone.addEventListener("dragleave", () => {
                zone.classList.remove("studio-drop-active");
            });

            zone.addEventListener("drop", (ev) => {
                ev.preventDefault();
                zone.classList.remove("studio-drop-active");
                this.handleDrop(ev, zone);
            });
        });
    }

    selectElement(element) {
        // Remove previous selection
        if (this.state.selectedElement) {
            this.state.selectedElement.classList.remove("studio-selected");
        }

        // Add new selection
        this.state.selectedElement = element;
        element.classList.add("studio-selected");

        // Notify parent component
        this.props.onElementSelected(element);
    }

    async handleDrop(ev, dropZone) {
        const widgetType = ev.dataTransfer.getData("widget-type");

        if (widgetType === "field") {
            // Show field selector
            const field = await this.selectField();
            if (field) {
                this.insertField(dropZone, field);
            }
        } else {
            this.insertWidget(dropZone, widgetType);
        }
    }

    insertField(parent, field) {
        const fieldElement = document.createElement("field");
        fieldElement.setAttribute("name", field.name);
        parent.appendChild(fieldElement);

        this.updateArchitecture();
    }

    insertWidget(parent, widgetType) {
        let element;

        switch (widgetType) {
            case "group":
                element = document.createElement("group");
                break;
            case "notebook":
                element = document.createElement("notebook");
                break;
            case "page":
                element = document.createElement("page");
                element.setAttribute("string", "New Page");
                break;
            case "button":
                element = document.createElement("button");
                element.setAttribute("string", "New Button");
                element.setAttribute("type", "object");
                element.setAttribute("class", "btn-primary");
                break;
            case "separator":
                element = document.createElement("separator");
                element.setAttribute("string", "");
                break;
            case "label":
                element = document.createElement("label");
                element.setAttribute("for", "");
                element.setAttribute("string", "New Label");
                break;
            default:
                return;
        }

        parent.appendChild(element);
        this.updateArchitecture();
    }

    updateArchitecture() {
        // Get the updated XML
        const container = this.viewRef.el;
        this.state.viewArch = container.innerHTML;

        // Update the view in the backend
        this.props.onArchitectureChanged(this.state.viewArch);
    }

    async selectField() {
        // This would open a dialog to select from available fields
        // For now, returning a mock field
        return {name: "x_new_field", type: "char"};
    }
}
