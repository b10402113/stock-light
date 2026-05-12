"""Tests for DailyPrice endpoints."""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.stocks.model import DailyPrice, Stock
from src.stocks.service import DailyPriceService


class TestDailyPriceRouter:
    """Tests for DailyPrice router endpoints"""

    @pytest.mark.asyncio
    async def test_list_daily_prices_success(self, client: AsyncClient, db_session: AsyncSession):
        """Test listing daily prices for a stock"""
        # Create stock
        stock = Stock(symbol="2330.TW", name="台積電", is_active=True)
        db_session.add(stock)
        await db_session.commit()
        await db_session.refresh(stock)

        # Create daily prices
        prices = []
        for i in range(5):
            p = DailyPrice(
                stock_id=stock.id,
                date=date.today() - timedelta(days=i),
                open=Decimal("600.00"),
                high=Decimal("650.00"),
                low=Decimal("590.00"),
                close=Decimal("630.00"),
                volume=1000000 + i * 10000,
            )
            prices.append(p)
            db_session.add(p)
        await db_session.commit()

        # List prices
        response = await client.get(f"/stocks/{stock.id}/prices")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert len(data["data"]["data"]) == 5
        assert data["data"]["has_more"] is False
        assert data["data"]["next_cursor"] is None

    @pytest.mark.asyncio
    async def test_list_daily_prices_stock_not_found(self, client: AsyncClient):
        """Test listing prices for non-existent stock"""
        response = await client.get("/stocks/99999/prices")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_list_daily_prices_with_date_range(self, client: AsyncClient, db_session: AsyncSession):
        """Test listing prices within date range"""
        # Create stock
        stock = Stock(symbol="2330.TW", name="台積電", is_active=True)
        db_session.add(stock)
        await db_session.commit()
        await db_session.refresh(stock)

        # Create prices for 10 days
        for i in range(10):
            p = DailyPrice(
                stock_id=stock.id,
                date=date.today() - timedelta(days=i),
                open=Decimal("600.00"),
                high=Decimal("650.00"),
                low=Decimal("590.00"),
                close=Decimal("630.00"),
                volume=1000000,
            )
            db_session.add(p)
        await db_session.commit()

        # Query specific date range
        start_date = (date.today() - timedelta(days=5)).isoformat()
        end_date = (date.today() - timedelta(days=2)).isoformat()

        response = await client.get(
            f"/stocks/{stock.id}/prices",
            params={"start_date": start_date, "end_date": end_date},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]["data"]) == 4  # days 2, 3, 4, 5

    @pytest.mark.asyncio
    async def test_list_daily_prices_with_pagination(self, client: AsyncClient, db_session: AsyncSession):
        """Test listing prices with keyset pagination"""
        # Create stock
        stock = Stock(symbol="2330.TW", name="台積電", is_active=True)
        db_session.add(stock)
        await db_session.commit()
        await db_session.refresh(stock)

        # Create 10 days of prices
        for i in range(10):
            p = DailyPrice(
                stock_id=stock.id,
                date=date.today() - timedelta(days=i),
                open=Decimal("600.00"),
                high=Decimal("650.00"),
                low=Decimal("590.00"),
                close=Decimal("630.00"),
                volume=1000000,
            )
            db_session.add(p)
        await db_session.commit()

        # Get first page
        response = await client.get(f"/stocks/{stock.id}/prices", params={"limit": 5})

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]["data"]) == 5
        assert data["data"]["has_more"] is True
        assert data["data"]["next_cursor"] is not None

        # Get next page using cursor (returned as string)
        cursor_str = data["data"]["next_cursor"]
        response2 = await client.get(
            f"/stocks/{stock.id}/prices",
            params={"limit": 5, "cursor": cursor_str},
        )

        assert response2.status_code == 200
        data2 = response2.json()
        # Second page should have remaining prices (5 more)
        assert len(data2["data"]["data"]) >= 1

    @pytest.mark.asyncio
    async def test_bulk_insert_daily_prices_success(self, client: AsyncClient, db_session: AsyncSession):
        """Test bulk inserting daily prices"""
        # Create stock
        stock = Stock(symbol="2330.TW", name="台積電", is_active=True)
        db_session.add(stock)
        await db_session.commit()
        await db_session.refresh(stock)

        # Bulk insert prices
        prices_data = []
        for i in range(5):
            prices_data.append({
                "date": (date.today() - timedelta(days=i)).isoformat(),
                "open": "600.00",
                "high": "650.00",
                "low": "590.00",
                "close": "630.00",
                "volume": 1000000,
            })

        response = await client.post(
            f"/stocks/{stock.id}/prices",
            json={"prices": prices_data},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["count"] == 5

    @pytest.mark.asyncio
    async def test_bulk_insert_daily_prices_upsert(self, client: AsyncClient, db_session: AsyncSession):
        """Test bulk insert updates existing records (upsert)"""
        # Create stock
        stock = Stock(symbol="2330.TW", name="台積電", is_active=True)
        db_session.add(stock)
        await db_session.commit()
        await db_session.refresh(stock)

        # Insert initial price
        initial_date = date.today()
        p1 = DailyPrice(
            stock_id=stock.id,
            date=initial_date,
            open=Decimal("600.00"),
            high=Decimal("650.00"),
            low=Decimal("590.00"),
            close=Decimal("630.00"),
            volume=1000000,
        )
        db_session.add(p1)
        await db_session.commit()

        # Bulk insert with same date (should update)
        response = await client.post(
            f"/stocks/{stock.id}/prices",
            json={
                "prices": [
                    {
                        "date": initial_date.isoformat(),
                        "open": "700.00",
                        "high": "750.00",
                        "low": "690.00",
                        "close": "730.00",
                        "volume": 2000000,
                    }
                ]
            },
        )

        assert response.status_code == 201

        # Verify price was updated by querying fresh from API
        response2 = await client.get(f"/stocks/{stock.id}/prices", params={"limit": 1})
        data = response2.json()
        assert data["data"]["data"][0]["open"] == "700.00"
        assert data["data"]["data"][0]["volume"] == 2000000

    @pytest.mark.asyncio
    async def test_bulk_insert_stock_not_found(self, client: AsyncClient):
        """Test bulk insert for non-existent stock"""
        response = await client.post(
            "/stocks/99999/prices",
            json={
                "prices": [
                    {
                        "date": date.today().isoformat(),
                        "open": "600.00",
                        "high": "650.00",
                        "low": "590.00",
                        "close": "630.00",
                        "volume": 1000000,
                    }
                ]
            },
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_bulk_insert_invalid_ohlcv(self, client: AsyncClient, db_session: AsyncSession):
        """Test bulk insert with invalid OHLCV (high < low)"""
        # Create stock
        stock = Stock(symbol="2330.TW", name="台積電", is_active=True)
        db_session.add(stock)
        await db_session.commit()
        await db_session.refresh(stock)

        # Insert with high < low
        response = await client.post(
            f"/stocks/{stock.id}/prices",
            json={
                "prices": [
                    {
                        "date": date.today().isoformat(),
                        "open": "600.00",
                        "high": "580.00",  # high < low - invalid
                        "low": "590.00",
                        "close": "630.00",
                        "volume": 1000000,
                    }
                ]
            },
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_bulk_insert_empty_prices(self, client: AsyncClient, db_session: AsyncSession):
        """Test bulk insert with empty prices list"""
        # Create stock
        stock = Stock(symbol="2330.TW", name="台積電", is_active=True)
        db_session.add(stock)
        await db_session.commit()
        await db_session.refresh(stock)

        response = await client.post(
            f"/stocks/{stock.id}/prices",
            json={"prices": []},
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_get_moving_average_success(self, client: AsyncClient, db_session: AsyncSession):
        """Test calculating moving average"""
        # Create stock
        stock = Stock(symbol="2330.TW", name="台積電", is_active=True)
        db_session.add(stock)
        await db_session.commit()
        await db_session.refresh(stock)

        # Create 10 days of prices with ascending closes
        for i in range(10):
            p = DailyPrice(
                stock_id=stock.id,
                date=date.today() - timedelta(days=i),
                open=Decimal("600.00"),
                high=Decimal("650.00"),
                low=Decimal("590.00"),
                close=Decimal(f"{600 + i}.00"),  # Ascending closes
                volume=1000000,
            )
            db_session.add(p)
        await db_session.commit()

        # Calculate 5-day MA
        response = await client.get(f"/stocks/{stock.id}/ma/5")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["period"] == 5
        assert data["data"]["value"] is not None
        assert data["data"]["data_points"] == 5

    @pytest.mark.asyncio
    async def test_get_moving_average_insufficient_data(self, client: AsyncClient, db_session: AsyncSession):
        """Test calculating MA with insufficient data points"""
        # Create stock
        stock = Stock(symbol="2330.TW", name="台積電", is_active=True)
        db_session.add(stock)
        await db_session.commit()
        await db_session.refresh(stock)

        # Create only 3 days of prices
        for i in range(3):
            p = DailyPrice(
                stock_id=stock.id,
                date=date.today() - timedelta(days=i),
                open=Decimal("600.00"),
                high=Decimal("650.00"),
                low=Decimal("590.00"),
                close=Decimal("630.00"),
                volume=1000000,
            )
            db_session.add(p)
        await db_session.commit()

        # Request 200MA (insufficient data)
        response = await client.get(f"/stocks/{stock.id}/ma/200")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["value"] is None  # Insufficient data
        assert data["data"]["data_points"] == 3

    @pytest.mark.asyncio
    async def test_get_moving_average_no_data(self, client: AsyncClient, db_session: AsyncSession):
        """Test calculating MA when stock has no prices"""
        # Create stock without prices
        stock = Stock(symbol="2330.TW", name="台積電", is_active=True)
        db_session.add(stock)
        await db_session.commit()
        await db_session.refresh(stock)

        response = await client.get(f"/stocks/{stock.id}/ma/5")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["value"] is None
        assert data["data"]["data_points"] == 0

    @pytest.mark.asyncio
    async def test_get_moving_average_invalid_period(self, client: AsyncClient, db_session: AsyncSession):
        """Test calculating MA with invalid period"""
        # Create stock
        stock = Stock(symbol="2330.TW", name="台積電", is_active=True)
        db_session.add(stock)
        await db_session.commit()
        await db_session.refresh(stock)

        # Period out of range
        response = await client.get(f"/stocks/{stock.id}/ma/600")

        assert response.status_code == 400
        assert "between 1 and 500" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_moving_average_stock_not_found(self, client: AsyncClient):
        """Test calculating MA for non-existent stock"""
        response = await client.get("/stocks/99999/ma/5")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_moving_average_as_of_date(self, client: AsyncClient, db_session: AsyncSession):
        """Test calculating MA as of a specific date"""
        # Create stock
        stock = Stock(symbol="2330.TW", name="台積電", is_active=True)
        db_session.add(stock)
        await db_session.commit()
        await db_session.refresh(stock)

        # Create 10 days of prices
        for i in range(10):
            p = DailyPrice(
                stock_id=stock.id,
                date=date.today() - timedelta(days=i),
                open=Decimal("600.00"),
                high=Decimal("650.00"),
                low=Decimal("590.00"),
                close=Decimal(f"{600 + i}.00"),
                volume=1000000,
            )
            db_session.add(p)
        await db_session.commit()

        # Calculate MA as of 3 days ago
        as_of = (date.today() - timedelta(days=3)).isoformat()
        response = await client.get(
            f"/stocks/{stock.id}/ma/5",
            params={"as_of_date": as_of},
        )

        assert response.status_code == 200
        data = response.json()
        # JSON returns date as string
        assert data["data"]["date"] == as_of


class TestDailyPriceService:
    """Tests for DailyPriceService methods"""

    @pytest.mark.asyncio
    async def test_bulk_insert_new_records(self, db_session: AsyncSession):
        """Test bulk insert creates new records"""
        # Create stock
        stock = Stock(symbol="2330.TW", name="台積電", is_active=True)
        db_session.add(stock)
        await db_session.commit()
        await db_session.refresh(stock)

        # Prepare price data
        from src.stocks.schema import DailyPriceBase

        prices = [
            DailyPriceBase(
                date=date.today() - timedelta(days=i),
                open=Decimal("600.00"),
                high=Decimal("650.00"),
                low=Decimal("590.00"),
                close=Decimal("630.00"),
                volume=1000000,
            )
            for i in range(5)
        ]

        count = await DailyPriceService.bulk_insert_prices(db_session, stock.id, prices)

        assert count == 5

    @pytest.mark.asyncio
    async def test_bulk_insert_duplicate_dates_upsert(self, db_session: AsyncSession):
        """Test bulk insert with duplicate dates performs upsert"""
        # Create stock
        stock = Stock(symbol="2330.TW", name="台積電", is_active=True)
        db_session.add(stock)
        await db_session.commit()
        await db_session.refresh(stock)

        from src.stocks.schema import DailyPriceBase

        # Insert initial price
        initial_prices = [
            DailyPriceBase(
                date=date.today(),
                open=Decimal("600.00"),
                high=Decimal("650.00"),
                low=Decimal("590.00"),
                close=Decimal("630.00"),
                volume=1000000,
            )
        ]
        await DailyPriceService.bulk_insert_prices(db_session, stock.id, initial_prices)

        # Insert same date with different values
        updated_prices = [
            DailyPriceBase(
                date=date.today(),
                open=Decimal("700.00"),
                high=Decimal("750.00"),
                low=Decimal("690.00"),
                close=Decimal("730.00"),
                volume=2000000,
            )
        ]
        count = await DailyPriceService.bulk_insert_prices(db_session, stock.id, updated_prices)

        assert count == 1

        # Verify updated
        prices, _ = await DailyPriceService.get_prices_by_range(db_session, stock.id, limit=1)
        assert prices[0].open == Decimal("700.00")

    @pytest.mark.asyncio
    async def test_get_prices_by_range_descending(self, db_session: AsyncSession):
        """Test getting prices by range in descending order"""
        # Create stock
        stock = Stock(symbol="2330.TW", name="台積電", is_active=True)
        db_session.add(stock)
        await db_session.commit()
        await db_session.refresh(stock)

        # Create 10 days of prices
        for i in range(10):
            p = DailyPrice(
                stock_id=stock.id,
                date=date.today() - timedelta(days=i),
                open=Decimal("600.00"),
                high=Decimal("650.00"),
                low=Decimal("590.00"),
                close=Decimal("630.00"),
                volume=1000000,
            )
            db_session.add(p)
        await db_session.commit()

        prices, _ = await DailyPriceService.get_prices_by_range(
            db_session, stock.id, limit=5, descending=True
        )

        assert len(prices) == 5
        # Most recent first
        assert prices[0].date == date.today()
        assert prices[4].date == date.today() - timedelta(days=4)

    @pytest.mark.asyncio
    async def test_get_prices_by_range_ascending(self, db_session: AsyncSession):
        """Test getting prices by range in ascending order"""
        # Create stock
        stock = Stock(symbol="2330.TW", name="台積電", is_active=True)
        db_session.add(stock)
        await db_session.commit()
        await db_session.refresh(stock)

        # Create 10 days of prices
        for i in range(10):
            p = DailyPrice(
                stock_id=stock.id,
                date=date.today() - timedelta(days=i),
                open=Decimal("600.00"),
                high=Decimal("650.00"),
                low=Decimal("590.00"),
                close=Decimal("630.00"),
                volume=1000000,
            )
            db_session.add(p)
        await db_session.commit()

        prices, _ = await DailyPriceService.get_prices_by_range(
            db_session,
            stock.id,
            start_date=date.today() - timedelta(days=9),
            end_date=date.today(),
            limit=10,
            descending=False,
        )

        assert len(prices) == 10
        # Oldest first
        assert prices[0].date == date.today() - timedelta(days=9)
        assert prices[9].date == date.today()

    @pytest.mark.asyncio
    async def test_calculate_ma_sufficient_data(self, db_session: AsyncSession):
        """Test calculating MA with sufficient data"""
        # Create stock
        stock = Stock(symbol="2330.TW", name="台積電", is_active=True)
        db_session.add(stock)
        await db_session.commit()
        await db_session.refresh(stock)

        # Create 5 days with known closes: 600, 601, 602, 603, 604
        closes = [600, 601, 602, 603, 604]
        for i, close in enumerate(closes):
            p = DailyPrice(
                stock_id=stock.id,
                date=date.today() - timedelta(days=i),
                open=Decimal("600.00"),
                high=Decimal("650.00"),
                low=Decimal("590.00"),
                close=Decimal(f"{close}.00"),
                volume=1000000,
            )
            db_session.add(p)
        await db_session.commit()

        # Calculate 5-day MA: should be (604+603+602+601+600)/5 = 602
        ma_value, data_points = await DailyPriceService.calculate_ma(db_session, stock.id, 5)

        assert ma_value == Decimal("602.00")
        assert data_points == 5

    @pytest.mark.asyncio
    async def test_calculate_ma_insufficient_data(self, db_session: AsyncSession):
        """Test calculating MA with insufficient data"""
        # Create stock
        stock = Stock(symbol="2330.TW", name="台積電", is_active=True)
        db_session.add(stock)
        await db_session.commit()
        await db_session.refresh(stock)

        # Create only 3 days
        for i in range(3):
            p = DailyPrice(
                stock_id=stock.id,
                date=date.today() - timedelta(days=i),
                open=Decimal("600.00"),
                high=Decimal("650.00"),
                low=Decimal("590.00"),
                close=Decimal("630.00"),
                volume=1000000,
            )
            db_session.add(p)
        await db_session.commit()

        # Request 200MA
        ma_value, data_points = await DailyPriceService.calculate_ma(db_session, stock.id, 200)

        assert ma_value is None
        assert data_points == 3

    @pytest.mark.asyncio
    async def test_get_latest_prices(self, db_session: AsyncSession):
        """Test getting latest N prices"""
        # Create stock
        stock = Stock(symbol="2330.TW", name="台積電", is_active=True)
        db_session.add(stock)
        await db_session.commit()
        await db_session.refresh(stock)

        # Create 10 days of prices
        for i in range(10):
            p = DailyPrice(
                stock_id=stock.id,
                date=date.today() - timedelta(days=i),
                open=Decimal("600.00"),
                high=Decimal("650.00"),
                low=Decimal("590.00"),
                close=Decimal("630.00"),
                volume=1000000,
            )
            db_session.add(p)
        await db_session.commit()

        prices = await DailyPriceService.get_latest_prices(db_session, stock.id, n=5)

        assert len(prices) == 5
        assert prices[0].date == date.today()  # Most recent first


class TestDailyPriceSchema:
    """Tests for DailyPrice Pydantic schemas"""

    def test_valid_daily_price_base(self):
        """Test creating valid DailyPriceBase"""
        from src.stocks.schema import DailyPriceBase

        price = DailyPriceBase(
            date=date.today(),
            open=Decimal("600.00"),
            high=Decimal("650.00"),
            low=Decimal("590.00"),
            close=Decimal("630.00"),
            volume=1000000,
        )

        assert price.date == date.today()
        assert price.open == Decimal("600.00")

    def test_invalid_high_less_than_low(self):
        """Test validation fails when high < low (OHLCV consistency check)"""
        from pydantic import ValidationError
        from src.stocks.schema import DailyPriceBase

        # OHLCV consistency validation will fail when high < low
        # Note: other validations may also fail depending on field order
        with pytest.raises(ValidationError) as exc:
            DailyPriceBase(
                date=date.today(),
                open=Decimal("580.00"),
                high=Decimal("585.00"),
                low=Decimal("590.00"),  # low > high - invalid
                close=Decimal("580.00"),
                volume=1000000,
            )

        # At least one OHLCV consistency validation should fail
        error_str = str(exc.value)
        assert any(
            msg in error_str
            for msg in ["high must be >= low", "low must be <= open", "low must be <= close"]
        )

    def test_invalid_high_less_than_open(self):
        """Test validation fails when high < open"""
        from pydantic import ValidationError
        from src.stocks.schema import DailyPriceBase

        with pytest.raises(ValidationError) as exc:
            DailyPriceBase(
                date=date.today(),
                open=Decimal("650.00"),
                high=Decimal("640.00"),  # Invalid: high < open
                low=Decimal("590.00"),
                close=Decimal("630.00"),
                volume=1000000,
            )

        assert "high must be >= open" in str(exc.value)

    def test_invalid_low_greater_than_close(self):
        """Test validation fails when low > close"""
        from pydantic import ValidationError
        from src.stocks.schema import DailyPriceBase

        with pytest.raises(ValidationError) as exc:
            DailyPriceBase(
                date=date.today(),
                open=Decimal("600.00"),  # low must be <= open, so open should be higher than low
                high=Decimal("650.00"),
                low=Decimal("640.00"),  # Invalid: low > close and low > open
                close=Decimal("630.00"),
                volume=1000000,
            )

        assert "low must be <= close" in str(exc.value) or "low must be <= open" in str(exc.value)

    def test_negative_price(self):
        """Test validation fails for negative price"""
        from pydantic import ValidationError
        from src.stocks.schema import DailyPriceBase

        with pytest.raises(ValidationError):
            DailyPriceBase(
                date=date.today(),
                open=Decimal("-100.00"),  # Invalid: negative
                high=Decimal("650.00"),
                low=Decimal("590.00"),
                close=Decimal("630.00"),
                volume=1000000,
            )

    def test_negative_volume(self):
        """Test validation fails for negative volume"""
        from pydantic import ValidationError
        from src.stocks.schema import DailyPriceBase

        with pytest.raises(ValidationError):
            DailyPriceBase(
                date=date.today(),
                open=Decimal("600.00"),
                high=Decimal("650.00"),
                low=Decimal("590.00"),
                close=Decimal("630.00"),
                volume=-1000,  # Invalid: negative
            )

    def test_bulk_create_limits(self):
        """Test bulk create min/max limits"""
        from pydantic import ValidationError
        from src.stocks.schema import DailyPriceBulkCreate, DailyPriceBase

        # Empty list (min_length=1)
        with pytest.raises(ValidationError):
            DailyPriceBulkCreate(prices=[])

        # Too many prices (max_length=1000)
        prices = [
            DailyPriceBase(
                date=date.today() + timedelta(days=i),
                open=Decimal("600.00"),
                high=Decimal("650.00"),
                low=Decimal("590.00"),
                close=Decimal("630.00"),
                volume=1000000,
            )
            for i in range(1001)
        ]

        with pytest.raises(ValidationError):
            DailyPriceBulkCreate(prices=prices)