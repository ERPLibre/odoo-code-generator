/** @odoo-module **/

import {Component, useState, useRef, onMounted, onWillUnmount} from "@odoo/owl";
import {useService} from "@web/core/utils/hooks";
import {_t} from "@web/core/l10n/translation";
import {Dialog} from "@web/core/dialog/dialog";

export class StudioXmlEditor extends Component {
    static template = "code_studio.XmlEditor";
    static components = {Dialog};
    static props = {
        initialXml: {type: String},
        onSave: {type: Function},
        close: {type: Function},
        readonly: {type: Boolean, optional: true},
    };

    setup() {
        this.notification = useService("notification");
        this.editorRef = useRef("editor");

        this.state = useState({
            xml:
                this.props.initialXml ||
                '<?xml version="1.0"?>\n<form>\n    <sheet>\n        <group>\n        </group>\n    </sheet>\n</form>',
            errors: [],
            isValid: true,
            isDirty: false,
            searchText: "",
            replaceText: "",
            showSearch: false,
        });

        this.shortcuts = {
            "Control+s": (e) => {
                e.preventDefault();
                this.save();
            },
            "Control+f": (e) => {
                e.preventDefault();
                this.toggleSearch();
            },
            "Control+h": (e) => {
                e.preventDefault();
                this.toggleReplace();
            },
            "Control+z": (e) => {
                e.preventDefault();
                this.undo();
            },
            "Control+y": (e) => {
                e.preventDefault();
                this.redo();
            },
        };

        this.history = {
            past: [],
            future: [],
            maxHistory: 50,
        };

        onMounted(() => {
            this.setupEditor();
            this.attachKeyboardShortcuts();
        });

        onWillUnmount(() => {
            this.detachKeyboardShortcuts();
        });
    }

    setupEditor() {
        const editor = this.editorRef.el;
        if (!editor) return;

        // Add line numbers
        this.addLineNumbers();

        // Syntax highlighting on input
        editor.addEventListener("input", () => {
            this.state.isDirty = true;
            this.validateXml();
            this.highlightSyntax();
            this.addToHistory();
        });

        // Tab handling
        editor.addEventListener("keydown", (e) => {
            if (e.key === "Tab") {
                e.preventDefault();
                const start = editor.selectionStart;
                const end = editor.selectionEnd;
                const value = editor.value;

                if (e.shiftKey) {
                    // Unindent
                    const beforeStart = value.lastIndexOf("\n", start - 1) + 1;
                    const afterEnd = value.indexOf("\n", end);
                    const endPos = afterEnd === -1 ? value.length : afterEnd;

                    const lines = value.substring(beforeStart, endPos).split("\n");
                    const unindented = lines
                        .map((line) => (line.startsWith("    ") ? line.substring(4) : line))
                        .join("\n");

                    editor.value = value.substring(0, beforeStart) + unindented + value.substring(endPos);
                    editor.selectionStart = start - 4;
                    editor.selectionEnd = end - 4 * lines.length;
                } else {
                    // Indent
                    editor.value = value.substring(0, start) + "    " + value.substring(end);
                    editor.selectionStart = editor.selectionEnd = start + 4;
                }

                this.state.xml = editor.value;
                this.highlightSyntax();
            }
        });

        // Initial syntax highlighting
        this.highlightSyntax();
    }

    addLineNumbers() {
        const editor = this.editorRef.el;
        const lineNumbers = editor.parentElement.querySelector(".line-numbers");

        const updateLineNumbers = () => {
            const lines = editor.value.split("\n").length;
            const numbers = Array.from({length: lines}, (_, i) => i + 1).join("\n");
            lineNumbers.textContent = numbers;
        };

        editor.addEventListener("input", updateLineNumbers);
        editor.addEventListener("scroll", () => {
            lineNumbers.scrollTop = editor.scrollTop;
        });

        updateLineNumbers();
    }

