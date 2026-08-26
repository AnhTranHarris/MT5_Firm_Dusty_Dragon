# Dusty Dragon Financial Constitution v1

Status: FROZEN BASELINE

## 1. Authority hierarchy

1. Human CEO owns brokerage-account creation, capitalization, emergency human override, and constitutional policy changes.
2. Dusty Dragon Core owns runtime capital authority and governance.
3. Desk Risk must pass before Portfolio Risk can evaluate incremental exposure.
4. Portfolio Risk may veto additional risk but cannot transfer capital or rewrite a desk strategy.
5. Contractors produce evidence or execute approved instructions only. They cannot independently create capital authority.

## 2. Universal desk objective hierarchy

SURVIVAL -> RISK COMPLIANCE -> PROCESS QUALITY -> CAPITAL PRESERVATION -> CAPITAL GROWTH -> STRETCH PERFORMANCE.

The 25% growth figure is an aspirational/stretch measurement only. It may never force trades, increase leverage, override a stop, loosen risk, or create catch-up behavior.

## 3. Desk risk baseline

- Per-trade risk target ceiling: 1%-2% of desk capital, with dynamic sizing allowed below 1%.
- Daily loss governance: normal hard control approximately 3%, absolute emergency ceiling approximately 5%, subject to versioned policy calibration.
- Active desk exposure guideline: 20%-30% of that desk's own capital, adjusted for risk and correlation.
- Position size is risk-first: allowed size is derived from dollar risk, stop distance, and broker instrument specification. Graduation grants a maximum sizing ceiling; it never commands use of that size.
- Broker minimum lot constraints must never cause Dusty to round upward into a risk violation. If the minimum executable size violates policy, the correct decision is NO TRADE.

## 4. Desk graduation

All new desks begin at the lowest permitted broker size, normally 0.01 lot where available, and intraday authority.

Graduation progressively adds longer holding authority while preserving shorter-horizon authority:

- Level 0: intraday
- Level 1: intraday + up to 2 days
- Level 2: multi-day
- Level 3: up to approximately one week
- Level 4+: multi-week, eventually up to approximately one month

Graduation evidence includes capital/equity quality, rolling trade-management quality, positive expectancy, profit factor/payoff quality, drawdown, recovery, risk-adjusted measures, and account-management compliance.

Universal trade-management quality target: >=85% across the rolling evaluation set. Profitable-trade rate is strategy-dependent and is never substituted for positive expectancy.

Gain Preservation Gate: graduation is blocked when the configured trailing-30-day realized-gain giveback or peak-equity-gain giveback exceeds policy limits. Initial constitutional reference values are 10% of realized gains or 15% of peak equity gains.

Demotion is based on rolling deterioration, not lifetime losing-trade count. The system must evaluate failed trades within a rolling sample together with management-quality and expectancy deterioration.

## 5. Desk health and catastrophic failure

Desk states: NORMAL -> CAUTION -> DEFENSIVE -> HALT -> QUARANTINE.

Initial reference bands are approximately:
- CAUTION around 5% weekly drawdown
- DEFENSIVE around 8%-10%
- HALT / investigation around 10%-15%
- 25% weekly capital or equity loss is catastrophic QUARANTINE

Exact operating thresholds remain versioned policy and may be calibrated only through controlled evidence.

Catastrophic quarantine requires no new trades, emergency position handling per liquidation policy, two weeks of research rehabilitation, revocation of graduation privileges, and restart from Level 0. Institutional knowledge, strategy lineage, failure history, and actual remaining account capital are preserved.

## 6. Learning and anti-overfitting

Live/demo loss never authorizes direct production self-rewrite.

All production changes follow:
DIAGNOSIS -> HYPOTHESIS -> CANDIDATE -> BACKTEST -> HOLDOUT VALIDATION -> CHALLENGER -> QUALIFICATION -> CONTROLLED PROMOTION.

Research separates recent diagnostic data, training/exploration data, and untouched holdout validation. Recent two-month windows are important but must be supplemented by broader historical/regime stress windows.

Monday-Friday nightly research uses symbols traded that day and multi-timeframe analysis. Saturday is deep research. Research may be queued/throttled by the Resource Governor but safety/execution work takes precedence.

## 7. Layer 0 demo exception

Demo desks follow funded-desk behavior except for a one-time bootstrap regime.

- Initial simulated capital: $20,000.
- During first 30 valid forward-trading days, selected non-catastrophic forward-trading risk thresholds may operate at 110% of the standard funded-desk limit.
- Catastrophic safety, evidence, governance, anti-overfitting, and qualification standards are never widened.
- Historical backtesting always uses standard funded-desk parameters.
- Replacing an expired demo account does not restart the bootstrap clock; the clock belongs to the persistent Dusty desk lineage.
- Every Sunday Dusty requests a human demo-capital reset to 75% of then-current demo capital. This is an external capital flow, never trading P&L.
- Layer-0 qualification uses 25 valid forward-trading days to accommodate time-limited broker demo accounts.
- Qualified non-expiring demos remain permanent research/challenge laboratories after live capitalization.

## 8. Layer 0 cohort integrity

