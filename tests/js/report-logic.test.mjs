// Tests for the screen time report's pure logic and rendering. Run: node --test "tests/js/**/*.test.mjs"
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

import { renderCard } from "../../custom_components/qustodio/www/card-logic.js";
import {
  dayLabel,
  hourlyMinutes,
  nextSort,
  rankedUsage,
  renderReport,
  stepDay,
} from "../../custom_components/qustodio/www/report-logic.js";

const TZ = "Australia/Sydney";
const FIXTURE = JSON.parse(readFileSync(new URL("./fixtures/day-report-2026-11-10.json", import.meta.url)));
const report = (overrides = {}) => ({ ...structuredClone(FIXTURE), ...overrides });
const opts = (overrides = {}) => ({ name: "Child One", tz: TZ, dark: false, today: "2026-11-10", showAll: false, ...overrides });
const round2 = (n) => Math.round(n * 100) / 100;

test("stepDay moves by calendar days within today and 30 days back", () => {
  const today = "2026-11-14";
  assert.equal(stepDay("2026-11-14", -1, today), "2026-11-13");
  assert.equal(stepDay("2026-11-14", 1, today), null); // no future days
  assert.equal(stepDay("2026-11-01", -1, today), "2026-10-31"); // month boundary
  assert.equal(stepDay("2026-10-16", -1, today), "2026-10-15"); // exactly 30 days back
  assert.equal(stepDay("2026-10-15", -1, today), null); // 31 days back
  assert.equal(stepDay("2026-10-15", 1, today), "2026-10-16");
});

test("stepDay isn't thrown by the daylight-saving change", () => {
  assert.equal(stepDay("2026-10-04", -1, "2026-10-20"), "2026-10-03");
  assert.equal(stepDay("2026-10-04", 1, "2026-10-20"), "2026-10-05");
  assert.equal(stepDay("2026-04-05", 1, "2026-04-20"), "2026-04-06");
});

test("dayLabel", () => {
  assert.equal(dayLabel("2026-11-14", "2026-11-14"), "Today");
  assert.equal(dayLabel("2026-11-13", "2026-11-14"), "Yesterday");
  assert.equal(dayLabel("2026-11-12", "2026-11-14"), "Thu 12 Nov");
  assert.equal(dayLabel("2026-10-31", "2026-11-14"), "Sat 31 Oct");
});

test("hourlyMinutes: each hour with usage, in local time", () => {
  const hours = hourlyMinutes(report(), TZ);
  assert.equal(hours.length, report().hours.length);
  assert.deepEqual(hours.find((h) => h.hour === 15), { hour: 15, minutes: 39.2 });
});

test("rankedUsage merges apps and websites, largest first, dropping zero minutes", () => {
  const r = report({
    apps: [
      { name: "Video app", package: "v", platform: "iOS", minutes: 35, thumbnail: null },
      { name: "Idle", package: "i", platform: "Android", minutes: 0, thumbnail: null },
      { name: "Maps", package: "m", platform: "Android", minutes: 10, thumbnail: null },
    ],
    websites: [{ host: "example.com", minutes: 10, pages: 3, blocked_pages: 0 }],
  });
  assert.deepEqual(rankedUsage(r), [
    { kind: "app", name: "Video app", detail: "App · iOS", minutes: 35, sharePct: 100 },
    { kind: "website", name: "example.com", detail: "Website", minutes: 10, sharePct: (10 / 35) * 100 },
    { kind: "app", name: "Maps", detail: "App · Android", minutes: 10, sharePct: (10 / 35) * 100 },
  ]);
  assert.deepEqual(rankedUsage(report({ apps: [], websites: [] })), []);
});

test("renderReport starts with the card's own summary for the day", () => {
  const html = renderReport(report(), opts());
  assert.ok(html.startsWith(renderCard(report(), { name: "Child One", tz: TZ, dark: false })));
  assert.match(html, /class="ranked"/);
});

