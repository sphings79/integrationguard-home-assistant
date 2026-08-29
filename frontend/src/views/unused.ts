import { html, nothing, type TemplateResult } from "lit";
import type { Repository } from "../types";
import { usageChip, type Ctx } from "../view";

function group(ctx: Ctx, items: Repository[]): TemplateResult {
  const { t } = ctx;
  return html`<div class="list">
    ${items.map(
      (item) => html`
        <div
          class="list-item clickable"
          @click=${() =>
            ctx.patchUi({ selected: item.key, search: "", category: "" })}
        >
          <div class="grow">
            <div class="name">${item.name}</div>
            <div class="sub">
              ${item.key} · ${t(`category.${item.category}`)}
              ${item.usage_confidence
                ? ` · ${t(`confidence.${item.usage_confidence}`)}`
                : ""}
            </div>
          </div>
          ${usageChip(t, item.usage)}
        </div>
      `,
    )}
  </div>`;
}

export function renderUnused(ctx: Ctx): TemplateResult {
  const { t, data } = ctx;
  const visible = data.repositories.filter((item) => !item.ignored);
  const unused = visible.filter(
    (item) => item.usage === "unused" || item.usage === "not_registered",
  );
  const undetermined = visible.filter((item) => item.usage === "undetermined");
  const uncertain = unused.some((item) => {
    const dashboards = (item.usage_detail as Record<string, unknown>)
      ?.uncertain_dashboards;
    return dashboards && Object.keys(dashboards).length > 0;
  });

  return html`
    <div class="card">
      <h2>${t("unused.title")}</h2>
      <p class="hint">${t("unused.description")}</p>
      ${uncertain ? html`<p class="hint">${t("unused.uncertain")}</p>` : nothing}
      ${unused.length === 0
        ? html`<p class="empty">${t("unused.none")}</p>`
        : group(ctx, unused)}
    </div>

    ${undetermined.length
      ? html`<div class="card">
          <h2>${t("unused.undetermined_title")}</h2>
          <p class="hint">${t("unused.undetermined_description")}</p>
          ${group(ctx, undetermined)}
        </div>`
      : nothing}

    ${data.settings.check_orphans
      ? html`<div class="card">
          <h2>${t("unused.orphans")}</h2>
          <p class="hint">${t("unused.orphans_description")}</p>
          ${data.orphans.length === 0
            ? html`<p class="empty">${t("unused.no_orphans")}</p>`
            : html`<div class="list">
                ${data.orphans.map(
                  (orphan) => html`
                    <div class="list-item">
                      <div class="grow">
                        <div class="name">${orphan.name ?? orphan.url}</div>
                        <div class="sub">${orphan.path ?? ""}</div>
                      </div>
                      <span class="chip">${t(`unused.orphan.${orphan.kind}`)}</span>
                    </div>
                  `,
                )}
              </div>`}
        </div>`
      : nothing}
  `;
}
