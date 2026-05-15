"""Tests for StockIndicator functionality."""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.stock_indicator.calculator import (
    calculate_indicators_from_prices,
    calculate_kdj,
    calculate_macd,
    calculate_rsi,
    calculate_sma,
)
from src.stock_indicator.model import StockIndicator
from src.stock_indicator.schema import (
    IndicatorType,
    KDJData,
    MACDData,
    RSIData,
    SMAData,
    generate_indicator_key,
    parse_indicator_key,
    StockIndicatorUpsert,
)
from src.stock_indicator.service import StockIndicatorService
from src.stocks.model import DailyPrice, Stock
from src.subscriptions.model import IndicatorSubscription


class TestIndicatorKeyGeneration:
    """Tests for indicator key generation and parsing"""

    def test_generate_rsi_key(self):
        """Test RSI indicator key generation"""
        key = generate_indicator_key(IndicatorType.RSI, [14])
        assert key == "RSI_14"

    def test_generate_sma_key(self):
        """Test SMA indicator key generation"""
        key = generate_indicator_key(IndicatorType.SMA, [20])
        assert key == "SMA_20"

    def test_generate_kdj_key(self):
        """Test KDJ indicator key generation"""
        key = generate_indicator_key(IndicatorType.KDJ, [9, 3, 3])
        assert key == "KDJ_9_3_3"

    def test_generate_macd_key(self):
        """Test MACD indicator key generation"""
        key = generate_indicator_key(IndicatorType.MACD, [12, 26, 9])
        assert key == "MACD_12_26_9"

    def test_parse_rsi_key(self):
        """Test parsing RSI indicator key"""
        ind_type, params = parse_indicator_key("RSI_14")
        assert ind_type == IndicatorType.RSI
        assert params == [14]

    def test_parse_macd_key(self):
        """Test parsing MACD indicator key"""
        ind_type, params = parse_indicator_key("MACD_12_26_9")
        assert ind_type == IndicatorType.MACD
        assert params == [12, 26, 9]

    def test_parse_invalid_key(self):
        """Test parsing invalid indicator key raises error"""
        with pytest.raises(ValueError):
            parse_indicator_key("INVALID_123")


class TestRSICalculation:
    """Tests for RSI indicator calculation"""

    def test_calculate_rsi_sufficient_data(self):
        """Test RSI calculation with sufficient price data"""
        # Generate sample prices (upward trend)
        prices = [Decimal(str(100 + i * 2)) for i in range(20)]

        rsi = calculate_rsi(prices, period=14)

        assert rsi is not None
        assert rsi.value >= 0
        assert rsi.value <= 100
        # Upward trend should have RSI > 50
        assert rsi.value > Decimal(50)

    def test_calculate_rsi_insufficient_data(self):
        """Test RSI returns None with insufficient data"""
        prices = [Decimal("100"), Decimal("102")]

        rsi = calculate_rsi(prices, period=14)

        assert rsi is None

    def test_calculate_rsi_constant_prices(self):
        """Test RSI with constant prices (no change)"""
        prices = [Decimal("100") for i in range(20)]

        rsi = calculate_rsi(prices, period=14)

        # RSI should be undefined or 50 when no changes
        # Implementation may vary, just check it returns a valid value or None
        if rsi is not None:
            assert rsi.value >= 0
            assert rsi.value <= 100


class TestSMACalculation:
    """Tests for SMA indicator calculation"""

    def test_calculate_sma_sufficient_data(self):
        """Test SMA calculation with sufficient price data"""
        prices = [Decimal("100"), Decimal("102"), Decimal("104"), Decimal("106"), Decimal("108")]

        sma = calculate_sma(prices, period=5)

        assert sma is not None
        assert sma.value == Decimal("104")  # (100+102+104+106+108)/5

    def test_calculate_sma_insufficient_data(self):
        """Test SMA returns None with insufficient data"""
        prices = [Decimal("100"), Decimal("102")]

        sma = calculate_sma(prices, period=10)

        assert sma is None

    def test_calculate_sma_uses_last_n_prices(self):
        """Test SMA uses only last N prices when more data available"""
        prices = [Decimal("50"), Decimal("60"), Decimal("100"), Decimal("102"), Decimal("104")]

        sma = calculate_sma(prices, period=3)

        assert sma is not None
        assert sma.value == Decimal("102")  # (100+102+104)/3


