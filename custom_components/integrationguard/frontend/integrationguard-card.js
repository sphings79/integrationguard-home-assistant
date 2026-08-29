import{i as v,n as x,r as p,a as b,f as w,l as $,b as y,S as m,c as l,t as _,d as h,A as g}from"./integrationguard-shared.js";var C=Object.defineProperty,z=Object.getOwnPropertyDescriptor,f=(t,e,s,i)=>{for(var a=i>1?void 0:i?z(e,s):e,r=t.length-1,n;r>=0;r--)(n=t[r])&&(a=(i?n(e,s,a):n(a))||a);return i&&a&&C(e,s,a),a};let d=class extends b{constructor(){super(...arguments),this.config={type:""},this.localizeFn=w,this.catalogueFor=""}setConfig(t){this.config=t}willUpdate(){const t=this.hass?.language||"en";t!==this.catalogueFor&&(this.catalogueFor=t,$(t).then(e=>{this.localizeFn=y(e)}))}patch(t){this.config={...this.config,...t},this.dispatchEvent(new CustomEvent("config-changed",{detail:{config:this.config},bubbles:!0,composed:!0}))}render(){const t=this.localizeFn;return l`
      <div class="form">
        <label>
          <span>${t("card.editor.title")}</span>
          <input
            type="text"
            .value=${this.config.title??""}
            @change=${e=>this.patch({title:e.target.value})}
          />
        </label>
        <label>
          <span>${t("card.editor.max_items")}</span>
          <input
            type="number"
            min="1"
            max="50"
            .value=${String(this.config.max_items??5)}
            @change=${e=>this.patch({max_items:Number(e.target.value)})}
          />
        </label>
        <label>
          <span>${t("card.editor.min_status")}</span>
          <select
            @change=${e=>this.patch({min_status:e.target.value})}
          >
            ${m.filter(e=>e!=="healthy").map(e=>l`
                <option
                  value=${e}
                  ?selected=${(this.config.min_status??"info")===e}
                >
                  ${t(`status.${e}`)}
                </option>
              `)}
          </select>
        </label>
        <label class="check">
          <input
            type="checkbox"
            .checked=${this.config.show_score??!0}
            @change=${e=>this.patch({show_score:e.target.checked})}
          />
          <span>${t("card.editor.show_score")}</span>
        </label>
        <label class="check">
          <input
            type="checkbox"
            .checked=${this.config.show_runtime??!0}
            @change=${e=>this.patch({show_runtime:e.target.checked})}
          />
          <span>${t("card.editor.show_runtime")}</span>
        </label>
      </div>
    `}};d.styles=v`
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
  `;f([x({attribute:!1})],d.prototype,"hass",2);f([p()],d.prototype,"config",2);f([p()],d.prototype,"localizeFn",2);d=f([_("integrationguard-card-editor")],d);var k=Object.defineProperty,F=Object.getOwnPropertyDescriptor,u=(t,e,s,i)=>{for(var a=i>1?void 0:i?F(e,s):e,r=t.length-1,n;r>=0;r--)(n=t[r])&&(a=(i?n(e,s,a):n(a))||a);return i&&a&&k(e,s,a),a};const O=6e4;let c=class extends b{constructor(){super(...arguments),this.config={type:""},this.data=null,this.localizeFn=w,this.catalogueFor=""}static getConfigElement(){return document.createElement("integrationguard-card-editor")}static getStubConfig(){return{type:"custom:integrationguard-card",show_score:!0}}setConfig(t){this.config={max_items:5,show_score:!0,show_runtime:!0,...t}}getCardSize(){return 1+Math.min(this.config.max_items??5,this.data?.problems.length??1)}connectedCallback(){super.connectedCallback(),this.timer=window.setInterval(()=>void this.fetch(),O)}disconnectedCallback(){super.disconnectedCallback(),this.timer&&window.clearInterval(this.timer)}willUpdate(){this.hass&&(this.data===null&&this.fetch(),this.syncCatalogue())}async syncCatalogue(){const t=this.hass.language||"en";t!==this.catalogueFor&&(this.catalogueFor=t,this.localizeFn=y(await $(t)))}async fetch(){if(this.hass)try{this.data=await this.hass.callWS({type:"integrationguard/card"})}catch{this.data={score:null,last_scan:null,total:0,problems:[],unused:0,runtime:[]}}}ring(t){const e=t>=90?h.healthy:t>=70?h.stale:h.abandoned,s=2*Math.PI*26;return l`
      <svg viewBox="0 0 60 60" class="ring" role="img" aria-label="${t}">
        <circle
          cx="30"
          cy="30"
          r="26"
          fill="none"
          stroke="var(--divider-color, rgba(127,127,127,.25))"
          stroke-width="6"
        />
        <circle
          cx="30"
          cy="30"
          r="26"
          fill="none"
          stroke=${e}
          stroke-width="6"
          stroke-linecap="round"
          stroke-dasharray="${s*t/100} ${s}"
          transform="rotate(-90 30 30)"
        />
        <text x="30" y="35" text-anchor="middle">${t}</text>
      </svg>
    `}render(){const t=this.localizeFn;if(!this.data)return g;const e=m.indexOf(this.config.min_status??"info"),s=this.data.problems.filter(o=>m.indexOf(o.status)>=e),i=this.config.show_runtime?this.data.runtime:[],a=this.config.max_items??5,r=[...s].slice(0,a),n=s.length-r.length;return l`
      <ha-card>
        <div class="head">
          ${this.config.show_score&&this.data.score!==null?this.ring(this.data.score):g}
          <div class="grow">
            <div class="title">${this.config.title??t("card.title")}</div>
            <div class="sub">
              ${t("overview.problems")}: ${s.length} ·
              ${t("overview.unused")}: ${this.data.unused} ·
              ${t("overview.runtime")}: ${this.data.runtime.length}
            </div>
          </div>
        </div>
        ${r.length===0&&i.length===0?l`<div class="empty">${t("card.nothing")}</div>`:l`<div class="list">
              ${i.map(o=>l`
                  <a class="item" href=${o.url}>
                    <span class="grow">${o.name}</span>
                    <span
                      class="dot"
                      style="background:${h.abandoned}"
                    ></span>
                    <span class="state">${t(`runtime.${o.state}`)}</span>
                  </a>
                `)}
              ${r.map(o=>l`
                  <a
                    class="item"
                    href=${o.url||"#"}
                    target=${o.url?"_blank":g}
                    rel="noreferrer"
                  >
                    <span class="grow">${o.name}</span>
                    <span
                      class="dot"
                      style="background:${h[o.status]}"
                    ></span>
                    <span class="state">${t(`status.${o.status}`)}</span>
                  </a>
                `)}
              ${n>0?l`<div class="more">${t("card.more",{count:n})}</div>`:g}
            </div>`}
      </ha-card>
    `}};c.styles=v`
    ha-card {
      padding: 16px;
      /* Set explicitly so the card reads correctly even where the host does
         not hand a colour down. */
      color: var(--primary-text-color);
    }
    .head {
      display: flex;
      align-items: center;
      gap: 16px;
    }
    .grow {
      flex: 1;
      min-width: 0;
    }
    .item .grow {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .title {
      font-size: 1.1rem;
      font-weight: 500;
    }
    .sub,
    .more,
    .empty {
      color: var(--secondary-text-color);
      font-size: 0.85rem;
    }
    .empty,
    .more {
      padding-top: 12px;
    }
    .ring {
      width: 60px;
      height: 60px;
      flex: none;
    }
    .ring text {
      fill: var(--primary-text-color);
      font-size: 18px;
      font-weight: 600;
    }
    .list {
      margin-top: 12px;
      display: flex;
      flex-direction: column;
    }
    .item {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px 0;
      border-top: 1px solid var(--divider-color, rgba(127, 127, 127, 0.25));
      color: var(--primary-text-color);
      text-decoration: none;
    }
    .dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      flex: none;
    }
    .state {
      color: var(--secondary-text-color);
      font-size: 0.85rem;
    }
  `;u([x({attribute:!1})],c.prototype,"hass",2);u([p()],c.prototype,"config",2);u([p()],c.prototype,"data",2);u([p()],c.prototype,"localizeFn",2);c=u([_("integrationguard-card")],c);window.customCards=window.customCards||[];window.customCards.push({type:"integrationguard-card",name:"IntegrationGuard",description:"Health of your installed extensions at a glance"});
