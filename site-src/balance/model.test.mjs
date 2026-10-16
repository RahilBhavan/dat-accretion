// node site-src/balance/model.test.mjs : exits non-zero if a readout differs from the page table.
import { balance, snapTo, splitRounded, unitOf, RANGES } from "./model.mjs";

const M = "−";
// m, STRC price, sale, retirement, sum, word (the page table at m = 1.2, plus m = 0.8)
const cases = [
  [1.2, 90, "+$20", "+$13", "+$33", "adds"],
  [1.2, 100, "+$20", "$0", "+$20", "adds"],
  [1.2, 110, "+$20", M + "$11", "+$9", "adds"],
  [1.2, 120, "+$20", M + "$20", "$0", "neutral"],
  [1.2, 130, "+$20", M + "$28", M + "$8", "gives back"],
  [0.8, 90, M + "$30", "+$13", M + "$17", "gives back"],
  [0.8, 100, M + "$30", "$0", M + "$30", "gives back"],
];
let failed = 0;
const check = (ok, line) => {
  console.log((ok ? "ok   " : "FAIL ") + line);
  if (!ok) failed++;
};

for (const [m, price, sale, retirement, sum, word] of cases) {
  const b = balance(m, price);
  const want = `Sale ${sale} · retirement ${retirement} = ${sum} per $120`;
  check(b.text.perRaise === want && b.word === word, `m ${m}, STRC $${price}: "${b.text.perRaise}", ${b.word} (want "${want}", ${word})`);
}
check(balance(1.2, 90).text.breakEven === "Break-even: STRC $120.00", `break-even at m 1.2: "${balance(1.2, 90).text.breakEven}"`);
check(balance(0.8, 90).text.breakEven === "Break-even: STRC $80.00", `break-even at m 0.8: "${balance(0.8, 90).text.breakEven}"`);
check(balance(1.2, 120).tilt === 0, "beam exactly level at m = q (1.2, $120)");
check(balance(1.0, 100).tilt === 0, "beam exactly level at m = q (1.0, $100)");
check(balance(1.25, 125).tilt === 0 && balance(0.995, 99.5).tilt === 0, "level at m = q off the round numbers");

// every stated sum checks: the two shown parts add to the shown total, each part within one unit of its value
const cents = (text) => (text === "$0" ? 0 : (text[0] === "+" ? 1 : -1) * Math.round(Number(text.slice(2)) * 100));
let adds = true, near = true, grid = 0;
for (let i = 0; i <= 140; i++) {
  for (let j = 0; j <= 120; j++) {
    const b = balance(snapTo(0.8 + i * 0.005, RANGES.m), 80 + j * 0.5);
    const s = splitRounded(b.fromCommon, b.fromPreferred);
    const unit = unitOf(b.perRaise) * 100;
    if (cents(s.a) + cents(s.b) !== cents(s.total)) adds = false;
    if (Math.abs(cents(s.a) - b.fromCommon * 100) > unit || Math.abs(cents(s.b) - b.fromPreferred * 100) > unit) near = false;
    if (Math.abs(cents(s.total) - b.perRaise * 100) > unit / 2 + 1e-6) near = false;
    grid++;
  }
}
check(adds, `sale + retirement = sum as shown, all ${grid} grid points`);
check(near, "each shown part within one unit of its value, the sum within half a unit");

// monotone in (m - q), bounded by 12 degrees, sign matches the readout word
let last = -Infinity, monotone = true, bounded = true, signs = true;
for (let price = 140; price >= 80; price -= 0.5) {
  const b = balance(1.2, price);
  if (b.tilt < last - 1e-12) monotone = false;
  last = b.tilt;
  if (Math.abs(b.tilt) >= 12) bounded = false;
  if (Math.sign(b.tilt) !== Math.sign(b.perRaise) && Math.abs(b.perRaise) > 1e-9) signs = false;
}
check(monotone, "tilt rises as STRC falls at fixed m");
check(bounded, "tilt stays inside 12 degrees");
check(signs, "tilt sign matches the per-raise sign");
check(!/—/.test(JSON.stringify(balance(1.2, 130))), "no em dash in any text");
check(snapTo(99.74, RANGES.price) === 99.5 && snapTo(1.1912, RANGES.m) === 1.19 && snapTo(200, RANGES.price) === 140, "snapping to steps and range");

console.log(failed ? `${failed} failed` : "all passed");
process.exit(failed ? 1 : 0);
