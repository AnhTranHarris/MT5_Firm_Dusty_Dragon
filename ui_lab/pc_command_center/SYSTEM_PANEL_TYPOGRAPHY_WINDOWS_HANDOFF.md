# Dusty Dragon System Panel Typography — Windows Handoff

Status: UI-Lab visual contract. This document prevents the eventual WinUI 3/WebView2 conversion from recreating per-panel typography drift.

## Reference density

`FIRM EVENT TIMELINE` is the baseline information-density reference for **all ordinary cockpit panels**, not merely the Command left rail.

The system-wide semantic scale is:

```text
Panel header       10 px-equivalent
Primary body        9 px-equivalent
Secondary label     8 px-equivalent
Caption/note        7.5 px-equivalent
Primary value      12 px-equivalent
Key value          14 px-equivalent maximum under ordinary conditions
Line-height         ~1.10
Dense scan row      ~18 px minimum
```

These are UI-Lab CSS pixels, not literal WinUI device pixels. The Windows application must translate them into DPI-aware typography tokens and validate them at 100%, 125%, 150%, and 200% scaling.

## Global spacing rule

When a panel is under vertical pressure, reduce in this order:

1. outer margin;
2. internal padding;
3. inter-row gap;
4. line leading;
5. optional explanatory prose;
6. only then reduce primary text size.

Never solve a layout problem by independently shrinking one panel until it becomes visually disconnected from the rest of the application.

## Uniformity rule

The same semantic role must look the same throughout Command, Trading, Risk, Performance, Research, Layer 0 Lab, and System:

- panel headers use one header token;
- ordinary data/prose uses one body token;
- metadata uses one secondary token;
- notes/captions use one caption token;
- comparable financial/operational values use one primary-value token.

Color, weight, and state accents may distinguish meaning. Arbitrary font-size changes must not be used as a substitute for hierarchy.

## Exceptions

Only true workspace-level hero values or specialized visualization labels may exceed the ordinary scale. Exceptions must be intentional, sparse, and documented. They may not cause surrounding panels to appear zoomed in/out relative to each other.

The analytical Trading Floor hierarchy may preserve stronger Desk/Layer identity weight, but its body telemetry must remain on the same system scale. 3D canvas labels are visualization geometry and are not governed by ordinary panel typography tokens.

## No-overlap contract

All text must remain non-overlapping at the minimum supported viewport and Windows scaling levels. If content cannot fit, prefer truncating optional description text or reflowing rows before shrinking below the supported body/caption tokens.

Do not introduce panel-internal vertical scrollbars merely to preserve oversized spacing. Cockpit panels should fit their assigned viewport whenever the information contract is bounded.

## Production implementation

Recommended WinUI token mapping:

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

WebView2-hosted surfaces should receive the same token values through CSS custom properties generated from the host theme/settings so native and web-rendered controls remain visually synchronized.

## Accessibility

Typography uniformity must not defeat accessibility. Windows Text Scale, high contrast, forced colors, keyboard focus, and screen-reader semantics remain authoritative. The layout should reflow when text scaling requires it rather than clipping or overlapping.

## QC before migration

Test every workspace at supported minimum/target resolutions and at 100/125/150/200% Windows scaling. Verify panel header consistency, body-text consistency, secondary-text consistency, no overlaps, no unintended scrollbars, no clipped values, forced-colors behavior, reduced/no-motion behavior, and long-content truncation/reflow.

Engineering target: zero known typography/spacing ambiguity before migration. Literal zero debugging cannot be guaranteed for live Windows/MT5 integration.
