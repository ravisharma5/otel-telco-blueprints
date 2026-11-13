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
notes:
  external: (external site)
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
---

<!-- Strings live in the front matter above; this body is not rendered. -->
