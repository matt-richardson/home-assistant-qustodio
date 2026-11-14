// The screen time report popup, opened by tapping the card: a child's day with a day picker, and apps and websites.
// A self-contained modal (not HA's internal dialog manager): closes with ×, Escape, the backdrop, or the browser/app
// Back button. Rendering lives in report-logic.js (unit-tested).
const version = new URL(import.meta.url).search;
const { CARD_STYLE, errorText, escapeHtml, localDate } = await import(
  new URL("./card-logic.js" + version, import.meta.url)
);
const { dayLabel, renderReport, stepDay } = await import(new URL("./report-logic.js" + version, import.meta.url));

const TAG = "qustodio-screen-time-report";
// Today can still change, so a cached report for today is reused for a minute at most; past days are kept
const TODAY_MAX_AGE_MS = 60_000;
// Ignore a backdrop tap this soon after opening: it's the second tap of a double-tap on the card
const BACKDROP_GRACE_MS = 300;
// The open popup, if any: opening again reuses it rather than stacking a second one
let current = null;

const STYLE = `
  :host { position: fixed; inset: 0; z-index: 10; }
  .backdrop { position: fixed; inset: 0; background: rgba(0, 0, 0, 0.5); }
  .dialog {
    overscroll-behavior: contain;
    position: fixed; inset: 0; margin: auto; box-sizing: border-box; width: min(720px, 100%); height: fit-content;
    max-height: 90vh; overflow: auto; padding: 16px 20px; border-radius: 12px;
    background: var(--card-background-color, var(--ha-card-background, #fff)); color: var(--primary-text-color);
  }
  @media (max-width: 600px) { .dialog { height: 100%; max-height: none; border-radius: 0; } }
  .header { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; }
  .header .day { flex: 1; text-align: center; font-weight: 500; }
  button {
    font: inherit; background: none; color: var(--primary-text-color); cursor: pointer;
    border: 1px solid var(--divider-color); border-radius: 6px; padding: 4px 10px;
  }
  button:disabled { opacity: 0.35; cursor: default; }
  .close { border: none; font-size: 20px; line-height: 1; }
  .ranked { margin-top: 20px; }
  .ranked h3 { font-size: 14px; font-weight: 500; margin: 0 0 8px; }
  .item { display: grid; grid-template-columns: 1fr auto auto; gap: 4px 12px; padding: 6px 0; font-size: 13px; border-bottom: 1px solid var(--divider-color); }
  .item .detail { color: var(--secondary-text-color); }
  .item .minutes { font-variant-numeric: tabular-nums; }
  .item .share { grid-column: 1 / -1; height: 3px; border-radius: 2px; background: var(--primary-color); }
  .show-all, .retry { margin-top: 10px; }
  details.table { margin-top: 16px; color: var(--secondary-text-color); font-size: 12px; }
  table { border-collapse: collapse; margin-top: 6px; }
  th, td { text-align: left; padding: 2px 16px 2px 0; }
  ${CARD_STYLE}
`;

