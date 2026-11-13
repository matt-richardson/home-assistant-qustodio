// Tests for the screen time card's pure logic and rendering. Run: node --test tests/js/
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

import {
  NORMAL_COLOR,
  OTHER_COLOR,
  countedByHour,
  errorText,
  escapeHtml,
  limitMinutes,
  limitReachedAt,
  minutesOver,
  renderCard,
  routineColors,
  stripLayout,
} from "../../custom_components/qustodio/www/card-logic.js";

const TZ = "Australia/Sydney";
const FIXTURE = JSON.parse(readFileSync(new URL("./fixtures/day-report-2026-11-10.json", import.meta.url)));
const report = (overrides = {}) => ({ ...structuredClone(FIXTURE), ...overrides });
const sum = (values) => Math.round(values.reduce((a, b) => a + b, 0) * 10) / 10;
const round2 = (n) => Math.round(n * 100) / 100;

test("countedByHour splits each hour and excludes routines that don't count", () => {
  const hours = countedByHour(report());
  assert.equal(sum(hours.map((h) => h.total)), 158.2);
  assert.equal(sum(hours.map((h) => h.counted)), 113.5);
  assert.deepEqual(
    hours.map((h) => h.counted),
    [20, 0, 25, 25, 43.5],
  );
  assert.deepEqual(hours[2].byRoutine, { school: 14.2 });
  assert.equal(hours[2].normal, 25);
});

test("countedByHour counts minutes under an unknown routine", () => {
  const r = report({ hours: [{ start: "2026-11-10T09:00:00+11:00", default_minutes: 0, routines: { gone: 10 } }] });
  assert.equal(countedByHour(r)[0].counted, 10);
});

test("limitMinutes is quota plus extra time, or null with no limit", () => {
  assert.equal(limitMinutes(report()), 120);
  assert.equal(limitMinutes(report({ extra_time_minutes: 15 })), 135);
  assert.equal(limitMinutes(report({ quota_minutes: null })), null);
  assert.equal(limitMinutes(report({ quota_minutes: 0 })), 0);
});

test("minutesOver", () => {
  assert.equal(minutesOver(report()), 0);
  assert.equal(minutesOver(report({ quota_minutes: 100 })), 13.5);
  assert.equal(minutesOver(report({ quota_minutes: 100, extra_time_minutes: 20 })), 0);
  assert.equal(minutesOver(report({ quota_minutes: null })), null);
});

test("limitReachedAt is the hour cumulative counted time reaches the limit", () => {
  assert.equal(limitReachedAt(report({ quota_minutes: 60 })), "2026-11-10T16:00:00+11:00");
  assert.equal(limitReachedAt(report({ quota_minutes: 0 })), "2026-11-10T08:00:00+11:00");
  assert.equal(limitReachedAt(report()), null);
  assert.equal(limitReachedAt(report({ quota_minutes: null })), null);
});

test("routineColors gives stable, distinct colours by name, then folds into other", () => {
  const routines = "ABCDEFGHI".split("").map((name, i) => ({ uid: `u${i}`, name, counts: i % 2 === 0 }));
  const colors = routineColors(routines, false);
  const firstSeven = routines.slice(0, 7).map((r) => colors[r.uid].color);
  assert.equal(new Set(firstSeven).size, 7);
  assert.ok(!firstSeven.includes(NORMAL_COLOR(false)));
  assert.equal(colors.u7.color, OTHER_COLOR(false));
  assert.equal(colors.u8.color, OTHER_COLOR(false));
  assert.equal(colors.u0.hatched, false);
  assert.equal(colors.u1.hatched, true);
  // Same routines in a different order (e.g. sorted by minutes) get the same colours
  const reversed = routineColors([...routines].reverse(), false);
  assert.equal(reversed.u3.color, colors.u3.color);
  assert.notEqual(routineColors(routines, true).u0.color, colors.u0.color);
});

test("routineColors gives removed routines the other colour", () => {
  const colors = routineColors([{ uid: "x", name: "Removed routine", counts: true, removed: true }], false);
  assert.equal(colors.x.color, OTHER_COLOR(false));
});

test("stripLayout defaults to 6am-10pm and places windows", () => {
  const layout = stripLayout(report(), TZ);
  assert.equal(layout.startHour, 6);
  assert.equal(layout.endHour, 22);
  const school = layout.windows.find((w) => w.uid === "school");
  assert.equal(round2(school.leftPct), 16.67);
  assert.equal(round2(school.widthPct), 41.15);
  const night = layout.windows.filter((w) => w.uid === "night").map((w) => [w.leftPct, w.widthPct]);
  assert.deepEqual(night, [
    [0, 12.5],
    [87.5, 12.5],
  ]);
  const bar = layout.bars.find((b) => b.hour === 15);
  assert.equal(bar.leftPct, (9 / 16) * 100);
  assert.equal(bar.widthPct, 100 / 16);
  assert.deepEqual(bar.segments, [
    { uid: null, minutes: 25 },
    { uid: "school", minutes: 14.2 },
  ]);
  // The filled width is the share of the hour used: 39.2 of 60 minutes of a 1/16-wide hour
  assert.equal(round2(bar.usedWidthPct), round2((100 / 16) * (39.2 / 60)));
});

