(() => {
  "use strict";

  /*
   * Trading Floor canvas presentation layer.
   *
   * Centralizes Saturn ring occlusion, high-contrast orb labels, and a subtle
   * depth-of-field cue for orbiting objects that recede behind the center plane.
   * The blur is deliberately capped at 1.2px so it reads as depth rather than
   * loss of information, and labels use a glyph outline rather than a box.
   */
  const proto = CanvasRenderingContext2D.prototype;
  const originalArc = proto.arc;
  const originalEllipse = proto.ellipse;
  const originalFillText = proto.fillText;
  const originalStroke = proto.stroke;
  const ringState = new WeakMap();

  const norm = value => String(value).replace(/\s+/g, "").toLowerCase();
  const isInnerLegacyRing = value => {
    const v = norm(value);
    return v === "rgba(255,215,110,0.9)" || v === "rgba(255,215,110,.9)";
  };
  const isOuterLegacyRing = value => {
    const v = norm(value);
    return v === "rgba(255,235,170,0.66)" || v === "rgba(255,235,170,.66)";
  };
  const isLegacyRing = value => isInnerLegacyRing(value) || isOuterLegacyRing(value);

  function depthBlurForRadius(radius) {
    // Perspective projection makes orbiting nodes smaller as they recede. The
    // center orb stays at 59px, so only projected orbiting nodes enter these
    // thresholds. Foreground and neutral-depth objects remain perfectly crisp.
    if (radius <= 29.5) return 1.2;
    if (radius <= 32) return 0.9;
    if (radius <= 34.5) return 0.55;
    if (radius <= 36) return 0.3;
    return 0;
  }

  proto.arc = function (x, y, radius, startAngle, endAngle, counterclockwise) {
    const fullCircle = Math.abs(startAngle) < 1e-6 && Math.abs(endAngle - Math.PI * 2) < 1e-4;
    if (fullCircle && radius >= 27 && radius <= 62) {
      const blur = depthBlurForRadius(radius);
      if (blur > 0) this.filter = `blur(${blur}px)`;
    }
    return originalArc.call(this, x, y, radius, startAngle, endAngle, counterclockwise);
  };

  proto.fillText = function (text, x, y, maxWidth) {
    // Orb labels are the only text drawn on this canvas. A compact black stroke
    // around the glyphs keeps white/cyan labels legible across changing sphere
    // lighting without introducing a rectangular badge or backdrop.
    const previousStroke = this.strokeStyle;
    const previousWidth = this.lineWidth;
    const previousJoin = this.lineJoin;
    const previousMiter = this.miterLimit;

    this.strokeStyle = "rgba(0,0,0,.92)";
    this.lineWidth = /(?:7px|8px)/.test(this.font) ? 1.8 : 2.4;
    this.lineJoin = "round";
    this.miterLimit = 2;
    if (maxWidth === undefined) this.strokeText(text, x, y);
    else this.strokeText(text, x, y, maxWidth);

    this.strokeStyle = previousStroke;
    this.lineWidth = previousWidth;
    this.lineJoin = previousJoin;
    this.miterLimit = previousMiter;

    return maxWidth === undefined
      ? originalFillText.call(this, text, x, y)
      : originalFillText.call(this, text, x, y, maxWidth);
  };

  proto.ellipse = function (x, y, rx, ry, rotation, startAngle, endAngle, counterclockwise) {
    if (isLegacyRing(this.strokeStyle) && Math.abs(startAngle) < 1e-6 && Math.abs(endAngle - Math.PI * 2) < 1e-4) {
      const entries = ringState.get(this) || [];
      entries.push({
        x, y, rx, ry, rotation,
        matrix: this.getTransform(),
        lineWidth: this.lineWidth,
        outer: isOuterLegacyRing(this.strokeStyle)
      });
      ringState.set(this, entries);
    }
    return originalEllipse.call(this, x, y, rx, ry, rotation, startAngle, endAngle, counterclockwise);
  };

  function greenRingStyle(entry, front) {
    if (entry.outer) {
      return front
        ? { stroke: "rgba(142,235,170,.52)", shadow: "rgba(91,218,139,.22)", blur: 7 }
        : { stroke: "rgba(132,226,162,.30)", shadow: "rgba(84,205,130,.12)", blur: 5 };
    }
    return front
      ? { stroke: "rgba(118,229,153,.72)", shadow: "rgba(84,215,132,.30)", blur: 9 }
      : { stroke: "rgba(116,220,150,.48)", shadow: "rgba(84,205,130,.18)", blur: 7 };
  }

  function drawFrontRingHalves(ctx) {
    const entries = ringState.get(ctx);
    if (!entries?.length) return;
    ringState.delete(ctx);

    for (const entry of entries) {
      const style = greenRingStyle(entry, true);
      ctx.save();
      const m = entry.matrix;
      ctx.setTransform(m.a, m.b, m.c, m.d, m.e, m.f);
      ctx.beginPath();
      originalEllipse.call(ctx, entry.x, entry.y, entry.rx, entry.ry, entry.rotation, 0, Math.PI, false);
      ctx.strokeStyle = style.stroke;
      ctx.shadowColor = style.shadow;
      ctx.shadowBlur = style.blur;
      ctx.lineWidth = entry.lineWidth;
      originalStroke.call(ctx);
      ctx.restore();
    }
  }

  proto.stroke = function (...args) {
    const originalStyle = this.strokeStyle;
    const originalShadow = this.shadowColor;
    const originalBlur = this.shadowBlur;

    if (isLegacyRing(originalStyle)) {
      const entries = ringState.get(this) || [];
      const entry = entries[entries.length - 1] || { outer: isOuterLegacyRing(originalStyle) };
      const style = greenRingStyle(entry, false);
      this.strokeStyle = style.stroke;
      this.shadowColor = style.shadow;
      this.shadowBlur = Math.min(Number(originalBlur) || 0, style.blur);
      const result = originalStroke.apply(this, args);
      this.strokeStyle = originalStyle;
      this.shadowColor = originalShadow;
      this.shadowBlur = originalBlur;
      return result;
    }

    const result = originalStroke.apply(this, args);
    if (norm(originalStyle) === "#ffd36f") drawFrontRingHalves(this);
    return result;
  };
})();