class QustodioScreenTimeReport extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._cache = new Map();
    this._token = 0;
    this._closed = false;
    this._showAll = false;
    this._onKey = (ev) => {
      if (ev.key === "Escape") this.close();
    };
    this._onPopState = () => this.close({ goBack: false });
    // Home Assistant navigating to another view: close, and leave history alone
    this._onLocationChanged = () => this.close({ goBack: false });
    this.shadowRoot.addEventListener("click", (ev) => {
      const target = ev.target?.closest?.("[data-action]");
      if (target) this._act(target.dataset.action);
    });
  }

  /** Show the popup for a child, starting on today. */
  open({ hass, profileId, name, returnFocus }) {
    Object.assign(this, { _hass: hass, _profileId: profileId, _name: name, _returnFocus: returnFocus });
    this._tz = hass.config.time_zone;
    this._today = localDate(this._tz);
    this._openedAt = Date.now();
    // An entry for the popup, so Back closes it rather than leaving the dashboard
    history.pushState({ qustodioReport: true }, "");
    addEventListener("popstate", this._onPopState);
    addEventListener("location-changed", this._onLocationChanged);
    addEventListener("keydown", this._onKey);
    // Keep the dashboard behind from scrolling while the popup is open
    this._pageOverflow = document.documentElement.style.overflow;
    document.documentElement.style.overflow = "hidden";
    this._focus = "close";
    this.showDay(this._today);
  }

  /**
   * Close the popup. goBack removes our history entry, but only while it's still the current one: if something else
   * has added an entry since (Home Assistant navigating, another dialog), going back would undo that instead.
   */
  close({ goBack = true } = {}) {
    if (this._closed) return;
    this._closed = true;
    if (current === this) current = null;
    removeEventListener("popstate", this._onPopState);
    removeEventListener("location-changed", this._onLocationChanged);
    removeEventListener("keydown", this._onKey);
    document.documentElement.style.overflow = this._pageOverflow;
    if (goBack && history.state?.qustodioReport) history.back();
    this.remove();
    this._returnFocus?.focus?.();
  }

  /** Show a day, from the cache when it's fresh enough, otherwise fetching it. */
  showDay(date, { refresh = false } = {}) {
    this._today = localDate(this._tz); // the popup may stay open past midnight
    this._token += 1;
    this._date = date;
    this._showAll = false;
    const cached = this._cache.get(date);
    const fresh = cached && (date !== this._today || Date.now() - cached.at < TODAY_MAX_AGE_MS);
    if (fresh && !refresh) {
      this._render({ report: cached.report });
      return;
    }
    this._render({ loading: true });
    this._fetch(date, this._token);
  }

  async _fetch(date, token) {
    let state;
    try {
      const report = await this._hass.callWS({ type: "qustodio/day_report", profile_id: this._profileId, date });
      this._cache.set(date, { report, at: Date.now() });
      state = { report };
    } catch (err) {
      state = { error: err?.code ?? "unknown" };
    }
    // Only draw the latest request (the user may have moved on, come back, or closed the popup)
    if (!this._closed && token === this._token) this._render(state);
  }

  _act(action) {
    if (action === "close") return this.close();
    if (action === "backdrop") {
      if (Date.now() - this._openedAt >= BACKDROP_GRACE_MS) this.close();
      return undefined;
    }
    if (action === "today") return this._go(this._today, "prev");
    if (action === "retry") return this.showDay(this._date, { refresh: true });
    if (action === "toggle-all") {
      this._showAll = !this._showAll;
      this._focus = "toggle-all";
      return this._render(this._state);
    }
    this._today = localDate(this._tz);
    const next = stepDay(this._date, action === "prev" ? -1 : 1, this._today);
    if (next) this._go(next, action);
    return undefined;
  }

  _go(date, focus) {
    this._focus = focus;
    this.showDay(date);
  }

  _render(state) {
    this._state = state;
    const date = this._date;
    const prev = stepDay(date, -1, this._today);
    const next = stepDay(date, 1, this._today);
    let body;
    if (state.loading) {
      body = `<div class="message">Loading…</div>`;
    } else if (state.error) {
      body = `<div class="message">${escapeHtml(errorText(state.error))}</div><button class="retry" data-action="retry">Try again</button>`;
    } else {
      const dark = Boolean(this._hass.themes?.darkMode);
      const opts = { name: this._name, tz: this._tz, dark, today: this._today, showAll: this._showAll };
      try {
        body = renderReport(state.report, opts);
      } catch (err) {
        // Unexpected data shouldn't leave the popup on "Loading…"
        console.error("Screen time report couldn't draw the day", err);
        body = `<div class="message">${escapeHtml(errorText())}</div><button class="retry" data-action="retry">Try again</button>`;
      }
    }
    const disabled = (day) => (day ? "" : " disabled");
    const todayButton = date === this._today ? "" : `<button class="today" data-action="today">Today</button>`;
    this.shadowRoot.innerHTML =
      `<style>${STYLE}</style><div class="backdrop" data-action="backdrop"></div>` +
      `<div class="dialog" role="dialog" aria-modal="true" aria-label="Screen time report for ${escapeHtml(this._name)}">` +
      `<div class="header">` +
      `<button class="nav" data-action="prev" aria-label="Previous day"${disabled(prev)}>◀</button>` +
      `<span class="day">${escapeHtml(dayLabel(date, this._today))}</span>` +
      `<button class="nav" data-action="next" aria-label="Next day"${disabled(next)}>▶</button>` +
      `${todayButton}<button class="close" data-action="close" aria-label="Close">×</button>` +
      `</div><div class="body">${body}</div></div>`;
    // innerHTML replaces the buttons, so put keyboard focus back where it was (or on close, if that button is now
    // disabled or gone)
    const gone = (this._focus === "prev" && !prev) || (this._focus === "next" && !next) || this._focus === "today";
    this.shadowRoot.querySelector(`[data-action="${gone ? "close" : this._focus}"]`)?.focus?.();
  }
}

if (!customElements.get(TAG)) customElements.define(TAG, QustodioScreenTimeReport);

/** Open the report popup for a child, on today. */
export function openReport(options) {
  if (current && !current._closed) return current;
  current = document.createElement(TAG);
  document.body.appendChild(current);
  current.open(options);
  return current;
}