class TestKDJCalculation:
    """Tests for KDJ indicator calculation"""

    def test_calculate_kdj_sufficient_data(self):
        """Test KDJ calculation with sufficient OHLC data"""
        # Generate sample OHLC data
        ohlcs = [
            (Decimal("100"), Decimal("110"), Decimal("95"), Decimal("105")) for i in range(15)
        ]

        kdj = calculate_kdj(ohlcs, k_period=9, d_period=3, j_period=3)

        assert kdj is not None
        assert kdj.k >= 0
        assert kdj.k <= 100
        assert kdj.d >= 0
        assert kdj.d <= 100

    def test_calculate_kdj_insufficient_data(self):
        """Test KDJ returns None with insufficient data"""
        ohlcs = [
            (Decimal("100"), Decimal("110"), Decimal("95"), Decimal("105")) for i in range(5)
        ]

        kdj = calculate_kdj(ohlcs, k_period=9)

        assert kdj is None

    def test_calculate_kdj_j_value_formula(self):
        """Test KDJ J value calculation (J = 3K - 2D)"""
        ohlcs = [
            (Decimal("100"), Decimal("110"), Decimal("95"), Decimal("105")) for i in range(15)
        ]

        kdj = calculate_kdj(ohlcs)

        if kdj:
            expected_j = kdj.k * Decimal(3) - kdj.d * Decimal(2)
            # Allow some rounding difference
            assert abs(kdj.j - expected_j) < Decimal("0.1")


class TestMACDCalculation:
    """Tests for MACD indicator calculation"""

    def test_calculate_macd_sufficient_data(self):
        """Test MACD calculation with sufficient price data"""
        # Generate sample prices
        prices = [Decimal(str(100 + i * 0.5)) for i in range(40)]

        macd = calculate_macd(prices, fast_period=12, slow_period=26, signal_period=9)

        assert macd is not None
        assert macd.macd is not None
        assert macd.signal is not None
        assert macd.histogram is not None
        # Histogram should be MACD - Signal
        expected_histogram = macd.macd - macd.signal
        assert abs(macd.histogram - expected_histogram) < Decimal("0.01")

    def test_calculate_macd_insufficient_data(self):
        """Test MACD returns None with insufficient data"""
        prices = [Decimal("100"), Decimal("102")]

        macd = calculate_macd(prices)

        assert macd is None


class TestCalculateIndicatorsFromPrices:
    """Tests for batch indicator calculation"""

    def test_calculate_default_indicators(self):
        """Test calculating default set of indicators"""
        closes = [Decimal(str(100 + i)) for i in range(40)]
        ohlcs = [
            (Decimal("100"), Decimal("105"), Decimal("95"), Decimal(str(100 + i)))
            for i in range(40)
        ]

        results = calculate_indicators_from_prices(closes, ohlcs)

        assert "RSI_14" in results
        assert "SMA_20" in results
        assert "KDJ_9_3_3" in results
        assert "MACD_12_26_9" in results

    def test_calculate_specific_indicators(self):
        """Test calculating specific indicator keys"""
        closes = [Decimal(str(100 + i)) for i in range(40)]
        indicator_keys = ["RSI_14", "SMA_20"]

        results = calculate_indicators_from_prices(closes, indicator_keys=indicator_keys)

        assert "RSI_14" in results
        assert "SMA_20" in results
        assert "KDJ_9_3_3" not in results  # Not requested

    def test_calculate_insufficient_data(self):
        """Test calculation with insufficient data returns empty dict"""
        closes = [Decimal("100")]
        indicator_keys = ["RSI_14"]

        results = calculate_indicators_from_prices(closes, indicator_keys=indicator_keys)

        assert len(results) == 0


