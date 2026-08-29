import { LitElement, css, html } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import {
  fallbackLocalizer,
  loadCatalogue,
  localize,
  type Localizer,
} from "../localize";
import type { HomeAssistant, Status } from "../types";
import { STATUS_ORDER } from "../view";
import type { CardConfig } from "./integrationguard-card";

/** The visual editor Lovelace opens for the card. */
@customElement("integrationguard-card-editor")
export class IntegrationGuardCardEditor extends LitElement {
  @property({ attribute: false }) hass!: HomeAssistant;
  @state() private config: CardConfig = { type: "" };
  @state() private localizeFn: Localizer = fallbackLocalizer;

  private catalogueFor = "";

  setConfig(config: CardConfig): void {
    this.config = config;
  }

  protected willUpdate(): void {
    const language = this.hass?.language || "en";
    if (language === this.catalogueFor) return;
    this.catalogueFor = language;
    void loadCatalogue(language).then((catalogue) => {
      this.localizeFn = localize(catalogue);
    });
  }

  private patch(change: Partial<CardConfig>): void {
    this.config = { ...this.config, ...change };
    this.dispatchEvent(
      new CustomEvent("config-changed", {
        detail: { config: this.config },
        bubbles: true,
        composed: true,
      }),
    );
  }

  render() {
    const t = this.localizeFn;
    return html`
      <div class="form">
        <label>
          <span>${t("card.editor.title")}</span>
          <input
            type="text"
            .value=${this.config.title ?? ""}
            @change=${(event: Event) =>
              this.patch({ title: (event.target as HTMLInputElement).value })}
          />
        </label>
        <label>
          <span>${t("card.editor.max_items")}</span>
          <input
            type="number"
            min="1"
            max="50"
            .value=${String(this.config.max_items ?? 5)}
            @change=${(event: Event) =>
              this.patch({
                max_items: Number((event.target as HTMLInputElement).value),
              })}
          />
        </label>
        <label>
          <span>${t("card.editor.min_status")}</span>
          <select
            @change=${(event: Event) =>
              this.patch({
                min_status: (event.target as HTMLSelectElement).value as Status,
              })}
          >
            ${STATUS_ORDER.filter((status) => status !== "healthy").map(
              (status) => html`
                <option
                  value=${status}
                  ?selected=${(this.config.min_status ?? "info") === status}
                >
                  ${t(`status.${status}`)}
                </option>
              `,
            )}
          </select>
        </label>
        <label class="check">
          <input
            type="checkbox"
            .checked=${this.config.show_score ?? true}
            @change=${(event: Event) =>
              this.patch({
                show_score: (event.target as HTMLInputElement).checked,
              })}
          />
          <span>${t("card.editor.show_score")}</span>
        </label>
        <label class="check">
          <input
            type="checkbox"
            .checked=${this.config.show_runtime ?? true}
            @change=${(event: Event) =>
              this.patch({
                show_runtime: (event.target as HTMLInputElement).checked,
              })}
          />
          <span>${t("card.editor.show_runtime")}</span>
        </label>
      </div>
    `;
  }

  static styles = css`
    .form {
      display: flex;
      flex-direction: column;
      gap: 12px;
      padding: 8px 0;
    }
    label {
      display: flex;
      flex-direction: column;
      gap: 4px;
      color: var(--secondary-text-color);
      font-size: 0.85rem;
    }
    label.check {
      flex-direction: row;
      align-items: center;
      gap: 8px;
    }
    input,
    select {
      font: inherit;
      color: var(--primary-text-color);
      background: var(--card-background-color, #fff);
      border: 1px solid var(--divider-color, rgba(127, 127, 127, 0.25));
      border-radius: 8px;
      padding: 7px 10px;
    }
  `;
}
