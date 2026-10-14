// Shared geometry for the rotation balance: the camera, the world layout, and the parts that move.
// build.mjs uses it for the static art; balance.js inlines it (imports and exports stripped) to rebuild
// the beam, the pans and the knob pointers in the page.
import { iso, depthOf, pathOf, circleRing, roundedPlan, lineOnTop, segment, ring, fitProjection, boxCorners, cameraOf, solidSvg, lineSvg, dotsSvg, translateAlong } from "../anatomy-kit/iso-kit.mjs";

export const VIEW_W = 600;
export const VIEW_H = 330;
export const AZ = 90; // face-on: a level beam is level on screen, so the reader can trust "level"
export const EL = 28;

export const PLINTH = { x: -166, y: -56, w: 332, d: 112, r: 6 };
export const PIVOT = [0, 0, 150.5];
export const AXIS_W = 9; // beam centreline above the knife edge
export const ARM = 118; // pivot to each end knife
export const HANG_W = 5; // where the stirrup hangs, in beam coordinates
export const PAN_TOP = 50; // pan top at level
export const PAN_R = 27;
export const PAN_H = 2.5;
export const DISC_H = 2.6; // one 0.1 disc
export const WEIGHT_R = 10;
export const HOOK_H = 6;
export const SPREAD = { r: 3.2, h: 1.6 };
export const CORD_ANGLES = [270, 30, 150]; // plan angles of the three cords; 270 is the back one
export const KNOBS = {
  m: { at: [-58, 28], dial: 17, r: 7.5, sweep: 270 },
  price: { at: [58, 28], dial: 17, r: 7.5, sweep: 270 },
};
export const KNOB_TOP = 9.5; // collar 0..2, body 2..9.5
export const NEEDLE = { y: 9.6, from: 0, to: 97 };
export const SCALE = { y: 8.5, arc: 94, minor: 2.2, major: 3.8, span: 12 };

const RAD = Math.PI / 180;

export const P = fitProjection(
  [
    ...boxCorners(PLINTH, -21, 0),
    [-ARM - 8, 0, PIVOT[2] + AXIS_W + 8 + ARM * Math.sin(12 * RAD)],
    [ARM + 8, 0, PIVOT[2] + AXIS_W + 8 + ARM * Math.sin(12 * RAD)],
    [-ARM - PAN_R, 0, PAN_TOP - 30],
    [ARM + PAN_R, 0, PAN_TOP - 30],
  ],
  VIEW_W,
  VIEW_H,
  { pad: 10, azimuth: AZ, elevation: EL },
);

const VIEW = (() => {
  const { sinA, cosA, sinE, cosE } = cameraOf(P);
  return [cosA * cosE, sinA * cosE, sinE];
})();
const LIGHT = (() => {
  const { sinA, cosA } = cameraOf(P);
  return [-sinA, cosA];
})();
const VIEW_FLOOR = (() => {
  const { sinA, cosA } = cameraOf(P);
  return [cosA, sinA];
})();

const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const crossV = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
const unitV = (a) => {
  const n = Math.hypot(a[0], a[1], a[2]) || 1;
  return [a[0] / n, a[1] / n, a[2] / n];
};
const mean = (list) => {
  const s = [0, 0, 0];
  for (const p of list) for (let i = 0; i < 3; i++) s[i] += p[i] / list.length;
  return s;
};

function hull2(points) {
  const sorted = [...points].sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  if (sorted.length < 3) return sorted;
  const cross = (o, a, b) => (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);
  const lower = [];
  for (const p of sorted) {
    while (lower.length >= 2 && cross(lower[lower.length - 2], lower[lower.length - 1], p) <= 0) lower.pop();
    lower.push(p);
  }
  const upper = [];
  for (let i = sorted.length - 1; i >= 0; i--) {
    const p = sorted[i];
    while (upper.length >= 2 && cross(upper[upper.length - 2], upper[upper.length - 1], p) <= 0) upper.pop();
    upper.push(p);
  }
  return [...lower.slice(0, -1), ...upper.slice(0, -1)];
}

