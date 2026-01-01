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
from textual.containers import Horizontal, Vertical, Container, ScrollableContainer
from textual.widgets import Static, Input, Button, Select
from textual.widgets.selection_list import Selection


class ChartWidget(Static):
    
    def __init__(self, symbol: str, price_data: deque, **kwargs):
        super().__init__(**kwargs)
        self.symbol = symbol
        self.price_data = price_data
        
    def render(self) -> Text:
        if not PLOTEXT_AVAILABLE:
            return Text(f"{self.symbol}\n\nPlotExt not available")
        
        if len(self.price_data) == 0:
            return Text(f"{self.symbol}\n\nWaiting for price data...")
        
        if len(self.price_data) == 1:
            price = list(self.price_data)[0]
            return Text(f"{self.symbol}\n\nFirst price: {price:.5f}\nWaiting for more data...")

        prices = list(self.price_data)
        x_vals = list(range(len(prices)))
        
        plt.clear_figure()
        plt.clear_data()
        plt.plot(x_vals, prices, marker="braille", label="price")
        
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
        first_price = prices[0]
        min_price = min(prices)
        max_price = max(prices)
        price_change = current_price - first_price
        price_change_pct = (price_change / first_price * 100) if first_price != 0 else 0
        change_symbol = "↑" if price_change > 0 else "↓" if price_change < 0 else "→"

        stats = (
            f"\n\nCurrent: {current_price:.5f} {change_symbol} {price_change:+.5f} ({price_change_pct:+.2f}%)\n"
            f"Min: {min_price:.5f} | Max: {max_price:.5f} | Points: {len(prices)}"
        )

        full = f"{self.symbol}\n\n{chart_str}{stats}"
        return Text.from_ansi(full)


class MarketDataWidget(Static):
    
    def __init__(self, bot, price_data: Dict, current_symbol: str = None, current_uic: int = None, **kwargs):
        super().__init__(**kwargs)
        self.bot = bot
        self.price_data = price_data
        self.current_symbol = current_symbol
        self.current_uic = current_uic
        
    def render(self) -> Text:
        from rich.text import Text
        
        result = Text()
        result.append("Market Data\n\n", style="bold cyan")
        
        if self.current_symbol and self.current_symbol in self.price_data and len(self.price_data[self.current_symbol]) > 0:
            prices = list(self.price_data[self.current_symbol])
            mid = prices[-1]
            spread_est = mid * 0.00015 
            bid = mid - (spread_est / 2)
            ask = mid + (spread_est / 2)
            
            change = 0
            change_pct = 0
            if len(prices) > 1:
                change = mid - prices[0]
                change_pct = (change / prices[0] * 100) if prices[0] != 0 else 0
            
            change_color = "green" if change >= 0 else "red"
            change_symbol = "↑" if change > 0 else "↓" if change < 0 else "→"
            
            result.append(f"{self.current_symbol}\n", style="bold yellow")
            result.append(f"Mid:    ", style="dim")
            result.append(f"{mid:.5f} ", style="bold white")
            result.append(f"{change_symbol} {change_pct:+.4f}%\n", style=f"bold {change_color}")
            
            result.append(f"Bid:    ", style="dim")
            result.append(f"{bid:.5f}\n", style="cyan")
            
            result.append(f"Ask:    ", style="dim")
            result.append(f"{ask:.5f}\n", style="magenta")
            
            result.append("─" * 36 + "\n", style="dim")
        else:
            result.append(f"{self.current_symbol}\n", style="bold yellow")
            result.append(f"Loading...\n", style="dim yellow")
            result.append("─" * 36 + "\n", style="dim")
        
        result.append("Other Pairs\n", style="bold dim")
        
        other_symbols = []
        for uic, symbol in list(self.bot.currencies.items())[:6]:
            if symbol == self.current_symbol:
                continue
            if symbol in self.price_data and len(self.price_data[symbol]) > 0:
                try:
                    prices = list(self.price_data[symbol])
                    current = prices[-1]
                    change = current - prices[0] if len(prices) > 1 else 0
                    change_pct = (change / prices[0] * 100) if len(prices) > 1 and prices[0] != 0 else 0
                    change_color = "green" if change >= 0 else "red"
                    other_symbols.append((symbol, current, change_pct, change_color))
                except Exception:
                    continue
        
        for i in range(0, len(other_symbols), 2):
            symbol1, price1, chg1, color1 = other_symbols[i]
            result.append(f"{symbol1[:7]:<7} ", style="cyan")
            result.append(f"{price1:>8.5f} ", style="white")
            result.append(f"{chg1:>7.4f}%", style=color1)
            
            if i + 1 < len(other_symbols):
                symbol2, price2, chg2, color2 = other_symbols[i + 1]
                result.append(f"  {symbol2[:7]:<7} ", style="cyan")
                result.append(f"{price2:>8.5f} ", style="white")
                result.append(f"{chg2:>7.4f}%", style=color2)
            
            result.append("\n")
        
        if not other_symbols:
            result.append("Loading other pairs...", style="dim yellow")
        
        return result


