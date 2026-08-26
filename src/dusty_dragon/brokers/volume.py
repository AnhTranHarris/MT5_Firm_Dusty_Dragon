from decimal import ROUND_FLOOR, Decimal

from dusty_dragon.brokers.contracts import SymbolSpec


def normalize_volume_down(requested_volume: float, spec: SymbolSpec) -> float:
    """Normalize a requested lot size to broker increments without increasing risk.

    Values below the broker minimum are lifted to the minimum because the broker
    cannot represent a smaller order. Values between valid steps are rounded
    down so normalization never silently increases exposure.
    """
    requested = Decimal(str(requested_volume))
    minimum = Decimal(str(spec.volume_min))
    maximum = Decimal(str(spec.volume_max))
    step = Decimal(str(spec.volume_step))

    if requested <= 0:
        raise ValueError("requested volume must be positive")
    if requested < minimum:
        return float(minimum)
    if requested > maximum:
        raise ValueError(
            f"requested volume {requested_volume} exceeds maximum {spec.volume_max}"
        )

    steps = ((requested - minimum) / step).to_integral_value(rounding=ROUND_FLOOR)
    normalized = minimum + steps * step
    return float(normalized)
