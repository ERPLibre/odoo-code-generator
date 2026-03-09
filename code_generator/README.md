# Code Generator

**Version**: 18.0.1.0.0 | **License**: AGPL-3 | **Author**: Mathben (mathben@technolibre.ca)

An Odoo 18 application module for ERPLibre that automates the generation of complete Odoo modules — models, views, menus, security rules, controllers, and data files — from metadata or existing module templates.

## Overview

The Code Generator replaces manual module scaffolding by capturing module structure as database records, then generating all the Python, XML, and CSV files needed for a fully functional Odoo module. It can also extract the structure of an existing module and reproduce it.

### Key capabilities

- Generate models with fields, constraints, computed methods, decorators, and inheritance
- Generate 10 view types: form, list, search, kanban, pivot, graph, calendar, diagram, activity, timeline
- Generate menus, action windows, security groups, and access rules
- Generate controllers with HTTP routes
- Export module data (nomenclator mode) with field whitelist/blacklist filtering
- Extract structure from existing modules and views
- Download generated modules as ZIP archives
- Support delegation inheritance (`_inherits`) and materialized paths (`_parent_store`)
- Support Odoo 18 field types: Properties, PropertiesDefinition, Many2one_reference
- Support asset bundles in `__manifest__.py`
- Helper for `@api.onchange` method generation

## Architecture

```
code_generator/
├── models/              # 27 model files — core data structures
├── wizards/             # 4 transient models — UI wizards for generation
├── controllers/         # HTTP endpoint for ZIP download
├── views/               # 36 XML view definitions
├── security/            # Access control (groups + CSV rules)
├── static/              # Icons and HTML description
├── tests/               # Unit tests
├── i18n/                # Spanish translations
├── hooks.py             # Post-install hook (dev mode setup)
├── code_generator_data.py        # File/directory generation utilities
├── extractor_module.py           # Parse existing module __manifest__
├── extractor_view.py             # Parse existing XML views
├── extractor_controller.py       # Parse existing controllers
└── python_controller_writer.py   # Controller code writer
```

**Stats**: ~13,500 lines of Python across 79 source files.

## Core models

### Module definition

| Model | Purpose |
|-------|---------|
| `code.generator.module` | Root aggregate — defines a module with its name, author, dependencies, assets, and references to all sub-components |
| `code.generator.module.dependency` | Module dependency (extends `ir.module.module.dependency`) |
| `code.generator.module.template.dependency` | Template-specific dependency |
| `code.generator.module.external.dependency` | External Python/binary dependency (e.g. `lxml`, `wkhtmltopdf`) |

### Models and fields

| Model | Purpose |
|-------|---------|
| `ir.model` (extended) | Adds code generation metadata — module link, menu hints, nomenclator flag, diagram config, activity support, `_inherits`, `_parent_store` |
| `ir.model.fields` (extended) | Adds per-view-type sequence, whitelist/blacklist flags, force_widget (100+ options), compute code, default_lambda |
| `code.generator.ir.model.fields` | Extended field metadata — comments, selection options, nomenclature filtering |
| `code.generator.ir.model.dependency` | Model inheritance tracking |
| `code.generator.pyclass` | External Python class to inherit from |

### Code injection

| Model | Purpose |
|-------|---------|
| `code.generator.model.code` | Python method snippet — name, code, decorator (supports `@api.onchange`, `@api.depends`, `@api.constrains`, etc.), parameters, return type |
| `code.generator.model.code.import` | Header import statement for generated Python files |
| `ir.model.constraint` (extended) | SQL constraint with create/drop management |
| `ir.model.server_constrain` | Server-side validation (constrains decorator + code) |

### Views and UI

| Model | Purpose |
|-------|---------|
| `code.generator.view` | View definition — type, model, inherit, sheet, decoration attributes |
| `code.generator.view.item` | Individual view element — field, button, filter, group, notebook, page, div, xpath (hierarchical tree) |
| `code.generator.menu` | Menu item — name, parent, sequence, action window link |
| `code.generator.act_window` | Action window — model, view_mode, target, wizard flag |