    highlightSyntax() {
        const editor = this.editorRef.el;
        const highlighted = editor.parentElement.querySelector(".syntax-highlighted");

        let code = this.escapeHtml(editor.value);

        // XML syntax highlighting
        code = code
            // Comments
            .replace(/(&lt;!--[\s\S]*?--&gt;)/g, '<span class="xml-comment">$1</span>')
            // Tags
            .replace(/(&lt;\/?[\w:]+)(.*?)(&gt;)/g, (match, p1, p2, p3) => {
                // Tag name
                let result = `<span class="xml-tag">${p1}</span>`;

                // Attributes
                if (p2) {
                    result += p2.replace(
                        /([\w:]+)(=)("[^"]*"|'[^']*')/g,
                        '<span class="xml-attr">$1</span><span class="xml-equals">$2</span><span class="xml-value">$3</span>'
                    );
                }

                result += `<span class="xml-tag">${p3}</span>`;
                return result;
            })
            // CDATA
            .replace(/(&lt;!\[CDATA\[[\s\S]*?\]\]&gt;)/g, '<span class="xml-cdata">$1</span>')
            // Processing instructions
            .replace(/(&lt;\?[\s\S]*?\?&gt;)/g, '<span class="xml-pi">$1</span>');

        highlighted.innerHTML = code + "\n";

        // Sync scroll
        highlighted.scrollTop = editor.scrollTop;
        highlighted.scrollLeft = editor.scrollLeft;
    }

    escapeHtml(text) {
        const div = document.createElement("div");
        div.textContent = text;
        return div.innerHTML;
    }

    validateXml() {
        try {
            const parser = new DOMParser();
            const xmlDoc = parser.parseFromString(this.state.xml, "text/xml");

            const errors = [];
            const errorNode = xmlDoc.querySelector("parsererror");

            if (errorNode) {
                const errorText = errorNode.textContent;
                const match = errorText.match(/line (\d+)/);
                const line = match ? parseInt(match[1]) : 1;

                errors.push({
                    line: line,
                    message: errorText.replace(/[\n\r]/g, " ").trim(),
                });
            }

            this.state.errors = errors;
            this.state.isValid = errors.length === 0;

            this.highlightErrors();
        } catch (e) {
            this.state.errors = [{line: 1, message: e.toString()}];
            this.state.isValid = false;
        }
    }

    highlightErrors() {
        const editor = this.editorRef.el;
        const lines = editor.value.split("\n");
        const errorLines = new Set(this.state.errors.map((e) => e.line - 1));

        // Update line number styling
        const lineNumberElements = editor.parentElement.querySelectorAll(".line-number");
        lineNumberElements.forEach((el, index) => {
            if (errorLines.has(index)) {
                el.classList.add("error");
            } else {
                el.classList.remove("error");
            }
        });
    }

    attachKeyboardShortcuts() {
        this.keydownHandler = (e) => {
            const key = this.getShortcutKey(e);
            if (this.shortcuts[key]) {
                this.shortcuts[key](e);
            }
        };

        document.addEventListener("keydown", this.keydownHandler);
    }

    detachKeyboardShortcuts() {
        if (this.keydownHandler) {
            document.removeEventListener("keydown", this.keydownHandler);
        }
    }

    getShortcutKey(e) {
        const parts = [];
        if (e.ctrlKey) parts.push("Control");
        if (e.altKey) parts.push("Alt");
        if (e.shiftKey) parts.push("Shift");
        if (e.key && e.key !== "Control" && e.key !== "Alt" && e.key !== "Shift") {
            parts.push(e.key);
        }
        return parts.join("+");
    }

    addToHistory() {
        const currentState = this.state.xml;

        if (this.history.past.length === 0 || this.history.past[this.history.past.length - 1] !== currentState) {
            this.history.past.push(currentState);

            if (this.history.past.length > this.history.maxHistory) {
                this.history.past.shift();
            }

            this.history.future = [];
        }
    }

    undo() {
        if (this.history.past.length > 1) {
            this.history.future.push(this.history.past.pop());
            this.state.xml = this.history.past[this.history.past.length - 1];
            this.editorRef.el.value = this.state.xml;
            this.highlightSyntax();
            this.validateXml();
        }
    }

    redo() {
        if (this.history.future.length > 0) {
            const state = this.history.future.pop();
            this.history.past.push(state);
            this.state.xml = state;
            this.editorRef.el.value = this.state.xml;
            this.highlightSyntax();
            this.validateXml();
        }
    }

