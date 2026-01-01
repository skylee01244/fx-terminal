import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    print("[WARNING] yfinance not available")


class FXDataHandler:
    
    def __init__(self):
        self.price_history: Dict[str, pd.DataFrame] = {}
        self.performance_metrics: Dict[str, float] = {}
    
    def add_price_data(self, symbol: str, price: float, timestamp: datetime = None) -> None:
        if timestamp is None:
            timestamp = datetime.now()
        
        if symbol not in self.price_history:
            self.price_history[symbol] = pd.DataFrame(columns=['timestamp', 'price'])
        
        new_row = pd.DataFrame({
            'timestamp': [timestamp],
            'price': [price]
        })
        
        self.price_history[symbol] = pd.concat([self.price_history[symbol], new_row], ignore_index=True)
    
        if len(self.price_history[symbol]) > 1000:
            self.price_history[symbol] = self.price_history[symbol].tail(1000).reset_index(drop=True)
        
 
    def get_price_statistics(self, symbol: str) -> Dict[str, float]:
        if symbol not in self.price_history or len(self.price_history[symbol]) < 2:
            return {}
        
        df = self.price_history[symbol]
        prices = df['price']
        
        stats = {
            'current_price': prices.iloc[-1],
            'min_price': prices.min(),
            'max_price': prices.max(),
            'mean_price': prices.mean(),
            'std_price': prices.std(),
            'price_change': prices.iloc[-1] - prices.iloc[-2] if len(prices) > 1 else 0,
            'price_change_pct': ((prices.iloc[-1] - prices.iloc[-2]) / prices.iloc[-2] * 100) if len(prices) > 1 and prices.iloc[-2] != 0 else 0,
            'volatility': prices.std() / prices.mean() * 100 if prices.mean() != 0 else 0,
            'data_points': len(prices)
        }
        
        return stats
    
    def calculate_technical_indicators(self, symbol: str) -> Dict[str, float]:
        if symbol not in self.price_history or len(self.price_history[symbol]) < 20:
            return {}
        
        df = self.price_history[symbol]
        prices = df['price']
        
        # Simple Moving Averages
        sma_5 = prices.rolling(window=5).mean().iloc[-1] if len(prices) >= 5 else None
        sma_20 = prices.rolling(window=20).mean().iloc[-1] if len(prices) >= 20 else None
        
        # Exponential Moving Averages
        ema_12 = prices.ewm(span=12).mean().iloc[-1] if len(prices) >= 12 else None
        ema_26 = prices.ewm(span=26).mean().iloc[-1] if len(prices) >= 26 else None
        
        # MACD
        macd = ema_12 - ema_26 if ema_12 and ema_26 else None
        
        # RSI (Relative Strength Index)
        rsi = self._calculate_rsi(prices) if len(prices) >= 14 else None
        
        # Bollinger Bands
        bb_upper, bb_lower = self._calculate_bollinger_bands(prices) if len(prices) >= 20 else (None, None)
        
        indicators = {
            'sma_5': sma_5,
            'sma_20': sma_20,
            'ema_12': ema_12,
            'ema_26': ema_26,
            'macd': macd,
            'rsi': rsi,
            'bb_upper': bb_upper,
            'bb_lower': bb_lower,
            'current_price': prices.iloc[-1]
        }
        
        return indicators
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1] if not rsi.empty else None
    
    def _calculate_bollinger_bands(self, prices: pd.Series, period: int = 20, std_dev: float = 2) -> Tuple[float, float]:
        sma = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        return upper_band.iloc[-1], lower_band.iloc[-1]
    
    def get_trading_signals(self, symbol: str) -> Dict[str, str]:
        indicators = self.calculate_technical_indicators(symbol)
        if not indicators:
            return {}
        
        signals = {}
        
        # Moving Average Crossover
        if indicators['sma_5'] and indicators['sma_20']:
            if indicators['sma_5'] > indicators['sma_20']:
                signals['ma_signal'] = 'BUY'
            elif indicators['sma_5'] < indicators['sma_20']:
                signals['ma_signal'] = 'SELL'
            else:
                signals['ma_signal'] = 'HOLD'
        
        # RSI Signal
        if indicators['rsi']:
            if indicators['rsi'] > 70:
                signals['rsi_signal'] = 'SELL'  # Overbought
            elif indicators['rsi'] < 30:
                signals['rsi_signal'] = 'BUY'   # Oversold
            else:
                signals['rsi_signal'] = 'HOLD'
        
        # Bollinger Bands Signal
        if indicators['bb_upper'] and indicators['bb_lower'] and indicators['current_price']:
            if indicators['current_price'] > indicators['bb_upper']:
                signals['bb_signal'] = 'SELL'  # Price above upper band
            elif indicators['current_price'] < indicators['bb_lower']:
                signals['bb_signal'] = 'BUY'   # Price below lower band
            else:
                signals['bb_signal'] = 'HOLD'
        
        # Overall Signal
        buy_signals = sum(1 for signal in signals.values() if signal == 'BUY')
        sell_signals = sum(1 for signal in signals.values() if signal == 'SELL')
        
        if buy_signals > sell_signals:
            signals['overall_signal'] = 'BUY'
        elif sell_signals > buy_signals:
            signals['overall_signal'] = 'SELL'
        else:
            signals['overall_signal'] = 'HOLD'
        
        return signals
    
    def get_market_data_from_yfinance(self, symbols: List[str], period: str = "1d") -> Dict[str, pd.DataFrame]:
        if not YFINANCE_AVAILABLE:
            return {}

        market_data = {}

        for symbol in symbols:
            try:
                yf_symbol = f"{symbol}=X"
                ticker = yf.Ticker(yf_symbol)
                data = ticker.history(period=period)

                if not data.empty:
                    market_data[symbol] = data
                else:
                    pass # no data for symbol

            except Exception:
                pass 

        return market_data
