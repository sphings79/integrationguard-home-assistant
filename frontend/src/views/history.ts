import { html, type TemplateResult } from "lit";
import { fmtDateTime, statusChip, type Ctx } from "../view";

export function renderHistory(ctx: Ctx): TemplateResult {
  const { t, ui } = ctx;
  if (ui.history === null) {
    ctx.loadHistory();
    return html`<div class="card"><p class="empty">${t("common.loading")}</p></div>`;
  }

  return html`
    <div class="card">
      <h2>${t("tab.history")}</h2>
      <p class="hint">${t("history.description")}</p>
      <div class="row wrap filters">
        <select
          @change=${(event: Event) =>
            ctx.patchUi({
              historyKind: (event.target as HTMLSelectElement).value,
              history: null,
            })}
        >
          <option value="">${t("history.kind")}: ${t("common.all")}</option>
          <option value="status" ?selected=${ui.historyKind === "status"}>
            ${t("history.kind.status")}
          </option>
          <option value="runtime" ?selected=${ui.historyKind === "runtime"}>
            ${t("history.kind.runtime")}
          </option>
        </select>
      </div>
      ${ui.history.length === 0
        ? html`<p class="empty">${t("history.none")}</p>`
        : html`<div class="list">
            ${ui.history.map(
              (event) => html`
                <div class="list-item">
                  <div class="grow">
                    <div class="name">${event.name || event.key}</div>
                    <div class="sub">
                      ${fmtDateTime(event.ts, ctx.language)} ·
                      ${t(`history.kind.${event.kind}`)} ·
                      ${event.previous
                        ? t("history.changed", {
                            previous: t(`status.${event.previous}`) || event.previous,
                            status: t(`status.${event.status}`) || event.status,
                          })
                        : t("history.appeared", {
                            status: t(`status.${event.status}`) || event.status,
                          })}
                    </div>
                  </div>
                  ${event.kind === "status"
                    ? statusChip(t, event.status)
                    : html`<span class="chip">${t(`runtime.${event.status}`)}</span>`}
                </div>
              `,
            )}
          </div>`}
    </div>
  `;
}
