# Same targets run locally and in CI (.github/workflows/lint.yml runs `make ci`).
# `make site` builds the docs site in strict mode (mkdocs.yml); `make ci` runs it,
# so a broken link, anchor, or nav entry fails CI. `make serve` previews locally.
# Doc paths only, so tools/tests/fixtures is never prose-linted.
# $(wildcard ...) drops directories that do not exist yet (platform/, catalog/).
# The Google Vale style is vendored at .vale/styles/Google (see PROVENANCE.txt);
# no target downloads styles.
# explorer/src/content holds every explorer UI string (copy.md), so Vale lints it.
DOC_DIRS := README.md site-src framework architecture platform catalog templates explorer/src/content
VALE ?= vale

.PHONY: setup lint lint-structure lint-prose test test-vale test-site render site serve explorer explorer-deps ci hooks

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
site:
	NO_MKDOCS_2_WARNING=1 uv run mkdocs build --strict --clean

serve:
	NO_MKDOCS_2_WARNING=1 uv run mkdocs serve --strict

# Installs the explorer's locked Node dependencies. npm ci only; explorer/.npmrc
# sets ignore-scripts=true, so no package install script runs.
explorer-deps:
	npm ci --prefix explorer

# Builds the explorer into explorer/dist. Astro telemetry stays off.
explorer:
	cd explorer && ASTRO_TELEMETRY_DISABLED=1 npx --no-install astro build

# Tests that read built output (site/ and explorer/dist); run after site and explorer.
test-site:
	uv run pytest -q -m site_output

ci: test test-vale lint site explorer test-site

# Installs the versioned git guards (core.hooksPath = tools/git-hooks); not part of `ci`.
hooks:
	sh tools/git-hooks/install.sh
