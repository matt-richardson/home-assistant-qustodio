// Screen time card for the Qustodio integration: where a child's screen time went today, by routine.
// Served and registered by the integration; logic and rendering live in card-logic.js (unit-tested).
// Load the logic with this file's own ?v= version, so an upgraded card never pairs with a cached older logic file
const version = new URL(import.meta.url).search;
const { CARD_STYLE, errorText, escapeHtml, localDate, renderCard } = await import(
  new URL("./card-logic.js" + version, import.meta.url)
);
const { openReport } = await import(new URL("./report-dialog.js" + version, import.meta.url));

const CARD_TYPE = "qustodio-screen-time-card";
const ATTRIBUTION = "Data provided by Qustodio";
const MIN_REFETCH_MS = 60_000;
// Just over the server's 5-minute cache for today, so the card catches up even when its sensor stops changing
const MAX_AGE_MS = 330_000;
// After failures, wait 1, 2, 4… minutes between retries (at most 15), rather than retrying on every HA update
const MAX_BACKOFF_MS = 900_000;

const STYLE = `
  ha-card { padding: 16px; cursor: pointer; }
  :host(:focus-visible) { outline: none; }
  :host(:focus-visible) ha-card { outline: 2px solid var(--primary-color); outline-offset: 2px; }
  ${CARD_STYLE}
`;

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
    this._token = 0;
    this._reset();
    // Tapping (or Enter/Space) opens the full report for the child
    this.addEventListener("click", () => this._openReport());
    this.addEventListener("keydown", (ev) => {
      if (ev.key !== "Enter" && ev.key !== " ") return;
      ev.preventDefault();
      this._openReport();
    });
  }

  // Attributes are set here, not in the constructor: document.createElement rejects an element that sets its own
  connectedCallback() {
    this.setAttribute("role", "button");
    if (!this.hasAttribute("tabindex")) this.tabIndex = 0;
  }

  _openReport() {
    const state = this._hass?.states[this._config?.entity];
    if (!state?.attributes?.profile_id) return;
    openReport({
      hass: this._hass,
      entity: this._config.entity,
      profileId: state.attributes.profile_id,
      name: state.attributes.friendly_name ?? this._config.entity,
      returnFocus: this,
    });
  }

  setConfig(config) {
    if (!config?.entity) throw new Error("Please choose a screen time sensor");
    // A different child: forget the old one's report, and ignore any of its requests still in flight
    if (this._config && config.entity !== this._config.entity) this._reset();
    this._config = config;
  }

  _reset() {
    this._token += 1;
    this._report = undefined;
    this._error = null;
    this._errors = 0;
    this._inFlight = false;
    this._lastFetch = 0;
    this._lastSeen = undefined;
    this._requestedDate = undefined;
  }

  set hass(hass) {
    this._hass = hass;
    const state = hass.states[this._config?.entity];
    if (!state) {
      this._render(`<div class="message">Sensor ${escapeHtml(this._config?.entity)} not found</div>`);
      return;
    }
    if (!this._inFlight && this._shouldFetch(state)) {
      this._fetch(state);
    } else if (!this._report && !this._error) {
      this._render(`<div class="message">Loading…</div>`);
    }
  }

  _shouldFetch(state) {
    if (this._lastSeen === undefined) return true;
    const age = Date.now() - this._lastFetch;
    // Never sooner than a minute after the last fetch, and back off further after failures
    const wait = this._errors ? Math.min(MIN_REFETCH_MS * 2 ** (this._errors - 1), MAX_BACKOFF_MS) : MIN_REFETCH_MS;
    if (age < wait) return false;
    if (this._errors) return true;
    if (age >= MAX_AGE_MS) return true;
    if (this._requestedDate !== localDate(this._hass.config.time_zone)) return true;
    return state.last_updated !== this._lastSeen;
  }

  async _fetch(state) {
    const token = this._token;
    const date = localDate(this._hass.config.time_zone);
    this._inFlight = true;
    this._lastSeen = state.last_updated;
    this._requestedDate = date;
    let report;
    let error = null;
    try {
      report = await this._hass.callWS({ type: "qustodio/day_report", profile_id: state.attributes.profile_id, date });
    } catch (err) {
      error = err?.code ?? "unknown";
    }
    if (token !== this._token) return; // the card was switched to another sensor meanwhile
    this._inFlight = false;
    this._lastFetch = Date.now();
    if (error) {
      this._error = error;
      this._errors += 1;
    } else {
      this._report = report;
      this._error = null;
      this._errors = 0;
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
    try {
      this._render(renderCard(this._report, { name, tz: this._hass.config.time_zone, dark }));
    } catch (err) {
      // Unexpected data shouldn't leave the card on "Loading…"
      console.error("Screen time card couldn't draw the report", err);
      this._render(`<div class="title">${escapeHtml(name)}</div><div class="message">${escapeHtml(errorText())}</div>`);
    }
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
