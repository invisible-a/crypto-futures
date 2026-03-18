import requests
import pandas as pd
import time

def fetch_klines(symbol, interval='1h', limit=200):
    """
    Fetch market data from Binance API (very reliable fallback).
    """
    url = "https://api.binance.com/api/v3/klines"
    params = {
        'symbol': symbol.upper(),
        'interval': interval,
        'limit': limit
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        if isinstance(data, list):
            # Binance returns [ot, open, high, low, close, vol, ct, ...]
            df = pd.DataFrame(data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume', 
                'close_time', 'qav', 'num_trades', 'taker_base_vol', 'taker_quote_vol', 'ignore'
            ])
            df[['open', 'high', 'low', 'close', 'volume']] = df[['open', 'high', 'low', 'close', 'volume']].apply(pd.to_numeric)
            return df
        else:
            print(f"Error from API: {data}")
            return None
    except Exception as e:
        print(f"Request failed: {e}")
        return None

def calculate_indicators(df):
    """
    Calculate EMA and RSI indicators.
    """
    # EMA 20, 50, 200
    df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
    df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()
    
    # RSI 14
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    return df

def analyze_trend(df):
    """
    Apply trend-following strategy logic.
    """
    if df is None or len(df) < 200:
        return "Insufficient data"
    
    last_row = df.iloc[-1]
    prev_row = df.iloc[-2]
    
    # Strategy logic
    is_bullish = (last_row['close'] > last_row['ema200']) and (last_row['ema20'] > last_row['ema50'])
    is_oversold = last_row['rsi'] < 30
    is_overbought = last_row['rsi'] > 70
    
    if is_bullish and not is_overbought:
        return "LONG"
    elif not is_bullish and is_overbought:
        return "SHORT"
    else:
        return "NO TRADE"

if __name__ == "__main__":
    symbol = "tonusdt"
    df = fetch_klines(symbol)
    if df is not None:
        df = calculate_indicators(df)
        decision = analyze_trend(df)
        last_price = df.iloc[-1]['close']
        last_rsi = df.iloc[-1]['rsi']
        print(f"--- Analysis for {symbol.upper()} ---")
        print(f"Last Price: {last_price}")
        print(f"RSI (14):   {last_rsi:.2f}")
        print(f"Decision:   {decision}")
    else:
        print("Failed to retrieve data.")
