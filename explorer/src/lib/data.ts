// Typed accessors over the exported explorer data. Every decision (fit, filters,
// stage, counts) is made by tools/site/export_explorer.py; this file only reads it.
// The JSON is written by `make explorer-data` and is not tracked.
import data from '../generated/explorer.json';

export interface Stage {
  id: string;
  label: string;
}

export interface Depth {
  id: 'recipe' | 'entry';
  label: string;
}

/** A goal tile: a goal id from data/explorer/goals.yaml with at least one use case. */
export interface Goal {
  id: string;
  count: number;
}

export interface Card {
  goal: string;
  summary: string;
  outcome: string;
  audience: string;
  measures: string[];
  risk: string;
}

export interface Counts {
  slots: number;
  blueprints: number;
  tiers: number;
}

export interface SlotRef {
  role: string;
  slot_name: string;
}

export interface TierCard {
  tier: string;
  used: boolean;
  matches_setup: boolean;
  slots: SlotRef[];
  note: string;
}

export interface FitEntry {
  gpu_index: number;
  gpu_count: number;
  slots: (SlotRef & { weights_gb: number })[];
  weights_gb: number;
  total_gb: number;
  pct: number;
  band: 'fits' | 'tight' | 'too-tight';
  message_id: 'fits' | 'tight' | 'too-tight' | 'too-tight-after-fp8';
}

export interface Source {
  url: string;
  label: string;
}

export interface Flag {
  setting: string;
  value: string | null;
  why: string;
  scope: string;
  sources: Source[];
}

export interface Variant {
  role: string;
  slot_name: string;
  tier: string;
  variant_id: string;
  checkpoint: string;
  precision: string;
  operator_made: boolean;
  model_card: string;
  red_hat_build: string | null;
}

export interface Related {
  title: string;
  url: string;
  source: string;
}

export interface Option {
  id: string;
  name: string;
  engine: string;
  tiers: string[];
  what: string;
  set: string[];
  check: string;
  limits: string[];
  related: Related[];
  sources: Source[];
  excluded_slots: string[];
  state: 'helps' | 'little' | 'not-applicable';
  reason_id: string | null;
  reason_text: string | null;
  reason_roles: string[];
  would_help: boolean;
  fit_note_id: string | null;
}

/** Weights of the far-edge slots on a CPU-only setup; no band and no percent. */
export interface CpuFit {
  slots: (SlotRef & { weights_gb: number })[];
  weights_gb: number;
  memory_parameter: string;
}

export interface State {
  tiers: TierCard[];
  /** False when no slot of the use case runs at the setup's tier. */
  runs_here: boolean;
  fit: FitEntry[];
  cpu_fit: CpuFit | null;
  flags: Flag[];
  variants: Variant[];
  other_tier_variants: Variant[];
  quantized_check: boolean;
  options: Option[];
  options_worth_testing: number;
}

export interface Setup {
  id: string;
  label: string;
  tier: string;
  ampere_note: boolean;
  gpu_count: number;
  memory_per_gpu_gb: number | null;
  vendor: string | null;
  cpu_only: boolean;
  /** ["yes", "no"] for GPU setups; ["any"] for a setup with one state. */
  batch_values: string[];
}

export interface Adaptation {
  rung: 'retrieval' | 'skills' | 'retrieval-and-skills' | 'head-retrain' | 'lora-if-gap';
  change: 'none' | 'retrain';
  rung_label: string;
  expertise: { id: string; label: string }[];
}

export interface Sandbox {
  fit: 'none' | 'execution' | 'whole-agent';
  label: string;
  why: string;
}

/** The use case's story, read from the recipe; an entry has no steps and no example. */
export interface Story {
  problem: string;
  steps: string[];
  example: { title: string; text: string } | null;
}

export interface UseCase {
  id: string;
  slug: string;
  domain: string;
  domain_label: string;
  title: string;
  recipe_url: string;
  doc_status: 'done' | 'review' | 'draft';
  stage: Stage;
  goal: string;
  depth: Depth;
  adaptation: Adaptation;
  sandbox: Sandbox;
  try_it_url: string | null;
  card: Card;
  story: Story;
  counts: Counts;
  slot_names: string[];
  platform_rows: string[][];
  approvals: string[][];
  parameters: string[][];
  states: Record<string, Record<string, State>>;
}

export interface Filters {
  domains: { id: string; label: string }[];
  stages: Stage[];
  tiers: string[];
  depths: Depth['id'][];
  changes: Adaptation['change'][];
}

export interface FitBands {
  fits_max_pct: number;
  tight_max_pct: number;
}

export interface Default {
  setup: string;
  batch: string;
}

/** An exploration idea: shown on the Ideas sub-tab, never in the gallery. */
export interface Idea {
  id: string;
  title: string;
  slug: string;
  domain: { id: string; label: string };
  depth: Depth;
  why: string;
  promote: string[];
  merged_into: string | null;
  docs_url: string;
}

export const useCases = data.use_cases as unknown as UseCase[];
export const ideas = (data.ideas ?? []) as unknown as Idea[];
export const filters = data.filters as Filters;
export const goals = data.goals as Goal[];
export const defaults = data.default as Default;
export const setups = data.setups as Setup[];
/** Fit band edges from data/serving/setups.yaml; ticks and footnote read these. */
export const fitBands = data.fit_bands as FitBands;
export const batchValues = ['yes', 'no'] as const;

/** Key of one precomputed state, as used in data-state attributes. */
export function stateKey(setup: string, batch: string): string {
  return `${setup}|${batch}`;
}

/** Setups with one state: the batch choice does not change them. */
export function singleState(setup: Setup): boolean {
  return setup.batch_values.length === 1;
}

/** Every state of a use case, in setup order then batch order. A CPU setup has one. */
export function statesOf(uc: UseCase): { key: string; setup: Setup; batch: string; state: State }[] {
  const out = [];
  for (const setup of setups) {
    for (const batch of setup.batch_values) {
      out.push({ key: stateKey(setup.id, batch), setup, batch, state: uc.states[setup.id][batch] });
    }
  }
  return out;
}

/** Fill {name} placeholders in a copy template. */
export function fill(template: string, values: Record<string, string | number>): string {
  return template.replace(/\{(\w+)\}/g, (match, name) =>
    Object.hasOwn(values, name) ? String(values[name]) : match,
  );
}

/** Join list items as prose: "a", "a and b", "a, b, and c". */
export function joinList(items: string[], and: string): string {
  if (items.length <= 2) return items.join(` ${and} `);
  return `${items.slice(0, -1).join(', ')}, ${and} ${items[items.length - 1]}`;
}

/** Split data text on backticks so code spans render as <code> (no HTML parsing). */
export function codeParts(text: string): { code: boolean; text: string }[] {
  return text.split('`').map((part, i) => ({ code: i % 2 === 1, text: part })).filter((p) => p.text);
}

/** Numbers as the page shows them: 48, 69.4. */
export function num(value: number): string {
  return String(value);
}

/** Tiers a use case runs in, read from its default state's tier cards. */
export function usedTiers(uc: UseCase): string[] {
  const state = uc.states[defaults.setup][defaults.batch];
  return state.tiers.filter((card) => card.used).map((card) => card.tier);
}

/** Link to a use-case page under the site base. */
export function useCasePath(uc: UseCase): string {
  return `${import.meta.env.BASE_URL}use-cases/${uc.slug}/`;
}
