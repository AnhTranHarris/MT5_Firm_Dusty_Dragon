(() => {
  // Presentation-only canvas shim for the UI laboratory.
  // The base renderer draws the Saturn rings first, then the gold orb. We keep
  // the full ring behind the orb and redraw only the lower/front half after the
  // orb stroke so the green rings visually wrap around the sphere in 3D.
  const proto = CanvasRenderingContext2D.prototype;
  const originalEllipse = proto.ellipse;
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
        ? { stroke: "rgba(142, 235, 170, 0.52)", shadow: "rgba(91, 218, 139, 0.22)", blur: 7 }
        : { stroke: "rgba(132, 226, 162, 0.30)", shadow: "rgba(84, 205, 130, 0.12)", blur: 5 };
    }
    return front
      ? { stroke: "rgba(118, 229, 153, 0.72)", shadow: "rgba(84, 215, 132, 0.30)", blur: 9 }
      : { stroke: "rgba(116, 220, 150, 0.48)", shadow: "rgba(84, 205, 130, 0.18)", blur: 7 };
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
      // Canvas Y grows downward; 0..PI is the lower/front half after the
      // Saturn renderer's local tilt transform.
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

    // This is the gold Saturn body outline in the base renderer. Once it has
    // been stroked, redraw the front ring halves over the orb to create true
    // visual occlusion rather than a flat ellipse sitting behind the planet.
    if (norm(originalStyle) === "#ffd36f") drawFrontRingHalves(this);
    return result;
  };
})();
