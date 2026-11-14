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
const TODAY = new Intl.DateTimeFormat("en-CA", { timeZone: "Australia/Sydney", year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date());
// The card asks for today's report, so the server would answer with today's date
const REPORT = { ...JSON.parse(readFileSync(new URL("./fixtures/day-report-2026-11-10.json", import.meta.url))), date: TODAY };
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
  assert.match(card.shadowRoot.innerHTML, /<span class="big">114 \/ 120 min<\/span>/);
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

test("refetches once the server's cache has expired, even if the sensor hasn't changed", async () => {
  const calls = [];
  const card = new Card();
  card.setConfig({ entity: ENTITY });
  const callWS = async (msg) => {
    calls.push(msg);
    return REPORT;
  };
  const realNow = Date.now;
  let now = realNow();
  Date.now = () => now;
  try {
    card.hass = makeHass("t1", callWS);
    await tick();
    now += 2 * 60_000;
    card.hass = makeHass("t1", callWS); // sensor unchanged, cache still fresh
    assert.equal(calls.length, 1);
    now += 4 * 60_000;
    card.hass = makeHass("t1", callWS); // sensor unchanged, but over 5.5 minutes since the last fetch
    await tick();
    assert.equal(calls.length, 2);
  } finally {
    Date.now = realNow;
  }
});

/** Run fn with Date.now() returning a controllable clock; returns {advance(ms)}. */
async function withClock(startIso, fn) {
  const realNow = Date.now;
  let now = Date.parse(startIso);
  Date.now = () => now;
  try {
    await fn({ advance: (ms) => (now += ms) });
  } finally {
    Date.now = realNow;
  }
}

test("after midnight, refetches for the new day, but no sooner than a minute after the last fetch", async () => {
  const calls = [];
  const card = new Card();
  card.setConfig({ entity: ENTITY });
  const callWS = async (msg) => {
    calls.push(msg);
    return { ...REPORT, date: msg.date };
  };
  await withClock("2026-11-10T23:59:30+11:00", async (clock) => {
    card.hass = makeHass("t1", callWS);
    await tick();
    assert.equal(calls[0].date, "2026-11-10");
    clock.advance(45_000); // 00:00:15, only 45 s since the last fetch
    card.hass = makeHass("t1", callWS);
    await tick();
    assert.equal(calls.length, 1);
    clock.advance(30_000); // 75 s since the last fetch
    card.hass = makeHass("t1", callWS);
    await tick();
    assert.equal(calls.length, 2);
    assert.equal(calls[1].date, "2026-11-11");
  });
});

test("failing fetches back off instead of retrying on every update", async () => {
  const calls = [];
  const card = new Card();
  card.setConfig({ entity: ENTITY });
  const callWS = async (msg) => {
    calls.push(msg);
    throw { code: "rate_limited" };
  };
  await withClock("2026-11-11T00:00:30+11:00", async (clock) => {
    card.hass = makeHass("t1", callWS);
    await tick();
    for (let i = 0; i < 20; i++) {
      clock.advance(2_000); // lots of HA state changes within the first minute
      card.hass = makeHass(`u${i}`, callWS);
      await tick();
    }
    assert.equal(calls.length, 1);
    clock.advance(21_000); // 61 s after the first failure: first retry
    card.hass = makeHass("v1", callWS);
    await tick();
    assert.equal(calls.length, 2);
    clock.advance(61_000); // only 61 s after the second failure: backing off (needs 120 s)
    card.hass = makeHass("v2", callWS);
    await tick();
    assert.equal(calls.length, 2);
    clock.advance(60_000); // 121 s after the second failure
    card.hass = makeHass("v3", callWS);
    await tick();
    assert.equal(calls.length, 3);
  });
});

function twoChildHass(callWS) {
  const child = (id, name, profile) => ({
    entity_id: id,
    last_updated: "t1",
    attributes: { profile_id: profile, friendly_name: name, attribution: "Data provided by Qustodio" },
  });
  return {
    states: { "sensor.alice": child("sensor.alice", "Alice", "p_alice"), "sensor.bob": child("sensor.bob", "Bob", "p_bob") },
    config: { time_zone: "Australia/Sydney" },
    themes: { darkMode: false },
    callWS,
  };
}

test("changing the sensor fetches the new child straight away", async () => {
  const calls = [];
  const card = new Card();
  const callWS = async (msg) => {
    calls.push(msg);
    return REPORT;
  };
  card.setConfig({ entity: "sensor.alice" });
  card.hass = twoChildHass(callWS);
  await tick();
  card.setConfig({ entity: "sensor.bob" });
  card.hass = twoChildHass(callWS);
  await tick();
  assert.deepEqual(
    calls.map((c) => c.profile_id),
    ["p_alice", "p_bob"],
  );
});

test("a response for the previous sensor is ignored", async () => {
  const pending = [];
  const card = new Card();
  const callWS = (msg) => new Promise((resolve) => pending.push({ msg, resolve }));
  card.setConfig({ entity: "sensor.alice" });
  card.hass = twoChildHass(callWS);
  card.setConfig({ entity: "sensor.bob" });
  card.hass = twoChildHass(callWS);
  assert.deepEqual(
    pending.map((p) => p.msg.profile_id),
    ["p_alice", "p_bob"],
  );
  pending[0].resolve({ ...REPORT, counted_minutes: 999 }); // Alice's late answer
  await tick();
  assert.doesNotMatch(card.shadowRoot.innerHTML, /999/);
  pending[1].resolve(REPORT);
  await tick();
  assert.match(card.shadowRoot.innerHTML, /<div class="title">Bob<\/div>/);
  assert.match(card.shadowRoot.innerHTML, /114 \/ 120 min/);
});

test("a report that can't be drawn shows an error instead of staying on Loading", async () => {
  const card = new Card();
  card.setConfig({ entity: ENTITY });
  card.hass = makeHass("t1", async () => ({ ...REPORT, hours: [{ start: "not a time", default_minutes: 5, routines: {} }] }));
  await tick();
  assert.match(card.shadowRoot.innerHTML, /Couldn&#39;t load today&#39;s screen time/); // escaped apostrophes
  assert.doesNotMatch(card.shadowRoot.innerHTML, /Loading/);
});

test("loads card-logic.js with the same version tag as the card", () => {
  const source = readFileSync(new URL("../../custom_components/qustodio/www/qustodio-screen-time-card.js", import.meta.url), "utf8");
  assert.doesNotMatch(source, /^import .* from "\.\/card-logic\.js";?$/m);
  assert.match(source, /import\(new URL\("\.\/card-logic\.js" \+ new URL\(import\.meta\.url\)\.search, import\.meta\.url\)/);
});

test("usage is drawn full height over the routine windows", () => {
  const source = readFileSync(new URL("../../custom_components/qustodio/www/qustodio-screen-time-card.js", import.meta.url), "utf8");
  assert.match(source, /\.use \{ position: absolute; inset: 0; \}/);
});

test("leaves room between the bar's time labels and the routine swatches", () => {
  const source = readFileSync(new URL("../../custom_components/qustodio/www/qustodio-screen-time-card.js", import.meta.url), "utf8");
  assert.match(source, /\.chips\.rules \{ margin: 14px 0 0;/);
});
