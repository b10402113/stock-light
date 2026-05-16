"""Subscription data preparation and indicator condition checking jobs."""

import logging
import time
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Any

from arq import create_pool
from arq.connections import ArqRedis
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from sqlalchemy import select, and_, or_, any_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.clients.fugle_client import FugoClient
from src.clients.redis_client import StockRedisClient
from src.clients.yfinance_client import YFinanceClient
from src.database import SessionFactory
from src.logging_config import get_console
from src.stock_indicator.model import StockIndicator
from src.stock_indicator.service import StockIndicatorService
from src.subscriptions.model import IndicatorSubscription, NotificationHistory
from src.stocks.schema import DailyPriceBase, StockSource
from src.stocks.service import DailyPriceService, StockService
from src.config import settings

logger = logging.getLogger(__name__)
console = get_console()

REDIS_INDICATOR_UPDATED_KEY = "indicator:updated:last_minute"


async def prepare_subscription_data(
    ctx: dict[str, Any],
    stock_id: int,
) -> dict[str, Any]:
    """Prepare stock data for subscription monitoring.

    This job is triggered when a user subscribes to a stock that doesn't have
    active monitoring or sufficient historical data.

    Steps:
    1. Add stock to Redis active set
    2. Fetch current price and update Redis cache
    3. Fetch 100 days of historical prices
    4. Insert historical prices to database (upsert)

    Args:
        ctx: ARQ context dict with 'redis_pool'
        stock_id: Stock ID to prepare

    Returns:
        dict with stock_id, status, and any error message
    """
    logger.info(f"[job]Starting subscription data preparation[/job] for stock_id=[stock]{stock_id}[/stock]")
    console.print(f"[time]━━━ Subscription Prep (stock_id={stock_id}) ━━━[/time]")

    redis_pool = ctx["redis"]
    redis_client = StockRedisClient(pool=redis_pool)

    result = {
        "stock_id": stock_id,
        "added_to_redis": False,
        "current_price_fetched": False,
        "historical_prices_count": 0,
        "success": False,
        "error": None,
    }

    try:
        # Step 1: Get stock info from database
        async with SessionFactory() as db:
            stock = await StockService.get_by_id(db, stock_id)
            if not stock:
                raise ValueError(f"Stock not found: {stock_id}")

            symbol = stock.symbol
            source = stock.source
            market = stock.market

        logger.info(f"Stock: id=[stock]{stock_id}[/stock], symbol=[job]{symbol}[/job], source=[time]{source}[/time], market=[info]{market}[/info]")
        console.print(f"  [dim]symbol:[/dim] [stock]{symbol}[/stock] [dim]source:[/dim] [time]{source}[/time]")

        # Step 2: Add stock to Redis active set
        added = await redis_client.add_active_stock(stock_id)
        result["added_to_redis"] = added
        logger.info(f"Added stock_id=[stock]{stock_id}[/stock] to Redis active set: [success]{added}[/success]")
        console.print(f"[success]✓ Added to Redis[/success]")

        # Step 3: Fetch current price from API and update Redis
        current_price = None
        if source == StockSource.FUGLE:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("[cyan]Fetching Fugle price...", total=1)

                fugle_client = FugoClient()
                quote = await fugle_client.get_intraday_quote(symbol)
                progress.update(task, completed=1)

                if quote and quote.lastPrice is not None:
                    current_price = float(quote.lastPrice)
                    await redis_client.set_stock_price(
                        stock_id, symbol, current_price, StockSource.FUGLE
                    )
                    result["current_price_fetched"] = True
                    logger.info(f"Fetched current price from Fugle: [success]{current_price}[/success]")
                    console.print(f"[success]✓ Fugle price: {current_price}[/success]")

        elif source == StockSource.YFINANCE:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("[cyan]Fetching YFinance price...", total=1)

                yfinance_client = YFinanceClient()
                price = await yfinance_client.get_current_price(symbol, market)
                progress.update(task, completed=1)

                if price is not None:
                    current_price = price
                    await redis_client.set_stock_price(
                        stock_id, symbol, current_price, StockSource.YFINANCE
                    )
                    result["current_price_fetched"] = True
                    logger.info(f"Fetched current price from YFinance: [success]{current_price}[/success]")
                    console.print(f"[success]✓ YFinance price: {current_price}[/success]")

        if current_price is None:
            logger.warning(f"Failed to fetch current price for stock_id=[stock]{stock_id}[/stock]")
            console.print("[warning]⚠ No current price[/warning]")

        # Step 4: Fetch historical prices (100 days) - ALWAYS use YFinance (free)
        # Calculate date range for last 100 trading days (approximately 140 calendar days)
        import datetime
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=140)

        historical_prices = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]Fetching historical prices...", total=1)

            # Always use YFinance for historical prices (free API)
            yfinance_client = YFinanceClient()
            prices = await yfinance_client.get_historical_prices(
                symbol,
                start_date.isoformat(),
                end_date.isoformat(),
                market,
            )
            progress.update(task, completed=1)

            for p in prices:
                historical_prices.append(
                    DailyPriceBase(
                        date=p["date"],
                        open=p["open"],
                        high=p["high"],
                        low=p["low"],
                        close=p["close"],
                        volume=p["volume"],
                    )
                )

        logger.info(f"Fetched [stock]{len(historical_prices)}[/stock] historical prices from API")
        console.print(f"[success]✓ {len(historical_prices)} historical prices[/success]")

        # Step 5: Insert historical prices to database (upsert)
        if historical_prices:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console,
            ) as progress:
                task = progress.add_task("[cyan]Inserting to database...", total=1)

                async with SessionFactory() as db:
                    count = await DailyPriceService.bulk_insert_prices(
                        db, stock_id, historical_prices
                    )
                    result["historical_prices_count"] = count
                    progress.update(task, completed=1)

                logger.info(f"Inserted/updated [success]{count}[/success] historical prices to database")
                console.print(f"[success]✓ {count} prices saved[/success]")

        result["success"] = True
        logger.info(f"[success]Subscription data preparation completed[/success] for stock_id=[stock]{stock_id}[/stock]")
        console.print(f"[success]━━━ Complete ━━━[/success]")

    except Exception as e:
        result["error"] = str(e)
        logger.error(f"[error]Subscription data preparation failed[/error] for stock_id=[stock]{stock_id}[/stock]: {e}")
        # Don't raise - let ARQ handle retry logic
        result["success"] = False

    return result


