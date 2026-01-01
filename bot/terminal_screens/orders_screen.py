from datetime import datetime
from typing import Dict, Optional
from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical, Container, ScrollableContainer
from textual.widgets import Static

class OrdersListWidget(Static):
    
    def __init__(self, bot, **kwargs):
        super().__init__(**kwargs)
        self.bot = bot
        
    def render(self) -> Text:
        result = Text()
        result.append("Open Orders\n\n", style="bold cyan")
        
        try:
            orders = self.bot.data_source.get_orders()
            
            if not orders.get("Data") or len(orders["Data"]) == 0:
                result.append("No pending orders\n\n", style="dim yellow")
                result.append("Place limit orders from the Trading tab\n", style="dim")
                result.append("   They will appear here until executed\n", style="dim")
            else:
                result.append(f"Found {len(orders['Data'])} pending order(s):\n\n", style="dim")
                
                for order in orders["Data"]:
                    try:
                        order_id = order.get("OrderId", "N/A")
                        symbol = order.get("DisplayAndFormat", {}).get("Symbol", "N/A")
                        side = order.get("BuySell", "N/A")
                        amount = order.get("Amount", 0)
                        order_type = order.get("OrderType", "N/A")
                        order_price = order.get("Price", 0)
                        duration = order.get("Duration", {}).get("DurationType", "N/A")
                        status = order.get("Status", "Working")
                        
                        side_color = "green" if side == "Buy" else "red"
                        
                        result.append(f"┌─ ", style="white")
                        result.append(f"{symbol} ", style="bold white")
                        result.append(f"[{order_type.upper()}]\n", style="cyan")
                        
                        result.append(f"│  Side:     ", style="dim")
                        result.append(f"{side} {amount:,} units\n", style=side_color)
                        
                        result.append(f"│  Price:    ", style="dim")
                        result.append(f"{order_price:.5f}\n", style="yellow")
                        
                        result.append(f"│  Duration: ", style="dim")
                        result.append(f"{duration}\n", style="white")
                        
                        result.append(f"│  Status:   ", style="dim")
                        result.append(f"{status}\n", style="cyan")
                        
                        result.append(f"│  Order ID: ", style="dim")
                        result.append(f"{order_id}\n", style="dim white")
                        
                        result.append(f"└─────────────────\n\n", style="dim")
                        
                    except Exception as e:
                        result.append(f"  Error parsing order: {str(e)}\n", style="red")
                        continue
            
            result.append("\n─" * 40 + "\n", style="dim")
            result.append("Active Positions\n\n", style="bold cyan")
            
            positions = self.bot.data_source.get_positions()
            if not positions.get("Data") or len(positions["Data"]) == 0:
                result.append("No open positions\n", style="dim yellow")
            else:
                for pos in positions["Data"]:
                    try:
                        fmt = pos["DisplayAndFormat"]
                        base = pos["PositionBase"]
                        view = pos["PositionView"]
                        
                        symbol = fmt["Symbol"]
                        amount = int(base["Amount"])
                        open_price = base["OpenPrice"]
                        current_price = view["CurrentPrice"]
                        pnl = view.get("ProfitLossOnTradeInBaseCurrency", 0)
                        
                        side = "LONG" if amount > 0 else "SHORT"
                        side_color = "green" if amount > 0 else "red"
                        pnl_color = "green" if pnl >= 0 else "red"
                        
                        result.append(f"{symbol} ", style="bold white")
                        result.append(f"[{side}] ", style=side_color)
                        result.append(f"{abs(amount):,} @ {open_price:.5f} ", style="white")
                        result.append(f"P/L: €{pnl:+,.2f}\n", style=pnl_color)
                        
                    except Exception:
                        continue
                
        except Exception as e:
            result.append(f"[ERROR]: {str(e)}", style="red")
        
        return result

class OrdersScreen(Container):
    
    DEFAULT_CSS = """
    OrdersScreen {
        layout: vertical;
        height: 100%;
        width: 100%;
    }
    
    OrdersScreen #header {
        background: $primary;
        color: $text;
        padding: 1;
        text-align: center;
        width: 100%;
    }
    
    OrdersScreen #orders_list {
        border: solid $warning;
        padding: 1;
        height: 1fr;
        width: 100%;
    }
    """
    
    def __init__(self, bot, **kwargs):
        super().__init__(**kwargs)
        self.bot = bot
        
    def compose(self) -> ComposeResult:
        yield Static(
            f"Orders - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            id="header"
        )
        
        with ScrollableContainer(id="orders_list"):
            yield OrdersListWidget(self.bot, id="orders")
    
    def update_widgets(self) -> None:
        try:
            header = self.query_one("#header", Static)
            header.update(f"Orders - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            orders = self.query_one("#orders", OrdersListWidget)
            orders.refresh()
        except Exception:
            pass