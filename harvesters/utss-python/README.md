# UTSS Python Catalog Harvester (`utss-python`)

The Python harvester component of the **Universal Type & Symbol System (UTSS)**. It performs comprehensive 4-pass harvesting of Python runtime objects, standard libraries, installed packages, AST syntax, and static typeshed (`.pyi`) stubs into the relational UTSS schema.

## Features
- **Stratum 0 (Ambient & Primitives):** 35 keywords, builtin types, operators, and global namespace primitives.
- **Stratum 1 (Standard Library):** Deep runtime introspection of CPython standard library modules (e.g. `math`, `sys`, `json`, `os`, `pathlib`, `typing`).
- **Stratum 2 (Installed Packages):** Dynamic discovery of site-packages in virtual environments.
- **Stratum 3 (Workspace Source):** Pure AST parsing of workspace Python code with syntax node coordinates and facets.
- **Pass 4 (Typeshed Overlay):** Applies static `.pyi` stub type annotations and signatures over compiled C-extensions and dynamic Python classes.

## CLI Usage

Run directly with Python:
```bash
# In this directory:
PYTHONPATH=.venv/lib/python3.13/site-packages:src python3 -m utss.cli --help

# Generate full stdlib + typeshed catalog:
bash 3.sh
```

## Running Tests
```bash
PYTHONPATH=.venv/lib/python3.13/site-packages:src python3 -m pytest tests
```

## License
MIT with the [UTSS Generated Output Exception](../../LICENSE-GENERATED-OUTPUT.md). Emitted catalog databases (`*.db`) are owned 100% by the user.
