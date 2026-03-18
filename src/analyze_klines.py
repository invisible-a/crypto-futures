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

def analyze_trend(df, sl_pct=0.02, tp_pct=0.05):
    """
    Apply trend-following strategy logic and calculate risk levels.
    """
    if df is None or len(df) < 200:
        return {"decision": "Insufficient data"}
    
    last_row = df.iloc[-1]
    last_price = last_row['close']
    
    # Strategy logic
    is_bullish = (last_row['close'] > last_row['ema200']) and (last_row['ema20'] > last_row['ema50'])
    is_oversold = last_row['rsi'] < 30
    is_overbought = last_row['rsi'] > 70
    
    decision = "NO TRADE"
    entry = None
    tp = None
    sl = None
    
    if is_bullish and not is_overbought:
        decision = "LONG"
        entry = last_price
        sl = entry * (1 - sl_pct)
        tp = entry * (1 + tp_pct)
    elif not is_bullish and is_overbought:
        decision = "SHORT"
        entry = last_price
        sl = entry * (1 + sl_pct)
        tp = entry * (1 - tp_pct)
        
    return {
        "decision": decision,
        "entry": entry,
        "tp": tp,
        "sl": sl,
        "rsi": last_row['rsi'],
        "price": last_price
    }

import sys

if __name__ == "__main__":
    # Command line arguments: symbol [sl_pct] [tp_pct]
    # Example: python src/analyze_klines.py xrpusdt 0.03 0.06
    symbol = sys.argv[1] if len(sys.argv) > 1 else "tonusdt"
    sl_val = float(sys.argv[2]) if len(sys.argv) > 2 else 0.02
    tp_val = float(sys.argv[3]) if len(sys.argv) > 3 else 0.05
    
    df = fetch_klines(symbol)
    if df is not None:
        df = calculate_indicators(df)
        result = analyze_trend(df, sl_pct=sl_val, tp_pct=tp_val)
        
        print(f"--- Analysis for {symbol.upper()} ---")
        print(f"Last Price: {result['price']}")
        print(f"RSI (14):   {result['rsi']:.2f}")
        print(f"Decision:   {result['decision']}")
        
        if result['entry']:
            print(f"\n--- Trade Setup ({sl_val*100}% SL / {tp_val*100}% TP) ---")
            print(f"Entry:      {result['entry']}")
            print(f"Take Profit: {result['tp']:.4f}")
            print(f"Stop Loss:   {result['sl']:.4f}")
    else:
        print(f"Failed to retrieve data for {symbol.upper()}.")
