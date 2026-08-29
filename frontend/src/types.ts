/** Everything the panel and the card exchange with the backend. */

export interface HomeAssistant {
  language: string;
  themes?: unknown;
  user?: { is_admin: boolean; name: string };
  states: Record<string, { state: string; attributes: Record<string, unknown> }>;
  callWS<T>(message: Record<string, unknown>): Promise<T>;
  callService(
    domain: string,
    service: string,
    data?: Record<string, unknown>,
  ): Promise<unknown>;
  formatEntityState?: (entity: unknown) => string;
}

export type Status = "healthy" | "info" | "stale" | "abandoned" | "critical";
export type Usage =
  | "used"
  | "unused"
  | "undetermined"
  | "not_registered"
  | "not_checked";
export type Confidence = "high" | "medium" | "low";

export interface Finding {
  rule_id: string;
  severity_id: string;
  penalty: number;
  params: Record<string, string | number>;
}

export interface Repository {
  key: string;
  full_name: string;
  slug: string;
  name: string;
  url: string;
  issues_url: string;
  releases_url: string;
  hacs_url: string | null;
  category: string;
  domain: string | null;
  description: string;
  installed_version: string;
  available_version: string;
  pending_update: boolean;
  is_default_store: boolean;
  last_push: string | null;
  last_release_at: string | null;
  stars: number | null;
  open_issues: number | null;
  archived: boolean | null;
  gone: boolean | null;
  removed_from_hacs: boolean;
  critical: boolean;
  min_ha_version: string | null;
  app_state: string | null;
  app_stage: string | null;
  app_boot: string | null;
  app_repository: string;
  detached: boolean | null;
  available: boolean | null;
  data_sources: Record<string, string>;
  score: number;
  status: Status;
  usage: Usage;
  usage_confidence: Confidence | null;
  usage_detail: Record<string, unknown>;
  ignored: boolean;
  findings: Finding[];
}

export interface RepairIssue {
  domain: string;
  issue_id: string;
  severity: string | null;
  is_fixable: boolean | null;
  translation_key: string | null;
  learn_more_url: string | null;
  breaks_in_ha_version: string | null;
  created: string | null;
}

export interface RuntimeEntry {
  domain: string;
  url: string | null;
  configuration_url: string;
  state: string;
  problem: boolean;
  title: string;
  full_name: string;
  reason: string;
  translation_key: string | null;
  since: string | null;
  entries: { entry_id: string; title: string; state: string; reason: string }[];
  repairs: RepairIssue[];
}

export interface Orphan {
  kind: string;
  name?: string;
  url?: string;
  path?: string;
}

export interface Severity {
  id: string;
  name: string;
  priority: number;
  color: string;
  icon: string;
  channels: string[];
  ignore_quiet_hours: boolean;
  persistent_notification: boolean;
}

export interface Rule {
  id: string;
  enabled: boolean;
  severity_id: string;
  penalty: number;
  threshold: number | null;
}

export interface RuleDefinition {
  id: string;
  default_severity: string;
  default_penalty: number;
  default_threshold: number | null;
  threshold_unit: "days" | "count" | null;
  requires_github: boolean;
  supersedes: string | null;
  categories: string[] | null;
}

export interface ChannelField {
  key: string;
  type: "text" | "number" | "secret" | "select" | "object";
  required?: boolean;
  example?: string;
  default?: string | number;
  options?: string[];
}

export interface Channel {
  id: string;
  name: string;
  kind: string;
  enabled: boolean;
  config: Record<string, unknown>;
  title_template: string;
  template: string;
}

export interface QuietHours {
  enabled: boolean;
  start: string;
  end: string;
  weekdays: number[];
}

export interface Settings {
  monitoring_enabled: boolean;
  scan_interval_hours: number;
  scan_time: string;
  categories_health: string[];
  categories_usage: string[];
  check_orphans: boolean;
  notify_on_recovery: boolean;
  runtime_enabled: boolean;
  runtime_include_all: boolean;
  runtime_grace_minutes: number;
  quiet_hours: QuietHours;
  history_retention_days: number;
  panel_access: "admins" | "all";
  ui_language: string;
}

export interface Ignore {
  key: string;
  until: string | null;
  reason: string;
}

export interface ScanMeta {
  last: string | null;
  duration: number | null;
  errors: Record<string, string>;
  github_remaining: number | null;
  github_pending: number;
  score: number | null;
  has_token: boolean;
}

export interface PanelData {
  settings: Settings;
  severities: Severity[];
  rules: Rule[];
  channels: Channel[];
  channel_fields: Record<string, ChannelField[]>;
  ignored: Ignore[];
  marked_used: string[];
  rule_catalogue: RuleDefinition[];
  categories: string[];
  runtime: RuntimeEntry[];
  runtime_states: string[];
  repositories: Repository[];
  orphans: Orphan[];
  scan: ScanMeta;
}

export interface HistoryEvent {
  id: number;
  ts: string;
  kind: string;
  key: string;
  name: string;
  category: string;
  previous: string;
  status: string;
  detail: Record<string, unknown>;
}
