# Same targets run locally and in CI (.github/workflows/lint.yml runs `make ci`).
# `make site` builds the docs (strict MkDocs, `make docs`) and the explorer, then
# merges them into site/ with a collision check, writes redirects for the old
# catalog/ URLs, and checks every internal link. `make ci` runs it, so a broken
# link, anchor, nav entry, or redirect fails CI. `make preview` serves the merged
# site under its base path; `make serve` previews the docs alone.
# Doc paths only, so tools/tests/fixtures is never prose-linted.
# $(wildcard ...) drops directories that do not exist yet (platform/, catalog/).
# The Google Vale style is vendored at .vale/styles/Google (see PROVENANCE.txt);
# no target downloads styles.
# explorer/src/content holds every explorer UI string (copy.md), so Vale lints it.
DOC_DIRS := README.md site-src framework architecture platform catalog proposal templates explorer/src/content
VALE ?= vale

.PHONY: setup lint lint-structure lint-prose test test-vale test-site test-pdf render facts docs site preview serve explorer explorer-data explorer-deps proposal-pdf ci hooks

# --locked fails instead of re-resolving when uv.lock is stale.
setup:
	uv sync --all-extras --locked

lint: lint-structure lint-prose

lint-structure:
	uv run python -m tools.bplint

lint-prose:
	$(VALE) $(wildcard $(DOC_DIRS))

test:
	uv run pytest -q

test-vale:
	$(VALE) test .vale/styles/Blueprints

# Rewrites the generated blocks: the serving page from data/serving/*.yaml, the
# Recipes overview (catalog/index.md) from use-case front matter, and the What you
# bring block on every use-case page from its adaptation field and the PB-11 matrix,
# and the proposal (proposal/index.md) from the blueprints.
# tools/tests/test_serving_data.py, test_catalog_overview.py,
# test_adaptation_field.py, and test_proposal.py fail on drift.
render:
	uv run python -m tools.site.render_serving
	uv run python -m tools.site.render_catalog
	uv run python -m tools.site.render_bring
	uv run python -m tools.site.build_proposal

# Prints every source URL the facts stamp covers (Sources tables, serving data,
# and extra_urls in data/facts-check.yaml). The stamp itself is checked by
# tools/tests/test_proposal.py inside `make test`. The network re-check is run by
# hand before a release: uv run python -m tools.site.facts --recheck --report <path>
facts:
	uv run python -m tools.site.facts --urls

# NO_MKDOCS_2_WARNING silences the Material end-of-life banner in logs.
docs:
	NO_MKDOCS_2_WARNING=1 uv run mkdocs build --strict --clean

# The proposal PDF, built offline by WeasyPrint from proposal/index.md (needs Pango:
# brew install pango). Without Pango it prints a skip notice and exits 0, unless
# REQUIRE_PDF=1. The Pages workflow installs pinned Pango and sets REQUIRE_PDF=1.
proposal-pdf:
	uv run python -m tools.site.build_pdf --out site/proposal/otel-telco-blueprints-proposal.pdf

# PDF tests that need no built site; they fail instead of skipping without Pango.
# Run before every push that touches the proposal or the print stylesheet.
test-pdf:
	REQUIRE_PDF=1 uv run pytest -q -m "pdf and not site_output"

# One artifact for Pages: docs plus explorer, merged by tools/site/merge_site.py.
# The proposal PDF is built into site/ after the docs build (which cleans site/)
# and before the merge, so the link check sees it.
site: docs explorer
	uv run python -m tools.site.build_pdf --out site/proposal/otel-telco-blueprints-proposal.pdf
	uv run python -m tools.site.merge_site

# Serves the merged site at http://127.0.0.1:8000/otel-telco-blueprints/ (run make site first).
preview:
	rm -rf .preview
	mkdir -p .preview
	cp -R site .preview/otel-telco-blueprints
	python3 -m http.server 8000 -d .preview

serve:
	NO_MKDOCS_2_WARNING=1 uv run mkdocs serve --strict

# Installs the explorer's locked Node dependencies. npm ci only; explorer/.npmrc
# sets ignore-scripts=true, so no package install script runs.
explorer-deps:
	npm ci --prefix explorer

# Writes explorer/src/generated/explorer.json (untracked) from recipe front matter
# and data/serving/*.yaml. The explorer build depends on it, so the JSON is always fresh.
explorer-data:
	uv run python -m tools.site.export_explorer

# Builds the explorer into explorer/dist. Astro telemetry stays off.
explorer: explorer-data
	cd explorer && ASTRO_TELEMETRY_DISABLED=1 npx --no-install astro build

# Tests that read built output (site/ and explorer/dist). Depends on site, so the
# build always runs first and is fresh, also under make -j.
test-site: site
	uv run pytest -q -m site_output

ci: test test-vale lint site test-site

# Installs the versioned git guards (core.hooksPath = tools/git-hooks); not part of `ci`.
hooks:
	sh tools/git-hooks/install.sh
