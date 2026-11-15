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
DOC_DIRS := README.md site-src framework architecture platform catalog templates explorer/src/content
VALE ?= vale

.PHONY: setup lint lint-structure lint-prose test test-vale test-site render docs site preview serve explorer explorer-data explorer-deps ci hooks

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

# Rewrites the serving page blocks rendered from data/serving/*.yaml.
# tools/tests/test_serving_data.py fails when the page drifts from the data.
render:
	uv run python -m tools.site.render_serving

# NO_MKDOCS_2_WARNING silences the Material end-of-life banner in logs.
docs:
	NO_MKDOCS_2_WARNING=1 uv run mkdocs build --strict --clean

# One artifact for Pages: docs plus explorer, merged by tools/site/merge_site.py.
site: docs explorer
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

# Tests that read built output (site/ and explorer/dist); run after site and explorer.
test-site:
	uv run pytest -q -m site_output

ci: test test-vale lint site test-site

# Installs the versioned git guards (core.hooksPath = tools/git-hooks); not part of `ci`.
hooks:
	sh tools/git-hooks/install.sh