class TestStockIndicatorService:
    """Tests for StockIndicatorService"""

    @pytest.mark.asyncio
    async def test_upsert_indicator_insert(self, db_session: AsyncSession):
        """Test inserting new indicator"""
        # Create stock
        stock = Stock(symbol="2330.TW", name="台積電", is_active=True)
        db_session.add(stock)
        await db_session.commit()
        await db_session.refresh(stock)

        # Upsert indicator
        indicator = await StockIndicatorService.upsert_indicator(
            db_session,
            stock.id,
            "RSI_14",
            {"value": 65.5},
        )

        assert indicator.id is not None
        assert indicator.stock_id == stock.id
        assert indicator.indicator_key == "RSI_14"
        assert indicator.data["value"] == 65.5

    @pytest.mark.asyncio
    async def test_upsert_indicator_update(self, db_session: AsyncSession):
        """Test updating existing indicator"""
        # Create stock
        stock = Stock(symbol="2330.TW", name="台積電", is_active=True)
        db_session.add(stock)
        await db_session.commit()
        await db_session.refresh(stock)

        # Insert initial indicator
        await StockIndicatorService.upsert_indicator(
            db_session,
            stock.id,
            "RSI_14",
            {"value": 60.0},
        )

        # Update with new value
        updated = await StockIndicatorService.upsert_indicator(
            db_session,
            stock.id,
            "RSI_14",
            {"value": 70.0},
        )

        assert updated.data["value"] == 70.0

        # Verify only one record exists (unique constraint)
        indicators = await StockIndicatorService.get_by_stock(db_session, stock.id)
        assert len(indicators) == 1

    @pytest.mark.asyncio
    async def test_bulk_upsert_indicators(self, db_session: AsyncSession):
        """Test bulk upserting multiple indicators"""
        # Create stock
        stock = Stock(symbol="2330.TW", name="台積電", is_active=True)
        db_session.add(stock)
        await db_session.commit()
        await db_session.refresh(stock)

        # Bulk upsert
        indicators_data = [
            StockIndicatorUpsert(
                stock_id=stock.id,
                indicator_key="RSI_14",
                data={"value": 65.0},
            ),
            StockIndicatorUpsert(
                stock_id=stock.id,
                indicator_key="SMA_20",
                data={"value": 150.0},
            ),
        ]

        count = await StockIndicatorService.bulk_upsert_indicators(db_session, indicators_data)

        assert count == 2

        # Verify both exist
        indicators = await StockIndicatorService.get_by_stock(db_session, stock.id)
        assert len(indicators) == 2

    @pytest.mark.asyncio
    async def test_get_by_stock(self, db_session: AsyncSession):
        """Test getting all indicators for a stock"""
        # Create stock
        stock = Stock(symbol="2330.TW", name="台積電", is_active=True)
        db_session.add(stock)
        await db_session.commit()
        await db_session.refresh(stock)

        # Insert multiple indicators
        await StockIndicatorService.upsert_indicator(
            db_session, stock.id, "RSI_14", {"value": 65.0}
        )
        await StockIndicatorService.upsert_indicator(
            db_session, stock.id, "SMA_20", {"value": 150.0}
        )
        await StockIndicatorService.upsert_indicator(
            db_session, stock.id, "MACD_12_26_9", {"macd": 0.5, "signal": 0.3, "histogram": 0.2}
        )

        indicators = await StockIndicatorService.get_by_stock(db_session, stock.id)

        assert len(indicators) == 3
        keys = [i.indicator_key for i in indicators]
        assert "RSI_14" in keys
        assert "SMA_20" in keys
        assert "MACD_12_26_9" in keys

    @pytest.mark.asyncio
    async def test_get_by_type(self, db_session: AsyncSession):
        """Test getting all stocks with specific indicator type"""
        # Create stocks
        stock1 = Stock(symbol="2330.TW", name="台積電", is_active=True)
        stock2 = Stock(symbol="2317.TW", name="鴻海", is_active=True)
        db_session.add_all([stock1, stock2])
        await db_session.commit()
        await db_session.refresh(stock1)
        await db_session.refresh(stock2)

        # Insert RSI for both stocks
        await StockIndicatorService.upsert_indicator(
            db_session, stock1.id, "RSI_14", {"value": 65.0}
        )
        await StockIndicatorService.upsert_indicator(
            db_session, stock2.id, "RSI_14", {"value": 70.0}
        )

        # Get all RSI_14 indicators
        indicators = await StockIndicatorService.get_by_type(db_session, "RSI_14")

        assert len(indicators) == 2

    @pytest.mark.asyncio
    async def test_get_by_stock_and_key(self, db_session: AsyncSession):
        """Test getting specific indicator for stock"""
        # Create stock
        stock = Stock(symbol="2330.TW", name="台積電", is_active=True)
        db_session.add(stock)
        await db_session.commit()
        await db_session.refresh(stock)

        # Insert indicator
        await StockIndicatorService.upsert_indicator(
            db_session, stock.id, "RSI_14", {"value": 65.0}
        )

        # Get specific indicator
        indicator = await StockIndicatorService.get_by_stock_and_key(
            db_session, stock.id, "RSI_14"
        )

        assert indicator is not None
        assert indicator.indicator_key == "RSI_14"
        assert indicator.data["value"] == 65.0

        # Get non-existent indicator
        missing = await StockIndicatorService.get_by_stock_and_key(
            db_session, stock.id, "SMA_20"
        )

        assert missing is None

    @pytest.mark.asyncio
    async def test_delete_by_stock(self, db_session: AsyncSession):
        """Test deleting all indicators for a stock"""
        # Create stock
        stock = Stock(symbol="2330.TW", name="台積電", is_active=True)
        db_session.add(stock)
        await db_session.commit()
        await db_session.refresh(stock)

        # Insert indicators
        await StockIndicatorService.upsert_indicator(
            db_session, stock.id, "RSI_14", {"value": 65.0}
        )
        await StockIndicatorService.upsert_indicator(
            db_session, stock.id, "SMA_20", {"value": 150.0}
        )

        # Delete all
        count = await StockIndicatorService.delete_by_stock(db_session, stock.id)

        assert count == 2

        # Verify deletion
        indicators = await StockIndicatorService.get_by_stock(db_session, stock.id)
        assert len(indicators) == 0

    @pytest.mark.asyncio
    async def test_get_stocks_with_indicators(self, db_session: AsyncSession):
        """Test getting list of stock IDs with indicator subscriptions"""
        from src.plans.model import LevelConfig, Plan
        from src.users.model import User
        from datetime import datetime, timezone, timedelta
        import bcrypt

        # Create user and plan
        hashed = bcrypt.hashpw("password".encode(), bcrypt.gensalt()).decode()
        user = User(email="test@example.com", hashed_password=hashed)
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        level = LevelConfig(
            level=1,
            name="Regular",
            monthly_price=Decimal("0"),
            yearly_price=Decimal("0"),
            max_subscriptions=10,
            max_alerts=10,
            is_purchasable=False,
        )
        db_session.add(level)
        await db_session.commit()

        plan = Plan(
            user_id=user.id,
            level=1,
            billing_cycle="monthly",
            price=Decimal("0"),
            due_date=datetime.now(timezone.utc) + timedelta(days=30),
            is_active=True,
        )
        db_session.add(plan)

        # Create stocks
        stock1 = Stock(symbol="2330.TW", name="台積電", is_active=True)
        stock2 = Stock(symbol="2317.TW", name="鴻海", is_active=True)
        stock3 = Stock(symbol="2454.TW", name="聯發科", is_active=True)
        db_session.add_all([stock1, stock2, stock3])
        await db_session.commit()

        # Create indicator subscriptions for stock1 and stock2
        sub1 = IndicatorSubscription(
            user_id=user.id,
            stock_id=stock1.id,
            title="RSI Alert",
            message="RSI trigger",
            signal_type="buy",
            timeframe="D",
            indicator_type="rsi",
            operator=">",
            target_value=Decimal("70"),
            is_active=True,
        )
        sub2 = IndicatorSubscription(
            user_id=user.id,
            stock_id=stock2.id,
            title="MACD Alert",
            message="MACD trigger",
            signal_type="buy",
            timeframe="D",
            indicator_type="macd",
            operator=">",
            target_value=Decimal("0"),
            is_active=True,
        )
        db_session.add_all([sub1, sub2])
        await db_session.commit()

        # Get stocks with indicator subscriptions
        stock_ids = await StockIndicatorService.get_stocks_with_indicators(db_session)

        assert stock1.id in stock_ids
        assert stock2.id in stock_ids
        assert stock3.id not in stock_ids  # No subscription

    @pytest.mark.asyncio
    async def test_get_required_indicator_keys(self, db_session: AsyncSession):
        """Test getting required indicator keys for a stock"""
        from src.plans.model import LevelConfig, Plan
        from src.users.model import User
        from datetime import datetime, timezone, timedelta
        import bcrypt

        # Create user and plan
        hashed = bcrypt.hashpw("password".encode(), bcrypt.gensalt()).decode()
        user = User(email="test2@example.com", hashed_password=hashed)
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        level = LevelConfig(
            level=1,
            name="Regular",
            monthly_price=Decimal("0"),
            yearly_price=Decimal("0"),
            max_subscriptions=10,
            max_alerts=10,
            is_purchasable=False,
        )
        db_session.add(level)
        await db_session.commit()

        plan = Plan(
            user_id=user.id,
            level=1,
            billing_cycle="monthly",
            price=Decimal("0"),
            due_date=datetime.now(timezone.utc) + timedelta(days=30),
            is_active=True,
        )
        db_session.add(plan)

        # Create stock
        stock = Stock(symbol="2330.TW", name="台積電", is_active=True)
        db_session.add(stock)
        await db_session.commit()
        await db_session.refresh(stock)

        # Create subscriptions with different indicators
        sub_rsi = IndicatorSubscription(
            user_id=user.id,
            stock_id=stock.id,
            title="RSI 14 Alert",
            message="RSI trigger",
            signal_type="buy",
            timeframe="D",
            indicator_type="rsi",
            operator=">",
            target_value=Decimal("70"),
            period=14,
            is_active=True,
        )
        sub_macd = IndicatorSubscription(
            user_id=user.id,
            stock_id=stock.id,
            title="MACD Alert",
            message="MACD trigger",
            signal_type="buy",
            timeframe="D",
            indicator_type="macd",
            operator=">",
            target_value=Decimal("0"),
            is_active=True,
        )
        db_session.add_all([sub_rsi, sub_macd])
        await db_session.commit()

        # Get required indicator keys
        keys = await StockIndicatorService.get_required_indicator_keys(db_session, stock.id)

        assert "RSI_14" in keys
        assert "MACD_12_26_9" in keys