### Extended Odoo models

| Model | Added fields |
|-------|-------------|
| `ir.ui.view` | `m2o_model`, whitelist/blacklist write flags |
| `ir.ui.menu` | `m2o_module`, `ignore_act_window` |
| `ir.actions.act_window` | `m2o_res_model`, `m2o_src_model` |
| `ir.actions.server` | `comment`, auto-populated boilerplate code |
| `ir.actions.report` | Computed `m2o_model`, `m2o_template` |
| `ir.actions.act_url` | `m2o_code_generator` |
| `ir.actions.todo` | `m2o_code_generator` |
| `res.groups` | `m2o_module` |
| `ir.module.module` | `header_manifest` |

## Wizards

| Wizard | Purpose |
|--------|---------|
| **Add Model** (`code.generator.add.model.wizard`) | Add existing models to a code generator module with field whitelist/blacklist and inheritance options |
| **Generate Views** (`code.generator.generate.views.wizard`) | Generate views, menus, access rules, and actions for selected models — supports per-view-type model selection and clear/rebuild |
| **Add Controller** (`code.generator.add.controller.wizard`) | Link models for controller generation, auto-add module dependencies |
| **Settings** (`res.config.settings`) | Configure data export mode (nomenclator vs non-nomenclator) |

## Model relationships

```
code.generator.module
├── o2m_models ──────────────────> ir.model
│   ├── field_id ────────────────> ir.model.fields
│   │   └── code_generator_ir_model_fields_ids ──> code.generator.ir.model.fields
│   ├── o2m_codes ───────────────> code.generator.model.code
│   ├── o2m_code_import ─────────> code.generator.model.code.import
│   ├── o2m_constraints ─────────> ir.model.constraint
│   ├── o2m_server_constrains ───> ir.model.server_constrain
│   └── inherit_model_ids ───────> code.generator.ir.model.dependency
├── code_generator_views_id ─────> code.generator.view
│   └── view_item_ids ───────────> code.generator.view.item (tree)
├── code_generator_menus_id ─────> code.generator.menu
│   └── m2o_act_window ──────────> code.generator.act_window
├── code_generator_act_window_id > code.generator.act_window
├── o2m_groups ──────────────────> res.groups
├── dependencies_id ─────────────> code.generator.module.dependency
├── dependencies_template_id ────> code.generator.module.template.dependency
└── external_dependencies_id ────> code.generator.module.external.dependency
```

## Workflow

### 1. Define module metadata

Create a `code.generator.module` record with name, author, category, dependencies, and optionally asset bundles.

```python
module = env["code.generator.module"].create([{
    "name": "my_module",
    "shortdesc": "My Module",
    "author": "My Company",
    "license": "AGPL-3",
    "assets": '{"web.assets_backend": ["my_module/static/src/js/*.js"]}',
}])
```

### 2. Add models

Use `add_update_model()` to register models with their fields programmatically, or use the **Add Model** wizard to import from existing `ir.model` records.

```python
model_id = module.add_update_model(
    "my.model",
    dct_field={"name": {"ttype": "char", "required": True}},
    dct_model={"description": "My Model"},
)
```

#### Delegation inheritance and hierarchical models

```python
# Delegation inheritance (_inherits)
model_id.inherits_model = "res.partner:partner_id"

# Materialized path for hierarchical data
model_id.parent_store = True
model_id.parent_name_field = "parent_id"
```

### 3. Inject code

Add Python methods via `code.generator.model.code` records and imports via `code.generator.model.code.import`.

#### Onchange methods

Use the helper to generate `@api.onchange` methods:

```python
module.add_onchange_method(
    model_id,
    field_names=["partner_id"],
    code="self.name = self.partner_id.name",
)
```

#### Access rules (ir.rule)

Use the helper to generate security rules for specific groups:

