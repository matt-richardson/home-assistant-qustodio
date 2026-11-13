// Smoke tests for the card element, with a minimal fake DOM. Run: node --test "tests/js/**/*.test.mjs"
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

const defined = {};
globalThis.window = globalThis;
globalThis.HTMLElement = class {
  constructor() {
    this.listeners = {};
    this.events = [];
  }
  attachShadow() {
    this.shadowRoot = { innerHTML: "" };
    return this.shadowRoot;
  }
  addEventListener(type, fn) {
    this.listeners[type] = fn;
  }
  dispatchEvent(event) {
    this.events.push(event);
    return true;
  }
};
globalThis.CustomEvent = class {
  constructor(type, init) {
    this.type = type;
    this.detail = init?.detail;
  }
};
globalThis.customElements = {
  define: (name, cls) => {
    defined[name] = cls;
  },
  get: (name) => defined[name],
};

await import("../../custom_components/qustodio/www/qustodio-screen-time-card.js");
const Card = defined["qustodio-screen-time-card"];
const REPORT = JSON.parse(readFileSync(new URL("./fixtures/day-report-2026-11-10.json", import.meta.url)));
const ENTITY = "sensor.child_one";

function makeHass(lastUpdated, callWS) {
  return {
    states: {
      [ENTITY]: {
        entity_id: ENTITY,
        last_updated: lastUpdated,
        attributes: { profile_id: "profile_1", friendly_name: "Child One", attribution: "Data provided by Qustodio" },
      },
    },
    config: { time_zone: "Australia/Sydney" },
    themes: { darkMode: false },
    callWS,
  };
}

const tick = () => new Promise((resolve) => setTimeout(resolve, 0));

test("registers the element and a card picker entry", () => {
  assert.ok(Card);
  const entry = window.customCards.find((c) => c.type === "qustodio-screen-time-card");
  assert.ok(entry);
  assert.equal(entry.name, "Screen time");
});

test("config form offers a Qustodio sensor picker", () => {
  const [field] = Card.getConfigForm().schema;
  assert.equal(field.name, "entity");
  assert.deepEqual(field.selector.entity.filter, [{ integration: "qustodio", domain: "sensor" }]);
});

test("stub config picks the first Qustodio sensor with a profile", () => {
  const hass = {
    states: {
      "sensor.other": { entity_id: "sensor.other", attributes: { profile_id: "x" } },
      [ENTITY]: { entity_id: ENTITY, attributes: { profile_id: "profile_1", attribution: "Data provided by Qustodio" } },
    },
  };
  assert.deepEqual(Card.getStubConfig(hass), { entity: ENTITY });
});

test("setConfig requires a sensor", () => {
  const card = new Card();
  assert.throws(() => card.setConfig({}), /Please choose a screen time sensor/);
});

test("fetches today's report and renders it", async () => {
  const calls = [];
  const card = new Card();
  card.setConfig({ entity: ENTITY });
  card.hass = makeHass("t1", async (msg) => {
    calls.push(msg);
    return REPORT;
  });
  await tick();
  assert.equal(calls.length, 1);
  assert.equal(calls[0].type, "qustodio/day_report");
  assert.equal(calls[0].profile_id, "profile_1");
  assert.match(calls[0].date, /^\d{4}-\d{2}-\d{2}$/);
  assert.match(card.shadowRoot.innerHTML, /113\.5/);
  assert.equal(card.getCardSize(), 3);
});

test("doesn't refetch within a minute, or while a request is in flight", async () => {
  let resolve;
  const calls = [];
  const card = new Card();
  card.setConfig({ entity: ENTITY });
  const callWS = (msg) => {
    calls.push(msg);
    return new Promise((r) => {
      resolve = r;
    });
  };
  card.hass = makeHass("t1", callWS);
  card.hass = makeHass("t2", callWS); // sensor updated while the first request is in flight
  assert.equal(calls.length, 1);
  resolve(REPORT);
  await tick();
  card.hass = makeHass("t3", callWS); // within a minute of the last fetch
  assert.equal(calls.length, 1);
});

test("shows an error message from the API", async () => {
  const card = new Card();
  card.setConfig({ entity: ENTITY });
  card.hass = makeHass("t1", async () => {
    throw { code: "unauthorized", message: "nope" };
  });
  await tick();
  assert.match(card.shadowRoot.innerHTML, /Only admins can view this report/);
});

test("clicking opens more-info for the sensor", async () => {
  const card = new Card();
  card.setConfig({ entity: ENTITY });
  card.listeners.click();
  assert.equal(card.events[0].type, "hass-more-info");
  assert.deepEqual(card.events[0].detail, { entityId: ENTITY });
});

test("shows a message when the configured sensor doesn't exist", () => {
  const card = new Card();
  card.setConfig({ entity: "sensor.gone" });
  card.hass = makeHass("t1", async () => REPORT);
  assert.match(card.shadowRoot.innerHTML, /Sensor sensor\.gone not found/);
});