// The kit's convex extrude, with each run of side facets that share a light bucket merged into one strip,
// so a round part costs a few paths instead of one per facet. Same tones, same outline, same bevel.
export function extrudeLite(ring, z, height, bevel = 0) {
  const count = ring.length;
  let area = 0;
  for (let i = 0; i < count; i++) area += ring[i][0] * ring[(i + 1) % count][1] - ring[(i + 1) % count][0] * ring[i][1];
  const counter = area > 0;
  const normals = ring.map(([ax, ay], i) => {
    const [bx, by] = ring[(i + 1) % count];
    const dx = bx - ax, dy = by - ay, len = Math.hypot(dx, dy) || 1;
    return counter ? [dy / len, -dx / len] : [-dy / len, dx / len];
  });
  const facing = normals.map(([nx, ny]) => nx * VIEW_FLOOR[0] + ny * VIEW_FLOOR[1] > 1e-9);
  const top = ring.map(([x, y]) => iso([x, y, z + height], P));
  const bottom = ring.map(([x, y]) => iso([x, y, z], P));
  const bucket = normals.map(([nx, ny]) => Math.min(3, Math.max(0, Math.floor(((nx * LIGHT[0] + ny * LIGHT[1] + 1) / 2) * 4))));
  const start = facing.findIndex((f, i) => f && !facing[(i - 1 + count) % count]);
  const shades = [[], [], [], []];
  const outline = [], crease = [], bevels = [];
  if (start >= 0) {
    // the visible run, from start while facing
    const run = [];
    for (let k = 0; k < count && facing[(start + k) % count]; k++) run.push((start + k) % count);
    const last = (run[run.length - 1] + 1) % count;
    const edge = [...run, last];
    crease.push(pathOf(edge.map((i) => top[i])));
    outline.push(pathOf(edge.map((i) => bottom[i])));
    outline.push(pathOf([top[start], bottom[start]]), pathOf([top[last], bottom[last]]));
    // hidden run along the top
    const back = [];
    for (let k = 0; k <= count - run.length; k++) back.push((last + k) % count);
    outline.push(pathOf(back.map((i) => top[i])));
    if (height > 0) {
      let from = 0;
      for (let k = 1; k <= run.length; k++) {
        if (k === run.length || bucket[run[k]] !== bucket[run[from]]) {
          const strip = run.slice(from, k);
          const end = (strip[strip.length - 1] + 1) % count;
          const ids = [...strip, end];
          shades[bucket[run[from]]].push(pathOf([...ids.map((i) => top[i]), ...ids.reverse().map((i) => bottom[i])], true));
          from = k;
        }
      }
    }
    if (bevel > 0) {
      const inset = ring.map(([x, y], i) => {
        const [ax, ay] = normals[(i - 1 + count) % count], [bx, by] = normals[i];
        const mx = ax + bx, my = ay + by, len = Math.hypot(mx, my) || 1;
        return iso([x - (mx / len) * bevel, y - (my / len) * bevel, z + height], P);
      });
      bevels.push(pathOf([top[run[0]], ...run.slice(1).map((i) => inset[i]), top[last]]));
    }
  } else {
    outline.push(pathOf(top, true));
  }
  return {
    fill: pathOf(hull2([...top, ...bottom]), true),
    outline: outline.join(""),
    crease: crease.join(""),
    top: pathOf(top, true),
    shades: shades.map((list) => list.join("")),
    bevel: bevels.join("") || undefined,
  };
}
export const cylinderLite = (cx, cy, r, z, h, steps = 32, bevel = 0) => extrudeLite(circleRing(cx, cy, r, steps), z, h, bevel);
export const slabLite = (plan, z, h, steps = 6, bevel = 0) => extrudeLite(roundedPlan(plan, steps), z, h, bevel);

