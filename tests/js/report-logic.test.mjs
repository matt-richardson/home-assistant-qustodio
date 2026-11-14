// Tests for the screen time report's pure logic and rendering. Run: node --test "tests/js/**/*.test.mjs"
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

import { renderCard, stripLayout } from "../../custom_components/qustodio/www/card-logic.js";
import {
  dayLabel,
  hourlyChart,
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

test("hourlyChart: one column per hour with usage, height is the share of the hour used", () => {
  const chart = hourlyChart(report(), TZ);
  const layout = stripLayout(report(), TZ);
  assert.equal(chart.startHour, layout.startHour);
  assert.equal(chart.endHour, layout.endHour);
  assert.deepEqual(chart.bands, { windows: layout.windows, defaultWindows: layout.defaultWindows });
  assert.equal(chart.columns.length, report().hours.length);
  const threePm = chart.columns.find((c) => c.hour === 15);
  assert.equal(threePm.minutes, 39.2);
  assert.equal(round2(threePm.heightPct), 65.33);
  assert.equal(threePm.leftPct, (9 / 16) * 100);
  assert.equal(threePm.label, "3pm · 40 min");
});

test("hourlyChart caps a column at the full hour", () => {
  const r = report({ hours: [{ start: "2026-11-10T09:00:00+11:00", default_minutes: 75, routines: {} }] });
  assert.equal(hourlyChart(r, TZ).columns[0].heightPct, 100);
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
  assert.match(html, /class="hourly"/);
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
  assert.match(renderReport(r, opts()), /Reader<\/span><span class="detail">App · macOS<\/span><span class="minutes">13 min<\/span>/);
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

test("renderReport hourly chart has a column per hour, labelled, with gridlines", () => {
  const html = renderReport(report(), opts());
  const chart = html.match(/<div class="hourly">(.*?)<\/div><\/div><\/div>/s)?.[0] ?? html;
  assert.equal((html.match(/class="column"/g) ?? []).length, report().hours.length);
  assert.match(html, /title="3pm · 40 min"/);
  assert.match(chart, /class="gridline" style="bottom:50%"/);
  assert.match(chart, /class="gridline" style="bottom:100%"/);
});

test("renderReport hourly table lists each hour with usage", () => {
  const html = renderReport(report(), opts());
  const table = html.match(/<table>(.*?)<\/table>/s)[1];
  assert.equal((table.match(/<tr>/g) ?? []).length, report().hours.length + 1); // + header row
  assert.match(table, /<td>3pm<\/td><td>40<\/td>/);
});

test("renderReport for an empty day", () => {
  const html = renderReport(report({ hours: [], routines: [], apps: [], websites: [], total_minutes: 0, counted_minutes: 0 }), opts());
  assert.match(html, /No screen time yet today/);
  assert.doesNotMatch(html, /class="hourly"/);
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
