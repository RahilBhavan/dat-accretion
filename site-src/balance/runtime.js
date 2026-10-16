// Page runtime for the rotation balance. build.mjs inlines this after the kit subset, model.mjs and
// geometry.mjs, with STATIC (prebuilt SVG strings) and CSS defined, all inside one closure.
const STYLE_ID = "balance-style-v2";
const TOUR_DELAY = 1.4;
const HIT_PX = 48; // knob hit area, CSS px, both ways (44 minimum plus margin)
const esc = (text) => String(text).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
const num = (value, fallback) => (Number.isFinite(Number(value)) && value !== null && value !== "" ? Number(value) : fallback);
const clampTo = (name, value) => Math.min(RANGES[name].max, Math.max(RANGES[name].min, value));
const shareOf = (name, value) => (value - RANGES[name].min) / (RANGES[name].max - RANGES[name].min);
const smooth = (t) => t * t * t * (t * (t * 6 - 15) + 10);

function themeOf() {
  const set = document.documentElement.dataset.theme;
  if (set === "light" || set === "dark") return set;
  return window.matchMedia && matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function injectStyle() {
  if (document.getElementById(STYLE_ID)) return;
  const style = document.createElement("style");
  style.id = STYLE_ID;
  style.textContent = CSS;
  document.head.appendChild(style);
}

// Idle tour: STRC sweeps between $90 and $135 at fixed m, pausing at break-even. It starts and ends at $90,
// the mount's default, so the first state is q = 0.90 (+$33 per $120 at m 1.2).
const TOUR_LOW = 90;
function tourPrice(t, m) {
  const be = Math.min(133, Math.max(92, 100 * m));
  const lo = TOUR_LOW;
  const legs = [
    [1.2, lo, lo], [3.6, lo, be], [2.6, be, be], [3.0, be, 135], [1.4, 135, 135], [3.0, 135, be], [2.6, be, be], [3.6, be, lo],
  ];
  const total = legs.reduce((sum, leg) => sum + leg[0], 0);
  let left = t % total;
  for (const [span, from, to] of legs) {
    if (left <= span) return from + (to - from) * smooth(left / span);
    left -= span;
  }
  return lo;
}

const LABEL =
  "An assay balance on a bench base. The left pan holds a stack of discs as tall as m, net mNAV; the right pan a stack as tall as q, the STRC price over $100; each disc is 0.1. The beam tips down on the taller side and is level when m equals q. The knob on the left sets m, the knob on the right sets the STRC price; the two sliders below the drawing set the same values.";

// Knobs are pointer only: the range inputs below the card are the accessible controls (one tab stop each).
function knobMarkup(name) {
  return `<g class="balance-knob" data-knob="${name}" aria-hidden="true"><path class="balance-hit" d="${knobHit(name)}"/></g>`;
}

function svgMarkup() {
  const pan = (side, key) =>
    `<g data-part="pan-${key}">${STATIC.pans[key].back}${STATIC.pans[key].dish}<g data-part="weights-${key}"></g>${STATIC.pans[key].front}</g>`;
  return `<svg class="iso-svg" viewBox="0 0 ${VIEW_W} ${VIEW_H}" role="img" aria-label="${esc(LABEL)}">` +
    `<g aria-hidden="true">${STATIC.back}` +
    `<path class="iso-line" data-tone="hi" data-part="ptr-m" d=""/>` +
    `<path class="iso-line" data-tone="hi" data-part="ptr-price" d=""/>` +
    `<g class="iso-dots" data-tone="hi"><circle data-part="be-dot" r="0.9" cx="0" cy="0"/></g>` +
    pan(-1, "l") + STATIC.column + pan(1, "r") +
    `<g data-part="beam"></g>` +
    `<path class="iso-line" data-tone="lit" data-free="end" data-part="needle" d="" style="stroke-width:1.1"/>` +
    `<g class="iso-dots" data-tone="hi"><circle data-part="hub" r="0.75" cx="0" cy="0"/></g></g>` +
    knobMarkup("m") + knobMarkup("price") +
    `</svg>`;
}

function controlMarkup(name, label) {
  const r = RANGES[name];
  return `<label class="balance-control"><span class="balance-control-row"><span>${label}</span><output data-out="${name}"></output></span>` +
    `<input type="range" aria-label="${label}" data-range="${name}" min="${r.min}" max="${r.max}" step="${r.step}"></label>`;
}

function todayText(today) {
  const label = today.label ? String(today.label) : "";
  if (/STRC/.test(label)) return label;
  const head = `m ${Number(today.m).toFixed(3)}, STRC $${Number(today.price).toFixed(2)}`;
  return label ? `${head}, ${label}` : head;
}

function mount(el, opts) {
  opts = opts || {};
  injectStyle();
  const target = { m: clampTo("m", num(opts.m, 1.2)), price: clampTo("price", num(opts.price, TOUR_LOW)) };
  const shown = { m: target.m, price: target.price };
  const today = opts.today && Number.isFinite(Number(opts.today.m)) && Number.isFinite(Number(opts.today.price)) ? opts.today : null;

  const root = document.createElement("div");
  root.className = "balance";
  root.dataset.theme = themeOf();
  root.innerHTML =
    `<figure class="balance-figure"><div class="balance-card iso-plate">` +
    `<div class="balance-head"><span class="balance-fig">Fig 1 <span class="balance-tag">Illustration</span></span><span class="balance-title">The rotation balance</span></div>` +
    `<div class="balance-stage">${svgMarkup()}</div>` +
    `<div class="balance-foot"><span class="balance-hint"><span class="balance-hint-wide">Drag a knob or slider, or use the arrow keys</span><span class="balance-hint-narrow">Drag a knob or slider</span></span><span class="balance-readout" data-readout><span data-line="1"></span><span data-line="2"></span></span></div>` +
    `</div>` +
    `<div class="balance-controls">${controlMarkup("m", "net mNAV (m)")}${controlMarkup("price", "STRC price")}</div>` +
    (today ? `<div class="balance-today"><button type="button" data-today>Set to the latest filed week</button><span>${esc(todayText(today))}</span></div>` : "") +
    (opts.caption === false ? "" : `<figcaption class="balance-caption">Illustration with toy numbers, not filed figures. Left pan: m, the price common sells at per $1 of net coins. Right pan: q, the price paid per $1 of preferred claim (STRC price ÷ $100). Each disc is 0.1. The beam is level at m = q, where STRC trades at $100 × m, and tips down on the m side while the rotation adds coins per share. The dot on the price dial marks break-even.</figcaption>`) +
    `</figure>`;
  el.textContent = "";
  el.appendChild(root);

  const $ = (sel) => root.querySelector(sel);
  const card = $(".balance-card");
  const beamG = $('[data-part="beam"]');
  const needle = $('[data-part="needle"]');
  const hub = $('[data-part="hub"]');
  const pans = { l: $('[data-part="pan-l"]'), r: $('[data-part="pan-r"]') };
  const weights = { l: $('[data-part="weights-l"]'), r: $('[data-part="weights-r"]') };
  const pointers = { m: $('[data-part="ptr-m"]'), price: $('[data-part="ptr-price"]') };
  const beDot = $('[data-part="be-dot"]');
  const lines = [$('[data-line="1"]'), $('[data-line="2"]')];
  const knobs = { m: $('[data-knob="m"]'), price: $('[data-knob="price"]') };
  const ranges = { m: $('[data-range="m"]'), price: $('[data-range="price"]') };
  const outs = { m: $('[data-out="m"]'), price: $('[data-out="price"]') };

  const still = window.matchMedia ? matchMedia("(prefers-reduced-motion: reduce)") : { matches: false };
  const beam = { x: balance(shown.m, shown.price).tilt, v: 0 };
  let touring = !still.matches, tourClock = 0, tau = 0.3, frame = 0, last = 0, visible = false, alive = true;
  const drawn = { tilt: NaN, l: NaN, r: NaN, m: NaN, price: NaN, be: NaN };
  let lastEmit = "";

  function render() {
    const b = balance(shown.m, shown.price);
    const tilt = beam.x;
    if (!(Math.abs(tilt - drawn.tilt) <= 0.0015)) {
      drawn.tilt = tilt;
      beamG.innerHTML = beamSvg(tilt);
      const n = needleAt(tilt);
      needle.setAttribute("d", n.d);
      hub.setAttribute("cx", n.hub[0].toFixed(2));
      hub.setAttribute("cy", n.hub[1].toFixed(2));
      pans.l.setAttribute("transform", panShift(-1, tilt));
      pans.r.setAttribute("transform", panShift(1, tilt));
    }
    if (!(Math.abs(b.left - drawn.l) <= 0.0004)) {
      drawn.l = b.left;
      weights.l.innerHTML = weightsSvg(-1, b.left);
    }
    if (!(Math.abs(b.right - drawn.r) <= 0.0004)) {
      drawn.r = b.right;
      weights.r.innerHTML = weightsSvg(1, b.right);
    }
    if (shown.m !== drawn.m) {
      drawn.m = shown.m;
      pointers.m.setAttribute("d", knobPointer("m", shareOf("m", shown.m)));
      const be = shareOf("price", 100 * shown.m);
      const inside = be >= -1e-9 && be <= 1 + 1e-9;
      beDot.style.display = inside ? "" : "none";
      if (inside) {
        const p = dialPoint("price", be, 12);
        beDot.setAttribute("cx", p[0].toFixed(2));
        beDot.setAttribute("cy", p[1].toFixed(2));
      }
      outs.m.textContent = b.text.m;
    }
    if (shown.price !== drawn.price) {
      drawn.price = shown.price;
      pointers.price.setAttribute("d", knobPointer("price", shareOf("price", shown.price)));
      outs.price.textContent = b.text.price;
    }
    const one = b.text.breakEven;
    const two = b.text.perRaise;
    if (lines[0].textContent !== one) lines[0].textContent = one;
    if (lines[1].textContent !== two) lines[1].textContent = two;
    return b;
  }

  function syncInputs() {
    for (const name of ["m", "price"]) {
      const v = String(target[name]);
      if (ranges[name].value !== v) ranges[name].value = v;
    }
  }

  function describe() {
    const b = balance(target.m, target.price);
    const t = b.text;
    const tail = `break-even STRC ${t.breakEvenValue}; sale ${t.sale}, retirement ${t.retirement}, ${t.total} per $120 raised`;
    ranges.m.setAttribute("aria-valuetext", `m ${t.m}; ${tail}`);
    ranges.price.setAttribute("aria-valuetext", `STRC ${t.price}; ${tail}`);
  }

  function emit(source, m, price) {
    const key = m.toFixed(4) + "|" + price.toFixed(3);
    if (key === lastEmit) return;
    lastEmit = key;
    const b = balance(m, price);
    el.dispatchEvent(new CustomEvent("balancechange", { detail: { m, price, breakEven: b.breakEven, perRaise: b.perRaise, word: b.word, source } }));
  }

  function stopTour() {
    if (!touring) return;
    touring = false;
    target.price = snapTo(shown.price, RANGES.price);
  }

  function steer(next, how, source) {
    stopTour();
    tau = how;
    if (next.m !== undefined) target.m = clampTo("m", num(next.m, target.m));
    if (next.price !== undefined) target.price = clampTo("price", num(next.price, target.price));
    syncInputs();
    describe();
    emit(source, target.m, target.price);
    run();
  }

  function tick(now) {
    frame = 0;
    if (!alive) return;
    const dt = last ? Math.min((now - last) / 1000, 1 / 30) : 1 / 60;
    last = now;
    const calm = still.matches;
    if (touring && calm) touring = false;
    if (touring) {
      tourClock += dt;
      if (tourClock > TOUR_DELAY) {
        const p = tourPrice(tourClock - TOUR_DELAY, target.m);
        target.price = p;
        shown.price = p;
        emit("tour", target.m, snapTo(p, RANGES.price));
      }
    }
    for (const name of ["m", "price"]) {
      if (calm) shown[name] = target[name];
      else {
        shown[name] += (target[name] - shown[name]) * (1 - Math.exp(-dt / tau));
        if (Math.abs(target[name] - shown[name]) < (name === "m" ? 2e-5 : 2e-3)) shown[name] = target[name];
      }
    }
    const want = balance(shown.m, shown.price).tilt;
    if (calm) {
      beam.x = want;
      beam.v = 0;
    } else {
      const stiff = 26, drag = 2 * Math.sqrt(stiff) * 0.72;
      for (let i = 0; i < 4; i++) {
        beam.v += ((want - beam.x) * stiff - beam.v * drag) * (dt / 4);
        beam.x += beam.v * (dt / 4);
      }
      if (Math.abs(want - beam.x) < 0.002 && Math.abs(beam.v) < 0.002) {
        beam.x = want;
        beam.v = 0;
      }
    }
    render();
    if (touring) syncInputs();
    const settled = !touring && shown.m === target.m && shown.price === target.price && beam.v === 0 && beam.x === want;
    if (visible && !settled) frame = requestAnimationFrame(tick);
  }

  function run() {
    if (!frame && visible && alive) {
      last = 0;
      frame = requestAnimationFrame(tick);
    }
    if (!visible || still.matches) {
      // offscreen or still: jump, so the drawing and readout are never stale
      shown.m = target.m;
      shown.price = target.price;
      beam.x = balance(shown.m, shown.price).tilt;
      beam.v = 0;
      render();
    }
  }

  // knobs: drag (pointer only); the range inputs take keys and assistive technology
  for (const name of ["m", "price"]) {
    const knob = knobs[name];
    const r = RANGES[name];
    let drag = null;
    knob.addEventListener("pointerdown", (event) => {
      stopTour();
      drag = { id: event.pointerId, x: event.clientX, y: event.clientY, from: target[name] };
      try { knob.setPointerCapture(event.pointerId); } catch (error) { /* synthetic pointers have no capture */ }
      event.preventDefault();
    });
    knob.addEventListener("pointermove", (event) => {
      if (!drag || event.pointerId !== drag.id) return;
      const moved = event.clientX - drag.x - (event.clientY - drag.y);
      const next = snapTo(drag.from + (moved / 180) * (r.max - r.min), r);
      if (next !== target[name]) steer({ [name]: next }, 0.1, "user");
    });
    const release = (event) => {
      if (drag && event.pointerId === drag.id) {
        try { knob.releasePointerCapture(event.pointerId); } catch (error) { /* already released */ }
        drag = null;
      }
    };
    knob.addEventListener("pointerup", release);
    knob.addEventListener("pointercancel", release);
    ranges[name].addEventListener("focus", stopTour);
    ranges[name].addEventListener("input", () => steer({ [name]: Number(ranges[name].value) }, 0.12, "user"));
  }
  const todayButton = root.querySelector("[data-today]");
  if (todayButton) todayButton.addEventListener("click", () => steer({ m: Number(today.m), price: Number(today.price) }, 0.4, "today"));
  card.addEventListener("pointerdown", stopTour);

  // theme follows the page, live
  const followTheme = () => {
    const t = themeOf();
    if (root.dataset.theme !== t) root.dataset.theme = t;
  };
  const themeWatch = new MutationObserver(followTheme);
  themeWatch.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
  const scheme = window.matchMedia ? matchMedia("(prefers-color-scheme: dark)") : null;
  if (scheme && scheme.addEventListener) scheme.addEventListener("change", followTheme);
  const onStill = () => {
    if (still.matches) touring = false;
    run();
  };
  if (still.addEventListener) still.addEventListener("change", onStill);

  const seen = new IntersectionObserver(
    (entries) => {
      visible = entries[entries.length - 1].isIntersecting;
      if (visible) run();
    },
    { rootMargin: "120px 0px" },
  );
  seen.observe(card);

  // keep each knob's hit area at least HIT_PX square on screen, whatever width the figure is drawn at
  const svg = root.querySelector(".iso-svg");
  const sizeHits = () => {
    const wide = svg.getBoundingClientRect().width;
    if (!wide) return;
    const units = (HIT_PX * VIEW_W) / wide;
    for (const name of ["m", "price"]) knobs[name].firstChild.setAttribute("d", knobHit(name, units, units));
  };
  const sized = window.ResizeObserver ? new ResizeObserver(sizeHits) : null;
  if (sized) sized.observe(svg);
  sizeHits();

  syncInputs();
  describe();
  render();
  queueMicrotask(() => emit("mount", target.m, target.price));

  return {
    set(next) {
      next = next || {};
      steer({ m: next.m, price: next.price }, 0.4, "set");
    },
    destroy() {
      alive = false;
      if (frame) cancelAnimationFrame(frame);
      seen.disconnect();
      if (sized) sized.disconnect();
      themeWatch.disconnect();
      if (scheme && scheme.removeEventListener) scheme.removeEventListener("change", followTheme);
      if (still.removeEventListener) still.removeEventListener("change", onStill);
      root.remove();
    },
  };
}

window.Balance = { mount };
