// Typed accessors over the exported explorer data. Every decision (fit, filters,
// stage, counts) is made by tools/site/export_explorer.py; this file only reads it.
// The JSON is written by `make explorer-data` and is not tracked.
import data from '../generated/explorer.json';

export interface Stage {
  id: string;
  label: string;
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

export interface Flag {
  setting: string;
  value: string | null;
  why: string;
  scope: string;
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
  excluded_slots: string[];
  state: 'helps' | 'little' | 'not-applicable';
  reason_id: string | null;
  reason_text: string | null;
  would_help: boolean;
  fit_note_id: string | null;
}

export interface State {
  tiers: TierCard[];
  fit: FitEntry[];
  flags: Flag[];
  variants: Variant[];
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
  memory_per_gpu_gb: number;
  vendor: string;
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
  card: Card;
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
}

export interface Default {
  setup: string;
  batch: string;
}

export const useCases = data.use_cases as unknown as UseCase[];
export const filters = data.filters as Filters;
export const defaults = data.default as Default;
export const setups = data.setups as Setup[];
export const batchValues = ['yes', 'no'] as const;

/** Key of one precomputed state, as used in data-state attributes. */
export function stateKey(setup: string, batch: string): string {
  return `${setup}|${batch}`;
}

/** Every state of a use case, in setup order then batch order. */
export function statesOf(uc: UseCase): { key: string; setup: Setup; batch: string; state: State }[] {
  const out = [];
  for (const setup of setups) {
    for (const batch of batchValues) {
      out.push({ key: stateKey(setup.id, batch), setup, batch, state: uc.states[setup.id][batch] });
    }
  }
  return out;
}

/** Fill {name} placeholders in a copy template. */
export function fill(template: string, values: Record<string, string | number>): string {
  return template.replace(/\{(\w+)\}/g, (match, name) =>
    name in values ? String(values[name]) : match,
  );
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
