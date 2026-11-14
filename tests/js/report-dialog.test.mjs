// Tests for the screen time report popup, with a minimal fake DOM. Run: node --test "tests/js/**/*.test.mjs"
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

// ---- Fake DOM ----------------------------------------------------------------------------------------------------
const defined = {};
const windowListeners = {};
const historyLog = [];
let focused = null;

globalThis.window = globalThis;
globalThis.addEventListener = (type, fn) => {
  (windowListeners[type] ??= new Set()).add(fn);
};
globalThis.removeEventListener = (type, fn) => windowListeners[type]?.delete(fn);
const fire = (type, event = {}) => [...(windowListeners[type] ?? [])].forEach((fn) => fn(event));
const historyStack = [null];
globalThis.history = {
  get state() {
    return historyStack[historyStack.length - 1];
  },
  pushState: (state) => {
    historyLog.push(["push", state]);
    historyStack.push(state);
  },
  back: () => {
    historyLog.push(["back"]);
    if (historyStack.length > 1) historyStack.pop();
  },
};
globalThis.HTMLElement = class {
  constructor() {
    this.removed = false;
  }
  attachShadow() {
    const listeners = {};
    this.shadowRoot = {
      innerHTML: "",
      addEventListener: (type, fn) => {
        listeners[type] = fn;
      },
      dispatch: (type, event) => listeners[type]?.(event),
      querySelector: (selector) => ({ focus: () => (focused = selector) }),
    };
    return this.shadowRoot;
  }
  remove() {
    this.removed = true;
    document.body.children.delete(this);
  }
};
globalThis.document = {
  documentElement: { style: { overflow: "" } },
  createElement: (tag) => new defined[tag](),
  body: {
    children: new Set(),
    appendChild(el) {
      this.children.add(el);
    },
  },
};
globalThis.customElements = {
  define: (name, cls) => {
    defined[name] = cls;
  },
  get: (name) => defined[name],
};

const { openReport } = await import("../../custom_components/qustodio/www/report-dialog.js");
const { dayLabel } = await import("../../custom_components/qustodio/www/report-logic.js");

// ---- Helpers -----------------------------------------------------------------------------------------------------
const FIXTURE = JSON.parse(readFileSync(new URL("./fixtures/day-report-2026-11-10.json", import.meta.url)));
const TZ = "Australia/Sydney";
const tick = () => new Promise((resolve) => setTimeout(resolve, 0));
const todayString = () =>
  new Intl.DateTimeFormat("en-CA", { timeZone: TZ, year: "numeric", month: "2-digit", day: "2-digit" }).format(
    new Date(Date.now()),
  );
const shift = (date, days) => new Date(Date.parse(`${date}T00:00:00Z`) + days * 86_400_000).toISOString().slice(0, 10);

function hassWith(callWS) {
  return { config: { time_zone: TZ }, themes: { darkMode: false }, callWS };
}

function open(callWS, extra = {}) {
  const returnFocus = { focus: () => (focused = "card") };
  const el = openReport({ hass: hassWith(callWS), entity: "sensor.child_one", profileId: "p1", name: "Child One", returnFocus, ...extra });
  return el;
}

const action = (el, name) => el.shadowRoot.dispatch("click", { target: { closest: () => ({ dataset: { action: name } }) } });
const reportFor = (msg) => ({ ...FIXTURE, date: msg.date });

function reset() {
  historyLog.length = 0;
  historyStack.length = 1;
  document.documentElement.style.overflow = "";
  for (const el of [...document.body.children]) el.close?.();
  historyLog.length = 0;
  historyStack.length = 1;
  for (const key of Object.keys(windowListeners)) windowListeners[key].clear();
  document.body.children.clear();
  focused = null;
}

// ---- Tests -------------------------------------------------------------------------------------------------------
test("opening adds one history entry, focuses close, and fetches today", async () => {
  reset();
  const calls = [];
  const el = open(async (msg) => {
    calls.push(msg);
    return reportFor(msg);
  });
  await tick();
  assert.ok(document.body.children.has(el));
  assert.deepEqual(historyLog, [["push", { qustodioReport: true }]]);
  assert.equal(calls.length, 1);
  assert.deepEqual(calls[0], { type: "qustodio/day_report", profile_id: "p1", date: todayString() });
  assert.match(el.shadowRoot.innerHTML, /role="dialog"/);
  assert.match(el.shadowRoot.innerHTML, /aria-modal="true"/);
  assert.match(el.shadowRoot.innerHTML, />Today</);
  assert.match(el.shadowRoot.innerHTML, /class="hourly"/);
  assert.equal(focused, '[data-action="close"]');
});

test("◀ shows yesterday; ▶ is disabled on today and Today appears on other days", async () => {
  reset();
  const calls = [];
  const el = open(async (msg) => {
    calls.push(msg.date);
    return reportFor(msg);
  });
  await tick();
  assert.match(el.shadowRoot.innerHTML, /data-action="next"[^>]*disabled/);
  assert.doesNotMatch(el.shadowRoot.innerHTML, /data-action="today"/);
  action(el, "prev");
  await tick();
  assert.deepEqual(calls, [todayString(), shift(todayString(), -1)]);
  assert.match(el.shadowRoot.innerHTML, />Yesterday</);
  assert.match(el.shadowRoot.innerHTML, /data-action="today"/);
  action(el, "today");
  await tick();
  assert.match(el.shadowRoot.innerHTML, />Today</);
});

