(() => {
  "use strict";

  /*
   * Trading Floor canvas presentation layer.
   *
   * This lab-level adapter centralizes three visual concerns that are not yet
   * part of the base renderer: Saturn ring occlusion, high-contrast orb labels,
   * and subtle depth-of-field for objects travelling behind the center plane.
   *
   * The implementation is intentionally conservative: blur never exceeds
   * 1.2px, text outline is drawn directly around glyphs (no label box), and all
   * state is scoped to the CanvasRenderingContext2D instance.
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
    // Projected orbiting nodes shrink as they move behind the center plane.
    // Center orb radius is 59px; ordinary projected nodes are ~28–46px.
    // Keeping the threshold below the neutral projected size means foreground
    // nodes remain crisp while only genuinely receding nodes soften.
    if (radius <= 29.5) return 1.2;
    if (radius <= 32) return 0.9;
    if (radius <= 34.5) return 0.55;
    if (radius <= 36) return 0.3;
    return 0;
  }

  proto.arc = function (x, y, radius, startAngle, endAngle, counterclockwise) {
    const isFullOrb = radius >= 27 && radius <= 62 && Math.abs(startAngle) < 1e-6 && Math.abs(endAngle - Math.PI * 2) < 1e-4;
    if (isFullOrb) {
      const blur = depthBlurForRadius(radius);
      if (blur > 0) this.filter = `blur(${blur}px)`;
    }
    return originalArc.call(this, x, y, radius, startAngle, endAngle, counterclockwise);
  };

  proto.fillText = function (text, x, y, maxWidth) {
    // Orb labels are the only canvas text in this prototype. Draw a compact
    // dark glyph outline first so white/cyan text remains readable as lighting
    // and depth change. This is a true text outline, not a rectangle or badge.
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
