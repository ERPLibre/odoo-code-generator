{
    "name": "Code Studio",
    "version": "18.0.1.0.0",
    "category": "Customization/Studio",
    "summary": "Generate models and fields into Odoo",
    "description": """
        Code Studio
        ===========

        - Generate models and fields into Odoo
    """,
    "author": "TechnoLibre",
    "website": "https://technolibre.ca",
    "depends": [
        "base",
        "web",
        "mail",
        "base_automation",
    ],
    "data": [
        "security/studio_security.xml",
        "security/ir.model.access.csv",
        "data/studio_data.xml",
        "views/studio_assets.xml",
        "views/studio_menu_views.xml",
        "views/studio_model_views.xml",
        "views/studio_field_views.xml",
        "views/studio_view_views.xml",
        "views/studio_action_views.xml",
        "views/studio_automation_views.xml",
        "views/studio_approval_views.xml",
        "wizards/studio_export_wizard_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            # JS
            "code_studio/static/src/js/**/*.js",
            # XML qweb (si nécessaire pour le client web)
            "code_studio/static/src/xml/**/*.xml",
            # SCSS/CSS
            "code_studio/static/src/scss/**/*.scss",
        ],
    },
    "installable": True,
    "application": True,
    "license": "AGPL-3",
}
