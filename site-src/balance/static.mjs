// The parts that never move, drawn once at build time.
import * as k from "../anatomy-kit/iso-kit.mjs";
import { P, PLINTH, PIVOT, AXIS_W, ARM, KNOBS, KNOB_TOP, SCALE, panBack, panDish, panFront, cylinderLite, slabLite } from "./geometry.mjs";

// the kit's signatures, drawn with merged facet strips
const cyl = (cx, cy, r, z, h, _P, steps = 32, bevel = 0) => cylinderLite(cx, cy, r, z, h, steps, bevel);
const slab = (plan, z, h, _P, steps = 8, bevel = 0) => slabLite(plan, z, h, steps, bevel);

const at = (point) => k.iso(point, P);
const S = (paths, style) => k.solidSvg(paths, style);
const L = (d, style) => k.lineSvg(d, style);
const D = (points, style) => k.dotsSvg(points, style);
const RAD = Math.PI / 180;
const byDepth = (points) => [...points].sort((a, b) => k.depthOf([a[0], a[1], 0], P) - k.depthOf([b[0], b[1], 0], P));

const DECK = k.insetPlan(PLINTH, 5);
const PLINTH_Z = [-15, -6];

function base() {
  const out = [`<path class="iso-halo" d="${k.haloOf(PLINTH, -21, 15, P)}"/>`];
  // levelling feet: flange, knurled screw
  for (const [x, y] of byDepth(k.corners(PLINTH, 20))) {
    out.push(S(cyl(x, y, 8, -21, 1.6, P, 32), { tone: "lo" }));
    out.push(S(cyl(x, y, 5.6, -19.4, 4.4, P, 28), { tone: "mid" }));
    out.push(L(k.knurl(x, y, 5.6, -19.4, -15, 22, P), { tone: "lo" }));
  }
  out.push(S(slab(PLINTH, PLINTH_Z[0], PLINTH_Z[1] - PLINTH_Z[0], P, 6, 0.8), { tone: "mid" }));
  out.push(S(slab(DECK, -6, 6, P, 6, 1.2), { tone: "mid" }));
  out.push(L(k.planOutline(k.insetPlan(DECK, 5), 0, P, 6), { tone: "faint" }));
  const screws = k.corners(DECK, 10);
  out.push(L(screws.map(([x, y]) => k.ring(x, y, 2.2, 0, P, 16)).join(""), { tone: "lo" }));
  out.push(D(screws.map(([x, y]) => at([x, y, 0])), { size: 0.5 }));
  // maker's plate on the plinth front: three rule lines stand for engraved text
  const plate = { x: -26, y: PLINTH.y + PLINTH.d, w: 52, d: 0.8, r: 0.3 };
  out.push(S(slab(plate, -13.6, 6.2, P, 2), { tone: "mid", crease: "faint" }));
  const face = plate.y + plate.d;
  out.push(L([[30, -9.4], [20, -10.8], [26, -12.2]].map(([len, z]) => k.segment([-18, face, z], [-18 + len, face, z], P)).join(""), { tone: "lo", free: true }));
  out.push(D([at([-23, face, -10.5]), at([23, face, -10.5])], { size: 0.45 }));
  // spirit level, bubble centred
  const lv = [-40, -32];
  out.push(S(cyl(lv[0], lv[1], 7, 0, 2.4, P, 40, 0.4), { tone: "mid" }));
  out.push(L(k.ring(lv[0], lv[1], 4.4, 2.4, P, 40), { tone: "lo" }));
  out.push(L(k.ring(lv[0], lv[1], 1.3, 2.4, P, 20), { tone: "mid" }));
  return out.join("");
}

function panRest(side) {
  const x = side * ARM;
  return [
    S(cyl(x, 0, 6.5, 0, 2.6, P, 32, 0.4), { tone: "mid" }),
    S(cyl(x, 0, 2.2, 2.6, 12.4, P, 20), { tone: "mid", crease: "none" }),
    S(cyl(x, 0, 6.8, 15, 2, P, 36, 0.4), { tone: "mid" }),
    L(k.ring(x, 0, 4.2, 17, P, 32), { tone: "faint" }),
  ].join("");
}

function labelPlate(side, letter) {
  const x = side * ARM;
  const plan = { x: x - 9, y: 28, w: 18, d: 11, r: 1.2 };
  return [
    S(slab(plan, 0, 0.8, P, 3), { tone: "mid", crease: "faint" }),
    L(k.planOutline(k.insetPlan(plan, 1.6), 0.8, P, 3), { tone: "faint" }),
    k.faceTextSvg(k.topMatrix([x - 2.2, 35.6], 0.8, P, "x"), letter, { size: 7, tone: "hi" }),
  ].join("");
}

