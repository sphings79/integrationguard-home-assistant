import { html, type TemplateResult } from "lit";
import type { Localizer } from "./localize";
import type {
  Channel,
  Finding,
  HistoryEvent,
  PanelData,
  Repository,
  Rule,
  Settings,
  Severity,
  Status,
} from "./types";

/** What every view gets handed by the panel shell. */
export interface Ctx {
  t: Localizer;
  data: PanelData;
  language: string;
  busy: boolean;
  /** View-local state the shell keeps for us. */
  ui: UiState;
  patchUi(patch: Partial<UiState>): void;
  /** Show one repository's detail, from wherever the user clicked. */
  open(key: string): void;
  scan(force?: boolean): void;
  saveSettings(settings: Settings, githubToken?: string): void;
  saveRules(rules: Rule[]): void;
  saveSeverities(severities: Severity[]): void;
  saveChannel(channel: Channel): void;
  deleteChannel(id: string): void;
  testChannel(channel: Channel): void;
  ignore(key: string, ignored: boolean): void;
  markUsed(key: string, used: boolean): void;
  loadHistory(): void;
  toast(message: string): void;
}

export interface UiState {
  search: string;
  category: string;
  status: string;
  usage: string;
  showIgnored: boolean;
  selected: string | null;
  editingChannel: Channel | null;
  history: HistoryEvent[] | null;
  historyKind: string;
}

export const EMPTY_UI: UiState = {
  search: "",
  category: "",
  status: "",
  usage: "",
  showIgnored: false,
  selected: null,
  editingChannel: null,
  history: null,
  historyKind: "",
};

export const STATUS_ORDER: Status[] = [
  "healthy",
  "info",
  "stale",
  "abandoned",
  "critical",
];

/** Theme colours, so the panel does not invent its own palette. */
export const STATUS_COLOR: Record<string, string> = {
  healthy: "var(--success-color, #4caf50)",
  info: "var(--info-color, #039be5)",
  stale: "var(--warning-color, #ffa726)",
  abandoned: "var(--error-color, #db4437)",
  critical: "var(--error-color, #db4437)",
};

export const USAGE_COLOR: Record<string, string> = {
  used: "var(--success-color, #4caf50)",
  unused: "var(--warning-color, #ffa726)",
  not_registered: "var(--error-color, #db4437)",
  undetermined: "var(--secondary-text-color)",
  not_checked: "var(--secondary-text-color)",
};

/** Render one finding as a sentence, from its key and its values. */
export function findingText(t: Localizer, finding: Finding): string {
  return t(`finding.${finding.rule_id}`, finding.params);
}

/** Format a stored timestamp in the browser's locale, or a dash. */
export function fmtDate(value: string | null, language: string): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleDateString(language, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

/** Format a timestamp with the time of day. */
export function fmtDateTime(value: string | null, language: string): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleString(language, { dateStyle: "short", timeStyle: "short" });
}

/** How many whole days ago a timestamp lies. */
export function daysAgo(value: string | null): number | null {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return Math.floor((Date.now() - date.getTime()) / 86400000);
}

export function statusChip(t: Localizer, status: string): TemplateResult {
  return html`<span
    class="badge solid"
    style="background:${STATUS_COLOR[status] ?? "var(--secondary-text-color)"}"
    >${t(`status.${status}`)}</span
  >`;
}

export function usageChip(t: Localizer, usage: string): TemplateResult {
  return html`<span
    class="badge solid"
    style="background:${USAGE_COLOR[usage] ?? "var(--secondary-text-color)"}"
    >${t(`usage.${usage}`)}</span
  >`;
}

/** Apply the filter bar to the repository list. */
export function filterRepositories(ui: UiState, items: Repository[]): Repository[] {
  const needle = ui.search.trim().toLowerCase();
  return items.filter((item) => {
    if (!ui.showIgnored && item.ignored) return false;
    if (ui.category && item.category !== ui.category) return false;
    if (ui.status && item.status !== ui.status) return false;
    if (ui.usage && item.usage !== ui.usage) return false;
    if (
      needle &&
      !item.name.toLowerCase().includes(needle) &&
      !item.key.toLowerCase().includes(needle)
    )
      return false;
    return true;
  });
}