test("stripLayout widens to cover usage outside 6am-10pm", () => {
  const r = report();
  r.hours.push({ start: "2026-11-10T04:00:00+11:00", default_minutes: 5, routines: {} });
  r.hours.push({ start: "2026-11-10T23:00:00+11:00", default_minutes: 5, routines: {} });
  const layout = stripLayout(r, TZ);
  assert.equal(layout.startHour, 4);
  assert.equal(layout.endHour, 24);
});

test("escapeHtml escapes markup characters", () => {
  assert.equal(escapeHtml(`<a href="x">'&'</a>`), "&lt;a href=&quot;x&quot;&gt;&#39;&amp;&#39;&lt;/a&gt;");
});

test("renderCard shows counted time against the limit and routine chips", () => {
  const html = renderCard(report(), { name: "Child One", tz: TZ, dark: false });
  assert.match(html, /113\.5/);
  assert.match(html, /120/);
  assert.match(html, /School/);
  assert.match(html, /doesn&#39;t count|doesn’t count/);
  assert.doesNotMatch(html, /over/);
});

test("renderCard shows minutes over and when the limit was hit", () => {
  const html = renderCard(report({ quota_minutes: 60 }), { name: "Child One", tz: TZ, dark: false });
  assert.match(html, /53\.5 min over/);
  assert.match(html, /4pm/);
});

test("renderCard with no limit", () => {
  const html = renderCard(report({ quota_minutes: null }), { name: "Child One", tz: TZ, dark: false });
  assert.match(html, /no limit/);
  assert.doesNotMatch(html, /over/);
});

test("renderCard escapes names from Qustodio", () => {
  const r = report();
  r.routines[0].name = "<img src=x onerror=alert(1)>";
  const html = renderCard(r, { name: "<script>x</script>", tz: TZ, dark: false });
  assert.doesNotMatch(html, /<img/);
  assert.doesNotMatch(html, /<script>/);
  assert.match(html, /&lt;img src=x onerror=alert\(1\)&gt;/);
});

test("renderCard for an empty day", () => {
  const html = renderCard(report({ hours: [], routines: [], total_minutes: 0, counted_minutes: 0 }), {
    name: "Child One",
    tz: TZ,
    dark: false,
  });
  assert.match(html, /No screen time yet today/);
});

test("errorText", () => {
  assert.equal(errorText("unauthorized"), "Only admins can view this report");
  assert.equal(errorText("not_found"), "This sensor isn't a child's screen time sensor");
  assert.equal(errorText("connection_error"), "Couldn't load today's screen time");
  assert.equal(errorText(undefined), "Couldn't load today's screen time");
});

test("routineColors stays the same when a routine is missing from the day", () => {
  const all = [
    { uid: "after", name: "After school" },
    { uid: "homework", name: "Homework" },
    { uid: "school", name: "School" },
  ];
  const weekday = routineColors(
    [
      { uid: "after", name: "After school", counts: true },
      { uid: "homework", name: "Homework", counts: false },
      { uid: "school", name: "School", counts: false },
    ],
    false,
    all,
  );
  const weekend = routineColors([{ uid: "school", name: "School", counts: false }], false, all);
  assert.equal(weekend.school.color, weekday.school.color);
  assert.equal(weekend.school.hatched, true);
});

test("renderCard uses the report's full routine list for colours", () => {
  const r = report();
  const full = renderCard(r, { name: "Child One", tz: TZ, dark: false });
  const fewer = report({ routines: r.routines.filter((x) => x.uid !== "homework") });
  const html = renderCard(fewer, { name: "Child One", tz: TZ, dark: false });
  const schoolColor = (markup) => markup.match(/background:([^"]+)"><\/span>School/)[1];
  assert.equal(schoolColor(html), schoolColor(full));
});

test("renderCard overlays usage horizontally: each hour fills the share used, split by routine, solid colour", () => {
  const html = renderCard(report(), { name: "Child One", tz: TZ, dark: false });
  assert.match(html, /class="use"/);
  assert.doesNotMatch(html, /height:/);
  assert.doesNotMatch(html, /opacity:/);
  const used = round2((100 / 16) * (39.2 / 60));
  assert.ok(html.includes(`left:${(9 / 16) * 100}%;width:${used}%`), "3pm block width is the share of the hour used");
  // The 3pm hour splits 25 normal : 14.2 school, as widths in a row
  assert.match(html, /flex:25 1 0[^"]*background:#2a78d6/);
  assert.match(html, /flex:14\.2 1 0/);
});

test("renderCard labels every routine scheduled today, dimming those with no minutes", () => {
  const html = renderCard(report(), { name: "Child One", tz: TZ, dark: false });
  assert.match(html, /class="chip idle"[^>]*>.*?Night · 0 min/s);
  assert.doesNotMatch(html, /class="chip idle"[^>]*>.*?School/s);
});

test("an hour's filled width is capped at the whole hour", () => {
  const r = report({ hours: [{ start: "2026-11-10T09:00:00+11:00", default_minutes: 75, routines: {} }] });
  const [bar] = stripLayout(r, TZ).bars;
  assert.equal(bar.usedWidthPct, bar.widthPct);
});