class TestStockIndicatorModel:
    """Tests for StockIndicator SQLAlchemy model"""

    @pytest.mark.asyncio
    async def test_model_creation(self, db_session: AsyncSession):
        """Test creating StockIndicator model instance"""
        # Create stock
        stock = Stock(symbol="2330.TW", name="台積電", is_active=True)
        db_session.add(stock)
        await db_session.commit()
        await db_session.refresh(stock)

        # Create indicator
        indicator = StockIndicator(
            stock_id=stock.id,
            indicator_key="RSI_14",
            data={"value": 65.5},
        )
        db_session.add(indicator)
        await db_session.commit()
        await db_session.refresh(indicator)

        assert indicator.id is not None
        assert indicator.stock_id == stock.id
        assert indicator.indicator_key == "RSI_14"
        assert indicator.created_at is not None
        assert indicator.updated_at is not None

    @pytest.mark.asyncio
    async def test_unique_constraint(self, db_session: AsyncSession):
        """Test unique constraint on (stock_id, indicator_key)"""
        from sqlalchemy.exc import IntegrityError

        # Create stock
        stock = Stock(symbol="2330.TW", name="台積電", is_active=True)
        db_session.add(stock)
        await db_session.commit()
        await db_session.refresh(stock)

        # Create first indicator
        indicator1 = StockIndicator(
            stock_id=stock.id,
            indicator_key="RSI_14",
            data={"value": 60.0},
        )
        db_session.add(indicator1)
        await db_session.commit()

        # Try to create duplicate (same stock_id and indicator_key)
        indicator2 = StockIndicator(
            stock_id=stock.id,
            indicator_key="RSI_14",
            data={"value": 70.0},
        )
        db_session.add(indicator2)

        with pytest.raises(IntegrityError):
            await db_session.commit()

    @pytest.mark.asyncio
    async def test_relationship_with_stock(self, db_session: AsyncSession):
        """Test StockIndicator relationship with Stock"""
        # Create stock
        stock = Stock(symbol="2330.TW", name="台積電", is_active=True)
        db_session.add(stock)
        await db_session.commit()
        await db_session.refresh(stock)

        # Create indicator
        indicator = StockIndicator(
            stock_id=stock.id,
            indicator_key="RSI_14",
            data={"value": 65.0},
        )
        db_session.add(indicator)
        await db_session.commit()
        await db_session.refresh(indicator)

        # Test relationship
        assert indicator.stock is not None
        assert indicator.stock.symbol == "2330.TW"