(() => {
  // UI-lab presentation shim only. It changes two known Saturn-ring stroke colors
  // emitted by app-v16.js while leaving the gold Saturn body and trading logic untouched.
  const proto = CanvasRenderingContext2D.prototype;
  const originalStroke = proto.stroke;
  proto.stroke = function (...args) {
    const originalStyle = this.strokeStyle;
    const originalShadow = this.shadowColor;
    const originalBlur = this.shadowBlur;

    if (originalStyle === "rgba(255, 215, 110, 0.9)" || originalStyle === "rgba(255,215,110,.9)") {
      this.strokeStyle = "rgba(116, 220, 150, 0.58)";
      this.shadowColor = "rgba(84, 205, 130, 0.30)";
      this.shadowBlur = Math.min(Number(this.shadowBlur) || 0, 12);
    } else if (originalStyle === "rgba(255, 235, 170, 0.66)" || originalStyle === "rgba(255,235,170,.66)") {
      this.strokeStyle = "rgba(132, 226, 162, 0.34)";
      this.shadowColor = "rgba(84, 205, 130, 0.18)";
      this.shadowBlur = Math.min(Number(this.shadowBlur) || 0, 8);
    }

    const result = originalStroke.apply(this, args);
    this.strokeStyle = originalStyle;
    this.shadowColor = originalShadow;
    this.shadowBlur = originalBlur;
    return result;
  };
})();
