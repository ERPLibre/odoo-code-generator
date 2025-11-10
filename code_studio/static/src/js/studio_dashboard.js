/** @odoo-module **/

import {registry} from "@web/core/registry";
import {Component, xml, useState, onWillStart} from "@odoo/owl";
import {useService} from "@web/core/utils/hooks";
import {_t} from "@web/core/l10n/translation";

export class StudioDashboard extends Component {
    static template = xml/* xml */ `
<div class="o_studio_dashboard h-100 d-flex flex-column">
    <div class="o_studio_dashboard_header d-flex align-items-center justify-content-between mb-3">
        <h1 class="m-0">Studio Dashboard</h1>
        <button class="btn btn-primary" t-on-click="createNewModel">
            <i class="fa fa-plus"/> Create Model
        </button>
    </div>

    <div t-if="state.isLoading" class="text-center p-5">
        <i class="fa fa-spinner fa-spin fa-3x"/>
    </div>

    <div t-else="" class="o_studio_dashboard_content">
        <!-- Statistics Cards -->
        <div class="row g-3 mb-4">
            <div class="col-md-3">
                <div class="o_studio_stat_card" role="button" t-on-click="openModelList">
                    <div class="o_stat_value">
                        <span t-esc="state.stats.totalModels"/>
                    </div>
                    <div class="o_stat_label">Models</div>
                    <i class="fa fa-database o_stat_icon"/>
                </div>
            </div>
            <div class="col-md-3">
                <div class="o_studio_stat_card" role="button" t-on-click="openFieldList">
                    <div class="o_stat_value">
                        <span t-esc="state.stats.totalFields"/>
                    </div>
                    <div class="o_stat_label">Fields</div>
                    <i class="fa fa-columns o_stat_icon"/>
                </div>
            </div>
            <div class="col-md-3">
                <div class="o_studio_stat_card" role="button" t-on-click="openViewList">
                    <div class="o_stat_value">
                        <span t-esc="state.stats.totalViews"/>
                    </div>
                    <div class="o_stat_label">Views</div>
                    <i class="fa fa-window-maximize o_stat_icon"/>
                </div>
            </div>
            <div class="col-md-3">
                <div class="o_studio_stat_card" role="button" t-on-click="openAutomationList">
                    <div class="o_stat_value">
                        <span t-esc="state.stats.totalAutomations"/>
                    </div>
                    <div class="o_stat_label">Automations</div>
                    <i class="fa fa-cogs o_stat_icon"/>
                </div>
            </div>
        </div>

        <div class="row g-3">
            <!-- Recent Models -->
            <div class="col-md-6">
                <div class="o_studio_panel">
                    <h3 class="mb-3">Recent Models</h3>
                    <div class="o_studio_model_list">
                        <div t-foreach="state.models" t-as="model" t-key="model.id"
                             class="o_studio_model_item d-flex align-items-center justify-content-between"
                             t-on-click="openModel(model.id)" role="button">
                            <div class="o_model_info">
                                <h5 class="m-0" t-esc="model.description"/>
                                <small class="text-muted" t-esc="model.name"/>
                            </div>
                            <div class="o_model_stats">
                                <span class="badge bg-secondary">
                                    <i class="fa fa-columns"/> <t t-esc="model.field_ids.length"/> fields
                                </span>
                                <span class="badge bg-secondary ms-2">
                                    <i class="fa fa-window-maximize"/> <t t-esc="model.view_ids.length"/> views
                                </span>
                            </div>
                        </div>
                        <div t-if="!state.models.length" class="text-muted text-center p-3">
                            No models created yet
                        </div>
                    </div>
                </div>
            </div>

            <!-- Recent Changes -->
            <div class="col-md-6">
                <div class="o_studio_panel">
                    <h3 class="mb-3">Recent Changes</h3>
                    <div class="o_studio_changes_list">
                        <div t-foreach="state.recentChanges" t-as="change" t-key="change.__key"
                             class="o_studio_change_item d-flex align-items-start gap-2">
                            <i t-att-class="'fa ' + getChangeIcon(change)"/>
                            <div class="o_change_info">
                                <div t-esc="change.field_description or change.description or change.name"/>
                                <small class="text-muted">
    <t t-esc="formatDate(change.write_date)"/>
    <t t-if="change.write_uid">
        <span class="ms-1">by</span>
        <span class="ms-1" t-esc="change.write_uid[1]"/>
    </t>
</small>

                            </div>
                        </div>
                        <div t-if="!state.recentChanges.length" class="text-muted text-center p-3">
                            No recent changes
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
    `;

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        // this.user = useService("user");

