(() => {
  "use strict";

  const data = window.DUSTY_MOCK;
  const target = document.querySelector("#timeline");
  if (!data || !target || !Array.isArray(data.overnight)) return;

  /*
   * UI-LAB significance adapter only.
   * Production Core must classify event scope/severity explicitly; the Windows UI
   * must not infer operational importance from message text.
   *
   * For the current fixture, a major desk event is either explicitly tied to a
   * Gxx desk/MT5 session, or the immediately relevant broker-recovery event that
   * leaves execution blocked. We retain only the five newest matching events.
   */
  const isMajorDeskEvent = ([, message]) => {
    const text = String(message || "");
    return /\bG\d{2}\b/i.test(text)
      || /\bMT5\s+G\d{2}\b/i.test(text)
      || /broker recovered; execution remained blocked/i.test(text);
  };

  const events = data.overnight
    .filter(isMajorDeskEvent)
    .slice(-5);

  target.innerHTML = events
    .map(([time, message]) => `<div class="timeline-row command-major-desk-event"><time>${time}</time><span>${message}</span></div>`)
    .join("");

  const panel = target.closest(".panel");
  panel?.classList.add("command-major-timeline-panel");
  panel?.setAttribute("aria-label", "Five most recent major desk-impact events");

  window.DUSTY_COMMAND_TIMELINE = Object.freeze({
    version:"3.2",
    maxEvents:5,
    events:events.map(([time,message]) => Object.freeze({time,message}))
  });
})();