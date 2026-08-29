# Dusty Dragon System Panel Typography — Windows Handoff

Status: UI-Lab visual contract. This document prevents the eventual WinUI 3/WebView2 conversion from recreating per-panel typography drift.

## Reference density

`FIRM EVENT TIMELINE` remains the information-density reference for all ordinary cockpit panels, but the global readable scale is now raised one step:

```text
Panel header                 11 px-equivalent
Ordinary body                10 px-equivalent minimum
Secondary label              10 px-equivalent minimum
Caption / note               10 px-equivalent minimum
Primary value                ~12 px-equivalent
Key / master value           ~14 px-equivalent
Normal line-height           ~1.16
Dense scan row               ~21 px minimum
```

These are UI-Lab CSS pixels, not literal WinUI device pixels. Production must translate them into DPI-aware semantic typography tokens and validate at 100%, 125%, 150%, and 200% Windows scaling.

## Global spacing and fill rule

Every bounded cockpit panel should stretch to the height assigned by its workspace grid/flex layout. Avoid fixed internal heights that manufacture dead space. When vertical pressure occurs, reclaim space in this order:

1. outer margins;
2. panel padding;
3. inter-component gaps;
4. row padding;
5. optional explanatory prose;
6. only then reconsider the information contract.

Do **not** reduce ordinary, secondary, or caption text below the 10 px-equivalent floor simply to make a panel fit. Reflow or remove nonessential prose first.

Text containers must have sufficient minimum row height and line-height so glyphs are not clipped and adjacent lines cannot overlap. A panel may be visually dense, but every displayed line must remain fully readable.

## Uniformity rule

The same semantic role must render at the same token throughout Command, Trading, Risk, Performance, Research, Layer 0 Lab, and System. Color, weight and state accents may distinguish meaning; arbitrary per-panel font-size changes may not.

## Exceptions

Only genuine workspace-level hero values or specialized visualization geometry may exceed the ordinary scale. Exceptions must be sparse and intentional. Analytical Trading Floor Desk/Layer identity may use weight and state color, while its telemetry remains on the system scale. 3D-canvas labels are visualization geometry rather than ordinary panel typography.

## No-overlap / no-cutoff contract

At the supported minimum viewport, no visible text may overlap another line or be partially clipped. If content cannot fit, remove optional notes, shorten labels, or reflow bounded rows before changing the typography floor. Avoid panel-internal vertical scrollbars for bounded cockpit data.

Panels should consume their assigned height without creating blank filler areas simply because old fixed dimensions survived from an earlier layout mode.

## Production token mapping

Recommended WinUI tokens:

```text
PanelHeaderTextStyle
PanelBodyTextStyle
PanelSecondaryTextStyle
PanelCaptionTextStyle
PanelValueTextStyle
PanelKeyValueTextStyle
PanelDenseRowHeight
PanelCompactPadding
PanelCompactGap
```

WebView2-hosted surfaces should receive the same token values through CSS custom properties emitted by the host theme/settings so native and web-rendered controls remain synchronized.

## Accessibility

Typography uniformity must not defeat accessibility. Windows Text Scale, high contrast, forced colors, keyboard focus and screen-reader semantics remain authoritative. Layout must reflow under accessibility scaling rather than clip or overlap.

## QC before migration

Test every workspace at target/minimum resolutions and 100/125/150/200% Windows scaling. Verify 11px-equivalent headers, 10px-equivalent minimum operator text, consistent 12px/14px financial values, compact whitespace, stretched panel occupancy, no overlaps, no clipped lines, no unintended internal scrollbars, forced-colors behavior, reduced/no-motion behavior and long-content truncation/reflow.

Engineering target: zero known typography/spacing ambiguity before migration. Literal zero debugging cannot be guaranteed for live Windows/MT5 integration.
