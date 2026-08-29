import { html, nothing, type TemplateResult } from "lit";
import {
  fmtDateTime,
  statusChip,
  STATUS_COLOR,
  STATUS_ORDER,
  type Ctx,
} from "../view";

/** The score as a ring, so the number is readable at a glance. */
function ring(score: number | null): TemplateResult {
  const value = score ?? 0;
  const colour =
    value >= 90
      ? STATUS_COLOR.healthy
      : value >= 70
        ? STATUS_COLOR.stale
        : STATUS_COLOR.abandoned;
  const circumference = 2 * Math.PI * 34;
  const dash = (circumference * value) / 100;
  return html`
    <svg viewBox="0 0 80 80" class="ring" role="img" aria-label="${value}">
      <circle
        cx="40"
        cy="40"
        r="34"
        fill="none"
        stroke="var(--divider-color, rgba(127,127,127,.25))"
        stroke-width="8"
      />
      <circle
        cx="40"
        cy="40"
        r="34"
        fill="none"
        stroke=${colour}
        stroke-width="8"
        stroke-linecap="round"
        stroke-dasharray="${dash} ${circumference}"
        transform="rotate(-90 40 40)"
      />
      <text x="40" y="46" text-anchor="middle" class="ring-value">
        ${score === null ? "–" : value}
      </text>
    </svg>
  `;
}

function tile(label: string, value: string | number, colour?: string) {
  return html`
    <div class="tile">
      <div class="tile-value" style=${colour ? `color:${colour}` : nothing}>
        ${value}
      </div>
      <div class="tile-label">${label}</div>
    </div>
  `;
}

export function renderOverview(ctx: Ctx): TemplateResult {
  const { t, data } = ctx;
  const visible = data.repositories.filter((item) => !item.ignored);
  const problems = visible.filter((item) => item.status !== "healthy");
  const unused = visible.filter((item) => item.usage === "unused");
  const runtimeProblems = data.runtime.filter((item) => item.problem);
  const repairs = data.runtime.reduce((sum, item) => sum + item.repairs.length, 0);
  const worst = [...problems].sort((a, b) => a.score - b.score).slice(0, 8);
  const byStatus = STATUS_ORDER.map(
    (status) =>
      [status, visible.filter((item) => item.status === status).length] as const,
  ).filter(([, count]) => count > 0);

  const errors = Object.entries(data.scan.errors);
  // t() hands back the key when it knows no sentence for it. Anything the
  // catalogue does not cover is shown as it came out of the backend.
  const errorText = ([key, detail]: [string, string]) => {
    const full = `overview.error.${key}`;
    const text = t(full);
    return text === full ? `${key}: ${detail}` : text;
  };

  return html`
    <div class="card">
      <div class="row wrap head">
        ${ring(data.scan.score)}
        <div class="tiles">
          ${tile(t("overview.repositories"), visible.length)}
          ${tile(
            t("overview.problems"),
            problems.length,
            problems.length ? STATUS_COLOR.stale : undefined,
          )}
          ${tile(
            t("overview.unused"),
            unused.length,
            unused.length ? STATUS_COLOR.stale : undefined,
          )}
          ${tile(
            t("overview.runtime"),
            runtimeProblems.length,
            runtimeProblems.length ? STATUS_COLOR.abandoned : undefined,
          )}
          ${tile(t("overview.repairs"), repairs)}
        </div>
        <div class="spacer"></div>
        <div class="scan">
          <button
            class="primary"
            ?disabled=${ctx.busy}
            @click=${() => ctx.scan()}
          >
            ${ctx.busy ? t("overview.scanning") : t("overview.scan_now")}
          </button>
          <p class="hint">
            ${t("overview.last_scan")}:
            ${data.scan.last
              ? fmtDateTime(data.scan.last, ctx.language)
              : t("common.never")}
          </p>
        </div>
      </div>

      ${byStatus.length
        ? html`<div class="bar">
            ${byStatus.map(
              ([status, count]) => html`
                <div
                  class="bar-part"
                  style="flex:${count};background:${STATUS_COLOR[status]}"
                  title="${t(`status.${status}`)}: ${count}"
                ></div>
              `,
            )}
          </div>`
        : nothing}

      ${errors.length
        ? html`<p class="error">
            ${t("overview.errors")}
            ${errors.map((entry) => html`<br />${errorText(entry)}`)}
          </p>`
        : nothing}
      ${data.scan.has_token
        ? nothing
        : html`<p class="hint">${t("overview.no_token")}</p>`}
      ${data.scan.github_pending
        ? html`<p class="hint">
            ${t("overview.github_pending", { count: data.scan.github_pending })}
          </p>`
        : nothing}
      ${data.scan.github_remaining !== null
        ? html`<p class="hint">
            ${t("overview.github_budget", { count: data.scan.github_remaining })}
          </p>`
        : nothing}
    </div>

    <div class="card">
      <h2>${t("overview.worst")}</h2>
      ${!data.scan.last
        ? html`<p class="empty">${t("overview.never_scanned")}</p>`
        : worst.length === 0
          ? html`<p class="empty">${t("overview.nothing_wrong")}</p>`
          : html`<div class="list">
              ${worst.map(
                (item) => html`
                  <div
                    class="list-item clickable"
                    @click=${() =>
                      ctx.patchUi({ selected: item.key, search: "" })}
                  >
                    <div class="grow">
                      <div class="name">${item.name}</div>
                      <div class="sub">${item.key}</div>
                    </div>
                    <span class="score">${item.score}</span>
                    ${statusChip(t, item.status)}
                  </div>
                `,
              )}
            </div>`}
    </div>
  `;
}
