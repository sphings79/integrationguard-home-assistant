import { html, nothing, type TemplateResult } from "lit";
import type { Repository } from "../types";
import {
  daysAgo,
  filterRepositories,
  findingText,
  fmtDate,
  statusChip,
  STATUS_ORDER,
  usageChip,
  type Ctx,
} from "../view";

const USAGE_VALUES = [
  "used",
  "unused",
  "undetermined",
  "not_registered",
  "not_checked",
];

function detail(ctx: Ctx, item: Repository): TemplateResult {
  const { t } = ctx;
  const pushDays = daysAgo(item.last_push);
  return html`
    <div class="card">
      <div class="row wrap">
        <button class="ghost" @click=${() => ctx.patchUi({ selected: null })}>
          ← ${t("common.back")}
        </button>
        <div class="spacer"></div>
        ${item.url
          ? html`<a class="ghost" href=${item.url} target="_blank" rel="noreferrer"
              >${t("repo.github")}</a
            >`
          : nothing}
        ${item.hacs_url
          ? html`<a class="ghost" href=${item.hacs_url}>${t("repo.manage")}</a>`
          : nothing}
      </div>

      <h2>${item.name}</h2>
      <p class="sub">${item.key}</p>
      ${item.description ? html`<p>${item.description}</p>` : nothing}

      <div class="row wrap chips">
        ${statusChip(t, item.status)} ${usageChip(t, item.usage)}
        ${item.usage_confidence
          ? html`<span class="chip"
              >${t(`confidence.${item.usage_confidence}`)}</span
            >`
          : nothing}
        <span class="chip">${t(`category.${item.category}`)}</span>
        ${item.is_default_store
          ? nothing
          : html`<span class="chip">${t("repo.custom")}</span>`}
        ${item.ignored ? html`<span class="chip">${t("repo.ignored")}</span>` : nothing}
        ${ctx.data.marked_used.includes(item.key)
          ? html`<span class="chip">${t("repo.marked_used")}</span>`
          : nothing}
      </div>

      <div class="facts">
        <div><span>${t("repo.score")}</span><b>${item.score}</b></div>
        <div>
          <span>${t("repo.installed")}</span
          ><b>${item.installed_version || "—"}</b>
        </div>
        <div>
          <span>${t("repo.available")}</span
          ><b>${item.available_version || "—"}</b>
        </div>
        <div>
          <span>${t("repo.last_push")}</span>
          <b>
            ${fmtDate(item.last_push, ctx.language)}
            ${pushDays === null ? "" : ` (${pushDays} ${t("common.days")})`}
          </b>
        </div>
        <div>
          <span>${t("repo.last_release")}</span
          ><b>${fmtDate(item.last_release_at, ctx.language)}</b>
        </div>
        <div><span>${t("repo.stars")}</span><b>${item.stars ?? "—"}</b></div>
        <div>
          <span>${t("repo.issues")}</span><b>${item.open_issues ?? "—"}</b>
        </div>
        ${item.category === "app"
          ? html`
              <div>
                <span>${t("repo.app_state")}</span
                ><b>${item.app_state ?? "—"}</b>
              </div>
              <div>
                <span>${t("repo.app_boot")}</span>
                <b>${item.app_boot === "auto" ? t("common.yes") : t("common.no")}</b>
              </div>
            `
          : nothing}
      </div>

      <h3>${t("repo.findings")}</h3>
      ${item.findings.length === 0
        ? html`<p class="empty">${t("repo.no_findings")}</p>`
        : html`<ul class="findings">
            ${item.findings.map(
              (finding) => html`<li>
                ${findingText(t, finding)}
                <span class="penalty">−${finding.penalty}</span>
              </li>`,
            )}
          </ul>`}

      <div class="row wrap actions">
        <button @click=${() => ctx.ignore(item.key, !item.ignored)}>
          ${item.ignored ? t("repo.unignore") : t("repo.ignore")}
        </button>
        <button
          @click=${() =>
            ctx.markUsed(item.key, !ctx.data.marked_used.includes(item.key))}
        >
          ${ctx.data.marked_used.includes(item.key)
            ? t("repo.unmark_used")
            : t("repo.mark_used")}
        </button>
      </div>
    </div>
  `;
}

export function renderRepositories(ctx: Ctx): TemplateResult {
  const { t, data, ui } = ctx;
  if (ui.selected) {
    const item = data.repositories.find((entry) => entry.key === ui.selected);
    if (item) return detail(ctx, item);
  }

  const items = filterRepositories(ui, data.repositories);
  return html`
    <div class="card">
      <div class="row wrap filters">
        <input
          type="search"
          .value=${ui.search}
          placeholder=${t("repo.search")}
          @input=${(event: Event) =>
            ctx.patchUi({ search: (event.target as HTMLInputElement).value })}
        />
        <select
          .value=${ui.category}
          @change=${(event: Event) =>
            ctx.patchUi({ category: (event.target as HTMLSelectElement).value })}
        >
          <option value="">${t("repo.category")}: ${t("common.all")}</option>
          ${data.categories.map(
            (category) =>
              html`<option value=${category} ?selected=${ui.category === category}>
                ${t(`category.${category}`)}
              </option>`,
          )}
        </select>
        <select
          @change=${(event: Event) =>
            ctx.patchUi({ status: (event.target as HTMLSelectElement).value })}
        >
          <option value="">${t("repo.status")}: ${t("common.all")}</option>
          ${STATUS_ORDER.map(
            (status) =>
              html`<option value=${status} ?selected=${ui.status === status}>
                ${t(`status.${status}`)}
              </option>`,
          )}
        </select>
        <select
          @change=${(event: Event) =>
            ctx.patchUi({ usage: (event.target as HTMLSelectElement).value })}
        >
          <option value="">${t("repo.usage")}: ${t("common.all")}</option>
          ${USAGE_VALUES.map(
            (usage) =>
              html`<option value=${usage} ?selected=${ui.usage === usage}>
                ${t(`usage.${usage}`)}
              </option>`,
          )}
        </select>
        <label class="checkbox">
          <input
            type="checkbox"
            .checked=${ui.showIgnored}
            @change=${(event: Event) =>
              ctx.patchUi({
                showIgnored: (event.target as HTMLInputElement).checked,
              })}
          />
          ${t("repo.show_ignored")}
        </label>
        <div class="spacer"></div>
        <span class="hint"
          >${t("repo.count", {
            count: items.length,
            total: data.repositories.length,
          })}</span
        >
      </div>
    </div>

    <div class="card flush">
      ${items.length === 0
        ? html`<p class="empty pad">${t("repo.none")}</p>`
        : html`<div class="list">
            ${items.map(
              (item) => html`
                <div
                  class="list-item clickable"
                  @click=${() => ctx.patchUi({ selected: item.key })}
                >
                  <div class="grow">
                    <div class="name">
                      ${item.name}
                      ${item.ignored
                        ? html`<span class="chip small"
                            >${t("repo.ignored")}</span
                          >`
                        : nothing}
                    </div>
                    <div class="sub">
                      ${item.key} · ${t(`category.${item.category}`)}
                    </div>
                  </div>
                  <span class="score">${item.score}</span>
                  ${item.usage === "unused" || item.usage === "not_registered"
                    ? usageChip(t, item.usage)
                    : nothing}
                  ${statusChip(t, item.status)}
                </div>
              `,
            )}
          </div>`}
    </div>
  `;
}