test("rapid ◀◀◀ draws only the last day asked for", async () => {
  reset();
  const pending = [];
  const el = open((msg) => new Promise((resolve) => pending.push({ msg, resolve })));
  pending[0].resolve(reportFor(pending[0].msg));
  await tick();
  action(el, "prev");
  action(el, "prev");
  action(el, "prev");
  const days = pending.slice(1).map((p) => p.msg.date);
  assert.deepEqual(days, [-1, -2, -3].map((d) => shift(todayString(), d)));
  // Answers arrive out of order: the -3 day first, then the older requests
  pending[3].resolve({ ...reportFor(pending[3].msg), counted_minutes: 33 });
  await tick();
  pending[1].resolve({ ...reportFor(pending[1].msg), counted_minutes: 11 });
  pending[2].resolve({ ...reportFor(pending[2].msg), counted_minutes: 22 });
  await tick();
  assert.match(el.shadowRoot.innerHTML, /<span class="big">33 \/ 120 min/);
});

test("past days are cached; today is reused within a minute", async () => {
  reset();
  const calls = [];
  const el = open(async (msg) => {
    calls.push(msg.date);
    return reportFor(msg);
  });
  await tick();
  action(el, "prev");
  await tick();
  action(el, "next");
  await tick();
  action(el, "prev");
  await tick();
  assert.deepEqual(calls, [todayString(), shift(todayString(), -1)]);
});

test("◀ stops at 30 days back", async () => {
  reset();
  const el = open(async (msg) => reportFor(msg));
  await tick();
  for (let i = 0; i < 30; i++) {
    action(el, "prev");
    await tick();
  }
  assert.match(el.shadowRoot.innerHTML, /data-action="prev"[^>]*disabled/);
  action(el, "prev"); // ignored
  await tick();
  assert.match(el.shadowRoot.innerHTML, new RegExp(`<span class="day">${dayLabel(shift(todayString(), -30), todayString())}</span>`));
});

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

for (const how of ["close", "backdrop"]) {
  test(`closing with ${how} removes it, goes back once, and returns focus`, async () => {
    reset();
    const el = open(async (msg) => reportFor(msg));
    await tick();
    assert.match(el.shadowRoot.innerHTML, /<div class="backdrop" data-action="backdrop"><\/div>/);
    if (how === "backdrop") await sleep(320); // a backdrop tap straight after opening is ignored (double-tap)
    action(el, how);
    assert.ok(el.removed);
    assert.deepEqual(historyLog, [["push", { qustodioReport: true }], ["back"]]);
    assert.equal(focused, "card");
    assert.equal(windowListeners.popstate.size, 0);
    assert.equal(windowListeners.keydown.size, 0);
  });
}

test("Escape closes it", async () => {
  reset();
  const el = open(async (msg) => reportFor(msg));
  await tick();
  fire("keydown", { key: "Escape" });
  assert.ok(el.removed);
  assert.deepEqual(historyLog, [["push", { qustodioReport: true }], ["back"]]);
});

test("the Back button closes it without going back again", async () => {
  reset();
  const el = open(async (msg) => reportFor(msg));
  await tick();
  fire("popstate");
  assert.ok(el.removed);
  assert.deepEqual(historyLog, [["push", { qustodioReport: true }]]);
  fire("popstate"); // a later Back after it's closed does nothing more
  assert.deepEqual(historyLog, [["push", { qustodioReport: true }]]);
});

test("a response arriving after closing isn't drawn", async () => {
  reset();
  let resolve;
  const el = open(() => new Promise((r) => (resolve = r)));
  action(el, "close");
  const before = el.shadowRoot.innerHTML;
  resolve(reportFor({ date: todayString() }));
  await tick();
  assert.equal(el.shadowRoot.innerHTML, before);
});

