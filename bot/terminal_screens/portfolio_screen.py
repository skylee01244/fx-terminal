from datetime import datetime
from typing import Dict, Optional

from rich.text import Text

from textual.app import ComposeResult
from textual.containers import Vertical, Container, ScrollableContainer
from textual.widgets import Static


class AccountBalanceWidget(Static):
    
    def __init__(self, bot, **kwargs):
        super().__init__(**kwargs)
        self.bot = bot
        
    def render(self) -> Text:
        result = Text()
        result.append("Account Balance\n\n", style="bold cyan")
        
        try:
            balance = self.bot.data_source.get_balance()
            currency_symbol = "$" if self.bot.data_source_type == "yahoo" else "€"
            
            cash_balance = balance.get('CashBalance', 0)
            total_value = balance.get('TotalValue', 0)

            available = balance.get('CashAvailableForTrading', 0)
            unrealized_pnl = balance.get('UnrealizedMarginProfitLoss', 0)
            
            invested_value = balance.get('MarginUsedByCurrentPositions', 0)
            invested_pct = balance.get('MarginUtilizationPct', 0)
            
            result.append(f"{'Total Equity:':<20}", style="bold white")
            result.append(f"{currency_symbol}{total_value:,.2f}\n", style="bold green" if total_value >= 1000000 else "bold red")
            
            result.append("─" * 35 + "\n", style="dim")
            
            result.append(f"{'Cash Available:':<20}", style="white")
            result.append(f"{currency_symbol}{cash_balance:,.2f}\n", style="cyan")
            
            result.append(f"{'Invested Value:':<20}", style="white")
            result.append(f"{currency_symbol}{invested_value:,.2f} ({invested_pct:.1f}%)\n", style="yellow")
            
            result.append("─" * 35 + "\n", style="dim")

            result.append(f"{'Unrealized P&L:':<20}", style="white")
            pnl_color = "green" if unrealized_pnl >= 0 else "red"
            result.append(f"{currency_symbol}{unrealized_pnl:+,.2f}\n", style=f"bold {pnl_color}")
            
            result.append("\n")
            
            open_positions = balance.get('OpenPositionsCount', 0)
            
            result.append(f"{'Open Positions:':<20}", style="white")
            result.append(f"{open_positions}\n", style="cyan")
            
        except Exception as e:
            result.append(f"Error loading balance: {str(e)}", style="red")
        
        return result


class PositionsWidget(Static):
    
    def __init__(self, bot, **kwargs):
        super().__init__(**kwargs)
        self.bot = bot
        
    def render(self) -> Text:
        result = Text()
        result.append("Open Positions\n\n", style="bold cyan")
        
        try:
            positions = self.bot.data_source.get_positions()
            currency_symbol = "$" if self.bot.data_source_type == "yahoo" else "€"
            
            if not positions.get("Data") or len(positions["Data"]) == 0:
                result.append("No open positions", style="dim yellow")
                return result
            
            for pos in positions["Data"]:
                try:
                    fmt = pos["DisplayAndFormat"]
                    base = pos["PositionBase"]
                    view = pos["PositionView"]
                    
                    symbol = fmt["Symbol"]
                    amount = int(base["Amount"])
                    open_price = base["OpenPrice"]
                    current_price = view["CurrentPrice"]
                    pnl = view["ProfitLossOnTradeInBaseCurrency"]
                    market_value = view["MarketValueInBaseCurrency"]
                    
                    # Position header
                    result.append(f"━━━ {symbol} ", style="bold white")
                    side = "LONG" if amount > 0 else "SHORT"
                    side_color = "green" if amount > 0 else "red"
                    result.append(f"[{side}]\n", style=f"bold {side_color}")
                    
                    # Position details
                    result.append(f"  Size:          ", style="dim")
                    result.append(f"{abs(amount):,} units\n", style="white")
                    
                    result.append(f"  Open Price:    ", style="dim")
                    result.append(f"{open_price:.5f}\n", style="cyan")
                    
                    result.append(f"  Current Price: ", style="dim")
                    price_color = "green" if current_price > open_price else "red" if current_price < open_price else "yellow"
                    result.append(f"{current_price:.5f}\n", style=price_color)
                    

                    result.append(f"  Value:   ", style="dim")
                    result.append(f"{market_value:,.2f}\n", style="white")
                    
                    result.append(f"  P&L (USD):     ", style="dim")
                    pnl_color = "bold green" if pnl >= 0 else "bold red"
                    pnl_pct = (pnl / (abs(amount) * open_price) * 100) if amount != 0 and open_price != 0 else 0
                    
                    # pnl in USD
                    result.append(f"${pnl:+,.2f} \n", style=pnl_color)
                    
                    result.append("\n")
                    
                except Exception as e:
                    result.append(f"[ERROR] {str(e)}\n", style="red")
                    continue
                
        except Exception as e:
            result.append(f"[ERROR] {str(e)}", style="red")
        
        return result


class PortfolioScreen(Container):
    DEFAULT_CSS = """
    PortfolioScreen {
        layout: vertical;
        height: 100%;
    }
    
    PortfolioScreen #header {
        background: $primary;
        color: $text;
        padding: 1;
        text-align: center;
        height: 3;
    }
    
    PortfolioScreen #balance {
        border: solid $success;
        padding: 1;
        height: auto;
        min-height: 15;
    }
    
    PortfolioScreen #positions_container {
        border: solid $accent;
        padding: 1;
        height: 1fr;
    }
    """
    
    def __init__(self, bot, **kwargs):
        super().__init__(**kwargs)
        self.bot = bot
        
    def compose(self) -> ComposeResult:
        yield Static(
            f"Portfolio - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            id="header"
        )
        
        yield AccountBalanceWidget(self.bot, id="balance")
        
        with ScrollableContainer(id="positions_container"):
            yield PositionsWidget(self.bot, id="positions")
    
    def update_widgets(self) -> None:
        try:
            header = self.query_one("#header", Static)
            header.update(f"Portfolio - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            balance = self.query_one("#balance", AccountBalanceWidget)
            balance.refresh()
            
            positions = self.query_one("#positions", PositionsWidget)
            positions.refresh()
        except Exception:
            pass