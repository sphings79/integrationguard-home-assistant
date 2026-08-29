import { LitElement, css, html, nothing, type TemplateResult } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { IntegrationGuardApi } from "./api";
import {
  fallbackLocalizer,
  loadCatalogue,
  localize,
  type Localizer,
} from "./localize";
import { sharedStyles } from "./styles";
import type { Channel, HomeAssistant, PanelData, Rule, Settings, Severity } from "./types";
import { EMPTY_UI, type Ctx, type UiState } from "./view";
import { renderChannels } from "./views/channels";
import { renderHistory } from "./views/history";
import { renderOverview } from "./views/overview";
import { renderRepositories } from "./views/repositories";
import { renderRules } from "./views/rules";
import { renderRuntime } from "./views/runtime";
import { renderSettings } from "./views/settings";
import { renderUnused } from "./views/unused";

type Tab =
  | "overview"
  | "repositories"
  | "unused"
  | "runtime"
  | "rules"
  | "channels"
  | "history"
  | "settings";

const ADMIN_TABS: Tab[] = ["rules", "channels", "settings"];

/** Sidebar panel: navigation, data loading and every action the views need. */
@customElement("integrationguard-panel")
export class IntegrationGuardPanel extends LitElement {
  @property({ attribute: false }) hass!: HomeAssistant;
  @property({ type: Boolean }) narrow = false;

  @state() private data: PanelData | null = null;
  @state() private tab: Tab = "overview";
  @state() private busy = false;
  @state() private message = "";
  @state() private ui: UiState = { ...EMPTY_UI };
  @state() private localizeFn: Localizer = fallbackLocalizer;

  private api: IntegrationGuardApi | null = null;
  private catalogueFor = "";