test("renderReport ranked list shows the top 10, with Show all for the rest", () => {
  const apps = Array.from({ length: 12 }, (_, i) => ({ name: `App ${i}`, package: `a${i}`, platform: "iOS", minutes: 20 - i }));
  const r = report({ apps, websites: [] });
  const top = renderReport(r, opts());
  assert.equal((top.match(/class="item"/g) ?? []).length, 10);
  assert.match(top, /<button class="show-all"[^>]*>Show all 12<\/button>/);
  const all = renderReport(r, opts({ showAll: true }));
  assert.equal((all.match(/class="item"/g) ?? []).length, 12);
  assert.match(all, /<button class="show-all"[^>]*>Show fewer<\/button>/);
  assert.doesNotMatch(renderReport(report(), opts()), /show-all/); // 2 items: no toggle
});

test("renderReport shows whole minutes in the ranked list", () => {
  const r = report({ apps: [{ name: "Reader", package: "r", platform: "macOS", minutes: 12.2 }], websites: [] });
  assert.match(renderReport(r, opts()), /Reader<\/td><td class="detail">App · macOS<\/td><td class="minutes">13 min<\/td>/);
});

test("renderReport notes: partial data, and past days use today's settings", () => {
  assert.match(renderReport(report({ partial: ["apps"] }), opts()), /Apps and websites couldn&#39;t be loaded for this day\./);
  assert.doesNotMatch(renderReport(report(), opts()), /couldn&#39;t be loaded/);
  const past = renderReport(report(), opts({ today: "2026-11-14" }));
  assert.match(past, /Routines and limits shown are today&#39;s settings; extra time isn&#39;t included\./);
  assert.doesNotMatch(renderReport(report(), opts()), /today&#39;s settings/); // the report is for today
});

test("renderReport escapes app names and website hosts", () => {
  const r = report({
    apps: [{ name: "<img src=x onerror=alert(1)>", package: "x", platform: "iOS", minutes: 5 }],
    websites: [{ host: "<script>x</script>.com", minutes: 4, pages: 1, blocked_pages: 0 }],
  });
  const html = renderReport(r, opts());
  assert.doesNotMatch(html, /<img/);
  assert.doesNotMatch(html, /<script>/);
  assert.match(html, /&lt;img src=x onerror=alert\(1\)&gt;/);
});

test("renderReport has no hourly chart (the card's bar already shows the hours)", () => {
  const html = renderReport(report(), opts());
  assert.doesNotMatch(html, /class="hourly"/);
  assert.doesNotMatch(html, /class="column"/);
});

test("renderReport hourly table lists each hour with usage", () => {
  const html = renderReport(report(), opts());
  const table = html.match(/<details class="table">.*?<table>(.*?)<\/table>/s)[1];
  assert.equal((table.match(/<tr>/g) ?? []).length, report().hours.length + 1); // + header row
  assert.match(table, /<td>3pm<\/td><td>40<\/td>/);
});

test("renderReport for an empty day", () => {
  const html = renderReport(report({ hours: [], routines: [], apps: [], websites: [], total_minutes: 0, counted_minutes: 0 }), opts());
  assert.match(html, /No screen time yet today/);
  assert.doesNotMatch(html, /class="ranked"/);
});

test("loads card-logic.js with the same version tag as the report", () => {
  const source = readFileSync(new URL("../../custom_components/qustodio/www/report-logic.js", import.meta.url), "utf8");
  assert.doesNotMatch(source, /^import .* from "\.\/card-logic\.js";?$/m);
  assert.match(source, /import\(new URL\("\.\/card-logic\.js" \+ new URL\(import\.meta\.url\)\.search, import\.meta\.url\)\)/);
});

test("rankedUsage copes with items that have no name", () => {
  const r = report({
    apps: [
      { name: null, package: "x", platform: "iOS", minutes: 5 },
      { name: "Maps", package: "m", platform: "iOS", minutes: 5 },
    ],
    websites: [{ host: null, minutes: 5, pages: 1, blocked_pages: 0 }],
  });
  assert.equal(rankedUsage(r).length, 3);
});

// ---- Sorting the apps and websites list ----

const MIXED = () =>
  report({
    apps: [
      { name: "beta", package: "b", platform: "iOS", minutes: 5 },
      { name: "Alpha", package: "a", platform: "Android", minutes: 20 },
    ],
    websites: [{ host: "gamma.com", minutes: 10, pages: 1, blocked_pages: 0 }],
  });
const names = (items) => items.map((i) => i.name);

test("rankedUsage sorts by name, type or minutes, either way", () => {
  assert.deepEqual(names(rankedUsage(MIXED())), ["Alpha", "gamma.com", "beta"]); // default: most minutes first
  assert.deepEqual(names(rankedUsage(MIXED(), { key: "minutes", dir: "asc" })), ["beta", "gamma.com", "Alpha"]);
  assert.deepEqual(names(rankedUsage(MIXED(), { key: "name", dir: "asc" })), ["Alpha", "beta", "gamma.com"]);
  assert.deepEqual(names(rankedUsage(MIXED(), { key: "name", dir: "desc" })), ["gamma.com", "beta", "Alpha"]);
  // Type: "App · Android" < "App · iOS" < "Website"
  assert.deepEqual(names(rankedUsage(MIXED(), { key: "detail", dir: "asc" })), ["Alpha", "beta", "gamma.com"]);
  assert.deepEqual(names(rankedUsage(MIXED(), { key: "detail", dir: "desc" })), ["gamma.com", "beta", "Alpha"]);
});

test("rankedUsage breaks ties by most minutes, then name", () => {
  const r = report({
    apps: [
      { name: "b", package: "b", platform: "iOS", minutes: 5 },
      { name: "a", package: "a", platform: "iOS", minutes: 5 },
      { name: "c", package: "c", platform: "iOS", minutes: 9 },
    ],
    websites: [],
  });
  assert.deepEqual(names(rankedUsage(r, { key: "detail", dir: "asc" })), ["c", "a", "b"]);
});

test("rankedUsage share bars stay relative to the largest item, whatever the order", () => {
  const items = rankedUsage(MIXED(), { key: "minutes", dir: "asc" });
  assert.deepEqual(items.map((i) => i.sharePct), [25, 50, 100]);
});

test("nextSort: a new column starts A to Z (minutes: largest first); the same column flips", () => {
  const start = { key: "minutes", dir: "desc" };
  assert.deepEqual(nextSort(start, "name"), { key: "name", dir: "asc" });
  assert.deepEqual(nextSort(start, "detail"), { key: "detail", dir: "asc" });
  assert.deepEqual(nextSort(start, "minutes"), { key: "minutes", dir: "asc" });
  assert.deepEqual(nextSort({ key: "name", dir: "asc" }, "name"), { key: "name", dir: "desc" });
  assert.deepEqual(nextSort({ key: "name", dir: "asc" }, "minutes"), { key: "minutes", dir: "desc" });
});

test("renderReport list has sortable headers showing the current sort", () => {
  const html = renderReport(MIXED(), opts());
  assert.match(html, /<th aria-sort="none"><button class="sort" data-action="sort-name">Name<\/button><\/th>/);
  assert.match(html, /<th aria-sort="none"><button class="sort" data-action="sort-detail">Type<\/button><\/th>/);
  assert.match(html, /<th aria-sort="descending"><button class="sort" data-action="sort-minutes">Minutes ▼<\/button><\/th>/);
  const byName = renderReport(MIXED(), opts({ sort: { key: "name", dir: "asc" } }));
  assert.match(byName, /<th aria-sort="ascending"><button class="sort" data-action="sort-name">Name ▲<\/button>/);
  assert.match(byName, /<th aria-sort="none"><button class="sort" data-action="sort-minutes">Minutes<\/button>/);
  assert.ok(byName.indexOf(">Alpha<") < byName.indexOf(">beta<"));
  assert.ok(byName.indexOf(">beta<") < byName.indexOf(">gamma.com<"));
});

test("renderReport list has no headers when there's nothing to list", () => {
  assert.doesNotMatch(renderReport(report({ apps: [], websites: [] }), opts()), /data-action="sort-/);
});
