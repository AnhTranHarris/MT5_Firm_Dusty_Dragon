# Dusty Dragon Portability Notes

## Current implementation target

Dusty Dragon is implemented for MetaTrader 5 first. MT5 is the concrete execution and market-data transport for the initial BoForex division.

## Future portability rule

MT5 must not become part of the firm's domain model. Strategy, forecasting, research, learning, portfolio, reporting, trade-decision, and risk-governance code must remain platform-neutral.

Only broker/transport adapters may depend on MT5-specific APIs, constants, return codes, order request structures, terminal lifecycle, symbol metadata, or account/session behavior.

## Translation notes for a future TradingView-compatible transport

When a future TradingView/broker integration is required, replace or translate only the transport-facing responsibilities below:

- MT5 terminal connection/session management
- symbol discovery and broker symbol naming
- timeframe mapping
- OHLCV/tick retrieval
- quote retrieval
- account and position reads
- order request translation
- order/fill/cancel status mapping
- broker-side error and return-code handling
- trading-session metadata

The following must remain unchanged and reusable:

- `TradeProposal` and trade-decision schema
- strategy and signal outputs
- Kronos forecast interface
- research and factor interfaces
- risk policy and firm-level limits
- portfolio exposure model
- trade/decision ledger
- attribution and learning records
- bot lineage and firm knowledge
- scheduling intent and weekly research lifecycle

## Adapter contract principle

Domain code should depend on a broker/execution interface, never on MetaTrader5 package objects directly. The MT5 adapter translates platform-neutral requests into MT5 requests and converts MT5 responses back into platform-neutral models.

Future adapters may include TradingView-linked broker execution, direct broker APIs, or other platforms. They should satisfy the same domain-facing contract rather than forcing strategy rewrites.

## Maintenance note

Do not implement speculative TradingView code now. APIs, supported broker integrations, Pine Script capabilities, webhook behavior, authentication flows, and broker execution paths may materially change before a migration is needed. Preserve architectural seams and update this document when MT5-specific behavior is introduced.
