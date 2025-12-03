{
    "name": "Code Generator - geoengine",
    "version": "18.0.1.0.0",
    "summary": "Code Generator - Manage geoengine",
    "description": "Code generator builder to manage geoengine",
    "author": "Mathben (mathben@technolibre.ca)",
    "category": "Extra Tools",
    "depends": [
        "code_generator",
        "base_geoengine",
    ],
    "license": "AGPL-3",
    "installable": True,
    "data": [
        "security/ir.model.access.csv",
        "wizards/code_generator_generate_views_wizard.xml",
    ],
    "post_init_hook": "post_init_hook",
}