async def check_indicator_subscriptions(ctx: dict[str, Any]) -> dict[str, Any]:
    """Check indicator subscriptions for updated stocks.

    Cron job running every minute. Queries stocks that were just updated,
    checks their subscription conditions, and sends notifications.

    Flow:
    1. Get updated stock IDs from Redis Set
    2. If empty, skip (no updated stocks)
    3. Query subscriptions for these stocks with JOIN to indicators
    4. Evaluate conditions using Python logic
    5. Send notifications and record to notification_histories
    6. Update subscription cooldown status

    Args:
        ctx: ARQ context dict with 'redis'

    Returns:
        dict with processing statistics
    """
    logger.info("[job]Starting check_indicator_subscriptions job[/job]")
    console.print("[time]━━━ Subscription Check ━━━[/time]")

    redis_pool = ctx["redis"]

    result = {
        "stocks_checked": 0,
        "subscriptions_evaluated": 0,
        "notifications_sent": 0,
        "conditions_triggered": 0,
        "errors": [],
        "success": False,
    }

    try:
        # Step 1: Get updated stock IDs from Redis
        updated_stock_ids_bytes = await redis_pool.smembers(REDIS_INDICATOR_UPDATED_KEY)

        if not updated_stock_ids_bytes:
            logger.info("No stocks updated in the last minute, skipping check")
            console.print("[info]No updated stocks, skipping[/info]")
            result["success"] = True
            return result

        updated_stock_ids = [int(sid.decode()) for sid in updated_stock_ids_bytes]
        logger.info(f"Checking subscriptions for [stock]{len(updated_stock_ids)}[/stock] updated stocks")
        console.print(f"[cyan]Checking {len(updated_stock_ids)} updated stocks...[/cyan]")

        # Clear Redis Set after reading
        await redis_pool.delete(REDIS_INDICATOR_UPDATED_KEY)

        # Step 2: Query subscriptions with indicators
        async with SessionFactory() as db:
            # Build query for subscriptions of updated stocks
            stmt = (
                select(IndicatorSubscription)
                .where(
                    and_(
                        IndicatorSubscription.stock_id.in_(updated_stock_ids),
                        IndicatorSubscription.is_deleted.is_(False),
                        IndicatorSubscription.is_active.is_(True),
                        or_(
                            IndicatorSubscription.cooldown_end_at.is_(None),
                            IndicatorSubscription.cooldown_end_at < datetime.now(timezone.utc),
                        ),
                    )
                )
                .options(
                    selectinload(IndicatorSubscription.stock),
                    selectinload(IndicatorSubscription.user),
                )
            )

            result_subscriptions = await db.execute(stmt)
            subscriptions = list(result_subscriptions.scalars().all())

            if not subscriptions:
                logger.info("No active subscriptions without cooldown for updated stocks")
                console.print("[info]No subscriptions to check[/info]")
                result["success"] = True
                return result

            logger.info(f"Found [stock]{len(subscriptions)}[/stock] subscriptions to evaluate")
            console.print(f"[cyan]Evaluating {len(subscriptions)} subscriptions...[/cyan]")

            # Step 3: Get indicators for these stocks
            stock_ids_with_subs = [sub.stock_id for sub in subscriptions]

            stmt_indicators = (
                select(StockIndicator)
                .where(StockIndicator.stock_id.in_(stock_ids_with_subs))
            )
            result_indicators = await db.execute(stmt_indicators)
            indicators = list(result_indicators.scalars().all())

            # Build indicators map: {stock_id: {indicator_key: data}}
            indicators_map: dict[int, dict[str, dict]] = {}
            for ind in indicators:
                if ind.stock_id not in indicators_map:
                    indicators_map[ind.stock_id] = {}
                indicators_map[ind.stock_id][ind.indicator_key] = ind.data

            result["stocks_checked"] = len(updated_stock_ids)
            result["subscriptions_evaluated"] = len(subscriptions)

            # Step 4: Evaluate each subscription
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console,
            ) as progress:
                task = progress.add_task("[cyan]Evaluating conditions...", total=len(subscriptions))

                for sub in subscriptions:
                    try:
                        # Evaluate condition group
                        triggered, triggered_value = await evaluate_subscription(
                            sub, indicators_map.get(sub.stock_id, {})
                        )

                        if triggered:
                            result["conditions_triggered"] += 1

                            # Send notification
                            await send_notification(db, sub, triggered_value)
                            result["notifications_sent"] += 1

                            logger.info(
                                f"Subscription [stock]{sub.id}[/stock] triggered "
                                f"for stock [job]{sub.stock.symbol}[/job], "
                                f"value=[success]{triggered_value}[/success]"
                            )
                            console.print(
                                f"[success]✓ Subscription {sub.id} triggered ({triggered_value})[/success]"
                            )

                        progress.advance(task)

                    except Exception as e:
                        error_msg = f"Subscription {sub.id}: {str(e)}"
                        logger.error(f"[error]{error_msg}[/error]", exc_info=True)
                        result["errors"].append(error_msg)
                        progress.advance(task)
                        continue

        result["success"] = True

        # Print summary table
        table = Table(
            title="Subscription Check Summary",
            show_header=True,
            header_style="bold cyan"
        )
        table.add_column("Metric", style="dim")
        table.add_column("Count", justify="right")
        table.add_row("Stocks Checked", str(result["stocks_checked"]))
        table.add_row("Subscriptions Evaluated", str(result["subscriptions_evaluated"]))
        table.add_row("Conditions Triggered", str(result["conditions_triggered"]))
        table.add_row("Notifications Sent", str(result["notifications_sent"]))
        table.add_row("Errors", str(len(result["errors"])))
        console.print(table)

        logger.info(
            f"[success]check_indicator_subscriptions completed[/success]: "
            f"checked [stock]{result['stocks_checked']}[/stock] stocks, "
            f"evaluated [job]{result['subscriptions_evaluated']}[/job] subscriptions, "
            f"triggered [success]{result['conditions_triggered']}[/success] conditions"
        )

    except Exception as e:
        result["errors"].append(f"Job error: {str(e)}")
        logger.error(f"[error]check_indicator_subscriptions job failed: {e}[/error]", exc_info=True)
        result["success"] = False

    return result


