---
title: "OTel Telco Production Blueprints"
doc_status: done
clarity_reviewed: "2026-11-09"
---

# OTel Telco Production Blueprints

## At a glance

| Item | Answer |
|---|---|
| What | Blueprints for running the OTel model family in production for telecom use cases, on Red Hat products |
| Who | GSMA members and telecom operators |
| Sources | Every blueprint links the source for each key claim: model card, research, Red Hat guidance, industry use case, or project documentation |
| Open source | Red Hat products show how the solution works. Any component can be replaced (no product support claims) |
| Website | [Docs site on GitHub Pages](https://ravisharma5.github.io/otel-telco-blueprints/) |
| Start here | [Definitions](framework/definitions.md), then the [glossary](framework/glossary.md) |

In this repository, "OTel" means the OTel model family, not OpenTelemetry.

## How to read

- [Definitions](framework/definitions.md): claim basis, the Sources table, autonomy ceiling, and component naming.
- [Glossary](framework/glossary.md): one meaning per term.
- [Style guide](framework/style-guide.md): page skeletons, budgets, and writing rules.
- [Review checklist](framework/review-checklist.md): what a doc needs before it's done.
- [Templates](templates/): starting points for platform and use-case blueprints.

## How to lint

You need `uv`, Vale 3.26.0, and Node (the version in `explorer/.node-version`).

| Command | What it does |
|---|---|
| `make setup` | Installs the locked Python dependencies (the Google Vale style is vendored at `.vale/styles/Google`, so nothing downloads) |
| `make lint` | Runs the structural linter and Vale |
| `make ci` | Runs tests, Vale rule tests, `make lint`, `make site`, `make explorer`, and `make test-site`, the same as CI |
| `make site` | Builds the docs site in strict mode |
| `make serve` | Previews the docs site at `http://127.0.0.1:8000` |
| `make explorer-deps` | Installs the locked explorer dependencies with `npm ci` (install scripts stay blocked) |
| `make explorer` | Builds the use-case explorer into `explorer/dist` |
| `make test-site` | Runs the tests that read the built site and explorer |
| `make hooks` | Installs the git guards that stop internal files and messages from being committed or pushed |

Local build: install Node from `explorer/.node-version`, then run `make explorer-deps`. No `.gitignore` is tracked, so add these lines to `.git/info/exclude`: `/explorer/node_modules/`, `/explorer/dist/`, `/explorer/.astro/`, and `/explorer/src/generated/`.

## License

- Code uses the `Apache-2.0` license. This covers `tools/`, `schemas/`, `.github/`, `Makefile`, `mkdocs.yml`, `tools/site/`, and `explorer/`. See [LICENSE](LICENSE).
- Documentation uses the `CC-BY-4.0` license. This covers `framework/`, `architecture/`, `platform/`, `catalog/`, `templates/`, the `site-src/` pages, and this README. See [LICENSE-docs](LICENSE-docs).
- The vendored Google Vale style in `.vale/styles/Google/` uses the `MIT` license. See its [LICENSE](.vale/styles/Google/LICENSE) and [PROVENANCE.txt](.vale/styles/Google/PROVENANCE.txt).
- The vendored Red Hat Display, Text, and Mono fonts in `site-src/brand/fonts/` use the SIL Open Font License 1.1. See [OFL.txt](site-src/brand/fonts/OFL.txt) and [PROVENANCE.txt](site-src/brand/fonts/PROVENANCE.txt).
