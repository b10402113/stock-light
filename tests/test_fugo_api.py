#!/usr/bin/env python3
"""Simple test script for Fugle API"""

import os
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

FUGO_API_KEY = os.getenv("FUGO_API_KEY")


async def test_fugo_api():
    """Test Fugle API connection"""

    import httpx

    if not FUGO_API_KEY:
        print("❌ FUGO_API_KEY not found in .env file")
        return

    # Fugle API endpoints - v1.0 format
    base_url = "https://api.fugle.tw/marketdata/v1.0/stock"

    # Headers with API token (Fugle uses X-API-KEY header)
    headers = {
        "X-API-KEY": FUGO_API_KEY,
    }

    # Test 1: Intraday Quote
    print("=== Test 1: Get Intraday Quote ===")
    async with httpx.AsyncClient() as client:
        url = f"{base_url}/intraday/quote/2330"

        response = await client.get(url, headers=headers)

        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success!")
            print(f"  Symbol: {data.get('symbol')} ({data.get('name')})")
            print(f"  Last Price: {data.get('lastPrice')}")
            print(f"  Change: {data.get('change')} ({data.get('changePercent')}%)")
            print(f"  Open: {data.get('openPrice')}")
            print(f"  High: {data.get('highPrice')}")
            print(f"  Low: {data.get('lowPrice')}")
            print(f"  Previous Close: {data.get('previousClose')}")
            print(f"  Volume: {data.get('total', {}).get('tradeVolume')}")
            print(f"  Trade Value: {data.get('total', {}).get('tradeValue')}")
            print(f"  Is Closed: {data.get('isClose')}")
        else:
            print(f"❌ Failed: {response.text}")

    # Test 2: Intraday Candles (OHLC data)
    print("\n=== Test 2: Get Intraday Candles ===")
    async with httpx.AsyncClient() as client:
        url = f"{base_url}/intraday/candles/2330"

        response = await client.get(url, headers=headers)

        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success! Got candles data")
            # Handle different response formats
            if isinstance(data, list) and len(data) > 0:
                candles = data
            elif isinstance(data, dict):
                candles = data.get("data", data.get("candles", []))
            else:
                candles = []
            if candles:
                print(f"  Number of candles: {len(candles)}")
                print(f"  First candle: {candles[0]}")
        else:
            print(f"❌ Failed: {response.text}")

    # Test 3: Historical Candles
    print("\n=== Test 3: Get Historical Candles ===")
    async with httpx.AsyncClient() as client:
        url = f"{base_url}/historical/candles/2330"
        params = {"from": "2025-01-01", "to": "2025-04-30"}

        response = await client.get(url, headers=headers, params=params)

        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success! Got historical candles data")
            # Handle different response formats
            if isinstance(data, list) and len(data) > 0:
                candles = data
            elif isinstance(data, dict):
                candles = data.get("data", data.get("candles", []))
            else:
                candles = []
            if candles:
                print(f"  Number of candles: {len(candles)}")
                print(f"  First candle: {candles[0]}")
                print(f"  Last candle: {candles[-1]}")
        else:
            print(f"❌ Failed: {response.text}")


if __name__ == "__main__":
    asyncio.run(test_fugo_api())