test("errors show the card's message with Try again, which refetches", async () => {
  reset();
  let fail = true;
  const calls = [];
  const el = open(async (msg) => {
    calls.push(msg.date);
    if (fail) throw { code: "connection_error" };
    return reportFor(msg);
  });
  await tick();
  assert.match(el.shadowRoot.innerHTML, /Couldn&#39;t load today&#39;s screen time/);
  assert.match(el.shadowRoot.innerHTML, /data-action="retry"/);
  fail = false;
  action(el, "retry");
  await tick();
  assert.equal(calls.length, 2);
  assert.match(el.shadowRoot.innerHTML, /class="hourly"/);
});

test("Show all expands the ranked list", async () => {
  reset();
  const apps = Array.from({ length: 12 }, (_, i) => ({ name: `App ${i}`, package: `a${i}`, platform: "iOS", minutes: 20 - i }));
  const el = open(async (msg) => ({ ...reportFor(msg), apps, websites: [] }));
  await tick();
  assert.equal((el.shadowRoot.innerHTML.match(/class="item"/g) ?? []).length, 10);
  action(el, "toggle-all");
  assert.equal((el.shadowRoot.innerHTML.match(/class="item"/g) ?? []).length, 12);
});

test("clicks outside any action do nothing", async () => {
  reset();
  const el = open(async (msg) => reportFor(msg));
  await tick();
  el.shadowRoot.dispatch("click", { target: { closest: () => null } });
  assert.ok(!el.removed);
});

test("loads its modules with the same version tag as itself", () => {
  const source = readFileSync(new URL("../../custom_components/qustodio/www/report-dialog.js", import.meta.url), "utf8");
  assert.doesNotMatch(source, /^import .* from "\.\/(card|report)-logic\.js";?$/m);
  assert.match(source, /new URL\("\.\/card-logic\.js" \+ version, import\.meta\.url\)/);
  assert.match(source, /new URL\("\.\/report-logic\.js" \+ version, import\.meta\.url\)/);
});


test("a backdrop tap straight after opening (the second tap of a double-tap) doesn't close it", async () => {
  reset();
  const el = open(async (msg) => reportFor(msg));
  action(el, "backdrop");
  assert.ok(!el.removed);
});

test("only one popup at a time: opening again reuses the open one", async () => {
  reset();
  const first = open(async (msg) => reportFor(msg));
  const second = open(async (msg) => reportFor(msg));
  assert.equal(second, first);
  assert.equal(document.body.children.size, 1);
  assert.equal(historyLog.length, 1);
});

test("× doesn't go back if something else has added a history entry since opening", async () => {
  reset();
  const el = open(async (msg) => reportFor(msg));
  await tick();
  history.pushState({ somewhereElse: true }, ""); // e.g. Home Assistant navigated
  action(el, "close");
  assert.ok(el.removed);
  assert.ok(!historyLog.some(([kind]) => kind === "back"));
});

test("Home Assistant navigating closes it without going back", async () => {
  reset();
  const el = open(async (msg) => reportFor(msg));
  await tick();
  fire("location-changed");
  assert.ok(el.removed);
  assert.ok(!historyLog.some(([kind]) => kind === "back"));
  assert.equal(windowListeners["location-changed"].size, 0);
});

test("locks the page behind from scrolling while open", async () => {
  reset();
  document.documentElement.style.overflow = "auto";
  const el = open(async (msg) => reportFor(msg));
  assert.equal(document.documentElement.style.overflow, "hidden");
  action(el, "close");
  assert.equal(document.documentElement.style.overflow, "auto");
});

test("a late failure for a day already shown doesn't replace it", async () => {
  reset();
  const pending = [];
  const el = open((msg) => new Promise((resolve, reject) => pending.push({ msg, resolve, reject })));
  pending[0].resolve(reportFor(pending[0].msg));
  await tick();
  action(el, "prev"); // yesterday, request A (still loading)
  action(el, "next"); // back to today (cached)
  action(el, "prev"); // yesterday again, request B
  assert.deepEqual(pending.slice(1).map((p) => p.msg.date), [shift(todayString(), -1), shift(todayString(), -1)]);
  pending[2].resolve({ ...reportFor(pending[2].msg), counted_minutes: 77 });
  await tick();
  pending[1].reject({ code: "connection_error" }); // A fails late
  await tick();
  assert.match(el.shadowRoot.innerHTML, /<span class="big">77 \/ 120 min/);
  assert.doesNotMatch(el.shadowRoot.innerHTML, /Couldn&#39;t load/);
});

test("when the button pressed becomes disabled, focus moves to close", async () => {
  reset();
  const el = open(async (msg) => reportFor(msg));
  await tick();
  action(el, "prev");
  await tick();
  assert.equal(focused, '[data-action="prev"]');
  action(el, "next"); // back on today: ▶ is now disabled
  await tick();
  assert.equal(focused, '[data-action="close"]');
});

test("after midnight, ▶ reaches the new day", async () => {
  reset();
  const realNow = Date.now;
  const start = Date.parse(`${todayString()}T23:59:30+11:00`);
  let now = start;
  Date.now = () => now;
  try {
    const calls = [];
    const el = open(async (msg) => {
      calls.push(msg.date);
      return reportFor(msg);
    });
    await tick();
    now += 120_000; // 00:01:30 the next day
    action(el, "next");
    await tick();
    assert.equal(calls.at(-1), shift(calls[0], 1));
    assert.match(el.shadowRoot.innerHTML, />Today</);
  } finally {
    Date.now = realNow;
  }
});

test("a day that can't be drawn shows an error with Try again, not Loading", async () => {
  reset();
  const el = open(async (msg) => ({ ...reportFor(msg), hours: [{ start: "not a time", default_minutes: 5, routines: {} }] }));
  await tick();
  assert.match(el.shadowRoot.innerHTML, /Couldn&#39;t load today&#39;s screen time/);
  assert.match(el.shadowRoot.innerHTML, /data-action="retry"/);
  assert.doesNotMatch(el.shadowRoot.innerHTML, /Loading/);
});
