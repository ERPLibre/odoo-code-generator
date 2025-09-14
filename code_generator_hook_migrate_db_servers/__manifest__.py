{
    "name": "Code Generator - Hook migrate DB servers",
    "version": "13.0.1.0.0",
    "summary": "Code Generator - Create hook migrate DB servers module",
    "description": (
        "Code generator builder to create hook for module installation, with"
        " automatic code for db migration."
    ),
    "author": "Mathben (mathben@technolibre.ca)",
    "category": "Extra Tools",
    "depends": [
        "code_generator_hook",
        "code_generator_db_servers",
    ],
    "installable": True,
    "auto_install": True,
    "data": [
        "views/code_generator.xml",
    ],
}
