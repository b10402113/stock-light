"""Technical indicator calculation functions."""

from decimal import Decimal
from typing import Any

from src.stock_indicator.schema import (
    IndicatorType,
    KDJData,
    MACDData,
    RSIData,
    SMAData,
    generate_indicator_key,
)


def calculate_rsi(prices: list[Decimal], period: int = 14) -> RSIData | None:
    """Calculate RSI (Relative Strength Index).

    Args:
        prices: List of closing prices (oldest to newest)
        period: RSI period (default 14)

    Returns:
        RSIData: RSI value or None if insufficient data
    """
    if len(prices) < period + 1:
        return None

    # Calculate price changes
    changes = []
    for i in range(1, len(prices)):
        change = prices[i] - prices[i - 1]
        changes.append(change)

    # Separate gains and losses
    gains = [max(0, c) for c in changes]
    losses = [abs(min(0, c)) for c in changes]

    # Calculate initial average gain and loss
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    # Use Wilder's smoothing method for subsequent values
    for i in range(period, len(changes)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        rsi = Decimal(100)
    else:
        rs = avg_gain / avg_loss
        rsi = Decimal(100) - (Decimal(100) / (1 + rs))

    return RSIData(value=rsi)


def calculate_sma(prices: list[Decimal], period: int = 20) -> SMAData | None:
    """Calculate SMA (Simple Moving Average).

    Args:
        prices: List of closing prices (oldest to newest)
        period: SMA period (default 20)

    Returns:
        SMAData: SMA value or None if insufficient data
    """
    if len(prices) < period:
        return None

    sma = sum(prices[-period:]) / period
    return SMAData(value=sma)


def calculate_kdj(
    prices: list[tuple[Decimal, Decimal, Decimal, Decimal]],
    k_period: int = 9,
    d_period: int = 3,
    j_period: int = 3,
) -> KDJData | None:
    """Calculate KDJ (Stochastic Oscillator).

    Args:
        prices: List of (open, high, low, close) tuples (oldest to newest)
        k_period: K line period (default 9)
        d_period: D line period (default 3)
        j_period: J line period (default 3)

    Returns:
        KDJData: K, D, J values or None if insufficient data
    """
    if len(prices) < k_period:
        return None

    # Calculate RSV (Raw Stochastic Value)
    rsv_values = []
    for i in range(k_period - 1, len(prices)):
        period_prices = prices[i - k_period + 1 : i + 1]
        highs = [p[1] for p in period_prices]
        lows = [p[2] for p in period_prices]
        close = prices[i][3]

        highest = max(highs)
        lowest = min(lows)

        if highest == lowest:
            rsv = Decimal(50)
        else:
            rsv = (close - lowest) / (highest - lowest) * Decimal(100)

        rsv_values.append(rsv)

    if len(rsv_values) < d_period:
        return None

    # Calculate K (smoothed RSV)
    k_values = []
    k = Decimal(50)  # Initial K value
    for rsv in rsv_values:
        k = (k * (d_period - 1) + rsv) / d_period
        k_values.append(k)

    # Calculate D (smoothed K)
    d_values = []
    d = Decimal(50)  # Initial D value
    for k_val in k_values:
        d = (d * (j_period - 1) + k_val) / j_period
        d_values.append(d)

    # Get latest values
    k_latest = k_values[-1] if k_values else Decimal(50)
    d_latest = d_values[-1] if d_values else Decimal(50)
    j_latest = k_latest * 3 - d_latest * 2

    return KDJData(k=k_latest, d=d_latest, j=j_latest)


def calculate_macd(
    prices: list[Decimal],
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
) -> MACDData | None:
    """Calculate MACD (Moving Average Convergence Divergence).

    Args:
        prices: List of closing prices (oldest to newest)
        fast_period: Fast EMA period (default 12)
        slow_period: Slow EMA period (default 26)
        signal_period: Signal line period (default 9)

    Returns:
        MACDData: MACD, signal, histogram values or None if insufficient data
    """
    if len(prices) < slow_period + signal_period:
        return None

    # Calculate EMAs
    def calculate_ema(data: list[Decimal], period: int) -> list[Decimal]:
        """Calculate EMA for a list of values."""
        multiplier = Decimal(2) / Decimal(period + 1)
        ema_values = []

        # Start with SMA for first EMA value
        sma = sum(data[:period]) / period
        ema_values.append(sma)

        # Calculate subsequent EMA values
        for i in range(period, len(data)):
            ema = (data[i] - ema_values[-1]) * multiplier + ema_values[-1]
            ema_values.append(ema)

        return ema_values

    # Calculate fast and slow EMA
    fast_ema = calculate_ema(prices, fast_period)
    slow_ema = calculate_ema(prices, slow_period)

    # Align EMA lists (fast EMA starts earlier)
    offset = slow_period - fast_period
    macd_values = []
    for i in range(len(slow_ema)):
        macd = fast_ema[i + offset] - slow_ema[i]
        macd_values.append(macd)

    # Calculate signal line (EMA of MACD)
    signal_ema = calculate_ema(macd_values, signal_period)

    # Get latest values
    macd_latest = macd_values[-1]
    signal_latest = signal_ema[-1]
    histogram_latest = macd_latest - signal_latest

    return MACDData(macd=macd_latest, signal=signal_latest, histogram=histogram_latest)


def calculate_indicators_from_prices(
    closes: list[Decimal],
    ohlcs: list[tuple[Decimal, Decimal, Decimal, Decimal]] | None = None,
    indicator_keys: list[str] | None = None,
) -> dict[str, dict[str, Any]]:
    """Calculate multiple indicators from price data.

    Args:
        closes: List of closing prices (oldest to newest)
        ohlcs: Optional list of (open, high, low, close) tuples for KDJ
        indicator_keys: Optional list of indicator keys to calculate

    Returns:
        dict: Indicator key to calculated data mapping
    """
    results: dict[str, dict[str, Any]] = {}

    # Calculate all default indicators if no specific keys provided
    if not indicator_keys:
        # Default indicators
        if len(closes) >= 15:
            rsi = calculate_rsi(closes, 14)
            if rsi:
                key = generate_indicator_key(IndicatorType.RSI, [14])
                results[key] = rsi.model_dump()

        if len(closes) >= 21:
            sma = calculate_sma(closes, 20)
            if sma:
                key = generate_indicator_key(IndicatorType.SMA, [20])
                results[key] = sma.model_dump()

        if ohlcs and len(ohlcs) >= 9:
            kdj = calculate_kdj(ohlcs, 9, 3, 3)
            if kdj:
                key = generate_indicator_key(IndicatorType.KDJ, [9, 3, 3])
                results[key] = kdj.model_dump()

        if len(closes) >= 35:
            macd = calculate_macd(closes, 12, 26, 9)
            if macd:
                key = generate_indicator_key(IndicatorType.MACD, [12, 26, 9])
                results[key] = macd.model_dump()
    else:
        # Calculate specific indicators
        from src.stock_indicator.schema import parse_indicator_key

        for key in indicator_keys:
            try:
                ind_type, params = parse_indicator_key(key)

                if ind_type == IndicatorType.RSI:
                    period = params[0] if params else 14
                    rsi = calculate_rsi(closes, period)
                    if rsi:
                        results[key] = rsi.model_dump()

                elif ind_type == IndicatorType.SMA:
                    period = params[0] if params else 20
                    sma = calculate_sma(closes, period)
                    if sma:
                        results[key] = sma.model_dump()

                elif ind_type == IndicatorType.KDJ:
                    if ohlcs:
                        k_period = params[0] if len(params) > 0 else 9
                        d_period = params[1] if len(params) > 1 else 3
                        j_period = params[2] if len(params) > 2 else 3
                        kdj = calculate_kdj(ohlcs, k_period, d_period, j_period)
                        if kdj:
                            results[key] = kdj.model_dump()

                elif ind_type == IndicatorType.MACD:
                    fast = params[0] if len(params) > 0 else 12
                    slow = params[1] if len(params) > 1 else 26
                    signal = params[2] if len(params) > 2 else 9
                    macd = calculate_macd(closes, fast, slow, signal)
                    if macd:
                        results[key] = macd.model_dump()

            except ValueError:
                # Skip invalid indicator keys
                continue

    return results