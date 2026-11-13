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

export interface TierCard {
  tier: string;
  used: boolean;
  matches_setup: boolean;
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
  states: Record<string, Record<string, { tiers: TierCard[] }>>;
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

/** Tiers a use case runs in, read from its default state's tier cards. */
export function usedTiers(uc: UseCase): string[] {
  const state = uc.states[defaults.setup][defaults.batch];
  return state.tiers.filter((card) => card.used).map((card) => card.tier);
}

/** Link to a use-case page under the site base. */
export function useCasePath(uc: UseCase): string {
  return `${import.meta.env.BASE_URL}use-cases/${uc.slug}/`;
}
