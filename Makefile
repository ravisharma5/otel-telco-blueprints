# Same targets run locally and in CI (.github/workflows/lint.yml runs `make ci`).
# `make site` builds the docs site in strict mode (mkdocs.yml); `make ci` runs it,
# so a broken link, anchor, or nav entry fails CI. `make serve` previews locally.
# Doc paths only, so tools/tests/fixtures is never prose-linted.
# $(wildcard ...) drops directories that do not exist yet (platform/, catalog/).
# The Google Vale style is vendored at .vale/styles/Google (see PROVENANCE.txt);
# no target downloads styles.
DOC_DIRS := README.md site-src framework architecture platform catalog templates
VALE ?= vale

.PHONY: setup lint lint-structure lint-prose test test-vale render site serve ci hooks

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

ci: test test-vale lint site

# Installs the versioned git guards (core.hooksPath = tools/git-hooks); not part of `ci`.
hooks:
	sh tools/git-hooks/install.sh
