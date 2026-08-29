import { html, nothing, type TemplateResult } from "lit";
import type { Rule } from "../types";
import type { Ctx } from "../view";

export function renderRules(ctx: Ctx): TemplateResult {
  const { t, data } = ctx;
  const byId = new Map(data.rules.map((rule) => [rule.id, rule]));

  const patch = (id: string, change: Partial<Rule>) => {
    const next = data.rules.map((rule) =>
      rule.id === id ? { ...rule, ...change } : rule,
    );
    ctx.saveRules(next);
  };

  const reset = () => {
    ctx.saveRules(
      data.rule_catalogue.map((definition) => ({
        id: definition.id,
        enabled: true,
        severity_id: definition.default_severity,
        penalty: definition.default_penalty,
        threshold: definition.default_threshold,
      })),
    );
  };

  return html`
    <div class="card">
      <h2>${t("tab.rules")}</h2>
      <p class="hint">${t("rules.description")}</p>
      <div class="row">
        <div class="spacer"></div>
        <button class="ghost" ?disabled=${ctx.busy} @click=${reset}>
          ${t("rules.reset")}
        </button>
      </div>
    </div>

    <div class="card flush">
      <div class="list">
        ${data.rule_catalogue.map((definition) => {
          const rule = byId.get(definition.id);
          if (!rule) return nothing;
          const onlyApps =
            definition.categories?.length === 1 &&
            definition.categories[0] === "app";
          const onlyHacs =
            definition.categories !== null && !definition.categories?.includes("app");
          return html`
            <div class="list-item rule">
              <label class="checkbox">
                <input
                  type="checkbox"
                  .checked=${rule.enabled}
                  ?disabled=${ctx.busy}
                  @change=${(event: Event) =>
                    patch(rule.id, {
                      enabled: (event.target as HTMLInputElement).checked,
                    })}
                />
              </label>
              <div class="grow">
                <div class="name">${t(`rule.${rule.id}`)}</div>
                <div class="sub">
                  ${definition.requires_github
                    ? html`<span class="chip small">${t("rules.needs_token")}</span>`
                    : nothing}
                  ${onlyApps
                    ? html`<span class="chip small">${t("rules.apps_only")}</span>`
                    : nothing}
                  ${onlyHacs
                    ? html`<span class="chip small">${t("rules.hacs_only")}</span>`
                    : nothing}
                </div>
              </div>
              ${definition.threshold_unit
                ? html`<label class="field small">
                    <span>${t("rules.threshold")}</span>
                    <span class="suffixed">
                      <input
                        type="number"
                        min="0"
                        .value=${String(rule.threshold ?? "")}
                        ?disabled=${ctx.busy || !rule.enabled}
                        @change=${(event: Event) =>
                          patch(rule.id, {
                            threshold: Number(
                              (event.target as HTMLInputElement).value,
                            ),
                          })}
                      />
                      <span class="suffix"
                        >${definition.threshold_unit === "days"
                          ? t("common.days")
                          : ""}</span
                      >
                    </span>
                  </label>`
                : nothing}
              <label class="field small">
                <span>${t("rules.penalty")}</span>
                <input
                  type="number"
                  min="0"
                  max="100"
                  .value=${String(rule.penalty)}
                  ?disabled=${ctx.busy || !rule.enabled}
                  @change=${(event: Event) =>
                    patch(rule.id, {
                      penalty: Number((event.target as HTMLInputElement).value),
                    })}
                />
              </label>
              <label class="field severity-field">
                <span>${t("rules.severity")}</span>
                <select
                  ?disabled=${ctx.busy || !rule.enabled}
                  @change=${(event: Event) =>
                    patch(rule.id, {
                      severity_id: (event.target as HTMLSelectElement).value,
                    })}
                >
                  ${data.severities.map(
                    (severity) => html`
                      <option
                        value=${severity.id}
                        ?selected=${severity.id === rule.severity_id}
                      >
                        ${severity.name}
                      </option>
                    `,
                  )}
                </select>
              </label>
            </div>
          `;
        })}
      </div>
    </div>

    ${renderSeverities(ctx)}
  `;
}

function renderSeverities(ctx: Ctx): TemplateResult {
  const { t, data } = ctx;
  const patch = (id: string, change: Record<string, unknown>) =>
    ctx.saveSeverities(
      data.severities.map((severity) =>
        severity.id === id ? { ...severity, ...change } : severity,
      ),
    );

  return html`
    <div class="card">
      <h2>${t("severities.title")}</h2>
      <p class="hint">${t("severities.description")}</p>
      <div class="list">
        ${data.severities.map(
          (severity) => html`
            <div class="list-item severity">
              <div class="grow">
                <input
                  type="text"
                  .value=${severity.name}
                  ?disabled=${ctx.busy}
                  @change=${(event: Event) =>
                    patch(severity.id, {
                      name: (event.target as HTMLInputElement).value,
                    })}
                />
                <div class="sub">${severity.id}</div>
              </div>
              <label class="field small">
                <span>${t("severities.priority")}</span>
                <input
                  type="number"
                  min="0"
                  max="100"
                  .value=${String(severity.priority)}
                  ?disabled=${ctx.busy}
                  @change=${(event: Event) =>
                    patch(severity.id, {
                      priority: Number((event.target as HTMLInputElement).value),
                    })}
                />
              </label>
              <label class="checkbox">
                <input
                  type="checkbox"
                  .checked=${severity.persistent_notification}
                  ?disabled=${ctx.busy}
                  @change=${(event: Event) =>
                    patch(severity.id, {
                      persistent_notification: (event.target as HTMLInputElement)
                        .checked,
                    })}
                />
                ${t("severities.persistent")}
              </label>
              <label class="checkbox">
                <input
                  type="checkbox"
                  .checked=${severity.ignore_quiet_hours}
                  ?disabled=${ctx.busy}
                  @change=${(event: Event) =>
                    patch(severity.id, {
                      ignore_quiet_hours: (event.target as HTMLInputElement)
                        .checked,
                    })}
                />
                ${t("severities.ignore_quiet")}
              </label>
              <div class="channels">
                <span class="sub">${t("severities.channels")}</span>
                ${data.channels.length === 0
                  ? html`<span class="sub">${t("common.none")}</span>`
                  : data.channels.map(
                      (channel) => html`
                        <label class="checkbox">
                          <input
                            type="checkbox"
                            .checked=${severity.channels.includes(channel.id)}
                            ?disabled=${ctx.busy}
                            @change=${(event: Event) => {
                              const on = (event.target as HTMLInputElement).checked;
                              const channels = on
                                ? [...severity.channels, channel.id]
                                : severity.channels.filter(
                                    (id) => id !== channel.id,
                                  );
                              patch(severity.id, { channels });
                            }}
                          />
                          ${channel.name || t(`kind.${channel.kind}`)}
                        </label>
                      `,
                    )}
              </div>
            </div>
          `,
        )}
      </div>
    </div>
  `;
}
