---
# Every explorer UI string lives here, so Vale lints it. Keys named buttons,
# headings, or notes carry word limits (4, 8, and 25) enforced by a test.
site:
  name: OTel Telco Blueprints
  home_title: "OTel Telco Blueprints: telecom AI use cases in production"
  skip_link: Skip to content
  repo_url: https://github.com/ravisharma5/otel-telco-blueprints
nav:
  label: Main
  items:
    - label: Use cases
      path: ""
    - label: Recipes
      path: recipes/
    - label: Platform
      path: platform/
    - label: Architecture
      path: architecture/
    - label: Framework
      path: framework/
buttons:
  menu: Menu
  github: GitHub
  open_recipe: Open the recipe
  # {count} is the number of options in the setup state, filled at build time.
  show_all_options: "Show all {count} options"
notes:
  external: (external site)
  no_js: Turn on JavaScript to change the setup. This page shows a regional site with one 96 GB GPU, with batch work sharing the GPUs.
  no_js_link: It may not match the setup in a shared link.
footer:
  notes:
    licence: Docs CC BY 4.0 · Code Apache-2.0
    otel: OTel here means the OTel model family, not OpenTelemetry.
home:
  hero:
    eyebrow: Open-source telecom AI blueprints
    headline: Run telecom AI use cases in production, with the models, platform, and controls each one needs.
    notes:
      lede: Pick a use case, see what it takes on your hardware, and follow a sourced recipe.
      otel: OTel is a family of open models tuned for telecom, not OpenTelemetry.
    buttons:
      otel_link: See the models
    otel_path: platform/intake-model-selection/
  how:
    headings:
      title: How it works
    steps:
      headings:
        - Pick a use case
        - See what it takes for your setup
        - Follow the recipe
      notes:
        - Start from the outcome you want.
        - Models, sizing, settings, and approvals for your hardware.
        - Step-by-step build, gates, and sources.
  goals:
    headings:
      title: What do you want to improve?
  gallery:
    headings:
      title: All use cases
      empty: No use case matches these filters
    notes:
      empty: Try fewer filters, or clear them to see all use cases.
    buttons:
      clear: Clear filters
      view: View use case
    filters:
      label: Filter use cases
      headings:
        domain: Domain
        stage: How far it goes
        tiers: Where it runs
      tiers:
        far-edge: Far edge
        regional: Regional site
        core: Core
    result_count: "{n} of {total} use cases"
    counts:
      slots:
        one: model slot
        other: model slots
      blueprints:
        one: platform blueprint
        other: platform blueprints
      tiers:
        one: site tier
        other: site tiers
      separator: " · "
    status:
      done: Recipe published
      review: Recipe in review
      draft: Recipe in draft
  architects:
    headings:
      title: Planning the platform?
    links:
      - label: Readiness questions
        path: framework/
      - label: Architecture overview
        path: architecture/
      - label: Platform blueprints
        path: platform/
      - label: All recipes
        path: recipes/
  note:
    headings:
      title: Open source, every claim sourced
    notes:
      body: These blueprints are open source. They're built with Red Hat products as one way to run each use case, and every claim links its source.
      replaceable: Any component can be replaced.
