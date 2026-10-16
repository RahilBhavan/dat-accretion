// The rotation balance, as numbers. A pure function of (m, price): everything the figure draws and reads out.
// m = net mNAV (common price / net coin value per share); q = STRC price / $100 notional.
// Selling $x of common leaves x(1 - 1/m) with existing holders; retiring $x of STRC adds x(1/q - 1).
// The readout states both parts and their sum, each rounded to whole dollars on its own.
// Together, per $x raised: x(1/q - 1/m), which is positive exactly while m > q, i.e. STRC below $100 x m.

export const RANGES = {
  price: { min: 80, max: 140, step: 0.5 },
  m: { min: 0.8, max: 1.5, step: 0.005 },
};
export const RAISE = 120;
export const TILT_MAX = 12;
export const TILT_SCALE = 0.25;
export const DISC = 0.1;

const MINUS = "−";

export function snapTo(value, { min, max, step }) {
  const clamped = Math.min(max, Math.max(min, Number(value)));
  const steps = Math.round((clamped - min) / step);
  return Math.round((min + steps * step) * 1e6) / 1e6;
}

const money2 = (value) => "$" + value.toFixed(2);

// A signed count of units as money: "+$20", "−$0.40", "$0".
function signed(units, unit) {
  if (units === 0) return "$0";
  const body = unit >= 1 ? String(Math.abs(units)) : (Math.abs(units) * unit).toFixed(2);
  return (units > 0 ? "+" : MINUS) + "$" + body;
}

// Round two parts so they add to their rounded sum (largest remainder), so the readout's sum always checks.
// Whole dollars, or cents when the sum is not zero but rounds to under $1. Each part stays within one unit.
export const unitOf = (sum) => (Math.abs(sum) >= 0.5 || Math.abs(sum) < 0.005 ? 1 : 0.01);
export function splitRounded(a, b) {
  const unit = unitOf(a + b);
  const total = Math.round((a + b) / unit);
  let ra = Math.round(a / unit), rb = Math.round(b / unit);
  const off = total - (ra + rb);
  if (off !== 0) {
    // move the part that rounding pushed furthest the other way
    const ea = (a / unit - ra) * off, eb = (b / unit - rb) * off;
    if (ea >= eb) ra += off;
    else rb += off;
  }
  return { sign: Math.sign(total), a: signed(ra, unit), b: signed(rb, unit), total: signed(total, unit) };
}

export function balance(m, price) {
  const q = price / 100;
  const breakEven = 100 * m;
  const fromCommon = RAISE * (1 - 1 / m);
  const fromPreferred = RAISE * (100 / price - 1);
  const perRaise = fromCommon + fromPreferred;
  const shown = splitRounded(fromCommon, fromPreferred);
  const word = shown.sign > 0 ? "adds" : shown.sign < 0 ? "gives back" : "neutral";
  // compare in millionths so m = q is exactly level
  const gap = (Math.round(m * 1e6) - Math.round(q * 1e6)) / 1e6;
  const tilt = TILT_MAX * Math.tanh(gap / TILT_SCALE);
  return {
    m,
    price,
    q,
    breakEven,
    fromCommon,
    fromPreferred,
    perRaise,
    word,
    tilt, // degrees, positive: the m side is heavier and goes down
    left: m, // stack on the m pan, in units of 1.0
    right: q, // stack on the q pan
    text: {
      breakEven: "Break-even: STRC " + money2(breakEven),
      breakEvenValue: money2(breakEven),
      perRaise: "Sale " + shown.a + " · retirement " + shown.b + " = " + shown.total + " per $" + RAISE,
      sale: shown.a,
      retirement: shown.b,
      total: shown.total,
      word,
      m: m.toFixed(3),
      price: money2(price),
      q: q.toFixed(3),
    },
  };
}