    toggleSearch() {
        this.state.showSearch = !this.state.showSearch;
        if (this.state.showSearch) {
            setTimeout(() => {
                const searchInput = this.el.querySelector(".search-input");
                if (searchInput) searchInput.focus();
            }, 100);
        }
    }

    toggleReplace() {
        this.state.showSearch = true;
        setTimeout(() => {
            const replaceInput = this.el.querySelector(".replace-input");
            if (replaceInput) replaceInput.focus();
        }, 100);
    }

    findNext() {
        const editor = this.editorRef.el;
        const searchText = this.state.searchText.toLowerCase();
        if (!searchText) return;

        const text = editor.value.toLowerCase();
        const start = editor.selectionEnd;
        const index = text.indexOf(searchText, start);

        if (index !== -1) {
            editor.selectionStart = index;
            editor.selectionEnd = index + searchText.length;
            editor.focus();
        } else {
            // Wrap around
            const wrapIndex = text.indexOf(searchText);
            if (wrapIndex !== -1 && wrapIndex < start) {
                editor.selectionStart = wrapIndex;
                editor.selectionEnd = wrapIndex + searchText.length;
                editor.focus();
            }
        }
    }

    findPrevious() {
        const editor = this.editorRef.el;
        const searchText = this.state.searchText.toLowerCase();
        if (!searchText) return;

        const text = editor.value.toLowerCase();
        const end = editor.selectionStart;
        const index = text.lastIndexOf(searchText, end - 1);

        if (index !== -1) {
            editor.selectionStart = index;
            editor.selectionEnd = index + searchText.length;
            editor.focus();
        }
    }

    replace() {
        const editor = this.editorRef.el;
        const selection = editor.value.substring(editor.selectionStart, editor.selectionEnd);

        if (selection.toLowerCase() === this.state.searchText.toLowerCase()) {
            const before = editor.value.substring(0, editor.selectionStart);
            const after = editor.value.substring(editor.selectionEnd);

            editor.value = before + this.state.replaceText + after;
            this.state.xml = editor.value;
            editor.selectionStart = editor.selectionStart;
            editor.selectionEnd = editor.selectionStart + this.state.replaceText.length;

            this.highlightSyntax();
            this.validateXml();
            this.state.isDirty = true;
        }

        this.findNext();
    }

    replaceAll() {
        if (!this.state.searchText) return;

        const editor = this.editorRef.el;
        const regex = new RegExp(this.state.searchText.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "gi");
        const newValue = editor.value.replace(regex, this.state.replaceText);

        if (newValue !== editor.value) {
            editor.value = newValue;
            this.state.xml = newValue;
            this.highlightSyntax();
            this.validateXml();
            this.state.isDirty = true;

            this.notification.add(_t("Replaced all occurrences"), {type: "info"});
        }
    }

    formatXml() {
        try {
            const parser = new DOMParser();
            const xmlDoc = parser.parseFromString(this.state.xml, "text/xml");

            if (xmlDoc.querySelector("parsererror")) {
                this.notification.add(_t("Cannot format invalid XML"), {type: "warning"});
                return;
            }

            const serializer = new XMLSerializer();
            const formatted = this.prettifyXml(serializer.serializeToString(xmlDoc));

            this.state.xml = formatted;
            this.editorRef.el.value = formatted;
            this.highlightSyntax();
            this.state.isDirty = true;
        } catch (e) {
            this.notification.add(_t("Error formatting XML"), {type: "danger"});
        }
    }

