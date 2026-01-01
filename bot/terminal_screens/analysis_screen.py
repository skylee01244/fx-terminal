import time
from datetime import datetime
from typing import Dict, Optional
from collections import deque

from rich.text import Text
import shutil
import pandas as pd

try:
    import plotext as plt
    PLOTEXT_AVAILABLE = True
except ImportError:
    PLOTEXT_AVAILABLE = False

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, Container
from textual.widgets import Static


class ChartWidget(Static):
    
    def __init__(self, symbol: str, price_data: deque, **kwargs):
        super().__init__(**kwargs)
        self.symbol = symbol
        self.price_data = price_data
        
    def render(self) -> Text:
        if not PLOTEXT_AVAILABLE or len(self.price_data) < 2:
            return Text(f"\n\nWaiting for price data")

        prices = list(self.price_data)
        x_vals = list(range(len(prices)))
        
        plt.clear_figure()
        plt.clear_data()
        plt.plot(x_vals, prices, marker="braille", label="price")
        
        # moving average
        if len(prices) >= 5:
            try:
                ma_series = pd.Series(prices).rolling(window=5).mean()
                ma_x = []
                ma_y = []
                for i, v in enumerate(ma_series):
                    if not pd.isna(v):
                        ma_x.append(i)
                        ma_y.append(float(v))
                if ma_x:
                    plt.plot(ma_x, ma_y, marker="braille", label="MA5")
            except Exception:
                pass
        
        # widget size
        try:
            widget_width = int(self.size.width) if self.size.width else 0
            widget_height = int(self.size.height) if self.size.height else 0
        except Exception:
            widget_width = 0
            widget_height = 0

        if widget_width <= 0 or widget_height <= 0:
            term_w, term_h = shutil.get_terminal_size(fallback=(120, 30))
            widget_width = term_w // 2
            widget_height = min(16, term_h - 8)

        chart_width = max(30, widget_width - 4)
        chart_height = max(6, widget_height - 6)

        plt.plotsize(chart_width, chart_height)
        plt.theme("dark")
        chart_str = plt.build()

        current_price = prices[-1]
        min_price = min(prices)
        max_price = max(prices)
        price_change = current_price - prices[0]
        price_change_pct = (price_change / prices[0] * 100) if prices[0] != 0 else 0
        change_symbol = "↑" if price_change > 0 else "↓" if price_change < 0 else "→"

        stats = (
            f"\n\nCurrent: {current_price:.5f} {change_symbol} {price_change:+.5f} ({price_change_pct:+.2f}%)\n"
            f"Min: {min_price:.5f} | Max: {max_price:.5f} | Points: {len(prices)}"
        )

        full = f"{self.symbol} - Analysis\n\n{chart_str}{stats}"
        return Text.from_ansi(full)


class IndicatorsWidget(Static):
    
    def __init__(self, bot, current_symbol: str, price_data: Dict, **kwargs):
        super().__init__(**kwargs)
        self.bot = bot
        self.current_symbol = current_symbol
        self.price_data = price_data
        
    def render(self) -> str:
        lines = ["Technical Indicators\n"]
        lines.append("─" * 32)

        try:
            indicators = self.bot.data.calculate_technical_indicators(self.current_symbol)
            if indicators:
                lines.append(f"SMA 5:  {indicators.get('sma_5', 'N/A')}")
                lines.append(f"SMA 20: {indicators.get('sma_20', 'N/A')}")
                lines.append(f"RSI:    {indicators.get('rsi', 'N/A')}")
                lines.append(f"MACD:   {indicators.get('macd', 'N/A')}")
                lines.append(f"BB Up:  {indicators.get('bb_upper', 'N/A')}")
                lines.append(f"BB Low: {indicators.get('bb_lower', 'N/A')}")
            else:
                lines.append("Insufficient data")
        except Exception:
            lines.append("Loading")
        
        return "\n".join(lines)


class SignalsWidget(Static):
    
    def __init__(self, bot, current_symbol: str, **kwargs):
        super().__init__(**kwargs)
        self.bot = bot
        self.current_symbol = current_symbol
        
    def render(self) -> str:
        lines = ["Signals\n"]
        lines.append("─" * 32)
        
        try:
            signals = self.bot.data.get_trading_signals(self.current_symbol)
            if signals:
                lines.append(f"MA Signal:  {signals.get('ma_signal', 'N/A')}")
                lines.append(f"RSI Signal: {signals.get('rsi_signal', 'N/A')}")
                lines.append(f"BB Signal:  {signals.get('bb_signal', 'N/A')}")
                lines.append("")
                lines.append(f"Overall: {signals.get('overall_signal', 'N/A')}")
            else:
                lines.append("Insufficient data")
        except Exception:
            lines.append("Loading")
        
        return "\n".join(lines)


class AnalysisScreen(Container):
    
    DEFAULT_CSS = """
    AnalysisScreen {
        layout: grid;
        grid-size: 2 2;
        grid-rows: 3 1fr;
        height: 100%;
    }
    
    AnalysisScreen #header {
        column-span: 2;
        background: $primary;
        color: $text;
        padding: 1;
        text-align: center;
    }
    
    AnalysisScreen #chart {
        border: solid $accent;
        padding: 1;
        height: 100%;
    }
    
    AnalysisScreen #indicators {
        border: solid $success;
        padding: 1;
    }
    
    AnalysisScreen #signals {
        border: solid $warning;
        padding: 1;
    }
    """
    
    def __init__(self, bot, current_uic: int, current_symbol: str, price_data: Dict, **kwargs):
        super().__init__(**kwargs)
        self.bot = bot
        self.current_uic = current_uic
        self.current_symbol = current_symbol
        self.price_data = price_data
        
    def compose(self) -> ComposeResult:
        yield Static(
            f"Analysis - {self.current_symbol} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            id="header"
        )
        
        if self.current_symbol not in self.price_data:
            self.price_data[self.current_symbol] = deque(maxlen=50)
        
        yield ChartWidget(self.current_symbol, self.price_data[self.current_symbol], id="chart")
        
        with Vertical():
            yield IndicatorsWidget(self.bot, self.current_symbol, self.price_data, id="indicators")
            yield SignalsWidget(self.bot, self.current_symbol, id="signals")
    
    def update_widgets(self) -> None:
        try:
            # Update header
            header = self.query_one("#header", Static)
            header.update(f"Analysis - {self.current_symbol} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            chart = self.query_one("#chart", ChartWidget)
            if self.current_symbol in self.price_data:
                chart.price_data = self.price_data[self.current_symbol]
            chart.refresh()
            
            indicators = self.query_one("#indicators", IndicatorsWidget)
            indicators.price_data = self.price_data
            indicators.refresh()
            
            signals = self.query_one("#signals", SignalsWidget)
            signals.refresh()
        except Exception as e:
            pass
