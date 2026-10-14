// node site-src/balance/model.test.mjs : exits non-zero if a readout differs from the page table.
import { balance, snapTo, RANGES } from "./model.mjs";

const M = "−";
const cases = [
  [1.2, 90, "+$33", "adds"],
  [1.2, 100, "+$20", "adds"],
  [1.2, 110, "+$9", "adds"],
  [1.2, 120, "$0", "neutral"],
  [1.2, 130, M + "$8", "gives back"],
];
let failed = 0;
const check = (ok, line) => {
  console.log((ok ? "ok   " : "FAIL ") + line);
  if (!ok) failed++;
};

for (const [m, price, dollars, word] of cases) {
  const b = balance(m, price);
  const want = `Per $120 raised: ${dollars} to common`;
  check(b.text.perRaise === want && b.word === word, `m ${m}, STRC $${price}: "${b.text.perRaise}", ${b.word} (want "${want}", ${word})`);
}
check(balance(1.2, 100).text.breakEven === "$100 × m = $120.00", `break-even at m 1.2: "${balance(1.2, 100).text.breakEven}"`);
check(balance(1.2, 120).tilt === 0, "beam exactly level at m = q (1.2, $120)");
check(balance(1.0, 100).tilt === 0, "beam exactly level at m = q (1.0, $100)");
check(balance(1.25, 125).tilt === 0 && balance(0.995, 99.5).tilt === 0, "level at m = q off the round numbers");

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