async def evaluate_subscription(
    subscription: IndicatorSubscription,
    indicators: dict[str, dict],
) -> tuple[bool, Decimal | None]:
    """Evaluate subscription condition group against current indicator values.

    Args:
        subscription: IndicatorSubscription entity
        indicators: Dict of indicator_key -> data for the stock

    Returns:
        tuple[bool, Decimal | None]: (triggered, triggered_value)
    """
    condition_group = subscription.condition_group
    logic = condition_group.get("logic", "and")
    conditions = condition_group.get("conditions", [])

    triggered_values = []

    for condition in conditions:
        ind_type = condition.get("indicator_type")
        operator = condition.get("operator")
        target_value = Decimal(str(condition.get("target_value")))
        timeframe = condition.get("timeframe", "D")
        period = condition.get("period")

        # Build indicator key
        indicator_key = build_indicator_key(ind_type, timeframe, period)

        if not indicator_key:
            # Price indicator - skip (not in stock_indicator table)
            continue

        # Get current indicator value
        indicator_data = indicators.get(indicator_key)
        if not indicator_data:
            logger.warning(
                f"Indicator [warning]{indicator_key}[/warning] not found "
                f"for stock [stock]{subscription.stock_id}[/stock]"
            )
            continue

        current_value = extract_indicator_value(ind_type, indicator_data)
        if current_value is None:
            continue

        # Compare values
        condition_triggered = compare_values(current_value, operator, target_value)

        if condition_triggered:
            triggered_values.append(current_value)

        # AND logic: all conditions must trigger
        # OR logic: any condition triggers
        if logic == "and" and not condition_triggered:
            return False, None
        elif logic == "or" and condition_triggered:
            return True, current_value

    # For AND logic: all conditions passed
    # For OR logic: no conditions triggered
    if logic == "and" and len(triggered_values) == len(conditions):
        # Return first triggered value (or average?)
        return True, triggered_values[0]
    elif logic == "or":
        return False, None

    return False, None