// A convex polyhedron in any orientation, shaded like the kit's prisms: tops (normal mostly up) take the top
// tone, sides the four light buckets; creases where two visible faces meet at more than 30 degrees.
export function polySolid(verts, faces) {
  const centre = mean(verts);
  const pts = verts.map((v) => iso(v, P));
  const shades = [[], [], [], []];
  const tops = [];
  const seen = [];
  for (const face of faces) {
    let n = unitV(crossV(sub(verts[face[1]], verts[face[0]]), sub(verts[face[2]], verts[face[0]])));
    if (dot(n, sub(mean(face.map((i) => verts[i])), centre)) < 0) n = [-n[0], -n[1], -n[2]];
    if (dot(n, VIEW) <= 1e-6) continue;
    const d = pathOf(face.map((i) => pts[i]), true);
    if (n[2] > 0.6) tops.push(d);
    else {
      const lit = (n[0] * LIGHT[0] + n[1] * LIGHT[1] + 1) / 2;
      shades[Math.min(3, Math.max(0, Math.floor(lit * 4)))].push(d);
    }
    seen.push({ face, n });
  }
  const crease = [];
  for (let a = 0; a < seen.length; a++) {
    for (let b = a + 1; b < seen.length; b++) {
      if (dot(seen[a].n, seen[b].n) > 0.866) continue;
      const fa = seen[a].face, fb = seen[b].face;
      for (let i = 0; i < fa.length; i++) {
        const p = fa[i], q = fa[(i + 1) % fa.length];
        const j = fb.indexOf(p);
        if (j >= 0 && (fb[(j + 1) % fb.length] === q || fb[(j - 1 + fb.length) % fb.length] === q)) crease.push(pathOf([pts[p], pts[q]]));
      }
    }
  }
  const outline = pathOf(hull2(pts), true);
  return { fill: outline, outline, crease: crease.join(""), top: tops.join(""), shades: shades.map((s) => s.join("")) };
}

// The beam's frame for a tilt (degrees, positive: the m end goes down).
export function beamFrame(tilt) {
  const t = tilt * RAD;
  const a = [Math.cos(t), 0, Math.sin(t)];
  const b = [-Math.sin(t), 0, Math.cos(t)];
  const at = (u, w, y) => [PIVOT[0] + u * a[0] + w * b[0], y, PIVOT[2] + u * a[2] + w * b[2]];
  return { a, b, at };
}

const HEX = [[0, 1, 3, 2], [4, 5, 7, 6], [0, 1, 5, 4], [2, 3, 7, 6], [0, 2, 6, 4], [1, 3, 7, 5]];
// a tapered block from u0 to u1: heights [w0, w1] and half-depths at each end
function taper(F, u0, u1, h0, h1, d0, d1) {
  const verts = [];
  for (const [u, h, d] of [[u0, h0, d0], [u1, h1, d1]]) for (const w of h) for (const y of [-d, d]) verts.push(F.at(u, w, y));
  return polySolid(verts, HEX);
}

export const ARM_IN = { h: [4.5, 13.5], d: 2.6 };
export const ARM_OUT = { h: [7, 11], d: 1.8 };

function armTicks(F, side) {
  const minor = [], major = [];
  const from = 14, to = ARM - 7;
  for (let i = 0; i <= 10; i++) {
    const u = from + ((to - from) * i) / 10;
    const t = (u - 8) / (ARM - 8);
    const top = ARM_IN.h[1] + (ARM_OUT.h[1] - ARM_IN.h[1]) * t;
    const y = ARM_IN.d + (ARM_OUT.d - ARM_IN.d) * t;
    const big = i % 5 === 0;
    const len = big ? 2.6 : 1.4;
    (big ? major : minor).push(pathOf([iso(F.at(side * u, top, y), P), iso(F.at(side * u, top - len, y), P)]));
  }
  return lineSvg(minor.join(""), { tone: "lo" }) + lineSvg(major.join(""), { tone: "mid" });
}

