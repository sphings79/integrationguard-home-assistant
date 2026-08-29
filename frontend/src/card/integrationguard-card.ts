import { LitElement, css, html, nothing, type TemplateResult } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import {
  fallbackLocalizer,
  loadCatalogue,
  localize,
  type Localizer,
} from "../localize";
import type { HomeAssistant, Status } from "../types";
import { STATUS_COLOR, STATUS_ORDER } from "../view";
import "./integrationguard-card-editor";

interface CardData {
  score: number | null;
  last_scan: string | null;
  total: number;
  problems: {
    key: string;
    name: string;
    category: string;
    status: Status;
    score: number;
    usage: string;
    url: string;
  }[];
  unused: number;
  runtime: { domain: string; name: string; state: string; url: string }[];
}

export interface CardConfig {
  type: string;
  title?: string;
  max_items?: number;
  min_status?: Status;
  show_score?: boolean;
  show_runtime?: boolean;
}

const REFRESH_MS = 60_000;

/** Compact view of what needs attention, for any dashboard. */
@customElement("integrationguard-card")
export class IntegrationGuardCard extends LitElement {
  @property({ attribute: false }) hass!: HomeAssistant;
  @state() private config: CardConfig = { type: "" };
  @state() private data: CardData | null = null;
  @state() private localizeFn: Localizer = fallbackLocalizer;

  private timer?: number;
  private catalogueFor = "";

  static getConfigElement() {
    return document.createElement("integrationguard-card-editor");
  }

  static getStubConfig(): CardConfig {
    return { type: "custom:integrationguard-card", show_score: true };
  }

  setConfig(config: CardConfig): void {
    this.config = { max_items: 5, show_score: true, show_runtime: true, ...config };
  }

  getCardSize(): number {
    return 1 + Math.min(this.config.max_items ?? 5, this.data?.problems.length ?? 1);
  }

  connectedCallback(): void {
    super.connectedCallback();
    this.timer = window.setInterval(() => void this.fetch(), REFRESH_MS);
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    if (this.timer) window.clearInterval(this.timer);
  }

  protected willUpdate(): void {
    if (!this.hass) return;
    if (this.data === null) void this.fetch();
    void this.syncCatalogue();
  }

  private async syncCatalogue(): Promise<void> {
    const language = this.hass.language || "en";
    if (language === this.catalogueFor) return;
    this.catalogueFor = language;
    this.localizeFn = localize(await loadCatalogue(language));
  }

  private async fetch(): Promise<void> {
    if (!this.hass) return;
    try {
      this.data = await this.hass.callWS<CardData>({
        type: "integrationguard/card",
      });
    } catch {
      this.data = {
        score: null,
        last_scan: null,
        total: 0,
        problems: [],
        unused: 0,
        runtime: [],
      };
    }
  }

  private ring(score: number): TemplateResult {
    const colour =
      score >= 90
        ? STATUS_COLOR.healthy
        : score >= 70
          ? STATUS_COLOR.stale
          : STATUS_COLOR.abandoned;
    const circumference = 2 * Math.PI * 26;
    return html`
      <svg viewBox="0 0 60 60" class="ring" role="img" aria-label="${score}">
        <circle
          cx="30"
          cy="30"
          r="26"
          fill="none"
          stroke="var(--divider-color, rgba(127,127,127,.25))"
          stroke-width="6"
        />
        <circle
          cx="30"
          cy="30"
          r="26"
          fill="none"
          stroke=${colour}
          stroke-width="6"
          stroke-linecap="round"
          stroke-dasharray="${(circumference * score) / 100} ${circumference}"
          transform="rotate(-90 30 30)"
        />
        <text x="30" y="35" text-anchor="middle">${score}</text>
      </svg>
    `;
  }

  render() {
    const t = this.localizeFn;
    if (!this.data) return nothing;

    const minIndex = STATUS_ORDER.indexOf(this.config.min_status ?? "info");
    const problems = this.data.problems.filter(
      (item) => STATUS_ORDER.indexOf(item.status) >= minIndex,
    );
    const runtime = this.config.show_runtime ? this.data.runtime : [];
    const limit = this.config.max_items ?? 5;
    const shown = [...problems].slice(0, limit);
    const hidden = problems.length - shown.length;

    return html`
      <ha-card>
        <div class="head">
          ${this.config.show_score && this.data.score !== null
            ? this.ring(this.data.score)
            : nothing}
          <div class="grow">
            <div class="title">${this.config.title ?? t("card.title")}</div>
            <div class="sub">
              ${t("overview.problems")}: ${problems.length} ·
              ${t("overview.unused")}: ${this.data.unused} ·
              ${t("overview.runtime")}: ${this.data.runtime.length}
            </div>
          </div>
        </div>
        ${shown.length === 0 && runtime.length === 0
          ? html`<div class="empty">${t("card.nothing")}</div>`
          : html`<div class="list">
              ${runtime.map(
                (item) => html`
                  <a class="item" href=${item.url}>
                    <span class="grow">${item.name}</span>
                    <span
                      class="dot"
                      style="background:${STATUS_COLOR.abandoned}"
                    ></span>
                    <span class="state">${t(`runtime.${item.state}`)}</span>
                  </a>
                `,
              )}
              ${shown.map(
                (item) => html`
                  <a
                    class="item"
                    href=${item.url || "#"}
                    target=${item.url ? "_blank" : nothing}
                    rel="noreferrer"
                  >
                    <span class="grow">${item.name}</span>
                    <span
                      class="dot"
                      style="background:${STATUS_COLOR[item.status]}"
                    ></span>
                    <span class="state">${t(`status.${item.status}`)}</span>
                  </a>
                `,
              )}
              ${hidden > 0
                ? html`<div class="more">${t("card.more", { count: hidden })}</div>`
                : nothing}
            </div>`}
      </ha-card>
    `;
  }

  static styles = css`
    ha-card {
      padding: 16px;
      /* Set explicitly so the card reads correctly even where the host does
         not hand a colour down. */
      color: var(--primary-text-color);
    }
    .head {
      display: flex;
      align-items: center;
      gap: 16px;
    }
    .grow {
      flex: 1;
      min-width: 0;
    }
    .item .grow {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .title {
      font-size: 1.1rem;
      font-weight: 500;
    }
    .sub,
    .more,
    .empty {
      color: var(--secondary-text-color);
      font-size: 0.85rem;
    }
    .empty,
    .more {
      padding-top: 12px;
    }
    .ring {
      width: 60px;
      height: 60px;
      flex: none;
    }
    .ring text {
      fill: var(--primary-text-color);
      font-size: 18px;
      font-weight: 600;
    }
    .list {
      margin-top: 12px;
      display: flex;
      flex-direction: column;
    }
    .item {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px 0;
      border-top: 1px solid var(--divider-color, rgba(127, 127, 127, 0.25));
      color: var(--primary-text-color);
      text-decoration: none;
    }
    .dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      flex: none;
    }
    .state {
      color: var(--secondary-text-color);
      font-size: 0.85rem;
    }
  `;
}

declare global {
  interface Window {
    customCards?: { type: string; name: string; description: string }[];
  }
}

window.customCards = window.customCards || [];
window.customCards.push({
  type: "integrationguard-card",
  name: "IntegrationGuard",
  description: "Health of your installed extensions at a glance",
});