        this.state = useState({
            models: [],
            recentChanges: [],
            stats: {
                totalModels: 0,
                totalFields: 0,
                totalViews: 0,
                totalAutomations: 0,
            },
            isLoading: true,
        });

        onWillStart(async () => {
            await this.loadDashboardData();
        });
    }

    async loadDashboardData() {
        try {
            const [models, stats, recentChanges] = await Promise.all([
                this.loadModels(),
                this.loadStats(),
                this.loadRecentChanges(),
            ]);
            this.state.models = models;
            this.state.stats = stats;
            this.state.recentChanges = recentChanges;
        } catch (error) {
            this.notification.add(_t("Error loading dashboard data"), {type: "danger"});
            // Optionally log
            // console.error("StudioDashboard load error", error);
        } finally {
            this.state.isLoading = false;
        }
    }

    async loadModels() {
        return this.orm.searchRead(
            "studio.model",
            [["state", "=", "active"]],
            ["name", "description", "field_ids", "view_ids"],
            {limit: 10, order: "create_date desc"}
        );
    }

    async loadStats() {
        const [modelCount, fieldCount, viewCount, automationCount] = await Promise.all([
            this.orm.searchCount("studio.model", []),
            this.orm.searchCount("studio.field", []),
            this.orm.searchCount("studio.view", []),
            this.orm.searchCount("studio.automation", []),
        ]);
        return {
            totalModels: modelCount,
            totalFields: fieldCount,
            totalViews: viewCount,
            totalAutomations: automationCount,
        };
    }

    async loadRecentChanges() {
        const recentModels = await this.orm.searchRead(
            "studio.model",
            [],
            ["name", "description", "write_date", "write_uid"],
            {limit: 5, order: "write_date desc"}
        );
        const modelsTagged = recentModels.map((r) => ({
            ...r,
            __model: "studio.model",
            __key: `m-${r.id}`,
        }));

        const recentFields = await this.orm.searchRead(
            "studio.field",
            [],
            ["name", "field_description", "write_date", "write_uid", "studio_model_id"],
            {limit: 5, order: "write_date desc"}
        );
        const fieldsTagged = recentFields.map((r) => ({
            ...r,
            __model: "studio.field",
            __key: `f-${r.id}`,
        }));

        return [...modelsTagged, ...fieldsTagged]
            .sort((a, b) => new Date(b.write_date) - new Date(a.write_date))
            .slice(0, 10);
    }

    // Actions
    createNewModel() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "studio.model",
            views: [[false, "form"]],
            target: "current",
            context: {default_state: "draft"},
        });
    }
    openModel(modelId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "studio.model",
            res_id: modelId,
            views: [[false, "form"]],
            target: "current",
        });
    }
    openModelList() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "studio.model",
            views: [
                [false, "list"],
                [false, "form"],
            ],
            target: "current",
        });
    }
    openFieldList() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "studio.field",
            views: [
                [false, "list"],
                [false, "form"],
            ],
            target: "current",
        });
    }
    openViewList() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "studio.view",
            views: [
                [false, "list"],
                [false, "form"],
            ],
            target: "current",
        });
    }
    openAutomationList() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "studio.automation",
            views: [
                [false, "list"],
                [false, "form"],
            ],
            target: "current",
        });
    }

    // Helpers
    getChangeIcon(change) {
        if (change.__model === "studio.model") return "fa-database";
        if (change.__model === "studio.field") return "fa-columns";
        return "fa-file";
    }
    formatDate(dateString) {
        if (!dateString) return "";
        const d = new Date(dateString);
        return `${d.toLocaleDateString()} ${d.toLocaleTimeString()}`;
    }
}

// Register as a client action (Odoo 18)
registry.category("actions").add("studio_dashboard", StudioDashboard);