// Everything that tilts, in painter's order: far arm, knife, centre block, near arm, end blocks, hub.
export function beamSvg(tilt) {
  const F = beamFrame(tilt);
  const out = [];
  const arm = (side) => solidSvg(taper(F, side * 8, side * ARM, ARM_IN.h, ARM_OUT.h, ARM_IN.d, ARM_OUT.d), { tone: "mid" }) + armTicks(F, side);
  const end = (side) => {
    const u0 = side * (ARM - 4), u1 = side * (ARM + 3.5);
    // end bearing block with its pin seen on the front face
    const pin = [];
    for (let i = 0; i <= 24; i++) pin.push(iso(F.at(side * ARM + 1.5 * Math.cos((i / 24) * 2 * Math.PI), 9.2 + 1.5 * Math.sin((i / 24) * 2 * Math.PI), 3.6), P));
    return solidSvg(taper(F, Math.min(u0, u1), Math.max(u0, u1), [HANG_W, 13.4], [HANG_W, 13.4], 3.6, 3.6), { tone: "mid" }) + lineSvg(pathOf(pin, true), { tone: "lo" });
  };
  const knife = polySolid(
    [F.at(-3.6, 3.2, -4.4), F.at(3.6, 3.2, -4.4), F.at(0, 0, -4.4), F.at(-3.6, 3.2, 4.4), F.at(3.6, 3.2, 4.4), F.at(0, 0, 4.4)],
    [[0, 1, 2], [3, 4, 5], [0, 1, 4, 3], [1, 2, 5, 4], [2, 0, 3, 5]],
  );
  out.push(arm(-1), end(-1));
  out.push(solidSvg(knife, { tone: "mid" }));
  out.push(solidSvg(taper(F, -9, 9, [3.2, 16], [3.2, 16], 5.2, 5.2), { tone: "mid" }));
  // centre block screws on its top
  out.push(dotsSvg([F.at(-6, 16, -2.8), F.at(6, 16, -2.8), F.at(-6, 16, 2.8), F.at(6, 16, 2.8)].map((p) => iso(p, P)), { size: 0.45 }));
  out.push(arm(1), end(1));
  // hub on the block's front face, round on the y axis
  const hubVerts = [];
  const N = 20;
  for (const y of [5.2, NEEDLE.y - 0.2]) for (let i = 0; i < N; i++) hubVerts.push(F.at(3.4 * Math.cos((i / N) * 2 * Math.PI), AXIS_W + 3.4 * Math.sin((i / N) * 2 * Math.PI), y));
  const hubFaces = [Array.from({ length: N }, (_, i) => i), Array.from({ length: N }, (_, i) => N + i)];
  for (let i = 0; i < N; i++) hubFaces.push([i, (i + 1) % N, N + ((i + 1) % N), N + i]);
  out.push(solidSvg(polySolid(hubVerts, hubFaces), { tone: "mid", crease: "faint" }));
  return out.join("");
}

// The needle hangs from the hub, perpendicular to the beam.
export function needleAt(tilt) {
  const F = beamFrame(tilt);
  return {
    d: pathOf([iso(F.at(0, AXIS_W, NEEDLE.y), P), iso(F.at(0, AXIS_W - NEEDLE.to, NEEDLE.y), P)]),
    hub: iso(F.at(0, AXIS_W, NEEDLE.y), P),
  };
}

// Where a stirrup hangs, and how far the pan group moves from level.
export function hangAt(side, tilt) {
  return beamFrame(tilt).at(side * ARM, HANG_W, 0);
}
export function panShift(side, tilt) {
  const now = hangAt(side, tilt), rest = hangAt(side, 0);
  return translateAlong(P, [now[0] - rest[0], 0, now[2] - rest[2]]);
}

const discs = (value) => {
  const tenths = value / 0.1;
  const whole = Math.floor(tenths + 1e-9);
  const list = [];
  for (let i = 0; i < whole; i++) list.push(DISC_H);
  const rest = (tenths - whole) * DISC_H;
  if (rest > 0.05) list.push(rest);
  return list;
};

