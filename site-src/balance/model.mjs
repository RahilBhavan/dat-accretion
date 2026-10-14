// The rotation balance, as numbers. A pure function of (m, price): everything the figure draws and reads out.
// m = net mNAV (common price / net coin value per share); q = STRC price / $100 notional.
// Selling $x of common leaves x(1 - 1/m) with existing holders; retiring $x of STRC adds x(1/q - 1).
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

export function wholeOrCents(value) {
  const size = Math.abs(value);
  if (size < 0.005) return { text: "$0", sign: 0 };
  const whole = Math.round(size);
  const sign = value > 0 ? 1 : -1;
  const body = whole >= 1 ? "$" + whole : "$" + size.toFixed(2);
  return { text: (sign > 0 ? "+" : MINUS) + body, sign };
}

export function balance(m, price) {
  const q = price / 100;
  const breakEven = 100 * m;
  const fromCommon = RAISE * (1 - 1 / m);
  const fromPreferred = RAISE * (100 / price - 1);
  const perRaise = fromCommon + fromPreferred;
  const shown = wholeOrCents(perRaise);
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
      breakEven: "$100 × m = " + money2(breakEven),
      perRaise: "Per $" + RAISE + " raised: " + shown.text + " to common",
      word,
      m: m.toFixed(3),
      price: money2(price),
      q: q.toFixed(3),
    },
  };
}