class OrderEntryWidget(Container):
    
    DEFAULT_CSS = """
    OrderEntryWidget {
        border: heavy $success;
        padding: 1;
        height: 100%;
        width: 100%;
        background: $boost;
    }
    
    OrderEntryWidget Static.title {
        text-style: bold;
        color: $accent;
        margin-bottom: 0;
    }
    
    OrderEntryWidget .order-label {
        width: 11;
        content-align: left middle;
        padding: 0;
        text-style: bold;
        color: $text;
    }
    
    OrderEntryWidget Input {
        width: 1fr;
        margin-right: 0;
    }
    
    OrderEntryWidget Select {
        width: 1fr;
        margin-right: 0;
    }
    
    OrderEntryWidget Button {
        width: 100%;
        margin-top: 1;
        margin-bottom: 1;
        height: 3;
    }
    
    OrderEntryWidget .order-row {
        height: 3;
        margin-bottom: 0;
    }
    
    OrderEntryWidget #summary {
        background: $panel;
        padding: 1;
        margin-top: 1;
        margin-bottom: 1;
        border: solid $primary;
        text-style: bold;
    }
    """
    
    def __init__(self, bot, current_uic: int, current_symbol: str, price_data: Dict, **kwargs):
        super().__init__(**kwargs)
        self.bot = bot
        self.current_uic = current_uic
        self.current_symbol = current_symbol
        self.price_data = price_data
        self.initial_price = self._get_current_price()
        
    def _get_current_price(self) -> float:
        if self.current_symbol in self.price_data and self.price_data[self.current_symbol]:
            return self.price_data[self.current_symbol][-1]
        
        try:
            prices = self.bot.get_fx_prices_unified([self.current_uic])
            if 'Data' in prices and prices['Data']:
                return prices['Data'][0]['Quote']['Mid']
        except Exception:
            pass
        return 0.0
        
    def compose(self) -> ComposeResult:
        yield Static("Order Entry", classes="title")
        
        # Order Type
        with Horizontal(classes="order-row"):
            yield Static("Type:", classes="order-label")
            yield Select(
                options=[
                    ("Market Order", "Market"),
                    ("Limit Order", "Limit"),
                ],
                value="Market",
                id="order_type",
                allow_blank=False
            )
        
        # Buy/Sell
        with Horizontal(classes="order-row"):
            yield Static("Side:", classes="order-label")
            yield Select(
                options=[
                    ("Buy", "Buy"),
                    ("Sell", "Sell"),
                ],
                value="Buy",
                id="order_side",
                allow_blank=False
            )
        
        with Horizontal(classes="order-row"):
            yield Static("Shares:", classes="order-label")
            yield Input(placeholder="100000", value="100000", id="order_shares", type="integer")
        
        with Horizontal(classes="order-row"):
            yield Static("Price:", classes="order-label")
            yield Input(
                placeholder="Market", 
                value=f"{self.initial_price:.5f}" if self.initial_price > 0 else "Market",
                id="order_price"
            )
        
        with Horizontal(classes="order-row"):
            yield Static("Duration:", classes="order-label")
            yield Select(
                options=[
                    ("Good Till Cancel", "G.T.C"),
                    ("Day Order", "Day"),
                    ("One Week", "Week"),
                ],
                value="G.T.C",
                id="order_duration",
                allow_blank=False
            )
        
        yield Static(self._get_summary(), id="summary")
        
        yield Button("PLACE ORDER", id="place_order_btn", variant="success")
    
    def _get_summary(self) -> str:
        try:
            current_price = self._get_current_price()
            balance = self.bot.data_source.get_balance()
            available = balance.get('CashAvailableForTrading', 0)
            currency_symbol = "$" if self.bot.data_source_type == "yahoo" else "€"
            
            try:
                order_side_select = self.query_one("#order_side", Select)
                side = order_side_select.value or "Buy"
            except Exception:
                side = "Buy"

            try:
                order_type_select = self.query_one("#order_type", Select)
                order_type = order_type_select.value
            except Exception:
                order_type = "Market"
            
            try:
                shares_input = self.query_one("#order_shares", Input)
                shares = int(shares_input.value.replace(",", ""))
            except Exception:
                shares = 0
            
            if order_type == "Market":
                total = current_price * shares
                price_display = f"{current_price:.5f}"
            else:
                try:
                    price_input = self.query_one("#order_price", Input)
                    price_value = price_input.value
                    if price_value and price_value != "Market":
                        limit_price = float(price_value)
                        total = limit_price * shares
                        price_display = f"{limit_price:.5f}"
                    else:
                        total = current_price * shares
                        price_display = f"{current_price:.5f}"
                except Exception:
                    total = current_price * shares
                    price_display = f"{current_price:.5f}"
            
            if side == "Sell":
                remaining = available + total
                impact_label = "Proceeds"
            else:
                remaining = available - total
                impact_label = "Cost"
            
            summary = f"Price: {price_display}\n"
            summary += f"{impact_label}:  {currency_symbol}{total:,.2f}\n"
            summary += f"Avail: {currency_symbol}{available:,.2f}\n"
            summary += f"After: {currency_symbol}{remaining:,.2f}"
            
            return summary
        except Exception as e:
            return f"Calculating..."
    
    def on_input_changed(self, event: Input.Changed) -> None:
        self._update_summary()
    
    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "order_type":
            try:
                price_input = self.query_one("#order_price", Input)
                if event.value == "Market":
                    price_input.value = "Market"
                    price_input.disabled = True
                else:
                    if price_input.value == "Market" or not price_input.value:
                        current_price = self._get_current_price()
                        price_input.value = f"{current_price:.5f}" if current_price > 0 else ""
                    price_input.disabled = False
            except Exception:
                pass
        
        self._update_summary()
    
    def _update_summary(self):
        try:
            summary_widget = self.query_one("#summary", Static)
            summary_widget.update(self._get_summary())
        except Exception:
            pass
    
    def get_order_params(self) -> dict:
        try:
            order_type_select = self.query_one("#order_type", Select)
            order_side_select = self.query_one("#order_side", Select)
            shares_input = self.query_one("#order_shares", Input)
            price_input = self.query_one("#order_price", Input)
            duration_select = self.query_one("#order_duration", Select)
            
            order_type = order_type_select.value or "Market"
            order_side = order_side_select.value or "Buy"
            shares = int(shares_input.value.replace(",", ""))
            duration = duration_select.value or "G.T.C"
            
            price_str = price_input.value
            if order_type == "Market" or price_str == "Market" or not price_str:
                price = None
            else:
                price = float(price_str)
            
            return {
                "type": order_type,
                "side": order_side,
                "shares": shares,
                "price": price,
                "duration": duration,
            }
        except Exception as e:
            return {"error": str(e)}
    
    def reset_fields(self):
        try:
            order_type_select = self.query_one("#order_type", Select)
            order_side_select = self.query_one("#order_side", Select)
            shares_input = self.query_one("#order_shares", Input)
            price_input = self.query_one("#order_price", Input)
            duration_select = self.query_one("#order_duration", Select)
            
            order_type_select.value = "Market"
            order_side_select.value = "Buy"
            shares_input.value = "100000"
            price_input.value = "Market"
            price_input.disabled = True
            duration_select.value = "G.T.C"
            
            self._update_summary()
        except Exception:
            pass


