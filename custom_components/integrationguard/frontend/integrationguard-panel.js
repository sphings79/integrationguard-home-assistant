import{i as z,c as n,A as c,e as _,s as f,S as C,d as b,g as R,u as k,h as E,j as x,k as O,m as N,n as q,r as m,a as W,E as I,f as T,b as j,l as F,t as P}from"./integrationguard-shared.js";class D{constructor(e){this.hass=e}update(e){this.hass=e}get(){return this.hass.callWS({type:"integrationguard/get"})}scan(e=!1){return this.hass.callWS({type:"integrationguard/scan",force:e})}saveSettings(e,a){const i={type:"integrationguard/settings/save",settings:e};return a!==void 0&&(i.github_token=a),this.hass.callWS(i)}saveRules(e){return this.hass.callWS({type:"integrationguard/rules/save",rules:e})}saveSeverities(e){return this.hass.callWS({type:"integrationguard/severities/save",severities:e})}saveChannel(e){return this.hass.callWS({type:"integrationguard/channels/save",channel:e})}deleteChannel(e){return this.hass.callWS({type:"integrationguard/channels/delete",channel_id:e})}testChannel(e){return this.hass.callWS({type:"integrationguard/channels/test",channel:e})}ignore(e,a,i=null,l=""){return this.hass.callWS({type:"integrationguard/ignore",key:e,ignored:a,until:i,reason:l})}markUsed(e,a){return this.hass.callWS({type:"integrationguard/mark_used",key:e,used:a})}history(e){return this.hass.callWS({type:"integrationguard/history",...e})}}const L=z`
  :host {
    --ig-gap: 16px;
    --ig-radius: var(--ha-card-border-radius, 12px);
    --ig-border: 1px solid var(--divider-color, rgba(127, 127, 127, 0.25));
    display: block;
    color: var(--primary-text-color);
    font-family: var(--paper-font-body1_-_font-family, inherit);
  }

  .card {
    background: var(--card-background-color, #fff);
    border-radius: var(--ig-radius);
    box-shadow: var(--ha-card-box-shadow, 0 1px 3px rgba(0, 0, 0, 0.12));
    padding: var(--ig-gap);
    margin-bottom: var(--ig-gap);
  }

  .card.flush {
    padding: 0;
    overflow: hidden;
  }

  h2 {
    font-size: 1.25rem;
    font-weight: 500;
    margin: 0 0 12px;
  }

  h3 {
    font-size: 1rem;
    font-weight: 500;
    margin: 0 0 8px;
  }

  p.hint {
    color: var(--secondary-text-color);
    font-size: 0.875rem;
    margin: 4px 0 0;
  }

  .row {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .row.wrap {
    flex-wrap: wrap;
  }

  .spacer {
    flex: 1;
  }

  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: var(--ig-gap);
  }

  label.field {
    display: block;
    margin-bottom: 14px;
  }

  label.field > span {
    display: block;
    font-size: 0.8125rem;
    color: var(--secondary-text-color);
    margin-bottom: 4px;
  }

  input[type="text"],
  input[type="number"],
  input[type="time"],
  select {
    width: 100%;
    box-sizing: border-box;
    padding: 9px 10px;
    border: var(--ig-border);
    border-radius: 8px;
    background: var(--secondary-background-color, transparent);
    color: var(--primary-text-color);
    font: inherit;
    font-size: 0.9375rem;
  }

  input:focus,
  select:focus {
    outline: 2px solid var(--primary-color);
    outline-offset: -1px;
  }

  .checkbox {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    margin-bottom: 12px;
    cursor: pointer;
  }

  .checkbox input {
    margin: 2px 0 0;
    accent-color: var(--primary-color);
    width: 18px;
    height: 18px;
    flex-shrink: 0;
  }

  .checkbox span {
    font-size: 0.9375rem;
    line-height: 1.35;
  }

  button {
    font: inherit;
    font-size: 0.9375rem;
    font-weight: 500;
    border: none;
    border-radius: 8px;
    padding: 9px 16px;
    cursor: pointer;
    background: var(--primary-color);
    color: var(--text-primary-color, #fff);
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }

  button.secondary {
    background: transparent;
    color: var(--primary-color);
    border: var(--ig-border);
  }

  button.danger {
    background: transparent;
    color: var(--error-color, #db4437);
    border: var(--ig-border);
  }

  button.plain {
    background: transparent;
    color: var(--secondary-text-color);
    padding: 6px 8px;
  }

  button:hover {
    filter: brightness(1.08);
  }

  button:disabled {
    opacity: 0.5;
    cursor: default;
  }

  .chips {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }

  .chip {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 5px 10px;
    border-radius: 999px;
    border: var(--ig-border);
    font-size: 0.8125rem;
    cursor: pointer;
    background: transparent;
    color: var(--primary-text-color);
    user-select: none;
  }

  .chip[data-selected="true"] {
    background: var(--primary-color);
    border-color: var(--primary-color);
    color: var(--text-primary-color, #fff);
  }

  .chip ha-icon {
    --mdc-icon-size: 16px;
  }

  .list-item {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 14px var(--ig-gap);
    border-bottom: var(--ig-border);
  }

  .list-item:last-child {
    border-bottom: none;
  }

  .list-item .title {
    font-size: 0.9375rem;
    font-weight: 500;
  }

  .list-item .subtitle {
    font-size: 0.8125rem;
    color: var(--secondary-text-color);
    margin-top: 2px;
  }

  .empty {
    text-align: center;
    padding: 40px 20px;
    color: var(--secondary-text-color);
  }

  .empty ha-icon {
    --mdc-icon-size: 48px;
    opacity: 0.4;
    margin-bottom: 12px;
  }

  .badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 500;
    background: var(--secondary-background-color, rgba(127, 127, 127, 0.15));
    color: var(--secondary-text-color);
  }

  /* Badges that carry a status colour of their own need readable text on it. */
  .badge.solid {
    color: var(--text-primary-color, #fff);
    white-space: nowrap;
  }

  .suffixed {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .suffixed input {
    flex: 1;
    min-width: 0;
  }

  .suffix {
    color: var(--secondary-text-color);
    font-size: 0.875rem;
    white-space: nowrap;
  }

  .error {
    color: var(--error-color, #db4437);
    font-size: 0.875rem;
    margin: 8px 0 0;
  }
`,H="__unchanged__";function U(s,e){const a={};for(const i of e)i.default!==void 0&&(a[i.key]=i.default);return{id:"",name:"",kind:s,enabled:!0,config:a,title_template:"",template:""}}function G(s,e,a,i){const{t:l}=s,r=e.config[a.key],t=p=>i({config:{...e.config,[a.key]:p}}),o=n`<span
    >${l(`field.${a.key}`)}${a.required?" *":""}</span
  >`;if(a.type==="select")return n`<label class="field">
      ${o}
      <select @change=${p=>t(p.target.value)}>
        ${(a.options??[]).map(p=>n`<option value=${p} ?selected=${String(r)===p}>
              ${p}
            </option>`)}
      </select>
    </label>`;if(a.type==="object")return n`<label class="field">
      ${o}
      <textarea
        rows="3"
        .value=${r?JSON.stringify(r,null,2):""}
        @change=${p=>{const u=p.target.value.trim();if(!u)return t(void 0);try{t(JSON.parse(u))}catch{s.toast(l("common.error"))}}}
      ></textarea>
    </label>`;const h=a.type==="secret";return n`<label class="field">
    ${o}
    <input
      type=${h?"password":a.type==="number"?"number":"text"}
      placeholder=${a.example??""}
      .value=${r==null?"":String(r)}
      @change=${p=>{const u=p.target.value;t(a.type==="number"?Number(u):u)}}
    />
    ${h&&r===H?n`<span class="hint">${l("channels.secret_kept")}</span>`:c}
  </label>`}function B(s,e){const{t:a,data:i}=s,l=i.channel_fields[e.kind]??[],r=t=>s.patchUi({editingChannel:{...e,...t}});return n`
    <div class="card">
      <h2>${e.id?e.name||a("channels.name"):a("channels.add")}</h2>
      <div class="row wrap">
        <label class="field">
          <span>${a("channels.name")}</span>
          <input
            type="text"
            .value=${e.name}
            @change=${t=>r({name:t.target.value})}
          />
        </label>
        <label class="field">
          <span>${a("channels.kind")}</span>
          <select
            @change=${t=>{const o=t.target.value;s.patchUi({editingChannel:{...U(o,i.channel_fields[o]??[]),id:e.id,name:e.name}})}}
          >
            ${Object.keys(i.channel_fields).map(t=>n`<option value=${t} ?selected=${t===e.kind}>
                  ${a(`kind.${t}`)}
                </option>`)}
          </select>
        </label>
        <label class="checkbox">
          <input
            type="checkbox"
            .checked=${e.enabled}
            @change=${t=>r({enabled:t.target.checked})}
          />
          ${a("channels.enabled")}
        </label>
      </div>

      <div class="row wrap">
        ${l.map(t=>G(s,e,t,r))}
      </div>

      <h3>${a("channels.templates")}</h3>
      <p class="hint">${a("channels.template_hint")}</p>
      <label class="field wide">
        <span>${a("channels.title_template")}</span>
        <input
          type="text"
          .value=${e.title_template}
          @change=${t=>r({title_template:t.target.value})}
        />
      </label>
      <label class="field wide">
        <span>${a("channels.body_template")}</span>
        <textarea
          rows="4"
          .value=${e.template}
          @change=${t=>r({template:t.target.value})}
        ></textarea>
      </label>

      <div class="row wrap actions">
        <button class="primary" ?disabled=${s.busy} @click=${()=>s.saveChannel(e)}>
          ${a("common.save")}
        </button>
        <button ?disabled=${s.busy} @click=${()=>s.testChannel(e)}>
          ${a("common.test")}
        </button>
        <button class="ghost" @click=${()=>s.patchUi({editingChannel:null})}>
          ${a("common.cancel")}
        </button>
        <div class="spacer"></div>
        ${e.id?n`<button
              class="danger"
              ?disabled=${s.busy}
              @click=${()=>s.deleteChannel(e.id)}
            >
              ${a("common.delete")}
            </button>`:c}
      </div>
    </div>
  `}function K(s){const{t:e,data:a,ui:i}=s;return i.editingChannel?B(s,i.editingChannel):n`
    <div class="card">
      <h2>${e("tab.channels")}</h2>
      <p class="hint">${e("channels.description")}</p>
      ${a.channels.length===0?n`<p class="empty">${e("channels.none")}</p>`:n`<div class="list">
            ${a.channels.map(l=>n`
                <div
                  class="list-item clickable"
                  @click=${()=>s.patchUi({editingChannel:l})}
                >
                  <div class="grow">
                    <div class="name">
                      ${l.name||e(`kind.${l.kind}`)}
                    </div>
                    <div class="sub">${e(`kind.${l.kind}`)}</div>
                  </div>
                  ${l.enabled?c:n`<span class="chip small">${e("common.no")}</span>`}
                </div>
              `)}
          </div>`}
      <div class="row actions">
        <button
          class="primary"
          @click=${()=>s.patchUi({editingChannel:U("ha_service",a.channel_fields.ha_service??[])})}
        >
          ${e("channels.add")}
        </button>
      </div>
    </div>
  `}function M(s){const{t:e,ui:a}=s;return a.history===null?(s.loadHistory(),n`<div class="card"><p class="empty">${e("common.loading")}</p></div>`):n`
    <div class="card">
      <h2>${e("tab.history")}</h2>
      <p class="hint">${e("history.description")}</p>
      <div class="row wrap filters">
        <select
          @change=${i=>s.patchUi({historyKind:i.target.value,history:null})}
        >
          <option value="">${e("history.kind")}: ${e("common.all")}</option>
          <option value="status" ?selected=${a.historyKind==="status"}>
            ${e("history.kind.status")}
          </option>
          <option value="runtime" ?selected=${a.historyKind==="runtime"}>
            ${e("history.kind.runtime")}
          </option>
        </select>
      </div>
      ${a.history.length===0?n`<p class="empty">${e("history.none")}</p>`:n`<div class="list">
            ${a.history.map(i=>n`
                <div class="list-item">
                  <div class="grow">
                    <div class="name">${i.name||i.key}</div>
                    <div class="sub">
                      ${_(i.ts,s.language)} ·
                      ${e(`history.kind.${i.kind}`)} ·
                      ${i.previous?e("history.changed",{previous:e(`status.${i.previous}`)||i.previous,status:e(`status.${i.status}`)||i.status}):e("history.appeared",{status:e(`status.${i.status}`)||i.status})}
                    </div>
                  </div>
                  ${i.kind==="status"?f(e,i.status):n`<span class="chip">${e(`runtime.${i.status}`)}</span>`}
                </div>
              `)}
          </div>`}
    </div>
  `}function V(s){const e=s??0,a=e>=90?b.healthy:e>=70?b.stale:b.abandoned,i=2*Math.PI*34,l=i*e/100;return n`
    <svg viewBox="0 0 80 80" class="ring" role="img" aria-label="${e}">
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
        stroke=${a}
        stroke-width="8"
        stroke-linecap="round"
        stroke-dasharray="${l} ${i}"
        transform="rotate(-90 40 40)"
      />
      <text x="40" y="46" text-anchor="middle" class="ring-value">
        ${s===null?"–":e}
      </text>
    </svg>
  `}function y(s,e,a){return n`
    <div class="tile">
      <div class="tile-value" style=${a?`color:${a}`:c}>
        ${e}
      </div>
      <div class="tile-label">${s}</div>
    </div>
  `}function J(s){const{t:e,data:a}=s,i=a.repositories.filter(d=>!d.ignored),l=i.filter(d=>d.status!=="healthy"),r=i.filter(d=>d.usage==="unused"),t=a.runtime.filter(d=>d.problem),o=a.runtime.reduce((d,v)=>d+v.repairs.length,0),h=[...l].sort((d,v)=>d.score-v.score).slice(0,8),p=C.map(d=>[d,i.filter(v=>v.status===d).length]).filter(([,d])=>d>0),u=Object.keys(a.scan.errors);return n`
    <div class="card">
      <div class="row wrap head">
        ${V(a.scan.score)}
        <div class="tiles">
          ${y(e("overview.repositories"),i.length)}
          ${y(e("overview.problems"),l.length,l.length?b.stale:void 0)}
          ${y(e("overview.unused"),r.length,r.length?b.stale:void 0)}
          ${y(e("overview.runtime"),t.length,t.length?b.abandoned:void 0)}
          ${y(e("overview.repairs"),o)}
        </div>
        <div class="spacer"></div>
        <div class="scan">
          <button
            class="primary"
            ?disabled=${s.busy}
            @click=${()=>s.scan()}
          >
            ${s.busy?e("overview.scanning"):e("overview.scan_now")}
          </button>
          <p class="hint">
            ${e("overview.last_scan")}:
            ${a.scan.last?_(a.scan.last,s.language):e("common.never")}
          </p>
        </div>
      </div>

      ${p.length?n`<div class="bar">
            ${p.map(([d,v])=>n`
                <div
                  class="bar-part"
                  style="flex:${v};background:${b[d]}"
                  title="${e(`status.${d}`)}: ${v}"
                ></div>
              `)}
          </div>`:c}

      ${u.length?n`<p class="error">
            ${e("overview.errors")}:
            ${u.map(d=>e(`overview.error.${d}`)||d).join(" ")}
          </p>`:c}
      ${a.scan.has_token?c:n`<p class="hint">${e("overview.no_token")}</p>`}
      ${a.scan.github_pending?n`<p class="hint">
            ${e("overview.github_pending",{count:a.scan.github_pending})}
          </p>`:c}
      ${a.scan.github_remaining!==null?n`<p class="hint">
            ${e("overview.github_budget",{count:a.scan.github_remaining})}
          </p>`:c}
    </div>

    <div class="card">
      <h2>${e("overview.worst")}</h2>
      ${a.scan.last?h.length===0?n`<p class="empty">${e("overview.nothing_wrong")}</p>`:n`<div class="list">
              ${h.map(d=>n`
                  <div
                    class="list-item clickable"
                    @click=${()=>s.patchUi({selected:d.key,search:""})}
                  >
                    <div class="grow">
                      <div class="name">${d.name}</div>
                      <div class="sub">${d.key}</div>
                    </div>
                    <span class="score">${d.score}</span>
                    ${f(e,d.status)}
                  </div>
                `)}
            </div>`:n`<p class="empty">${e("overview.never_scanned")}</p>`}
    </div>
  `}const Y=["used","unused","undetermined","not_registered","not_checked"];function X(s,e){const{t:a}=s,i=E(e.last_push);return n`
    <div class="card">
      <div class="row wrap">
        <button class="ghost" @click=${()=>s.patchUi({selected:null})}>
          ← ${a("common.back")}
        </button>
        <div class="spacer"></div>
        ${e.url?n`<a class="ghost" href=${e.url} target="_blank" rel="noreferrer"
              >${a("repo.github")}</a
            >`:c}
        ${e.hacs_url?n`<a class="ghost" href=${e.hacs_url}>${a("repo.manage")}</a>`:c}
      </div>

      <h2>${e.name}</h2>
      <p class="sub">${e.key}</p>
      ${e.description?n`<p>${e.description}</p>`:c}

      <div class="row wrap chips">
        ${f(a,e.status)} ${k(a,e.usage)}
        ${e.usage_confidence?n`<span class="chip"
              >${a(`confidence.${e.usage_confidence}`)}</span
            >`:c}
        <span class="chip">${a(`category.${e.category}`)}</span>
        ${e.is_default_store?c:n`<span class="chip">${a("repo.custom")}</span>`}
        ${e.ignored?n`<span class="chip">${a("repo.ignored")}</span>`:c}
        ${s.data.marked_used.includes(e.key)?n`<span class="chip">${a("repo.marked_used")}</span>`:c}
      </div>

      <div class="facts">
        <div><span>${a("repo.score")}</span><b>${e.score}</b></div>
        <div>
          <span>${a("repo.installed")}</span
          ><b>${e.installed_version||"—"}</b>
        </div>
        <div>
          <span>${a("repo.available")}</span
          ><b>${e.available_version||"—"}</b>
        </div>
        <div>
          <span>${a("repo.last_push")}</span>
          <b>
            ${x(e.last_push,s.language)}
            ${i===null?"":` (${i} ${a("common.days")})`}
          </b>
        </div>
        <div>
          <span>${a("repo.last_release")}</span
          ><b>${x(e.last_release_at,s.language)}</b>
        </div>
        <div><span>${a("repo.stars")}</span><b>${e.stars??"—"}</b></div>
        <div>
          <span>${a("repo.issues")}</span><b>${e.open_issues??"—"}</b>
        </div>
        ${e.category==="app"?n`
              <div>
                <span>${a("repo.app_state")}</span
                ><b>${e.app_state??"—"}</b>
              </div>
              <div>
                <span>${a("repo.app_boot")}</span>
                <b>${e.app_boot==="auto"?a("common.yes"):a("common.no")}</b>
              </div>
            `:c}
      </div>

      <h3>${a("repo.findings")}</h3>
      ${e.findings.length===0?n`<p class="empty">${a("repo.no_findings")}</p>`:n`<ul class="findings">
            ${e.findings.map(l=>n`<li>
                ${O(a,l)}
                <span class="penalty">−${l.penalty}</span>
              </li>`)}
          </ul>`}

      <div class="row wrap actions">
        <button @click=${()=>s.ignore(e.key,!e.ignored)}>
          ${e.ignored?a("repo.unignore"):a("repo.ignore")}
        </button>
        <button
          @click=${()=>s.markUsed(e.key,!s.data.marked_used.includes(e.key))}
        >
          ${s.data.marked_used.includes(e.key)?a("repo.unmark_used"):a("repo.mark_used")}
        </button>
      </div>
    </div>
  `}function Q(s){const{t:e,data:a,ui:i}=s;if(i.selected){const r=a.repositories.find(t=>t.key===i.selected);if(r)return X(s,r)}const l=R(i,a.repositories);return n`
    <div class="card">
      <div class="row wrap filters">
        <input
          type="search"
          .value=${i.search}
          placeholder=${e("repo.search")}
          @input=${r=>s.patchUi({search:r.target.value})}
        />
        <select
          .value=${i.category}
          @change=${r=>s.patchUi({category:r.target.value})}
        >
          <option value="">${e("repo.category")}: ${e("common.all")}</option>
          ${a.categories.map(r=>n`<option value=${r} ?selected=${i.category===r}>
                ${e(`category.${r}`)}
              </option>`)}
        </select>
        <select
          @change=${r=>s.patchUi({status:r.target.value})}
        >
          <option value="">${e("repo.status")}: ${e("common.all")}</option>
          ${C.map(r=>n`<option value=${r} ?selected=${i.status===r}>
                ${e(`status.${r}`)}
              </option>`)}
        </select>
        <select
          @change=${r=>s.patchUi({usage:r.target.value})}
        >
          <option value="">${e("repo.usage")}: ${e("common.all")}</option>
          ${Y.map(r=>n`<option value=${r} ?selected=${i.usage===r}>
                ${e(`usage.${r}`)}
              </option>`)}
        </select>
        <label class="checkbox">
          <input
            type="checkbox"
            .checked=${i.showIgnored}
            @change=${r=>s.patchUi({showIgnored:r.target.checked})}
          />
          ${e("repo.show_ignored")}
        </label>
        <div class="spacer"></div>
        <span class="hint"
          >${e("repo.count",{count:l.length,total:a.repositories.length})}</span
        >
      </div>
    </div>

    <div class="card flush">
      ${l.length===0?n`<p class="empty pad">${e("repo.none")}</p>`:n`<div class="list">
            ${l.map(r=>n`
                <div
                  class="list-item clickable"
                  @click=${()=>s.patchUi({selected:r.key})}
                >
                  <div class="grow">
                    <div class="name">
                      ${r.name}
                      ${r.ignored?n`<span class="chip small"
                            >${e("repo.ignored")}</span
                          >`:c}
                    </div>
                    <div class="sub">
                      ${r.key} · ${e(`category.${r.category}`)}
                    </div>
                  </div>
                  <span class="score">${r.score}</span>
                  ${r.usage==="unused"||r.usage==="not_registered"?k(e,r.usage):c}
                  ${f(e,r.status)}
                </div>
              `)}
          </div>`}
    </div>
  `}function Z(s){const{t:e,data:a}=s,i=new Map(a.rules.map(t=>[t.id,t])),l=(t,o)=>{const h=a.rules.map(p=>p.id===t?{...p,...o}:p);s.saveRules(h)},r=()=>{s.saveRules(a.rule_catalogue.map(t=>({id:t.id,enabled:!0,severity_id:t.default_severity,penalty:t.default_penalty,threshold:t.default_threshold})))};return n`
    <div class="card">
      <h2>${e("tab.rules")}</h2>
      <p class="hint">${e("rules.description")}</p>
      <div class="row">
        <div class="spacer"></div>
        <button class="ghost" ?disabled=${s.busy} @click=${r}>
          ${e("rules.reset")}
        </button>
      </div>
    </div>

    <div class="card flush">
      <div class="list">
        ${a.rule_catalogue.map(t=>{const o=i.get(t.id);if(!o)return c;const h=t.categories?.length===1&&t.categories[0]==="app",p=t.categories!==null&&!t.categories?.includes("app");return n`
            <div class="list-item rule">
              <label class="checkbox">
                <input
                  type="checkbox"
                  .checked=${o.enabled}
                  ?disabled=${s.busy}
                  @change=${u=>l(o.id,{enabled:u.target.checked})}
                />
              </label>
              <div class="grow">
                <div class="name">${e(`rule.${o.id}`)}</div>
                <div class="sub">
                  ${t.requires_github?n`<span class="chip small">${e("rules.needs_token")}</span>`:c}
                  ${h?n`<span class="chip small">${e("rules.apps_only")}</span>`:c}
                  ${p?n`<span class="chip small">${e("rules.hacs_only")}</span>`:c}
                </div>
              </div>
              ${t.threshold_unit?n`<label class="field small">
                    <span>${e("rules.threshold")}</span>
                    <span class="suffixed">
                      <input
                        type="number"
                        min="0"
                        .value=${String(o.threshold??"")}
                        ?disabled=${s.busy||!o.enabled}
                        @change=${u=>l(o.id,{threshold:Number(u.target.value)})}
                      />
                      <span class="suffix"
                        >${t.threshold_unit==="days"?e("common.days"):""}</span
                      >
                    </span>
                  </label>`:c}
              <label class="field small">
                <span>${e("rules.penalty")}</span>
                <input
                  type="number"
                  min="0"
                  max="100"
                  .value=${String(o.penalty)}
                  ?disabled=${s.busy||!o.enabled}
                  @change=${u=>l(o.id,{penalty:Number(u.target.value)})}
                />
              </label>
              <label class="field severity-field">
                <span>${e("rules.severity")}</span>
                <select
                  ?disabled=${s.busy||!o.enabled}
                  @change=${u=>l(o.id,{severity_id:u.target.value})}
                >
                  ${a.severities.map(u=>n`
                      <option
                        value=${u.id}
                        ?selected=${u.id===o.severity_id}
                      >
                        ${u.name}
                      </option>
                    `)}
                </select>
              </label>
            </div>
          `})}
      </div>
    </div>

    ${ee(s)}
  `}function ee(s){const{t:e,data:a}=s,i=(l,r)=>s.saveSeverities(a.severities.map(t=>t.id===l?{...t,...r}:t));return n`
    <div class="card">
      <h2>${e("severities.title")}</h2>
      <p class="hint">${e("severities.description")}</p>
      <div class="list">
        ${a.severities.map(l=>n`
            <div class="list-item severity">
              <div class="grow">
                <input
                  type="text"
                  .value=${l.name}
                  ?disabled=${s.busy}
                  @change=${r=>i(l.id,{name:r.target.value})}
                />
                <div class="sub">${l.id}</div>
              </div>
              <label class="field small">
                <span>${e("severities.priority")}</span>
                <input
                  type="number"
                  min="0"
                  max="100"
                  .value=${String(l.priority)}
                  ?disabled=${s.busy}
                  @change=${r=>i(l.id,{priority:Number(r.target.value)})}
                />
              </label>
              <label class="checkbox">
                <input
                  type="checkbox"
                  .checked=${l.persistent_notification}
                  ?disabled=${s.busy}
                  @change=${r=>i(l.id,{persistent_notification:r.target.checked})}
                />
                ${e("severities.persistent")}
              </label>
              <label class="checkbox">
                <input
                  type="checkbox"
                  .checked=${l.ignore_quiet_hours}
                  ?disabled=${s.busy}
                  @change=${r=>i(l.id,{ignore_quiet_hours:r.target.checked})}
                />
                ${e("severities.ignore_quiet")}
              </label>
              <div class="channels">
                <span class="sub">${e("severities.channels")}</span>
                ${a.channels.length===0?n`<span class="sub">${e("common.none")}</span>`:a.channels.map(r=>n`
                        <label class="checkbox">
                          <input
                            type="checkbox"
                            .checked=${l.channels.includes(r.id)}
                            ?disabled=${s.busy}
                            @change=${t=>{const h=t.target.checked?[...l.channels,r.id]:l.channels.filter(p=>p!==r.id);i(l.id,{channels:h})}}
                          />
                          ${r.name||e(`kind.${r.kind}`)}
                        </label>
                      `)}
              </div>
            </div>
          `)}
      </div>
    </div>
  `}function se(s,e){return e?"var(--secondary-text-color)":s==="ok"?b.stale:b.abandoned}function ae(s){const{t:e,data:a}=s,i=a.runtime.filter(t=>t.problem),l=a.runtime.filter(t=>!t.problem&&t.state!=="ok"),r=(t,o)=>n`
    <div class="list-item">
      <div class="grow">
        <div class="name">${t.title||t.domain}</div>
        <div class="sub">
          ${t.domain} · ${e(`runtime.${t.state}`)}
          ${t.since?` · ${e("runtime.since",{time:_(t.since,s.language)})}`:""}
          ${o?` · ${e("runtime.waiting")}`:""}
        </div>
        ${t.reason?n`<div class="sub reason">${t.reason}</div>`:c}
        ${t.repairs.length?n`<div class="sub">
              ${e("runtime.repairs")}:
              ${t.repairs.map(h=>h.translation_key||h.issue_id).join(", ")}
            </div>`:c}
        ${t.entries.length>1?n`<div class="sub">
              ${e("runtime.entries",{count:t.entries.length})}
            </div>`:c}
      </div>
      <a class="ghost" href=${t.configuration_url}>${e("runtime.open")}</a>
      ${t.url?n`<a class="ghost" href=${t.url} target="_blank" rel="noreferrer"
            >${e("repo.github")}</a
          >`:c}
      <span
        class="badge solid"
        style="background:${se(t.state,o)}"
        >${e(`runtime.${t.state}`)}</span
      >
    </div>
  `;return n`
    <div class="card">
      <h2>${e("runtime.title")}</h2>
      ${i.length===0&&l.length===0?n`<p class="empty">${e("runtime.no_problems")}</p>`:n`<div class="list">
            ${i.map(t=>r(t,!1))}
            ${l.map(t=>r(t,!0))}
          </div>`}
    </div>
  `}const te=[1,3,6,12,24,48,168],w=[0,1,2,3,4,5,6];function ie(s){const{t:e,data:a}=s,i=a.settings,l=t=>s.saveSettings({...i,...t}),r=(t,o,h)=>n`
    <div class="field wide">
      <span>${t}</span>
      <div class="row wrap">
        ${a.categories.map(p=>n`
            <label class="checkbox">
              <input
                type="checkbox"
                .checked=${o.includes(p)}
                ?disabled=${s.busy}
                @change=${u=>{const v=u.target.checked?[...o,p]:o.filter(A=>A!==p);l({[h]:v})}}
              />
              ${e(`category.${p}`)}
            </label>
          `)}
      </div>
    </div>
  `;return n`
    <div class="card">
      <h2>${e("settings.scan")}</h2>
      <div class="row wrap">
        <label class="field">
          <span>${e("settings.scan_interval")}</span>
          <select
            ?disabled=${s.busy}
            @change=${t=>l({scan_interval_hours:Number(t.target.value)})}
          >
            ${te.map(t=>n`
                <option
                  value=${t}
                  ?selected=${i.scan_interval_hours===t}
                >
                  ${t} ${e("common.hours")}
                </option>
              `)}
          </select>
        </label>
        <label class="field">
          <span>${e("settings.scan_time")}</span>
          <input
            type="time"
            .value=${i.scan_time}
            ?disabled=${s.busy}
            @change=${t=>l({scan_time:t.target.value})}
          />
        </label>
      </div>
      <p class="hint">${e("settings.scan_time_hint")}</p>
      ${r(e("settings.categories_health"),i.categories_health,"categories_health")}
      ${r(e("settings.categories_usage"),i.categories_usage,"categories_usage")}
      <label class="checkbox">
        <input
          type="checkbox"
          .checked=${i.check_orphans}
          ?disabled=${s.busy}
          @change=${t=>l({check_orphans:t.target.checked})}
        />
        ${e("settings.check_orphans")}
      </label>
    </div>

    <div class="card">
      <h2>${e("settings.github")}</h2>
      <p class="hint">${e("settings.github_token_hint")}</p>
      ${a.scan.has_token?n`<p class="hint">${e("settings.github_token_set")}</p>`:c}
      <label class="field wide">
        <span>${e("settings.github_token")}</span>
        <input
          type="password"
          autocomplete="off"
          placeholder=${a.scan.has_token?"••••••••":""}
          ?disabled=${s.busy}
          @change=${t=>{const o=t.target.value;s.saveSettings(i,o)}}
        />
      </label>
    </div>

    <div class="card">
      <h2>${e("settings.runtime")}</h2>
      <label class="checkbox">
        <input
          type="checkbox"
          .checked=${i.runtime_enabled}
          ?disabled=${s.busy}
          @change=${t=>l({runtime_enabled:t.target.checked})}
        />
        ${e("settings.runtime_enabled")}
      </label>
      <label class="checkbox">
        <input
          type="checkbox"
          .checked=${i.runtime_include_all}
          ?disabled=${s.busy||!i.runtime_enabled}
          @change=${t=>l({runtime_include_all:t.target.checked})}
        />
        ${e("settings.runtime_include_all")}
      </label>
      <label class="field">
        <span>${e("settings.runtime_grace")}</span>
        <span class="suffixed">
          <input
            type="number"
            min="0"
            .value=${String(i.runtime_grace_minutes)}
            ?disabled=${s.busy||!i.runtime_enabled}
            @change=${t=>l({runtime_grace_minutes:Number(t.target.value)})}
          />
          <span class="suffix">${e("common.minutes")}</span>
        </span>
      </label>
      <p class="hint">${e("settings.runtime_grace_hint")}</p>
    </div>

    <div class="card">
      <h2>${e("settings.notifications")}</h2>
      <label class="checkbox">
        <input
          type="checkbox"
          .checked=${i.notify_on_recovery}
          ?disabled=${s.busy}
          @change=${t=>l({notify_on_recovery:t.target.checked})}
        />
        ${e("settings.notify_on_recovery")}
      </label>

      <h3>${e("settings.quiet_hours")}</h3>
      <label class="checkbox">
        <input
          type="checkbox"
          .checked=${i.quiet_hours.enabled}
          ?disabled=${s.busy}
          @change=${t=>l({quiet_hours:{...i.quiet_hours,enabled:t.target.checked}})}
        />
        ${e("settings.quiet_enabled")}
      </label>
      <div class="row wrap">
        <label class="field">
          <span>${e("settings.quiet_from")}</span>
          <input
            type="time"
            .value=${i.quiet_hours.start}
            ?disabled=${s.busy||!i.quiet_hours.enabled}
            @change=${t=>l({quiet_hours:{...i.quiet_hours,start:t.target.value}})}
          />
        </label>
        <label class="field">
          <span>${e("settings.quiet_to")}</span>
          <input
            type="time"
            .value=${i.quiet_hours.end}
            ?disabled=${s.busy||!i.quiet_hours.enabled}
            @change=${t=>l({quiet_hours:{...i.quiet_hours,end:t.target.value}})}
          />
        </label>
      </div>
      <div class="field wide">
        <span>${e("settings.quiet_weekdays")}</span>
        <div class="row wrap">
          ${w.map(t=>n`
              <label class="checkbox">
                <input
                  type="checkbox"
                  .checked=${i.quiet_hours.weekdays.length===0||i.quiet_hours.weekdays.includes(t)}
                  ?disabled=${s.busy||!i.quiet_hours.enabled}
                  @change=${o=>{const h=o.target.checked,p=i.quiet_hours.weekdays.length===0?[...w]:i.quiet_hours.weekdays,u=h?[...new Set([...p,t])].sort():p.filter(d=>d!==t);l({quiet_hours:{...i.quiet_hours,weekdays:u}})}}
                />
                ${e(`weekday.${t}`)}
              </label>
            `)}
        </div>
      </div>
      <p class="hint">${e("settings.quiet_hint")}</p>
    </div>

    <div class="card">
      <h2>${e("settings.panel")}</h2>
      <div class="row wrap">
        <label class="field">
          <span>${e("settings.panel_access")}</span>
          <select
            ?disabled=${s.busy}
            @change=${t=>l({panel_access:t.target.value})}
          >
            <option value="admins" ?selected=${i.panel_access==="admins"}>
              ${e("settings.panel_admins")}
            </option>
            <option value="all" ?selected=${i.panel_access==="all"}>
              ${e("settings.panel_all")}
            </option>
          </select>
        </label>
        <label class="field">
          <span>${e("settings.language")}</span>
          <select
            ?disabled=${s.busy}
            @change=${t=>l({ui_language:t.target.value})}
          >
            <option value="auto" ?selected=${i.ui_language==="auto"}>
              ${e("settings.language_auto")}
            </option>
            ${N.map(t=>n`<option value=${t} ?selected=${i.ui_language===t}>
                  ${t}
                </option>`)}
          </select>
        </label>
        <label class="field">
          <span>${e("settings.history_retention")}</span>
          <span class="suffixed">
            <input
              type="number"
              min="1"
              .value=${String(i.history_retention_days)}
              ?disabled=${s.busy}
              @change=${t=>l({history_retention_days:Number(t.target.value)})}
            />
            <span class="suffix">${e("common.days")}</span>
          </span>
        </label>
      </div>
    </div>
  `}function S(s,e){const{t:a}=s;return n`<div class="list">
    ${e.map(i=>n`
        <div
          class="list-item clickable"
          @click=${()=>s.patchUi({selected:i.key,search:"",category:""})}
        >
          <div class="grow">
            <div class="name">${i.name}</div>
            <div class="sub">
              ${i.key} · ${a(`category.${i.category}`)}
              ${i.usage_confidence?` · ${a(`confidence.${i.usage_confidence}`)}`:""}
            </div>
          </div>
          ${k(a,i.usage)}
        </div>
      `)}
  </div>`}function ne(s){const{t:e,data:a}=s,i=a.repositories.filter(o=>!o.ignored),l=i.filter(o=>o.usage==="unused"||o.usage==="not_registered"),r=i.filter(o=>o.usage==="undetermined"),t=l.some(o=>{const h=o.usage_detail?.uncertain_dashboards;return h&&Object.keys(h).length>0});return n`
    <div class="card">
      <h2>${e("unused.title")}</h2>
      <p class="hint">${e("unused.description")}</p>
      ${t?n`<p class="hint">${e("unused.uncertain")}</p>`:c}
      ${l.length===0?n`<p class="empty">${e("unused.none")}</p>`:S(s,l)}
    </div>

    ${r.length?n`<div class="card">
          <h2>${e("unused.undetermined_title")}</h2>
          <p class="hint">${e("unused.undetermined_description")}</p>
          ${S(s,r)}
        </div>`:c}

    ${a.settings.check_orphans?n`<div class="card">
          <h2>${e("unused.orphans")}</h2>
          <p class="hint">${e("unused.orphans_description")}</p>
          ${a.orphans.length===0?n`<p class="empty">${e("unused.no_orphans")}</p>`:n`<div class="list">
                ${a.orphans.map(o=>n`
                    <div class="list-item">
                      <div class="grow">
                        <div class="name">${o.name??o.url}</div>
                        <div class="sub">${o.path??""}</div>
                      </div>
                      <span class="chip">${e(`unused.orphan.${o.kind}`)}</span>
                    </div>
                  `)}
              </div>`}
        </div>`:c}
  `}var re=Object.defineProperty,le=Object.getOwnPropertyDescriptor,$=(s,e,a,i)=>{for(var l=i>1?void 0:i?le(e,a):e,r=s.length-1,t;r>=0;r--)(t=s[r])&&(l=(i?t(e,a,l):t(l))||l);return i&&l&&re(e,a,l),l};const oe=["rules","channels","settings"];let g=class extends W{constructor(){super(...arguments),this.narrow=!1,this.data=null,this.tab="overview",this.busy=!1,this.message="",this.ui={...I},this.localizeFn=T,this.api=null,this.catalogueFor=""}get isAdmin(){return this.hass?.user?.is_admin??!1}willUpdate(){this.hass&&(this.api?this.api.update(this.hass):(this.api=new D(this.hass),this.load()),this.syncCatalogue())}get language(){const s=this.data?.settings.ui_language;return s&&s!=="auto"?s:this.hass?.language||"en"}async syncCatalogue(){const s=this.language;s!==this.catalogueFor&&(this.catalogueFor=s,this.localizeFn=j(await F(s)))}async load(){if(this.api)try{this.data=await this.api.get()}catch(s){this.message=String(s?.message??s)}}async run(s,e){if(!this.busy){this.busy=!0;try{await s(),e&&this.toast(e)}catch(a){this.toast(String(a?.message??this.localizeFn("common.error")))}finally{this.busy=!1,await this.load()}}}toast(s){this.message=s,window.setTimeout(()=>{this.message===s&&(this.message="")},4e3)}context(){const s=this.localizeFn;return{t:s,data:this.data,language:this.language,busy:this.busy,ui:this.ui,patchUi:e=>{this.ui={...this.ui,...e}},scan:(e=!1)=>void this.run(()=>this.api.scan(e)),saveSettings:(e,a)=>void this.run(()=>this.api.saveSettings(e,a),s("common.saved")),saveRules:e=>void this.run(()=>this.api.saveRules(e),s("common.saved")),saveSeverities:e=>void this.run(()=>this.api.saveSeverities(e),s("common.saved")),saveChannel:e=>void this.run(async()=>{await this.api.saveChannel(e),this.ui={...this.ui,editingChannel:null}},s("common.saved")),deleteChannel:e=>void this.run(async()=>{await this.api.deleteChannel(e),this.ui={...this.ui,editingChannel:null}}),testChannel:e=>void this.run(()=>this.api.testChannel(e),s("channels.test_ok")),ignore:(e,a)=>void this.run(()=>this.api.ignore(e,a)),markUsed:(e,a)=>void this.run(()=>this.api.markUsed(e,a)),loadHistory:()=>void this.fetchHistory(),toast:e=>this.toast(e)}}async fetchHistory(){if(!(!this.api||this.ui.history!==null)){this.ui={...this.ui,history:[]};try{const s=await this.api.history({limit:200,kind:this.ui.historyKind||null});this.ui={...this.ui,history:s.events}}catch{this.ui={...this.ui,history:[]}}}}tabs(){const s=this.data,e=s?.repositories.filter(i=>!i.ignored)??[],a=[["overview","tab.overview",null],["repositories","tab.repositories",e.length],["unused","tab.unused",e.filter(i=>i.usage==="unused"||i.usage==="not_registered").length],["runtime","tab.runtime",(s?.runtime??[]).filter(i=>i.problem).length],["rules","tab.rules",null],["channels","tab.channels",null],["history","tab.history",null],["settings","tab.settings",null]];return this.isAdmin?a:a.filter(([i])=>!oe.includes(i))}body(){const s=this.context();switch(this.tab){case"repositories":return Q(s);case"unused":return ne(s);case"runtime":return ae(s);case"rules":return Z(s);case"channels":return K(s);case"history":return M(s);case"settings":return ie(s);default:return J(s)}}render(){const s=this.localizeFn;return this.data?n`
      <header>
        <h1>IntegrationGuard</h1>
      </header>
      <nav>
        ${this.tabs().map(([e,a,i])=>n`
            <button
              class=${e===this.tab?"active":""}
              @click=${()=>{this.tab=e,this.ui={...this.ui,selected:null,editingChannel:null}}}
            >
              ${s(a)}
              ${i?n`<span class="count">${i}</span>`:c}
            </button>
          `)}
      </nav>
      ${this.body()}
      ${this.message?n`<div class="toast">${this.message}</div>`:c}
    `:n`<div class="card"><p class="empty">${s("common.loading")}</p></div>`}};g.styles=[L,z`
      :host {
        display: block;
        padding: 16px;
        max-width: 1100px;
        margin: 0 auto;
        box-sizing: border-box;
      }
      header {
        display: flex;
        align-items: center;
        gap: 12px;
        flex-wrap: wrap;
        margin-bottom: 16px;
      }
      h1 {
        font-size: 1.5rem;
        font-weight: 500;
        margin: 0;
      }
      nav {
        display: flex;
        gap: 4px;
        flex-wrap: wrap;
        margin-bottom: 16px;
      }
      nav button {
        background: none;
        border: none;
        border-bottom: 2px solid transparent;
        color: var(--secondary-text-color);
        padding: 8px 12px;
        cursor: pointer;
        font-size: 0.95rem;
        border-radius: 0;
      }
      nav button.active {
        color: var(--primary-color);
        border-bottom-color: var(--primary-color);
      }
      nav button .count {
        display: inline-block;
        min-width: 18px;
        margin-left: 6px;
        padding: 0 5px;
        border-radius: 9px;
        background: var(--secondary-background-color, rgba(127, 127, 127, 0.2));
        font-size: 0.75rem;
      }
      .toast {
        position: fixed;
        left: 50%;
        bottom: 24px;
        transform: translateX(-50%);
        background: var(--primary-color);
        color: var(--text-primary-color, #fff);
        padding: 10px 18px;
        border-radius: 20px;
        z-index: 10;
      }
      .head {
        gap: 24px;
      }
      .ring {
        width: 96px;
        height: 96px;
        flex: none;
      }
      .ring-value {
        fill: var(--primary-text-color);
        font-size: 22px;
        font-weight: 600;
      }
      .tiles {
        display: flex;
        gap: 20px;
        flex-wrap: wrap;
      }
      .tile-value {
        font-size: 1.6rem;
        font-weight: 600;
      }
      .tile-label {
        color: var(--secondary-text-color);
        font-size: 0.8rem;
      }
      .bar {
        display: flex;
        height: 8px;
        border-radius: 4px;
        overflow: hidden;
        margin-top: 16px;
      }
      .bar-part {
        height: 100%;
      }
      .grow {
        flex: 1;
        min-width: 0;
      }
      .name {
        font-weight: 500;
      }
      .sub {
        color: var(--secondary-text-color);
        font-size: 0.8rem;
        word-break: break-word;
      }
      .sub.reason {
        color: var(--error-color, #db4437);
      }
      .score {
        font-variant-numeric: tabular-nums;
        color: var(--secondary-text-color);
        margin-right: 8px;
      }
      .clickable {
        cursor: pointer;
      }
      .clickable:hover {
        background: var(--secondary-background-color, rgba(127, 127, 127, 0.08));
      }
      .facts {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 10px 20px;
        margin: 16px 0;
      }
      .facts div {
        display: flex;
        justify-content: space-between;
        gap: 12px;
        border-bottom: var(--ig-border);
        padding-bottom: 4px;
      }
      .facts span {
        color: var(--secondary-text-color);
      }
      .findings {
        margin: 0;
        padding-left: 18px;
      }
      .findings li {
        margin-bottom: 4px;
      }
      .penalty {
        color: var(--secondary-text-color);
        font-size: 0.8rem;
        margin-left: 6px;
      }
      .filters {
        gap: 8px;
      }
      /* The shared form styling stretches inputs to the full width, which is
         right in a stacked form and wrong in a filter bar. */
      .filters input:not([type="checkbox"]),
      .filters select {
        width: auto;
        min-width: 150px;
      }
      .filters input[type="search"] {
        min-width: 220px;
      }
      .field {
        display: flex;
        flex-direction: column;
        gap: 4px;
        font-size: 0.85rem;
        color: var(--secondary-text-color);
      }
      .field.wide {
        width: 100%;
        margin-top: 12px;
      }
      .field input:not([type="checkbox"]),
      .field select,
      .field textarea {
        width: 100%;
        box-sizing: border-box;
      }
      .checkbox input[type="checkbox"] {
        width: auto;
        min-width: 0;
        flex: none;
      }
      .field.small input,
      .field.small select {
        width: 90px;
        min-width: 90px;
      }
      .field.severity-field select {
        width: 150px;
      }
      .list-item.rule,
      .list-item.severity {
        flex-wrap: wrap;
        gap: 12px;
      }
      .channels {
        display: flex;
        gap: 10px;
        flex-wrap: wrap;
        align-items: center;
        width: 100%;
      }
      .pad {
        padding: 16px;
      }
      .actions {
        margin-top: 16px;
      }
      a.ghost {
        text-decoration: none;
      }
      input,
      select,
      textarea {
        font: inherit;
        color: var(--primary-text-color);
        background: var(--card-background-color, #fff);
        border: var(--ig-border);
        border-radius: 8px;
        padding: 7px 10px;
      }
      button {
        font: inherit;
        border-radius: 20px;
        border: var(--ig-border);
        background: none;
        color: var(--primary-text-color);
        padding: 7px 16px;
        cursor: pointer;
      }
      button.primary {
        background: var(--primary-color);
        color: var(--text-primary-color, #fff);
        border-color: transparent;
      }
      button.danger {
        color: var(--error-color, #db4437);
      }
      button.ghost,
      a.ghost {
        border: none;
        color: var(--primary-color);
        padding: 7px 10px;
      }
      button[disabled] {
        opacity: 0.5;
        cursor: default;
      }
    `];$([q({attribute:!1})],g.prototype,"hass",2);$([q({type:Boolean})],g.prototype,"narrow",2);$([m()],g.prototype,"data",2);$([m()],g.prototype,"tab",2);$([m()],g.prototype,"busy",2);$([m()],g.prototype,"message",2);$([m()],g.prototype,"ui",2);$([m()],g.prototype,"localizeFn",2);g=$([P("integrationguard-panel")],g);
