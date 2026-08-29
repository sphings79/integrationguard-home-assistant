import { html, nothing, type TemplateResult } from "lit";
import { fmtDateTime, STATUS_COLOR, type Ctx } from "../view";

/** A working integration with an open repair message is a warning, not an error. */
function colour(state: string, muted: boolean): string {
  if (muted) return "var(--secondary-text-color)";
  return state === "ok" ? STATUS_COLOR.stale : STATUS_COLOR.abandoned;
}

export function renderRuntime(ctx: Ctx): TemplateResult {
  const { t, data } = ctx;
  const problems = data.runtime.filter((item) => item.problem);
  const waiting = data.runtime.filter(
    (item) => !item.problem && item.state !== "ok",
  );

  const entry = (item: (typeof data.runtime)[number], muted: boolean) => html`
    <div class="list-item">
      <div class="grow">
        <div class="name">${item.title || item.domain}</div>
        <div class="sub">
          ${item.domain} · ${t(`runtime.${item.state}`)}
          ${item.since ? ` · ${t("runtime.since", {
            time: fmtDateTime(item.since, ctx.language),
          })}` : ""}
          ${muted ? ` · ${t("runtime.waiting")}` : ""}
        </div>
        ${item.reason ? html`<div class="sub reason">${item.reason}</div>` : nothing}
        ${item.repairs.length
          ? html`<div class="sub">
              ${t("runtime.repairs")}:
              ${item.repairs
                .map((issue) => issue.translation_key || issue.issue_id)
                .join(", ")}
            </div>`
          : nothing}
        ${item.entries.length > 1
          ? html`<div class="sub">
              ${t("runtime.entries", { count: item.entries.length })}
            </div>`
          : nothing}
      </div>
      <a class="ghost" href=${item.configuration_url}>${t("runtime.open")}</a>
      ${item.url
        ? html`<a class="ghost" href=${item.url} target="_blank" rel="noreferrer"
            >${t("repo.github")}</a
          >`
        : nothing}
      <span
        class="badge solid"
        style="background:${colour(item.state, muted)}"
        >${t(`runtime.${item.state}`)}</span
      >
    </div>
  `;

  return html`
    <div class="card">
      <h2>${t("runtime.title")}</h2>
      ${problems.length === 0 && waiting.length === 0
        ? html`<p class="empty">${t("runtime.no_problems")}</p>`
        : html`<div class="list">
            ${problems.map((item) => entry(item, false))}
            ${waiting.map((item) => entry(item, true))}
          </div>`}
    </div>
  `;
}