Layer 0 requires at least six independently qualified demo-desk proofs. Each counted desk must reach at least Multi-Day graduation and satisfy all individual requirements.

Hardware determines cohort concurrency but never reduces the six-proof requirement.

Cohorts are atomic. If any admitted desk validly fails, zero desks from that cohort count. Previously completed unanimous cohorts retain their valid credits. Infrastructure failure may classify a run INVALID rather than FAIL, but neither counts as a pass.

Cohort membership/configuration is frozen at test start.

After at least six valid proofs from unanimous cohorts, the six-desk portfolio must also qualify before Layer 1 can be requested.

## 9. Live Desk Capital Chain Gate

Layer 1 begins with one human-created/funded MT5 Generalist desk after Layer 0 qualification and human authorization.

To request the next live desk, every currently existing live desk in the layer must maintain end-of-NY-trading-day equity >= $5,000 for seven consecutive valid trading days, remain healthy/risk-compliant, have no unresolved critical incident, and pass portfolio/system health checks.

If any desk closes below $5,000 on any qualifying day, the seven-day streak resets. Aggregate equity can never substitute for an individual desk floor.

Expansion requests are issued on Sunday and require human account creation/capitalization.

## 10. Recursive layer qualification

Within a live layer, existing desks collectively earn the right to request the next desk through the Capital Chain Gate.

When six desk slots are filled, the layer is not automatically graduated. All six must remain individually qualified and the layer portfolio must qualify before the layer can request Desk 01 of the next layer.

Child layers inherit validated institutional knowledge but never parent capital, P&L, drawdown history, MT5 credentials, or qualification state.

## 11. Portfolio governance

Desk capital is financially isolated. No desk may transfer capital to, subsidize, recapitalize, or conceal another desk.

Portfolio equity is an analytical aggregation only.

Preferred realized portfolio growth objective: 5% per monthly cycle. It is never a quota and cannot cause forced trading or risk escalation.

Portfolio governance focuses on risks desks cannot see alone: correlation, concentration, common-factor exposure, simultaneous drawdown, tail behavior, risk contribution, transaction-cost drag, and capital-growth efficiency.

Execution path:
STRATEGY OPPORTUNITY -> DESK RISK PASS -> PORTFOLIO RISK PASS -> APPROVED ORDER -> EXECUTION.

A portfolio rejection of an otherwise valid desk signal must be recorded as PORTFOLIO_CAPACITY_REJECTED, not BAD_SIGNAL, so learning statistics are not contaminated.

Idiosyncratic desk failure isolates the desk. Portfolio-wide intervention requires systemic evidence.

Portfolio states mirror: NORMAL -> CAUTION -> DEFENSIVE -> HALT -> QUARANTINE, with actions controlling new aggregate risk rather than rewriting healthy desk strategies.

## 12. Layer 0 challenge authority

Only Layer 0 has formal adversarial challenge authority.

Once a live layer reaches six desks, it receives seven valid trading days of baseline operation. Layer 0 may then run a 30-valid-trading-day challenge campaign. Layer 0 may challenge a different live layer only when the 90-trading-day challenge interval permits.

Challenge success is based on risk-adjusted, cost-adjusted, robust capital growth, not raw return alone. A challenge win creates a promotion candidate and still requires reproduction, holdout/regime validation, cost/slippage stress, and controlled promotion.

Layer 0 may also perform non-invasive supplemental research for underperforming layers. Supplemental research has no production authority and does not count as a formal challenge campaign.

## 13. Layer 2 styles

Nine active style candidates compete for six specialization slots:
- Trend Following
- Momentum
- Breakout
- Mean Reversion
- Swing
- Range
- Reversal
- Event/Catalyst
- Statistical/Relative Value

Scalping is hardware-deferred, not permanently excluded.

Layer 1 generates style-attributed evidence, including fractional attribution for multi-style trades. Style selection emphasizes risk-adjusted capital growth, expectancy, drawdown, robustness, payoff quality, management quality, stability, capital efficiency, transaction-cost efficiency, and evidence strength.

Top-six ranking alone is insufficient; a candidate must exceed a configurable evidence/quality floor and pass independent Layer-0 validation. Unselected styles remain reserve candidates.

## 14. Layer 3 broker-aware specialization

Layer 3 is derived from the broker's actual tradable universe. Six distinct sectors are not required.

Duplicate sector desks are permitted when broker breadth is limited or evidence favors additional specialization, but sibling variants must maintain approximately 20% meaningful strategic/execution variation and must pass both structural and behavioral variation checks.

Functional duplicates are not accepted as diversification. Dusty monitors signal overlap, entry overlap, symbol/directional overlap, holding-time overlap, P&L/drawdown correlation, common-factor exposure, and simultaneous-loss frequency.

## 15. Contractor and execution sovereignty

Dusty's internal financial data model belongs to Dusty, not MT5, Vibe, Kronos, Nautilus, LEAN, Qlib, or any other contractor.

ForecastEvidence, ResearchEvidence, and BacktestResult can never directly create broker orders. Only Dusty Core may create ApprovedOrder after all governance gates pass.

Contractors are replaceable; the firm, ledger, institutional knowledge, and audit history are not.
