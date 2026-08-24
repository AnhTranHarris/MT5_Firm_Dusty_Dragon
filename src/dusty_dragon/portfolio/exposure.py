from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from dusty_dragon.brokers.contracts import Position
from dusty_dragon.domain.trades import Side, TradeProposal
from pydantic import BaseModel, Field


KNOWN_FX_CURRENCIES = frozenset(
    {
        "AUD",
        "CAD",
        "CHF",
        "CNH",
        "CZK",
        "DKK",
        "EUR",
        "GBP",
        "HKD",
        "HUF",
        "JPY",
        "MXN",
        "NOK",
        "NZD",
        "PLN",
        "SEK",
        "SGD",
        "TRY",
        "USD",
        "ZAR",
    }
)


class PortfolioDecision(StrEnum):
    ALLOW = "allow"
    DENY = "deny"


class FxPair(BaseModel):
    base: str
    quote: str


class PortfolioReview(BaseModel):
    decision: PortfolioDecision
    reasons: list[str] = Field(default_factory=list)
    current_net_lots: dict[str, float] = Field(default_factory=dict)
    projected_net_lots: dict[str, float] = Field(default_factory=dict)


def parse_fx_symbol(symbol: str) -> FxPair:
    """Parse a broker FX symbol while tolerating common suffixes.

    Examples such as ``EURUSD``, ``EURUSDm`` and ``EURUSD.pro`` normalize to
    EUR/USD. Prefix-based broker aliases intentionally fail closed until an
    explicit symbol map is added for that broker division.
    """

    letters = "".join(character for character in symbol.upper() if character.isalpha())
    if len(letters) < 6:
        raise ValueError(f"cannot parse FX symbol: {symbol}")
    base, quote = letters[:3], letters[3:6]
    if base not in KNOWN_FX_CURRENCIES or quote not in KNOWN_FX_CURRENCIES:
        raise ValueError(f"unsupported FX currency code in symbol: {symbol}")
    if base == quote:
        raise ValueError(f"FX symbol cannot use the same base and quote currency: {symbol}")
    return FxPair(base=base, quote=quote)


def currency_exposure_from_positions(positions: list[Position]) -> dict[str, float]:
    """Return directional currency exposure in lot-equivalent units.

    This is intentionally *not* a USD-notional or margin calculation. It is an
    early firm-level concentration signal. Monetary exposure will later use
    contract sizes, FX conversion, and account-level portfolio snapshots.
    """

    exposure: dict[str, float] = {}
    for position in positions:
        pair = parse_fx_symbol(position.symbol)
        sign = 1.0 if position.side == Side.BUY else -1.0
        exposure[pair.base] = exposure.get(pair.base, 0.0) + sign * position.volume
        exposure[pair.quote] = exposure.get(pair.quote, 0.0) - sign * position.volume
    return exposure


@dataclass(frozen=True)
class FirmPortfolioGovernor:
    """Fail-closed currency concentration gate for the trading firm.

    Vibe-Trading reference: portfolio state is a separate read-only concern and
    incomplete inputs are surfaced rather than silently omitted.

    Automaton reference: this is a centralized policy capability that every bot
    instance can call before execution; bots do not grant themselves exceptions.

    Kronos remains upstream and has no ability to override portfolio limits.
    """

    max_abs_currency_net_lots: float = 0.05

    def __post_init__(self) -> None:
        if self.max_abs_currency_net_lots <= 0:
            raise ValueError("max_abs_currency_net_lots must be positive")

    def evaluate(
        self,
        proposal: TradeProposal,
        positions: list[Position],
        *,
        proposed_volume: float,
    ) -> PortfolioReview:
        if proposed_volume <= 0:
            raise ValueError("proposed_volume must be positive")

        try:
            current = currency_exposure_from_positions(positions)
            pair = parse_fx_symbol(proposal.symbol)
        except ValueError as exc:
            return PortfolioReview(
                decision=PortfolioDecision.DENY,
                reasons=[f"portfolio exposure unavailable: {exc}"],
            )

        projected = dict(current)
        sign = 1.0 if proposal.side == Side.BUY else -1.0
        projected[pair.base] = projected.get(pair.base, 0.0) + sign * proposed_volume
        projected[pair.quote] = projected.get(pair.quote, 0.0) - sign * proposed_volume

        breaches = [
            (currency, lots)
            for currency, lots in sorted(projected.items())
            if abs(lots) > self.max_abs_currency_net_lots + 1e-12
        ]
        if breaches:
            reasons = [
                (
                    f"projected {currency} net exposure {lots:+.4f} lots exceeds "
                    f"firm limit {self.max_abs_currency_net_lots:.4f}"
                )
                for currency, lots in breaches
            ]
            return PortfolioReview(
                decision=PortfolioDecision.DENY,
                reasons=reasons,
                current_net_lots=current,
                projected_net_lots=projected,
            )

        return PortfolioReview(
            decision=PortfolioDecision.ALLOW,
            current_net_lots=current,
            projected_net_lots=projected,
        )
