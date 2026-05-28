# Documentation Structure

Documentation is organized by ownership.

## Root Documentation

Root-level documentation describes cross-module concerns:

- repository architecture;
- module boundaries;
- data flow between modules;
- shared documentation conventions.

## Module Documentation

Each top-level module owns its own `README.md`. The module README is the entry point for that module and should contain:

- module responsibility;
- local structure;
- important commands;
- links to module-specific documents.

Detailed module decisions belong in the module's own `docs/` directory when the topic is larger than a short README section.

## Duplication Rule

The root README links to module READMEs instead of duplicating their details. Module READMEs link to local `docs/` files instead of duplicating design decisions across several places.