function dial(name, count) {
  const { at: [x, y], dial: r } = KNOBS[name];
  const ticks = k.radialTicks(x, y, r - 0.3, count, 2, 0.8, [1.6, 3], P, -135 * RAD, 270 * RAD);
  return [S(cyl(x, y, r, 0, 0.8, P, 64), { tone: "mid", crease: "faint" }), L(ticks.minor, { tone: "lo" }), L(ticks.major, { tone: "mid" })].join("");
}

function knobBody(name) {
  const { at: [x, y], r } = KNOBS[name];
  return [
    S(cyl(x, y, r + 2, 0.8, 1.6, P, 40, 0.4), { tone: "mid" }),
    S(cyl(x, y, r, 2.4, KNOB_TOP - 2.4, P, 48, 0.5), { tone: "mid" }),
    L(k.knurl(x, y, r, 2.4, KNOB_TOP - 1.6, 40, P), { tone: "lo" }),
    L(k.sideArc(x, y, r, KNOB_TOP - 1.6, P, 32), { tone: "faint" }),
    L(k.ring(x, y, 1.6, KNOB_TOP, P, 16), { tone: "lo" }),
  ].join("");
}

export function backSvg() {
  return [base(), panRest(-1), panRest(1), labelPlate(-1, "m"), labelPlate(1, "q"), dial("m", 14), knobBody("m"), dial("price", 12), knobBody("price")].join("");
}

export function columnSvg() {
  const out = [];
  const zTop = 141;
  out.push(S(cyl(0, 0, 15, 0, 3, P, 64, 0.6), { tone: "mid" }));
  out.push(D([45, 135, 225, 315].map((a) => at([12 * Math.cos(a * RAD), 12 * Math.sin(a * RAD), 3])), { size: 0.45 }));
  out.push(S(cyl(0, 0, 8.5, 3, 7, P, 48, 0.4), { tone: "mid" }));
  out.push(S(cyl(0, 0, 5.6, 10, zTop - 10, P, 40), { tone: "mid", crease: "none", inner: L(k.sideArc(0, 0, 5.6, 40, P, 24) + k.sideArc(0, 0, 5.6, 112, P, 24), { tone: "faint" }) }));
  // scale bracket and plate, then its arc and ticks centred on the needle's pivot
  out.push(S(slab({ x: -3, y: 4.5, w: 6, d: 2.5, r: 0.5 }, 59, 8, P, 2), { tone: "mid" }));
  out.push(S(slab({ x: -25, y: SCALE.y - 1.5, w: 50, d: 1.5, r: 0.6 }, 55, 17, P, 3, 0.3), { tone: "mid" }));
  const cz = PIVOT[2] + AXIS_W;
  const on = (deg, r) => at([r * Math.sin(deg * RAD), SCALE.y, cz - r * Math.cos(deg * RAD)]);
  const arc = [];
  for (let i = 0; i <= 48; i++) arc.push(on(-SCALE.span + (2 * SCALE.span * i) / 48, SCALE.arc));
  out.push(L(k.pathOf(arc), { tone: "mid" }));
  const minor = [], major = [];
  for (let deg = -SCALE.span; deg <= SCALE.span; deg++) {
    if (deg === 0) continue;
    const big = deg % 4 === 0;
    (big ? major : minor).push(k.pathOf([on(deg, SCALE.arc), on(deg, SCALE.arc + (big ? SCALE.major : SCALE.minor))]));
  }
  out.push(L(minor.join(""), { tone: "lo" }), L(major.join(""), { tone: "mid" }));
  out.push(L(k.pathOf([on(0, SCALE.arc), on(0, SCALE.arc + 5)]), { tone: "hi" }));
  out.push(D([at([-22, SCALE.y, 69.5]), at([22, SCALE.y, 69.5])], { size: 0.45 }));
  // pillar head and agate plane the knife edge rests on
  const cap = { x: -16, y: -9, w: 32, d: 18, r: 2 };
  out.push(S(slab(cap, zTop, 8, P, 4, 0.6), { tone: "mid" }));
  out.push(D(k.corners(cap, 3).map(([x, y]) => at([x, y, zTop + 8])), { size: 0.45 }));
  out.push(S(slab({ x: -6.5, y: -5.5, w: 13, d: 11, r: 1 }, zTop + 8, PIVOT[2] - zTop - 8, P, 3), { tone: "mid" }));
  return out.join("");
}

export const panParts = (side) => ({ back: panBack(side), dish: panDish(side), front: panFront(side) });