def build_indicator_key(indicator_type: str, timeframe: str, period: int | None) -> str | None:
    """Build indicator key from subscription condition.

    Args:
        indicator_type: Indicator type (rsi, sma, macd, kd)
        timeframe: Timeframe (D or W)
        period: Period for RSI/SMA

    Returns:
        str | None: Indicator key or None for price
    """
    from src.stock_indicator.schema import IndicatorType, generate_indicator_key

    if indicator_type.lower() == "price":
        return None

    try:
        ind_type = IndicatorType(indicator_type.lower())
    except ValueError:
        return None

    # Default periods
    default_params = {
        IndicatorType.KDJ: [9, 3, 3],
        IndicatorType.MACD: [12, 26, 9],
    }

    if ind_type in default_params:
        return generate_indicator_key(ind_type, default_params[ind_type], timeframe)
    elif ind_type in (IndicatorType.RSI, IndicatorType.SMA):
        params = [period] if period else [14] if ind_type == IndicatorType.RSI else [20]
        return generate_indicator_key(ind_type, params, timeframe)

    return None


def extract_indicator_value(indicator_type: str, indicator_data: dict) -> Decimal | None:
    """Extract indicator value from indicator data dict.

    Args:
        indicator_type: Indicator type
        indicator_data: Indicator data dict

    Returns:
        Decimal | None: Extracted value
    """
    try:
        ind_type_lower = indicator_type.lower()

        if ind_type_lower == "rsi":
            # RSI: data.value
            value = indicator_data.get("value")
            return Decimal(str(value)) if value is not None else None

        elif ind_type_lower == "sma":
            # SMA: data.value
            value = indicator_data.get("value")
            return Decimal(str(value)) if value is not None else None

        elif ind_type_lower == "macd":
            # MACD: data.histogram (MACD - Signal)
            histogram = indicator_data.get("histogram")
            return Decimal(str(histogram)) if histogram is not None else None

        elif ind_type_lower in ("kd", "kdj"):
            # KDJ: data.k (default K value)
            k_value = indicator_data.get("k")
            return Decimal(str(k_value)) if k_value is not None else None

        return None

    except Exception as e:
        logger.error(f"Failed to extract indicator value: {e}")
        return None


def compare_values(current: Decimal, operator: str, target: Decimal) -> bool:
    """Compare current value against target using operator.

    Args:
        current: Current indicator value
        operator: Comparison operator
        target: Target threshold value

    Returns:
        bool: Whether condition is met
    """
    if operator == ">":
        return current > target
    elif operator == "<":
        return current < target
    elif operator == ">=":
        return current >= target
    elif operator == "<=":
        return current <= target
    elif operator == "==":
        return current == target
    elif operator == "!=":
        return current != target

    return False


async def send_notification(
    db: AsyncSession,
    subscription: IndicatorSubscription,
    triggered_value: Decimal,
) -> None:
    """Send notification for triggered subscription.

    Args:
        db: Database session
        subscription: IndicatorSubscription entity
        triggered_value: Value that triggered the condition
    """
    # Insert notification history
    notification = NotificationHistory(
        user_id=subscription.user_id,
        indicator_subscription_id=subscription.id,
        triggered_value=triggered_value,
        send_status="pending",
        triggered_at=datetime.now(timezone.utc),
    )
    db.add(notification)

    # Update subscription status
    subscription.is_triggered = True
    cooldown_hours = settings.SUBSCRIPTION_COOLDOWN_HOURS
    subscription.cooldown_end_at = datetime.now(timezone.utc) + timedelta(hours=cooldown_hours)

    await db.commit()

    logger.info(
        f"[success]Notification recorded[/success]: "
        f"user=[stock]{subscription.user_id}[/stock], "
        f"subscription=[job]{subscription.id}[/job], "
        f"value=[success]{triggered_value}[/success]"
    )