// Screen time card for the Qustodio integration: where a child's screen time went today, by routine.
// Served and registered by the integration; logic and rendering live in card-logic.js (unit-tested).
import { errorText, escapeHtml, renderCard } from "./card-logic.js";

const CARD_TYPE = "qustodio-screen-time-card";
const ATTRIBUTION = "Data provided by Qustodio";
const MIN_REFETCH_MS = 60_000;

const STYLE = `
  ha-card { padding: 16px; cursor: pointer; }
  .title { font-weight: 500; font-size: 16px; margin-bottom: 4px; }
  .headline .big { font-size: 28px; font-weight: 600; font-variant-numeric: tabular-nums; }
  .headline .unit { color: var(--secondary-text-color); }
  .over { color: var(--primary-text-color); font-size: 13px; margin-top: 2px; }
  .chips { display: flex; flex-wrap: wrap; gap: 6px 12px; margin: 10px 0; font-size: 13px; }
  .chip { display: inline-flex; align-items: center; gap: 6px; color: var(--primary-text-color); }
  .swatch { width: 10px; height: 10px; border-radius: 2px; display: inline-block; outline: 1px solid var(--divider-color); }
  .note { color: var(--secondary-text-color); font-size: 12px; }
  .strip { position: relative; height: 28px; border-radius: 4px; background: var(--secondary-background-color); overflow: hidden; }
  .window { position: absolute; top: 0; bottom: 0; opacity: 0.18; }
  .bar { position: absolute; bottom: 0; top: 0; display: flex; flex-direction: column-reverse; gap: 1px; padding: 0 1px; box-sizing: border-box; }
  .seg { width: 100%; border-radius: 1px; }
  .ticks { position: relative; height: 16px; font-size: 11px; color: var(--secondary-text-color); }
  .ticks span { position: absolute; transform: translateX(-50%); }
  .ticks span:first-child { transform: none; }
  .ticks span:last-child { transform: translateX(-100%); }
  .empty, .message { color: var(--secondary-text-color); margin-top: 8px; }
`;

/** Today's date (YYYY-MM-DD) in a time zone. */
function localDate(tz) {
  return new Intl.DateTimeFormat("en-CA", { timeZone: tz, year: "numeric", month: "2-digit", day: "2-digit" }).format(
    new Date(),
  );
}

class QustodioScreenTimeCard extends HTMLElement {
  static getConfigForm() {
    return {
      schema: [
        {
          name: "entity",
          required: true,
          selector: { entity: { filter: [{ integration: "qustodio", domain: "sensor" }] } },
        },
      ],
    };
  }

  static getStubConfig(hass) {
    const sensor = Object.values(hass.states).find(
      (state) =>
        state.entity_id.startsWith("sensor.") &&
        state.attributes?.profile_id !== undefined &&
        state.attributes?.attribution === ATTRIBUTION,
    );
    return { entity: sensor ? sensor.entity_id : "" };
  }

  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._inFlight = false;
    this._lastFetch = 0;
    this._lastSeen = undefined;
    this.addEventListener("click", () => {
      this.dispatchEvent(
        new CustomEvent("hass-more-info", { bubbles: true, composed: true, detail: { entityId: this._config?.entity } }),
      );
    });
  }

  setConfig(config) {
    if (!config?.entity) throw new Error("Please choose a screen time sensor");
    this._config = config;
  }

  set hass(hass) {
    this._hass = hass;
    const state = hass.states[this._config?.entity];
    if (!state) {
      this._render(`<div class="message">Sensor ${escapeHtml(this._config?.entity)} not found</div>`);
      return;
    }
    const first = this._lastSeen === undefined;
    const due = Date.now() - this._lastFetch >= MIN_REFETCH_MS;
    if (!this._inFlight && state.last_updated !== this._lastSeen && (first || due)) {
      this._fetch(state);
    } else if (!this._report && !this._error) {
      this._render(`<div class="message">Loading…</div>`);
    }
  }

  async _fetch(state) {
    this._inFlight = true;
    this._lastSeen = state.last_updated;
    try {
      this._report = await this._hass.callWS({
        type: "qustodio/day_report",
        profile_id: state.attributes.profile_id,
        date: localDate(this._hass.config.time_zone),
      });
      this._error = null;
    } catch (err) {
      this._error = err?.code ?? "unknown";
    } finally {
      this._inFlight = false;
      this._lastFetch = Date.now();
    }
    this._renderReport();
  }

  _renderReport() {
    const state = this._hass.states[this._config.entity];
    const name = state?.attributes?.friendly_name ?? this._config.entity;
    if (this._error) {
      this._render(
        `<div class="title">${escapeHtml(name)}</div><div class="message">${escapeHtml(errorText(this._error))}</div>`,
      );
      return;
    }
    const dark = Boolean(this._hass.themes?.darkMode);
    this._render(renderCard(this._report, { name, tz: this._hass.config.time_zone, dark }));
  }

  _render(body) {
    this.shadowRoot.innerHTML = `<style>${STYLE}</style><ha-card>${body}</ha-card>`;
  }

  getCardSize() {
    return 3;
  }
}

if (!customElements.get(CARD_TYPE)) {
  customElements.define(CARD_TYPE, QustodioScreenTimeCard);
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: CARD_TYPE,
    name: "Screen time",
    description: "Where a child's screen time went today, by routine.",
  });
}
