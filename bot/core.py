import time
import sys
from datetime import datetime
from .account import get_user_info, get_client_info, get_accounts, get_balance, get_positions
from .execution import get_fx_prices, place_limit_order, place_market_order, convert_to_market_order
from .data_handler import FXDataHandler
from .trading_terminal import TradingTerminal



class SaxoTradingBot:
    def __init__(self, access_token, data_source_type="saxo"):
        self.data_source_type = data_source_type
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        self.client_key = None
        self.account_key = None
        self.data_source = None
        self.async_client = None

        self.currencies = {
            16: "EUR/DKK",
            21: "EUR/USD", 
            31: "USD/JPY",
            22: "GBP/USD",
            17: "EUR/GBP",
        }
        
        self.data = FXDataHandler()
        self.terminal = TradingTerminal(self)
        

        
 

    def setup(self):
        from .data_source import SaxoDataSource, YahooFinanceDataSource
        
        if self.data_source_type == "saxo":
            user = get_user_info(self.headers)
            client = get_client_info(self.headers)
            accounts = get_accounts(self.headers)

            self.client_key = client['ClientKey']
            default_account_id = client['DefaultAccountId']

            for account in accounts['Data']:
                if account['AccountId'] == default_account_id:
                    self.account_key = account['AccountKey']
                    break

            print(f"ClientKey: {self.client_key}")
            print(f"AccountKey: {self.account_key}")
            
            self.data_source = SaxoDataSource(self.headers, self.client_key, self.account_key)
        else:
            print("Starting Balance: $1,000,000")
            print("Data Source: Yahoo Finance\n")
            
            self.data_source = YahooFinanceDataSource()
            
            self.client_key = "PAPER_TRADING"
            self.account_key = "PAPER_ACCOUNT"

    def get_position_size(self, uic):
        positions = self.data_source.get_positions()
        
        for position in positions.get("Data", []):
            base = position.get("PositionBase", {})
            if str(base.get("Uic")) == str(uic):
                amount = int(base["Amount"])
                symbol = position["DisplayAndFormat"]["Symbol"]
                return amount, symbol
        
        return 0, None
    
    def get_fx_prices_unified(self, uics):
        return self.data_source.get_prices(uics)

    def raw_api_price_monitor(self, uics, update_interval=1.0):
        from .execution import get_fx_prices
        
        print("Press Ctrl+C to exit\n")
        
        previous_prices = {}
        
        try:
            while True:
                
                try:
                    prices = self.get_fx_prices_unified(uics)
                    
                    if 'Data' not in prices:
                        print("No 'Data' field in API")
                        time.sleep(update_interval)
                        continue

                    for i, uic in enumerate(uics):
                        if i >= len(prices['Data']):
                            print(f"UIC {uic}: No data")
                            continue
                        
                        try:
                            quote = prices['Data'][i]['Quote']
                            symbol = self.currencies.get(uic, f"UIC {uic}")
                            
                            mid = quote['Mid']
                            bid = quote.get('Bid', 'N/A')
                            ask = quote.get('Ask', 'N/A')
                            
                            if symbol in previous_prices:
                                prev_mid = previous_prices[symbol]
                                change = mid - prev_mid
                                
                                if change > 0:
                                    change_indicator = f"{change:.5f}"
                                elif change < 0:    
                                    change_indicator = f"{change:.5f}"
                                else:
                                    change_indicator = "0%"
                            else:
                                change_indicator = ""


                            print(f"\n{symbol} (UIC {uic}):")
                            print(f"  Mid:    {mid:.5f}")
                            print(f"  Bid:    {bid}")
                            print(f"  Ask:    {ask}")
                            print(f"  Change: {change_indicator}")
                            
                            previous_prices[symbol] = mid
                            
                        except (KeyError, IndexError) as e:
                            print(f"Error processing UIC {uic}")
                    
                except Exception as e:
                    print(f"Error fetching prices")
                    import traceback
                    traceback.print_exc()
                
                time.sleep(update_interval)
                
        except KeyboardInterrupt:
            pass

    def run(self):
        self.setup()

        def show_currencies():
            for uic, symbol in sorted(self.currencies.items()):
                print(f" {uic}: {symbol}")

        def get_uic_input(default_uic=None):
            while True:
                show_currencies()
                raw = input(f"Enter UIC: ").strip()
                if not raw and default_uic is not None:
                    return int(default_uic)
                if raw.isdigit():
                    return int(raw)
                print("Invalid")

        def get_multiple_uics():
            show_currencies()
            print("\nEnter UICs (eg: 16,21): ")
            raw = input("UICs: ").strip()
            
            if not raw:
                return [16, 21]
            
            try:
                uics = [int(x.strip()) for x in raw.split(',')]
                return uics
            except ValueError:
                print("Invalid")
                return [16, 21]

        def show_menu():
            print("\n>> FX Trading Terminal")
            print("1) Trading Terminal")
            print("2) [DEBUG]Raw API Price Monitor")
            print("3) Exit\n")

        while True:
            show_menu()
            choice = input("Select an option: ").strip()


            if choice == '1':
                uic = get_uic_input(default_uic=16)
                update_interval = 1
                self.terminal.run(uic, update_interval)

            elif choice == '2':
                uics = get_multiple_uics()
                self.raw_api_price_monitor(uics)

            elif choice == '3':
                break

            else:
                print("[ERROR] Invalid")