    prettifyXml(xml) {
        const PADDING = "    ";
        const reg = /(>)(<)(\/*)/g;
        let pad = 0;

        xml = xml.replace(reg, "$1\r\n$2$3");

        return xml
            .split("\r\n")
            .map((node) => {
                let indent = 0;
                if (node.match(/.+<\/\w[^>]*>$/)) {
                    indent = 0;
                } else if (node.match(/^<\/\w/)) {
                    if (pad !== 0) {
                        pad -= 1;
                    }
                } else if (node.match(/^<\w[^>]*[^\/]>.*$/)) {
                    indent = 1;
                } else {
                    indent = 0;
                }

                const padding = PADDING.repeat(pad);
                pad += indent;

                return padding + node;
            })
            .join("\r\n");
    }

    async save() {
        if (!this.state.isValid) {
            this.notification.add(_t("Cannot save invalid XML"), {type: "danger"});
            return;
        }

        if (!this.state.isDirty) {
            this.props.close();
            return;
        }

        try {
            await this.props.onSave(this.state.xml);
            this.state.isDirty = false;
            this.notification.add(_t("XML saved successfully"), {type: "success"});
            this.props.close();
        } catch (error) {
            this.notification.add(_t("Error saving XML"), {type: "danger"});
        }
    }

    cancel() {
        if (this.state.isDirty) {
            if (!confirm(_t("You have unsaved changes. Are you sure you want to close?"))) {
                return;
            }
        }
        this.props.close();
    }
}

// XML Editor Template
StudioXmlEditor.template = /* xml */ `
<Dialog size="'lg'" title="'XML Editor'" t-on-close="cancel">
    <div class="o_studio_xml_editor">
        <!-- Toolbar -->
        <div class="xml-editor-toolbar">
            <div class="btn-group">
                <button class="btn btn-sm btn-secondary" t-on-click="formatXml" title="Format XML">
                    <i class="fa fa-indent"/> Format
                </button>
                <button class="btn btn-sm btn-secondary" t-on-click="undo" title="Undo (Ctrl+Z)">
                    <i class="fa fa-undo"/>
                </button>
                <button class="btn btn-sm btn-secondary" t-on-click="redo" title="Redo (Ctrl+Y)">
                    <i class="fa fa-repeat"/>
                </button>
            </div>

            <div class="btn-group">
                <button class="btn btn-sm btn-secondary" t-on-click="toggleSearch" title="Find (Ctrl+F)">
                    <i class="fa fa-search"/> Find
                </button>
            </div>

            <div class="validation-status">
                <span t-if="state.isValid" class="text-success">
                    <i class="fa fa-check-circle"/> Valid XML
                </span>
                <span t-else="" class="text-danger">
                    <i class="fa fa-exclamation-circle"/> Invalid XML
                </span>
            </div>
        </div>

        <!-- Search/Replace Bar -->
        <div t-if="state.showSearch" class="search-replace-bar">
            <div class="search-row">
                <input type="text" class="form-control search-input"
                       placeholder="Find..."
                       t-model="state.searchText"
                       t-on-keydown.enter="findNext"/>
                <button class="btn btn-sm btn-secondary" t-on-click="findPrevious">
                    <i class="fa fa-chevron-up"/>
                </button>
                <button class="btn btn-sm btn-secondary" t-on-click="findNext">
                    <i class="fa fa-chevron-down"/>
                </button>
            </div>
            <div class="replace-row">
                <input type="text" class="form-control replace-input"
                       placeholder="Replace with..."
                       t-model="state.replaceText"/>
                <button class="btn btn-sm btn-secondary" t-on-click="replace">Replace</button>
                <button class="btn btn-sm btn-secondary" t-on-click="replaceAll">Replace All</button>
            </div>
            <button class="close-search" t-on-click="() => state.showSearch = false">
                <i class="fa fa-times"/>
            </button>
        </div>

        <!-- Editor -->
        <div class="xml-editor-container">
            <div class="line-numbers"></div>
            <div class="editor-wrapper">
                <textarea t-ref="editor"
                          class="xml-editor-textarea"
                          t-model="state.xml"
                          t-att-readonly="props.readonly"
                          spellcheck="false"/>
                <div class="syntax-highlighted"></div>
            </div>
        </div>

        <!-- Error Messages -->
        <div t-if="state.errors.length" class="error-messages">
            <div t-foreach="state.errors" t-as="error" t-key="error_index" class="error-message">
                <i class="fa fa-exclamation-triangle"/>
                Line <t t-esc="error.line"/>: <t t-esc="error.message"/>
            </div>
        </div>
    </div>

    <t t-set-slot="footer">
        <button class="btn btn-primary" t-on-click="save" t-att-disabled="!state.isValid">
            Save
        </button>
        <button class="btn btn-secondary" t-on-click="cancel">Cancel</button>
        <span t-if="state.isDirty" class="text-warning ms-3">
            <i class="fa fa-circle"/> Unsaved changes
        </span>
    </t>
</Dialog>
`;