// Pan group parts at level; the page moves the whole group with panShift.
export function panBack(side) {
  const x = side * ARM;
  const hook = hangAt(side, 0);
  const low = hook[2] - HOOK_H - SPREAD.h;
  const out = [];
  for (const angle of CORD_ANGLES) {
    const c = Math.cos(angle * RAD), s = Math.sin(angle * RAD);
    const front = c * VIEW[0] + s * VIEW[1] > 0;
    if (front) continue;
    out.push(lineSvg(segment([x + 2.4 * c, s * 2.4, low], [x + (PAN_R - 1.2) * c, (PAN_R - 1.2) * s, PAN_TOP], P), { tone: "lo" }));
  }
  return out.join("");
}

export function panDish(side) {
  const x = side * ARM;
  return [
    solidSvg(cylinderLite(x, 0, 11, PAN_TOP - PAN_H - 1.6, 1.6, 40), { tone: "mid" }),
    solidSvg(cylinderLite(x, 0, PAN_R, PAN_TOP - PAN_H, PAN_H, 64, 0.6), { tone: "mid" }),
    lineSvg(ring(x, 0, PAN_R - 3.2, PAN_TOP, P, 72), { tone: "faint" }),
  ].join("");
}

export function weightsSvg(side, value) {
  const x = side * ARM;
  let z = PAN_TOP;
  const out = [];
  for (const h of discs(value)) {
    out.push(solidSvg(cylinderLite(x, 0, WEIGHT_R, z, h, 40), { tone: "hi", crease: "lo" }));
    z += h;
  }
  // a lifting knob on top of every stack, the same on both pans
  out.push(solidSvg(cylinderLite(x, 0, 3, z, 3.4, 24), { tone: "hi", crease: "lo" }));
  return out.join("");
}

export function panFront(side) {
  const x = side * ARM;
  const hook = hangAt(side, 0);
  const low = hook[2] - HOOK_H - SPREAD.h;
  const out = [];
  for (const angle of CORD_ANGLES) {
    const c = Math.cos(angle * RAD), s = Math.sin(angle * RAD);
    if (!(c * VIEW[0] + s * VIEW[1] > 0)) continue;
    out.push(lineSvg(segment([x + 2.4 * c, s * 2.4, low], [x + (PAN_R - 1.2) * c, (PAN_R - 1.2) * s, PAN_TOP], P), { tone: "lo" }));
  }
  out.push(solidSvg(cylinderLite(x, 0, SPREAD.r, low, SPREAD.h, 24), { tone: "mid" }));
  out.push(solidSvg(cylinderLite(x, 0, 1.3, low + SPREAD.h, HOOK_H, 16), { tone: "mid", crease: "none" }));
  return out.join("");
}

// Knob pointer, angle from the value's share of its range: 0 at -135 degrees (from -y, clockwise from above).
export function knobPointer(name, share) {
  const { at, r, sweep } = KNOBS[name];
  const angle = (-sweep / 2 + share * sweep) * RAD;
  const sx = Math.sin(angle), sy = -Math.cos(angle);
  return lineOnTop([at[0] + sx * 1.6, at[1] + sy * 1.6], [at[0] + sx * (r - 0.3), at[1] + sy * (r - 0.3)], KNOB_TOP, P);
}

export function dialPoint(name, share, radius) {
  const { at, sweep } = KNOBS[name];
  const angle = (-sweep / 2 + share * sweep) * RAD;
  return iso([at[0] + Math.sin(angle) * radius, at[1] - Math.cos(angle) * radius, 0.8], P);
}

export const knobDepth = (name) => depthOf([KNOBS[name].at[0], KNOBS[name].at[1], 0], P);
export const knobHit = (name) => ring(KNOBS[name].at[0], KNOBS[name].at[1], KNOBS[name].dial + 6, 0.8, P, 48);
export const knobFocus = (name) => ring(KNOBS[name].at[0], KNOBS[name].at[1], KNOBS[name].dial + 2.5, 0.8, P, 64);