```python
# Portal users can read their own records
module.add_access_rule(
    model_id,
    "base.group_portal",
    domain_force="[('create_uid', '=', user.id)]",
    perm_write=False,
    perm_create=False,
    perm_unlink=False,
)

# Internal users have full access
module.add_access_rule(
    model_id,
    "base.group_user",
)
```

### 4. Generate views

Use the **Generate Views** wizard to create form, list, search, and other views. Field ordering is controlled by `code_generator_*_view_sequence` fields, and visibility by whitelist/blacklist flags.

### 5. Download

Access `/code_generator/<module_ids>` to download a ZIP containing the complete generated module with:
- `__init__.py` files
- `__manifest__.py` (with `assets` if configured)
- `models/*.py` with all fields, methods, decorators
- `views/*.xml` with all view definitions
- `security/ir.model.access.csv`
- `data/*.csv` (nomenclator mode)
- `controllers/*.py` (if configured)

## Supported field types

The code generator supports all Odoo 18 field types including:

| Type | Generated class | Notes |
|------|----------------|-------|
| `char`, `text`, `html` | `fields.Char`, `fields.Text`, `fields.Html` | Standard text types |
| `integer`, `float`, `monetary` | `fields.Integer`, `fields.Float`, `fields.Monetary` | Numeric types |
| `boolean` | `fields.Boolean` | |
| `date`, `datetime` | `fields.Date`, `fields.Datetime` | |
| `binary` | `fields.Binary` | |
| `selection`, `reference` | `fields.Selection`, `fields.Reference` | With selection items |
| `many2one`, `one2many`, `many2many` | `fields.Many2one`, `fields.One2many`, `fields.Many2many` | Relational types |
| `properties` | `fields.Properties` | Odoo 17+ — dynamic user-defined fields, auto-extracts `definition_record` |
| `properties_definition` | `fields.PropertiesDefinition` | Odoo 17+ — schema definition for Properties fields |
| `many2one_reference` | `fields.Many2oneReference` | Odoo 17+ — polymorphic reference, auto-extracts `model_field` |

## Extractors

The module includes extractors to reverse-engineer existing modules:

| Extractor | Input | Output |
|-----------|-------|--------|
| `ExtractorModule` | Module directory path | Dependencies, external deps, manifest header |
| `ExtractorView` | XML view files | `code.generator.view` + `code.generator.view.item` records |
| `ExtractorController` | Controller files | Controller metadata |

## Extensibility

The writer provides hook methods that external modules can override:

| Hook method | Purpose |
|-------------|---------|
| `set_manifest_file_extra(cw, module)` | Add custom entries to `__manifest__.py` |
| `set_xml_data_file(module)` | Generate additional XML data files (e.g. `ir.cron` via `code_generator_cron`) |
| `set_xml_views_file(module)` | Generate additional view files |
| `set_module_python_file(module)` | Generate additional Python files |
| `set_module_css_file(module)` | Generate CSS/SCSS files |
| `set_module_js_file(module)` | Generate JavaScript/OWL component files |
| `set_extra_get_lst_file_generate(module)` | Run extra generation logic |
| `write_extra_pre_init_hook(module, cw)` | Add code to `pre_init_hook` |
| `write_extra_post_init_hook(module, cw)` | Add code to `post_init_hook` |
| `write_extra_uninstall_hook(module, cw)` | Add code to `uninstall_hook` |

## Security

- **Group**: `code_generator_manager` — full CRUD on all code generator models (19 access rules)
- **Group**: `base.group_user` — access to wizards only
- **Requirement**: Module must be installed with `--dev` mode (enforced in `post_init_hook`)

## Dependencies

- `base`
- `mail`

## Writer utilities

The `code.generator.writer` model provides formatting helpers used during code generation:

| Method | Example |
|--------|---------|
| `_fmt_underscores("res.partner")` | `res_partner` |
| `_fmt_camel("res.partner")` | `ResPartner` |
| `_fmt_title("res.partner")` | `Res Partner` |
| `_get_odoo_ttype_class("char")` | `fields.Char` |
| `_get_python_class_4inherit(model)` | `models.Model` / `models.TransientModel` |