  static styles = [
    sharedStyles,
    css`
      :host {
        display: block;
        padding: 16px;
        max-width: 1100px;
        margin: 0 auto;
        box-sizing: border-box;
      }
      header {
        display: flex;
        align-items: center;
        gap: 12px;
        flex-wrap: wrap;
        margin-bottom: 16px;
      }
      h1 {
        font-size: 1.5rem;
        font-weight: 500;
        margin: 0;
      }
      nav {
        display: flex;
        gap: 4px;
        flex-wrap: wrap;
        margin-bottom: 16px;
      }
      nav button {
        background: none;
        border: none;
        border-bottom: 2px solid transparent;
        color: var(--secondary-text-color);
        padding: 8px 12px;
        cursor: pointer;
        font-size: 0.95rem;
        border-radius: 0;
      }
      nav button.active {
        color: var(--primary-color);
        border-bottom-color: var(--primary-color);
      }
      nav button .count {
        display: inline-block;
        min-width: 18px;
        margin-left: 6px;
        padding: 0 5px;
        border-radius: 9px;
        background: var(--secondary-background-color, rgba(127, 127, 127, 0.2));
        font-size: 0.75rem;
      }
      .toast {
        position: fixed;
        left: 50%;
        bottom: 24px;
        transform: translateX(-50%);
        background: var(--primary-color);
        color: var(--text-primary-color, #fff);
        padding: 10px 18px;
        border-radius: 20px;
        z-index: 10;
      }
      .head {
        gap: 24px;
      }
      .ring {
        width: 96px;
        height: 96px;
        flex: none;
      }
      .ring-value {
        fill: var(--primary-text-color);
        font-size: 22px;
        font-weight: 600;
      }
      .tiles {
        display: flex;
        gap: 20px;
        flex-wrap: wrap;
      }
      .tile-value {
        font-size: 1.6rem;
        font-weight: 600;
      }
      .tile-label {
        color: var(--secondary-text-color);
        font-size: 0.8rem;
      }
      .bar {
        display: flex;
        height: 8px;
        border-radius: 4px;
        overflow: hidden;
        margin-top: 16px;
      }
      .bar-part {
        height: 100%;
      }
      .grow {
        flex: 1;
        min-width: 0;
      }
      .name {
        font-weight: 500;
      }
      .sub {
        color: var(--secondary-text-color);
        font-size: 0.8rem;
        word-break: break-word;
      }
      .sub.reason {
        color: var(--error-color, #db4437);
      }
      .score {
        font-variant-numeric: tabular-nums;
        color: var(--secondary-text-color);
        margin-right: 8px;
      }
      .clickable {
        cursor: pointer;
      }
      .clickable:hover {
        background: var(--secondary-background-color, rgba(127, 127, 127, 0.08));
      }
      .facts {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 10px 20px;
        margin: 16px 0;
      }
      .facts div {
        display: flex;
        justify-content: space-between;
        gap: 12px;
        border-bottom: var(--ig-border);
        padding-bottom: 4px;
      }
      .facts span {
        color: var(--secondary-text-color);
      }
      .findings {
        margin: 0;
        padding-left: 18px;
      }
      .findings li {
        margin-bottom: 4px;
      }
      .penalty {
        color: var(--secondary-text-color);
        font-size: 0.8rem;
        margin-left: 6px;
      }
      .filters {
        gap: 8px;
      }
      /* The shared form styling stretches inputs to the full width, which is
         right in a stacked form and wrong in a filter bar. */
      .filters input:not([type="checkbox"]),
      .filters select {
        width: auto;
        min-width: 150px;
      }
      .filters input[type="search"] {
        min-width: 220px;
      }
      .field {
        display: flex;
        flex-direction: column;
        gap: 4px;
        font-size: 0.85rem;
        color: var(--secondary-text-color);
      }
      .field.wide {
        width: 100%;
        margin-top: 12px;
      }
      .field input:not([type="checkbox"]),
      .field select,
      .field textarea {
        width: 100%;
        box-sizing: border-box;
      }
      .checkbox input[type="checkbox"] {
        width: auto;
        min-width: 0;
        flex: none;
      }
      .field.small input,
      .field.small select {
        width: 90px;
        min-width: 90px;
      }
      .field.severity-field select {
        width: 150px;
      }
      .list-item.rule,
      .list-item.severity {
        flex-wrap: wrap;
        gap: 12px;
      }
      .channels {
        display: flex;
        gap: 10px;
        flex-wrap: wrap;
        align-items: center;
        width: 100%;
      }
      .pad {
        padding: 16px;
      }
      .actions {
        margin-top: 16px;
      }
      a.ghost {
        text-decoration: none;
      }
      /* The browser default is unreadable on a dark theme. */
      a {
        color: var(--primary-color);
      }
      input,
      select,
      textarea {
        font: inherit;
        color: var(--primary-text-color);
        background: var(--card-background-color, #fff);
        border: var(--ig-border);
        border-radius: 8px;
        padding: 7px 10px;
      }
      button {
        font: inherit;
        border-radius: 20px;
        border: var(--ig-border);
        background: none;
        color: var(--primary-text-color);
        padding: 7px 16px;
        cursor: pointer;
      }
      button.primary {
        background: var(--primary-color);
        color: var(--text-primary-color, #fff);
        border-color: transparent;
      }
      button.danger {
        color: var(--error-color, #db4437);
      }
      button.ghost,
      a.ghost {
        border: none;
        color: var(--primary-color);
        padding: 7px 10px;
      }
      button[disabled] {
        opacity: 0.5;
        cursor: default;
      }
    `,
  ];

  private get isAdmin(): boolean {
    return this.hass?.user?.is_admin ?? false;
  }

  protected willUpdate(): void {
    if (!this.hass) return;
    if (!this.api) {
      this.api = new IntegrationGuardApi(this.hass);
      void this.load();
    } else {
      this.api.update(this.hass);
    }
    void this.syncCatalogue();
  }

  private get language(): string {
    const configured = this.data?.settings.ui_language;
    if (configured && configured !== "auto") return configured;
    return this.hass?.language || "en";
  }

  private async syncCatalogue(): Promise<void> {
    const language = this.language;
    if (language === this.catalogueFor) return;
    this.catalogueFor = language;
    this.localizeFn = localize(await loadCatalogue(language));
  }

  private async load(): Promise<void> {
    if (!this.api) return;
    try {
      this.data = await this.api.get();
    } catch (error) {
      this.message = String((error as { message?: string })?.message ?? error);
    }
  }

  /** Run one action, then reload so every view sees the same truth. */
  private async run(action: () => Promise<unknown>, ok?: string): Promise<void> {
    if (this.busy) return;
    this.busy = true;
    try {
      await action();
      if (ok) this.toast(ok);
    } catch (error) {
      this.toast(
        String((error as { message?: string })?.message ?? this.localizeFn("common.error")),
      );
    } finally {
      this.busy = false;
      await this.load();
    }
  }

