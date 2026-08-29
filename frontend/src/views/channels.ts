import { html, nothing, type TemplateResult } from "lit";
import type { Channel, ChannelField } from "../types";
import type { Ctx } from "../view";

const SECRET_PLACEHOLDER = "__unchanged__";

function blank(kind: string, fields: ChannelField[]): Channel {
  const config: Record<string, unknown> = {};
  for (const field of fields) {
    if (field.default !== undefined) config[field.key] = field.default;
  }
  return {
    id: "",
    name: "",
    kind,
    enabled: true,
    config,
    title_template: "",
    template: "",
  };
}

function renderField(
  ctx: Ctx,
  channel: Channel,
  field: ChannelField,
  patch: (change: Partial<Channel>) => void,
): TemplateResult {
  const { t } = ctx;
  const value = channel.config[field.key];
  const set = (raw: unknown) =>
    patch({ config: { ...channel.config, [field.key]: raw } });
  const label = html`<span
    >${t(`field.${field.key}`)}${field.required ? " *" : ""}</span
  >`;

  if (field.type === "select") {
    return html`<label class="field">
      ${label}
      <select @change=${(e: Event) => set((e.target as HTMLSelectElement).value)}>
        ${(field.options ?? []).map(
          (option) =>
            html`<option value=${option} ?selected=${String(value) === option}>
              ${option}
            </option>`,
        )}
      </select>
    </label>`;
  }

  if (field.type === "object") {
    return html`<label class="field">
      ${label}
      <textarea
        rows="3"
        .value=${value ? JSON.stringify(value, null, 2) : ""}
        @change=${(e: Event) => {
          const raw = (e.target as HTMLTextAreaElement).value.trim();
          if (!raw) return set(undefined);
          try {
            set(JSON.parse(raw));
          } catch {
            ctx.toast(t("common.error"));
          }
        }}
      ></textarea>
    </label>`;
  }

  const isSecret = field.type === "secret";
  return html`<label class="field">
    ${label}
    <input
      type=${isSecret ? "password" : field.type === "number" ? "number" : "text"}
      placeholder=${field.example ?? ""}
      .value=${value === undefined || value === null ? "" : String(value)}
      @change=${(e: Event) => {
        const raw = (e.target as HTMLInputElement).value;
        set(field.type === "number" ? Number(raw) : raw);
      }}
    />
    ${isSecret && value === SECRET_PLACEHOLDER
      ? html`<span class="hint">${t("channels.secret_kept")}</span>`
      : nothing}
  </label>`;
}

function editor(ctx: Ctx, channel: Channel): TemplateResult {
  const { t, data } = ctx;
  const fields = data.channel_fields[channel.kind] ?? [];
  const patch = (change: Partial<Channel>) =>
    ctx.patchUi({ editingChannel: { ...channel, ...change } });

  return html`
    <div class="card">
      <h2>${channel.id ? channel.name || t("channels.name") : t("channels.add")}</h2>
      <div class="row wrap">
        <label class="field">
          <span>${t("channels.name")}</span>
          <input
            type="text"
            .value=${channel.name}
            @change=${(e: Event) =>
              patch({ name: (e.target as HTMLInputElement).value })}
          />
        </label>
        <label class="field">
          <span>${t("channels.kind")}</span>
          <select
            @change=${(e: Event) => {
              const kind = (e.target as HTMLSelectElement).value;
              ctx.patchUi({
                editingChannel: {
                  ...blank(kind, data.channel_fields[kind] ?? []),
                  id: channel.id,
                  name: channel.name,
                },
              });
            }}
          >
            ${Object.keys(data.channel_fields).map(
              (kind) =>
                html`<option value=${kind} ?selected=${kind === channel.kind}>
                  ${t(`kind.${kind}`)}
                </option>`,
            )}
          </select>
        </label>
        <label class="checkbox">
          <input
            type="checkbox"
            .checked=${channel.enabled}
            @change=${(e: Event) =>
              patch({ enabled: (e.target as HTMLInputElement).checked })}
          />
          ${t("channels.enabled")}
        </label>
      </div>

      <div class="row wrap">
        ${fields.map((field) => renderField(ctx, channel, field, patch))}
      </div>

      <h3>${t("channels.templates")}</h3>
      <p class="hint">${t("channels.template_hint")}</p>
      <label class="field wide">
        <span>${t("channels.title_template")}</span>
        <input
          type="text"
          .value=${channel.title_template}
          @change=${(e: Event) =>
            patch({ title_template: (e.target as HTMLInputElement).value })}
        />
      </label>
      <label class="field wide">
        <span>${t("channels.body_template")}</span>
        <textarea
          rows="4"
          .value=${channel.template}
          @change=${(e: Event) =>
            patch({ template: (e.target as HTMLTextAreaElement).value })}
        ></textarea>
      </label>

      <div class="row wrap actions">
        <button class="primary" ?disabled=${ctx.busy} @click=${() => ctx.saveChannel(channel)}>
          ${t("common.save")}
        </button>
        <button ?disabled=${ctx.busy} @click=${() => ctx.testChannel(channel)}>
          ${t("common.test")}
        </button>
        <button class="ghost" @click=${() => ctx.patchUi({ editingChannel: null })}>
          ${t("common.cancel")}
        </button>
        <div class="spacer"></div>
        ${channel.id
          ? html`<button
              class="danger"
              ?disabled=${ctx.busy}
              @click=${() => ctx.deleteChannel(channel.id)}
            >
              ${t("common.delete")}
            </button>`
          : nothing}
      </div>
    </div>
  `;
}

export function renderChannels(ctx: Ctx): TemplateResult {
  const { t, data, ui } = ctx;
  if (ui.editingChannel) return editor(ctx, ui.editingChannel);

  return html`
    <div class="card">
      <h2>${t("tab.channels")}</h2>
      <p class="hint">${t("channels.description")}</p>
      ${data.channels.length === 0
        ? html`<p class="empty">${t("channels.none")}</p>`
        : html`<div class="list">
            ${data.channels.map(
              (channel) => html`
                <div
                  class="list-item clickable"
                  @click=${() => ctx.patchUi({ editingChannel: channel })}
                >
                  <div class="grow">
                    <div class="name">
                      ${channel.name || t(`kind.${channel.kind}`)}
                    </div>
                    <div class="sub">${t(`kind.${channel.kind}`)}</div>
                  </div>
                  ${channel.enabled
                    ? nothing
                    : html`<span class="chip small">${t("common.no")}</span>`}
                </div>
              `,
            )}
          </div>`}
      <div class="row actions">
        <button
          class="primary"
          @click=${() =>
            ctx.patchUi({
              editingChannel: blank(
                "ha_service",
                data.channel_fields.ha_service ?? [],
              ),
            })}
        >
          ${t("channels.add")}
        </button>
      </div>
    </div>
  `;
}
