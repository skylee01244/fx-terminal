import time
import threading
from datetime import datetime
from typing import Dict, Optional
from collections import deque

try:
    from textual.app import App, ComposeResult
    from textual.containers import Horizontal, Container, VerticalScroll
    from textual.widgets import Footer, Button, Static, ContentSwitcher, Input
    from textual import work
    from textual.binding import Binding
    TEXTUAL_AVAILABLE = True
except ImportError:
    TEXTUAL_AVAILABLE = False
    print("[WARNING] A")

try:
    from .terminal_screens import TradingScreen, AnalysisScreen, PortfolioScreen, OrdersScreen
    SCREENS_AVAILABLE = True
except ImportError:
    SCREENS_AVAILABLE = False
    print("[WARNING] B")

try:
    from .order_monitor import OrderMonitor
    ORDER_MONITOR_AVAILABLE = True
except ImportError:
    ORDER_MONITOR_AVAILABLE = False
    print("[WARNING] C")


class TradingTerminalApp(App):
    CSS = """
    Screen {
        layers: base overlay;
    }
    
    #nav_bar {
        layer: overlay;
        dock: top;
        height: 3;
        background: $boost;
        padding: 0 1;
    }
    
    #nav_bar Horizontal {
        height: 100%;
        align: left middle;
    }
    
    #nav_bar Button {
        margin: 0 1;
        min-width: 16;
    }
    
    .active_tab {
        background: $primary;
        color: $text;
        border: tall $accent;
    }
    
    .inactive_tab {
        background: $surface;
        color: $text-muted;
    }
    
    #content_area {
        height: 1fr;
    }
    """
    
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("1", "switch_tab('trading')", "Trading", show=False),
        Binding("2", "switch_tab('analysis')", "Analysis", show=False),
        Binding("3", "switch_tab('portfolio')", "Portfolio", show=False),
        Binding("4", "switch_tab('orders')", "Orders", show=False),
    ]
    
    def __init__(self, bot, uic: int, update_interval: float = 2.0):
        super().__init__()
        self.bot = bot
        self.current_uic = uic
        self.current_symbol = bot.currencies.get(uic, f"UIC {uic}")
        self.update_interval = update_interval
        self.running = False
        self.price_data = {}
        self.timestamp_data = {}
        self.max_points = 50
        self.current_tab = "trading"
        
        if ORDER_MONITOR_AVAILABLE:
            self.order_monitor = OrderMonitor(bot, app=None) 
        else:
            self.order_monitor = None
        
    def compose(self) -> ComposeResult:
        with Container(id="nav_bar"):
            with Horizontal():
                yield Button("Trading", id="tab_trading", classes="active_tab")
                yield Button("Analysis", id="tab_analysis", classes="inactive_tab")
                yield Button("Portfolio", id="tab_portfolio", classes="inactive_tab")
                yield Button("Orders", id="tab_orders", classes="inactive_tab")
                yield Static("  |  Press 1-4 to switch tabs, q to quit")
        
        with ContentSwitcher(id="content_area", initial="trading"):
            # Trading screen
            yield TradingScreen(
                self.bot,
                self.current_uic,
                self.current_symbol,
                self.price_data,
                id="trading"
            )
            # Analysis screen
            yield AnalysisScreen(
                self.bot,
                self.current_uic,
                self.current_symbol,
                self.price_data,
                id="analysis"
            )
            # Portfolio screen
            yield PortfolioScreen(
                self.bot,
                id="portfolio"
            )
            # Orders screen
            yield OrdersScreen(
                self.bot,
                id="orders"
            )
    
        yield Footer()
    
    def on_mount(self) -> None:
        self.running = True
        
        if self.order_monitor:
            self.order_monitor.app = self
            self.order_monitor.start()

        self.fetch_prices_background()
        self.update_ui_background()
    
    @work(exclusive=True, thread=True)
    def fetch_prices_background(self) -> None:
        uics = list(self.bot.currencies.keys())[:5]
        
        while self.running:
            try:
                prices = self.bot.get_fx_prices_unified(uics)
                current_time = datetime.now()
                
                if 'Data' not in prices:
                    time.sleep(self.update_interval)
                    continue
                
                for i, uic in enumerate(uics):
                    if i < len(prices.get('Data', [])):
                        try:
                            quote = prices['Data'][i]['Quote']
                            price = quote['Mid']
                            symbol = self.bot.currencies.get(uic, f"UIC {uic}")

                            if symbol not in self.price_data:
                                self.price_data[symbol] = deque(maxlen=self.max_points)
                            
                            if symbol not in self.timestamp_data:
                                self.timestamp_data[symbol] = deque(maxlen=self.max_points)
                            
                            self.price_data[symbol].append(price)
                            self.timestamp_data[symbol].append(current_time)
                            
                            self.bot.data.add_price_data(symbol, price)
                            
                        except Exception as e:
                            import traceback
                            traceback.print_exc()
                    else:
                        pass
                
            except Exception as e:
                import traceback
                print(f"Error fetching prices: {e}")
                traceback.print_exc()
                pass
            
            time.sleep(self.update_interval)
    
    @work(exclusive=True, thread=True)
    def update_ui_background(self) -> None:
        while self.running:
            try:
                trading_screen = self.query_one("#trading", TradingScreen)
                if trading_screen:
                    trading_screen.update_widgets()
                
                analysis_screen = self.query_one("#analysis", AnalysisScreen)
                if analysis_screen:
                    analysis_screen.update_widgets()
                
                portfolio_screen = self.query_one("#portfolio", PortfolioScreen)
                if portfolio_screen:
                    portfolio_screen.update_widgets()
                
                orders_screen = self.query_one("#orders", OrdersScreen)
                if orders_screen:
                    orders_screen.update_widgets()
            except Exception:
                pass
            
            time.sleep(0.5)
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "tab_trading":
            self.switch_to_tab("trading")
        elif event.button.id == "tab_analysis":
            self.switch_to_tab("analysis")
        elif event.button.id == "tab_portfolio":
            self.switch_to_tab("portfolio")
        elif event.button.id == "tab_orders":
            self.switch_to_tab("orders")
    
    def switch_to_tab(self, tab_name: str) -> None:
        if tab_name == self.current_tab:
            return
        
        self.current_tab = tab_name
        
        try:
            trading_btn = self.query_one("#tab_trading", Button)
            analysis_btn = self.query_one("#tab_analysis", Button)
            portfolio_btn = self.query_one("#tab_portfolio", Button)
            orders_btn = self.query_one("#tab_orders", Button)
            
            for btn in [trading_btn, analysis_btn, portfolio_btn, orders_btn]:
                btn.remove_class("active_tab")
                btn.add_class("inactive_tab")
            
            
            active_btn = None
            if tab_name == "trading":
                active_btn = trading_btn
            elif tab_name == "analysis":
                active_btn = analysis_btn
            elif tab_name == "portfolio":
                active_btn = portfolio_btn
            elif tab_name == "orders":
                active_btn = orders_btn
            
            if active_btn:
                active_btn.remove_class("inactive_tab")
                active_btn.add_class("active_tab")
        except Exception:
            pass
        
        try:
            content_switcher = self.query_one(ContentSwitcher)
            content_switcher.current = tab_name
        except Exception:
            pass
    
    def action_switch_tab(self, tab_name: str) -> None:
        self.switch_to_tab(tab_name)
    
    def action_quit(self) -> None:
        self.running = False
        
        # Stop order monitor
        if self.order_monitor:
            self.order_monitor.stop()
        
        self.exit()


class TradingTerminal:
    
    def __init__(self, bot):
        self.bot = bot
        self.running = False
        self.price_data = {}
        self.timestamp_data = {} 
        self.max_points = 50
        self.current_symbol = None
        self.current_uic = None
        
    def run(self, uic: int, update_interval: float = 2.0):
        if not TEXTUAL_AVAILABLE:
            print("Textual library required")
            return
        
        print("\nq to Quit")
        print("1 for Trading")
        print("2 for Analysis")
        print("3 for Portfolio")
        print("4 for Orders")

        time.sleep(2)

        app = TradingTerminalApp(self.bot, uic, update_interval)
        app.run()