class TradingScreen(Container):
    
    DEFAULT_CSS = """
    TradingScreen {
        layout: grid;
        grid-size: 2 3;
        grid-rows: 3 3fr 1fr;
        height: 100%;
    }
    
    TradingScreen #header {
        column-span: 2;
        background: $primary;
        color: $text;
        padding: 1;
        text-align: center;
    }
    
    TradingScreen #chart {
        border: solid $accent;
        padding: 1;
        height: 100%;
        row-span: 2;
    }
    
    TradingScreen #market_data {
        border: solid $warning;
        padding: 1;
        height: 100%;
        max-height: 15;
    }
    
    TradingScreen #order_entry {
        height: 100%;
    }
    
    TradingScreen #placeholder {
        border: dashed $primary;
        padding: 1;
        height: 100%;
        background: $surface;
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
            f"Trading - {self.current_symbol} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            id="header"
        )
        
        if self.current_symbol not in self.price_data:
            self.price_data[self.current_symbol] = deque(maxlen=50)
        
        yield ChartWidget(self.current_symbol, self.price_data[self.current_symbol], id="chart")
        
        yield OrderEntryWidget(self.bot, self.current_uic, self.current_symbol, self.price_data, id="order_entry")
        
        yield MarketDataWidget(self.bot, self.price_data, self.current_symbol, self.current_uic, id="market_data")
        
        yield Static("", id="placeholder")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "place_order_btn":
            self.place_order()
    
    def place_order(self) -> None:
        try:
            order_entry = self.query_one("#order_entry", OrderEntryWidget)
            params = order_entry.get_order_params()
            
            if "error" in params:
                self.app.notify(f"Error: {params['error']}", severity="error")
                return
            
            if params["shares"] <= 0:
                self.app.notify("Shares must be greater than 0", severity="error")
                return
            
            if params["side"].lower() not in ["buy", "sell"]:
                self.app.notify("Side must be 'Buy' or 'Sell'", severity="error")
                return

            if params["side"].lower() == "sell":
                try:
                    positions = self.bot.data_source.get_positions()
                    current_position = 0
                    
                    found = False
                    if "Data" in positions and positions["Data"]:
                        for pos in positions["Data"]:
                            pos_uic = pos.get("Uic") or pos.get("PositionBase", {}).get("Uic")
                            if str(pos_uic) == str(self.current_uic):
                                current_position = float(pos["PositionBase"]["Amount"])
                                found = True
                                break
                    
                    if not found or current_position <= 0:
                        self.app.notify("No position to sell.", severity="error")
                        return
                    
                    if abs(params["shares"]) > abs(current_position):
                        self.app.notify(f"Cannot sell {params['shares']}. Only {abs(int(current_position))} available.", severity="error")
                        return
                except Exception as e:
                    self.app.notify(f"Position Check Error: {str(e)}", severity="error")
                    return
            
            if params["side"].lower() == "buy":
                try:
                    balance = self.bot.data_source.get_balance()
                    available = balance.get('CashAvailableForTrading', 0)
                    
                    if params["type"].lower() == "market":
                        price = order_entry._get_current_price()
                    else:
                        price = params["price"] or 0
                    
                    required = price * params["shares"]
                    
                    if required > available:
                        self.app.notify(f"Insufficient funds", severity="error")
                        return
                except Exception:
                    pass
            
            resp = self.bot.data_source.place_order(
                self.current_uic,
                params["shares"],
                params["side"].capitalize(),
                order_type=params["type"].capitalize(),
                price=params["price"],
                duration=params["duration"]
            )
            
            if 'error' in resp:
                self.app.notify(f"Order Error: {resp['error']}", severity="error")
            else:
                message = resp.get('Message', f"{params['type']} {params['side']} Placed")
                self.app.notify(f"{message}", severity="information")
                order_entry.reset_fields()
                
        except Exception as e:
            self.app.notify(f"Error: {str(e)}", severity="error")
    
    def update_widgets(self) -> None:
        try:
            header = self.query_one("#header", Static)
            header.update(f"Trading - {self.current_symbol} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            chart = self.query_one("#chart", ChartWidget)
            if self.current_symbol in self.price_data:
                chart.price_data = self.price_data[self.current_symbol]
            chart.refresh()
            
            market = self.query_one("#market_data", MarketDataWidget)
            market.price_data = self.price_data
            market.current_symbol = self.current_symbol
            market.current_uic = self.current_uic
            market.refresh()
            
            order_entry = self.query_one("#order_entry", OrderEntryWidget)
            order_entry._update_summary()
        except Exception:
            pass