# Use-case page. Setup labels come from data/serving/setups.yaml through the JSON;
# count words reuse home.gallery.counts and tier labels reuse home.gallery.filters.tiers.
use_case:
  page_title: "{title} · {site}"
  rail:
    label: Use case summary and setup
    headings:
      glance: At a glance
      setup: Your setup
      nav: On this page
  setup:
    headings:
      question: Where are you deploying first?
      batch: Does batch work share the GPUs?
    notes:
      ampere: On Ampere cards, use W4A16 builds instead of FP8.
      invalid: That setup isn't in the list, so this page shows a regional site with one 96 GB GPU.
      invalid_wide: Pick your setup on the left.
      invalid_narrow: Pick your setup above.
    batch_options:
      "yes": "Yes: evaluation or training-data jobs"
      "no": "No: interactive traffic only"
    # Sentence form, used in the section sub-line and the no-JS line.
    batch_sentence:
      "yes": Batch work shares the GPUs.
      "no": Only interactive traffic uses the GPUs.
    # Live-region announcement after a change.
    announce: "Showing {setup}, {batch}."
    announce_batch:
      "yes": batch work shares the GPUs
      "no": interactive traffic only
    count_caption: advanced options worth testing on this setup
    no_js_setup: "Setup shown: {setup}."
  sections:
    nav:
      why: Why and what it takes
      setup: Recommended for your setup
      needs: What you need
      recipe: Recipe
    headings:
      setup: Recommended for your setup
      needs: What you need
      recipe: Recipe
      where: Where each model runs
      settings: Key settings
      thresholds: Thresholds you set
      advanced: Advanced serving options
    notes:
      setup_sub: "{setup}. {batch} Change your setup to update this section."
  why:
    headings:
      why: Why do it
      takes: What it takes
    rows:
      who: Who it helps
      know: How you'll know
      stage: How far it goes
      risk: Risk
      sites: Sites
      takes: Takes
    sites_join: " and "
    takes: "{slots} and {blueprints}"
  stages:
    inform: Never changes the network. People read and decide.
    recommend: Suggests fixes. An approver signs off every change.
    act: Runs approved low-risk actions once it has earned that stage. Everything else goes to a person.
  tiers:
    your_setup: Your setup
  fit:
    gpu_title: "GPU {n} of {count}: {slots}"
    weights: "Weights: about {gb} GB of {total} GB"
    pct: "{pct}% · {band}"
    bands:
      fits: Fits
      tight: Tight
      too-tight: Too tight
    messages:
      fits: Leaves room for the KV cache.
      tight: Little room for the KV cache, so plan for fewer requests at once.
      too-tight: Use FP8 builds, smaller slots, or move a slot to core.
    footnote: "Estimate: the smallest build of each slot, weights only. Leave room for the KV cache. Fits: 60% or less. Tight: up to 80%. Too tight: over 80%."
  settings:
    caption: Key settings for this setup
    columns:
      setting: Setting
      value: Value
      why: Why
    scope_setup: For this setup
    no_value: No value
  thresholds:
    caption: Thresholds and who sets them
    columns:
      parameter: Parameter
      owner: Owner
    notes:
      no_defaults: No defaults. Each owner sets the value from your own evaluation.
      quantized: "A quantized build adds one check: it must do no worse than the full-precision model on the same gates."
  advanced:
    notes:
      sub: Options to test. Each says where it helps and how to check it on your traffic with the same gates.
    # Toggle label once every option shows; the UI-SPEC wording runs past the 4-word button limit.
    toggle_fewer: Show options for this use case
    helps: "Helps here: {reason}"
    little: Little benefit for this use case.
    not_applicable: "Doesn't apply to this setup: {reason}"
    labels:
      set: Set
      check: Check
      limits: Limits
      related: "Related recipe: {title} ({source})"
    tag_join: " · "
    # Added after a "Helps here" reason when the setup stays tight with the builds swapped in.
    fit_notes:
      still-tight: Even with these builds, the fit bar shows Tight on this setup.
      still-too-tight: Even with these builds, the slots are too big for this setup. See the fit bar.
    tiers:
      far-edge: far edge
      regional: regional
      core: core
  # Not-applicable reasons keyed by reason id (data/serving/options.yaml rules).
  reasons:
    core-only: Core only. Your setup is a regional site.
    regional-only: Regional only. Your setup is a core pool.
    not-amd-paths: Not in llm-d's AMD paths.
    batch-only: Only matters when batch work shares the GPUs.
    not-needed-at-core: "Not needed at core: these GPUs fit the full-precision models."
    fits-without-fp8: "Not needed here: the full-precision builds fit this setup."
  needs:
    headings:
      models: Models
      platform: Platform
      approvals: Approvals
    notes:
      replaceable: Any component can be replaced. These show one way to build it.
    columns:
      slot: Slot
      model: Model to run
      role: Component role
      product: Red Hat product used
      action: Action
      gate: Gate outcome
      approver: Who approves
  models:
    published: "{checkpoint}, pinned by revision"
    # {precision} is FP8, or W4A16 for an Ampere build.
    operator_made: "Operator-made {precision} build of {checkpoint}. Build it with LLM Compressor and register it, pinned by digest."
    precision:
      fp8: FP8
      w4a16: W4A16
  recipe:
    title: "Build it: {title}"
    notes:
      body: Step-by-step build, full settings, gates, and the ten readiness questions to answer before production.
    tags:
      - Deploy steps
      - Verification checks
      - Governance and RACI
      - Readiness questions
      - Sources
---

<!-- Strings live in the front matter above; this body is not rendered. -->
