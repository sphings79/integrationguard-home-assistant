import { html, nothing, type TemplateResult } from "lit";
import { AVAILABLE_LANGUAGES } from "../localize";
import type { Settings } from "../types";
import type { Ctx } from "../view";

const INTERVALS = [1, 3, 6, 12, 24, 48, 168];
const WEEKDAYS = [0, 1, 2, 3, 4, 5, 6];

export function renderSettings(ctx: Ctx): TemplateResult {
  const { t, data } = ctx;
  const settings = data.settings;

  const patch = (change: Partial<Settings>) =>
    ctx.saveSettings({ ...settings, ...change });

  const categoryPicker = (
    label: string,
    selected: string[],
    key: "categories_health" | "categories_usage",
  ) => html`
    <div class="field wide">
      <span>${label}</span>
      <div class="row wrap">
        ${data.categories.map(
          (category) => html`
            <label class="checkbox">
              <input
                type="checkbox"
                .checked=${selected.includes(category)}
                ?disabled=${ctx.busy}
                @change=${(event: Event) => {
                  const on = (event.target as HTMLInputElement).checked;
                  const next = on
                    ? [...selected, category]
                    : selected.filter((item) => item !== category);
                  patch({ [key]: next } as Partial<Settings>);
                }}
              />
              ${t(`category.${category}`)}
            </label>
          `,
        )}
      </div>
    </div>
  `;

  return html`
    <div class="card">
      <h2>${t("settings.scan")}</h2>
      <div class="row wrap">
        <label class="field">
          <span>${t("settings.scan_interval")}</span>
          <select
            ?disabled=${ctx.busy}
            @change=${(event: Event) =>
              patch({
                scan_interval_hours: Number(
                  (event.target as HTMLSelectElement).value,
                ),
              })}
          >
            ${INTERVALS.map(
              (hours) => html`
                <option
                  value=${hours}
                  ?selected=${settings.scan_interval_hours === hours}
                >
                  ${hours} ${t("common.hours")}
                </option>
              `,
            )}
          </select>
        </label>
        <label class="field">
          <span>${t("settings.scan_time")}</span>
          <input
            type="time"
            .value=${settings.scan_time}
            ?disabled=${ctx.busy}
            @change=${(event: Event) =>
              patch({ scan_time: (event.target as HTMLInputElement).value })}
          />
        </label>
      </div>
      <p class="hint">${t("settings.scan_time_hint")}</p>
      ${categoryPicker(
        t("settings.categories_health"),
        settings.categories_health,
        "categories_health",
      )}
      ${categoryPicker(
        t("settings.categories_usage"),
        settings.categories_usage,
        "categories_usage",
      )}
      <label class="checkbox">
        <input
          type="checkbox"
          .checked=${settings.check_orphans}
          ?disabled=${ctx.busy}
          @change=${(event: Event) =>
            patch({ check_orphans: (event.target as HTMLInputElement).checked })}
        />
        ${t("settings.check_orphans")}
      </label>
    </div>

    <div class="card">
      <h2>${t("settings.github")}</h2>
      <p class="hint">${t("settings.github_token_hint")}</p>
      ${data.scan.has_token
        ? html`<p class="hint">${t("settings.github_token_set")}</p>`
        : nothing}
      <label class="field wide">
        <span>${t("settings.github_token")}</span>
        <input
          type="password"
          autocomplete="off"
          placeholder=${data.scan.has_token ? "••••••••" : ""}
          ?disabled=${ctx.busy}
          @change=${(event: Event) => {
            const value = (event.target as HTMLInputElement).value;
            ctx.saveSettings(settings, value);
          }}
        />
      </label>
    </div>

    <div class="card">
      <h2>${t("settings.runtime")}</h2>
      <label class="checkbox">
        <input
          type="checkbox"
          .checked=${settings.runtime_enabled}
          ?disabled=${ctx.busy}
          @change=${(event: Event) =>
            patch({
              runtime_enabled: (event.target as HTMLInputElement).checked,
            })}
        />
        ${t("settings.runtime_enabled")}
      </label>
      <label class="checkbox">
        <input
          type="checkbox"
          .checked=${settings.runtime_include_all}
          ?disabled=${ctx.busy || !settings.runtime_enabled}
          @change=${(event: Event) =>
            patch({
              runtime_include_all: (event.target as HTMLInputElement).checked,
            })}
        />
        ${t("settings.runtime_include_all")}
      </label>
      <label class="field">
        <span>${t("settings.runtime_grace")}</span>
        <span class="suffixed">
          <input
            type="number"
            min="0"
            .value=${String(settings.runtime_grace_minutes)}
            ?disabled=${ctx.busy || !settings.runtime_enabled}
            @change=${(event: Event) =>
              patch({
                runtime_grace_minutes: Number(
                  (event.target as HTMLInputElement).value,
                ),
              })}
          />
          <span class="suffix">${t("common.minutes")}</span>
        </span>
      </label>
      <p class="hint">${t("settings.runtime_grace_hint")}</p>
    </div>

    <div class="card">
      <h2>${t("settings.notifications")}</h2>
      <label class="checkbox">
        <input
          type="checkbox"
          .checked=${settings.notify_on_recovery}
          ?disabled=${ctx.busy}
          @change=${(event: Event) =>
            patch({
              notify_on_recovery: (event.target as HTMLInputElement).checked,
            })}
        />
        ${t("settings.notify_on_recovery")}
      </label>

      <h3>${t("settings.quiet_hours")}</h3>
      <label class="checkbox">
        <input
          type="checkbox"
          .checked=${settings.quiet_hours.enabled}
          ?disabled=${ctx.busy}
          @change=${(event: Event) =>
            patch({
              quiet_hours: {
                ...settings.quiet_hours,
                enabled: (event.target as HTMLInputElement).checked,
              },
            })}
        />
        ${t("settings.quiet_enabled")}
      </label>
      <div class="row wrap">
        <label class="field">
          <span>${t("settings.quiet_from")}</span>
          <input
            type="time"
            .value=${settings.quiet_hours.start}
            ?disabled=${ctx.busy || !settings.quiet_hours.enabled}
            @change=${(event: Event) =>
              patch({
                quiet_hours: {
                  ...settings.quiet_hours,
                  start: (event.target as HTMLInputElement).value,
                },
              })}
          />
        </label>
        <label class="field">
          <span>${t("settings.quiet_to")}</span>
          <input
            type="time"
            .value=${settings.quiet_hours.end}
            ?disabled=${ctx.busy || !settings.quiet_hours.enabled}
            @change=${(event: Event) =>
              patch({
                quiet_hours: {
                  ...settings.quiet_hours,
                  end: (event.target as HTMLInputElement).value,
                },
              })}
          />
        </label>
      </div>
      <div class="field wide">
        <span>${t("settings.quiet_weekdays")}</span>
        <div class="row wrap">
          ${WEEKDAYS.map(
            (day) => html`
              <label class="checkbox">
                <input
                  type="checkbox"
                  .checked=${settings.quiet_hours.weekdays.length === 0 ||
                  settings.quiet_hours.weekdays.includes(day)}
                  ?disabled=${ctx.busy || !settings.quiet_hours.enabled}
                  @change=${(event: Event) => {
                    const on = (event.target as HTMLInputElement).checked;
                    const current =
                      settings.quiet_hours.weekdays.length === 0
                        ? [...WEEKDAYS]
                        : settings.quiet_hours.weekdays;
                    const next = on
                      ? [...new Set([...current, day])].sort()
                      : current.filter((item) => item !== day);
                    patch({
                      quiet_hours: { ...settings.quiet_hours, weekdays: next },
                    });
                  }}
                />
                ${t(`weekday.${day}`)}
              </label>
            `,
          )}
        </div>
      </div>
      <p class="hint">${t("settings.quiet_hint")}</p>
    </div>

    <div class="card">
      <h2>${t("settings.panel")}</h2>
      <div class="row wrap">
        <label class="field">
          <span>${t("settings.panel_access")}</span>
          <select
            ?disabled=${ctx.busy}
            @change=${(event: Event) =>
              patch({
                panel_access: (event.target as HTMLSelectElement)
                  .value as Settings["panel_access"],
              })}
          >
            <option value="admins" ?selected=${settings.panel_access === "admins"}>
              ${t("settings.panel_admins")}
            </option>
            <option value="all" ?selected=${settings.panel_access === "all"}>
              ${t("settings.panel_all")}
            </option>
          </select>
        </label>
        <label class="field">
          <span>${t("settings.language")}</span>
          <select
            ?disabled=${ctx.busy}
            @change=${(event: Event) =>
              patch({ ui_language: (event.target as HTMLSelectElement).value })}
          >
            <option value="auto" ?selected=${settings.ui_language === "auto"}>
              ${t("settings.language_auto")}
            </option>
            ${AVAILABLE_LANGUAGES.map(
              (code) =>
                html`<option value=${code} ?selected=${settings.ui_language === code}>
                  ${code}
                </option>`,
            )}
          </select>
        </label>
        <label class="field">
          <span>${t("settings.history_retention")}</span>
          <span class="suffixed">
            <input
              type="number"
              min="1"
              .value=${String(settings.history_retention_days)}
              ?disabled=${ctx.busy}
              @change=${(event: Event) =>
                patch({
                  history_retention_days: Number(
                    (event.target as HTMLInputElement).value,
                  ),
                })}
            />
            <span class="suffix">${t("common.days")}</span>
          </span>
        </label>
      </div>
    </div>
  `;
}