  private toast(message: string): void {
    this.message = message;
    window.setTimeout(() => {
      if (this.message === message) this.message = "";
    }, 4000);
  }

  private context(): Ctx {
    const t = this.localizeFn;
    return {
      t,
      data: this.data!,
      language: this.language,
      busy: this.busy,
      ui: this.ui,
      patchUi: (patch) => {
        this.ui = { ...this.ui, ...patch };
      },
      scan: (force = false) => void this.run(() => this.api!.scan(force)),
      saveSettings: (settings: Settings, token?: string) =>
        void this.run(
          () => this.api!.saveSettings(settings, token),
          t("common.saved"),
        ),
      saveRules: (rules: Rule[]) =>
        void this.run(() => this.api!.saveRules(rules), t("common.saved")),
      saveSeverities: (severities: Severity[]) =>
        void this.run(
          () => this.api!.saveSeverities(severities),
          t("common.saved"),
        ),
      saveChannel: (channel: Channel) =>
        void this.run(async () => {
          await this.api!.saveChannel(channel);
          this.ui = { ...this.ui, editingChannel: null };
        }, t("common.saved")),
      deleteChannel: (id: string) =>
        void this.run(async () => {
          await this.api!.deleteChannel(id);
          this.ui = { ...this.ui, editingChannel: null };
        }),
      testChannel: (channel: Channel) =>
        void this.run(
          () => this.api!.testChannel(channel),
          t("channels.test_ok"),
        ),
      ignore: (key: string, ignored: boolean) =>
        void this.run(() => this.api!.ignore(key, ignored)),
      markUsed: (key: string, used: boolean) =>
        void this.run(() => this.api!.markUsed(key, used)),
      loadHistory: () => void this.fetchHistory(),
      toast: (message: string) => this.toast(message),
    };
  }

  private async fetchHistory(): Promise<void> {
    if (!this.api || this.ui.history !== null) return;
    // Placeholder first, so the view does not ask again while it loads.
    this.ui = { ...this.ui, history: [] };
    try {
      const result = await this.api.history({
        limit: 200,
        kind: this.ui.historyKind || null,
      });
      this.ui = { ...this.ui, history: result.events };
    } catch {
      this.ui = { ...this.ui, history: [] };
    }
  }

  private tabs(): [Tab, string, number | null][] {
    const data = this.data;
    const visible = data?.repositories.filter((item) => !item.ignored) ?? [];
    const all: [Tab, string, number | null][] = [
      ["overview", "tab.overview", null],
      ["repositories", "tab.repositories", visible.length],
      [
        "unused",
        "tab.unused",
        visible.filter(
          (item) => item.usage === "unused" || item.usage === "not_registered",
        ).length,
      ],
      [
        "runtime",
        "tab.runtime",
        (data?.runtime ?? []).filter((item) => item.problem).length,
      ],
      ["rules", "tab.rules", null],
      ["channels", "tab.channels", null],
      ["history", "tab.history", null],
      ["settings", "tab.settings", null],
    ];
    return this.isAdmin
      ? all
      : all.filter(([tab]) => !ADMIN_TABS.includes(tab));
  }

  private body(): TemplateResult {
    const ctx = this.context();
    switch (this.tab) {
      case "repositories":
        return renderRepositories(ctx);
      case "unused":
        return renderUnused(ctx);
      case "runtime":
        return renderRuntime(ctx);
      case "rules":
        return renderRules(ctx);
      case "channels":
        return renderChannels(ctx);
      case "history":
        return renderHistory(ctx);
      case "settings":
        return renderSettings(ctx);
      default:
        return renderOverview(ctx);
    }
  }

  render() {
    const t = this.localizeFn;
    if (!this.data) {
      return html`<div class="card"><p class="empty">${t("common.loading")}</p></div>`;
    }
    return html`
      <header>
        <h1>IntegrationGuard</h1>
      </header>
      <nav>
        ${this.tabs().map(
          ([tab, label, count]) => html`
            <button
              class=${tab === this.tab ? "active" : ""}
              @click=${() => {
                this.tab = tab;
                this.ui = { ...this.ui, selected: null, editingChannel: null };
              }}
            >
              ${t(label)}
              ${count ? html`<span class="count">${count}</span>` : nothing}
            </button>
          `,
        )}
      </nav>
      ${this.body()}
      ${this.message ? html`<div class="toast">${this.message}</div>` : nothing}
    `;
  }
}
