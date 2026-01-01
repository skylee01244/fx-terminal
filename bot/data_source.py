from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime
import time

class DataSource(ABC):
    @abstractmethod
    def get_prices(self, instruments: List[int]) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    def get_balance(self) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    def get_positions(self) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    def get_orders(self) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    def place_order(self, instrument: int, amount: int, buy_sell: str, order_type: str = "Market", price: Optional[float] = None, duration: str = "G.T.C") -> Dict[str, Any]:
        pass

    @abstractmethod
    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        pass

class SaxoDataSource(DataSource):
    
    def __init__(self, headers: Dict[str, str], client_key: str, account_key: str):
        self.headers = headers
        self.client_key = client_key
        self.account_key = account_key
    
    def get_prices(self, instruments: List[int]) -> Dict[str, Any]:
        from .execution import get_fx_prices
        return get_fx_prices(self.headers, self.account_key, instruments)
    
    def get_balance(self) -> Dict[str, Any]:
        from .account import get_balance, get_positions
        
        # 1 Get raw data from API
        balance_data = get_balance(self.headers, self.client_key, self.account_key)
        positions_data = get_positions(self.headers, self.client_key)
        
        # 2 Manually calculate the REAL "Invested Value" (Notional)
        full_invested_value = 0.0
        
        if "Data" in positions_data:
            for pos in positions_data["Data"]:
                try:
                    amount = float(pos.get("PositionBase", {}).get("Amount", 0))
                    price = float(pos.get("PositionView", {}).get("CurrentPrice", 0))
                    
                    if price == 0:
                        price = float(pos.get("PositionBase", {}).get("OpenPrice", 0))
                    
                    # Value = Amount * Price
                    full_invested_value += abs(amount * price)
                except Exception:
                    pass
        
        # 3 Override Balance Logic
        total_equity = float(balance_data.get("TotalValue", 0))
        
        simulated_cash_available = total_equity - full_invested_value
        
        balance_data["MarginUsedByCurrentPositions"] = full_invested_value 
        balance_data["CashAvailableForTrading"] = simulated_cash_available
        balance_data["CashBalance"] = simulated_cash_available
        
        if total_equity > 0:
            balance_data["MarginUtilizationPct"] = (full_invested_value / total_equity) * 100
        else:
            balance_data["MarginUtilizationPct"] = 0
            
        return balance_data
    
    def get_positions(self) -> Dict[str, Any]:
        from .account import get_positions
        return get_positions(self.headers, self.client_key)
    
    def get_orders(self) -> Dict[str, Any]:
        from .orders import get_orders
        return get_orders(self.headers, self.client_key)
    
    def place_order(self, instrument: int, amount: int, buy_sell: str, order_type: str = "Market", price: Optional[float] = None, duration: str = "G.T.C") -> Dict[str, Any]:
        from .execution import place_market_order
        
        # Saxo API Logic
        if order_type.lower() in ["limit"] and price is not None:
            url = f"https://gateway.saxobank.com/sim/openapi/trade/v2/orders"
            duration_map = {"G.T.C": "GoodTillCancel", "Day": "DayOrder", "Week": "GoodTillDate"}
            duration_type = duration_map.get(duration, "GoodTillCancel")
            
            data = {
                "Uic": instrument,
                "BuySell": buy_sell,
                "AssetType": "FxSpot",
                "Amount": amount,
                "OrderPrice": price,
                "OrderType": "Limit",
                "OrderRelation": "StandAlone",
                "ManualOrder": True,
                "OrderDuration": {"DurationType": duration_type},
                "AccountKey": self.account_key
            }
            import requests
            return requests.post(url, json=data, headers=self.headers).json()
        else:
            return place_market_order(self.headers, self.account_key, instrument, amount, buy_sell)

    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        from .orders import cancel_order
        return cancel_order(self.headers, self.account_key, order_id)

class YahooFinanceDataSource(DataSource):
    
    UIC_TO_TICKER = {
        16: "EURDKK=X",
        21: "EURUSD=X",
        31: "JPY=X", 
        22: "GBPUSD=X",
        17: "EURGBP=X",
    }
    
    TICKER_TO_SYMBOL = {
        "EURDKK=X": "EUR/DKK",
        "EURUSD=X": "EUR/USD",
        "JPY=X": "USD/JPY",
        "GBPUSD=X": "GBP/USD",
        "EURGBP=X": "EUR/GBP",
    }
    
    def __init__(self):
        self.balance = 1_000_000.0
        self.currency = "USD"
        self.positions = {} 
        self._ticker_cache = {}
        self.orders = {} 
        
    def _get_ticker(self, ticker_symbol: str):
        if ticker_symbol not in self._ticker_cache:
            try:
                import yfinance as yf
                self._ticker_cache[ticker_symbol] = yf.Ticker(ticker_symbol)
            except ImportError:
                print("yfinance not installed.")
        return self._ticker_cache[ticker_symbol]
    
    def get_prices(self, instruments: List[int]) -> Dict[str, Any]:
        import yfinance as yf
        data_list = []
        
        for uic in instruments:
            ticker_symbol = self.UIC_TO_TICKER.get(uic)
            if not ticker_symbol: continue
            
            current_price = None
            try:
                ticker = self._get_ticker(ticker_symbol)
                hist = ticker.history(period="1d", interval="1m")
                if not hist.empty:
                    current_price = float(hist['Close'].dropna().iloc[-1])
                else:
                    hist = ticker.history(period="1d", interval="5m")
                    if not hist.empty:
                        current_price = float(hist['Close'].dropna().iloc[-1])
            except Exception:
                pass
            
            if current_price is None:
                defaults = {"EURUSD=X": 1.09, "EURDKK=X": 7.45, "JPY=X": 149.0, "GBPUSD=X": 1.27, "EURGBP=X": 0.86}
                current_price = defaults.get(ticker_symbol, 1.0)
            
            spread = current_price * 0.0001
            
            data_list.append({
                "Uic": uic,
                "AssetType": "FxSpot",
                "Quote": {
                    "Mid": current_price,
                    "Bid": current_price - spread / 2,
                    "Ask": current_price + spread / 2,
                },
                "DisplayAndFormat": {
                    "Symbol": self.TICKER_TO_SYMBOL.get(ticker_symbol, ticker_symbol),
                }
            })
        
        return {"Data": data_list}
    
    def _convert_value_to_usd(self, value: float, uic: int, current_pair_price: float) -> float:
        ticker = self.UIC_TO_TICKER.get(uic)
        if not ticker: return value
        
        if ticker in ["EURUSD=X", "GBPUSD=X"]:
            return value
        if ticker == "JPY=X":
            return value / current_pair_price if current_pair_price else 0
        if ticker == "EURGBP=X":
            try:
                prices = self.get_prices([22])
                if prices.get('Data'):
                    gbp_usd = prices['Data'][0]['Quote']['Mid']
                    return value * gbp_usd
            except:
                pass 
        if ticker == "EURDKK=X":
            try:
                prices = self.get_prices([21]) 
                if prices.get('Data'):
                    eur_usd = prices['Data'][0]['Quote']['Mid']
                    return value * eur_usd / current_pair_price
            except:
                pass
        return value

    def get_balance(self) -> Dict[str, Any]:
        invested_value_usd = 0.0
        unrealized_pnl = 0.0
        
        for uic, position in self.positions.items():
            prices = self.get_prices([uic])
            if prices.get('Data'):
                current_price = prices['Data'][0]['Quote']['Mid']
                open_price = position['open_price']
                amount = position['amount']
                
                market_val_quote = amount * current_price
                market_val_usd = self._convert_value_to_usd(market_val_quote, uic, current_price)
                invested_value_usd += market_val_usd
                
                raw_pnl = (current_price - open_price) * amount
                usd_pnl = self._convert_value_to_usd(raw_pnl, uic, current_price)
                unrealized_pnl += usd_pnl
        
        total_value = self.balance + invested_value_usd
        
        return {
            "Currency": self.currency,
            "CashBalance": self.balance,
            "CashAvailableForTrading": self.balance,
            "CollateralAvailable": self.balance,
            "UnrealizedMarginProfitLoss": unrealized_pnl,
            "TotalValue": total_value,
            "OpenPositionsCount": len(self.positions),
            "MarginUsedByCurrentPositions": invested_value_usd,
            "MarginUtilizationPct": (invested_value_usd / total_value * 100) if total_value > 0 else 0,
        }
    
    def get_positions(self) -> Dict[str, Any]:
        positions_list = []
        for uic, position in self.positions.items():
            prices = self.get_prices([uic])
            if not prices.get('Data'): continue
            
            current_price = prices['Data'][0]['Quote']['Mid']
            open_price = position['open_price']
            amount = position['amount']
            symbol = position['symbol']
            
            raw_pnl = (current_price - open_price) * amount
            usd_pnl = self._convert_value_to_usd(raw_pnl, uic, current_price)
            
            market_value = amount * current_price
            
            positions_list.append({
                "PositionId": f"PAPER_{uic}",
                "PositionBase": {
                    "Uic": uic,
                    "Amount": amount,
                    "OpenPrice": open_price,
                    "ExecutionTimeOpen": position['opened_time'].isoformat(),
                    "AssetType": "FxSpot",
                },
                "PositionView": {
                    "CurrentPrice": current_price,
                    "ProfitLossOnTradeInBaseCurrency": usd_pnl, 
                    "MarketValueInBaseCurrency": market_value,
                },
                "DisplayAndFormat": {"Symbol": symbol}
            })
        
        return {"Data": positions_list}
    
    def get_orders(self) -> Dict[str, Any]:
        return {"Data": []}
    
    def place_order(self, instrument: int, amount: int, buy_sell: str, order_type: str = "Market", price: Optional[float] = None, duration: str = "G.T.C") -> Dict[str, Any]:
        prices = self.get_prices([instrument])
        if not prices.get('Data'):
            return {"error": "Could not fetch price"}
        
        current_price = prices['Data'][0]['Quote']['Mid']
        symbol = prices['Data'][0]['DisplayAndFormat']['Symbol']
        is_buy = buy_sell.lower() == "buy"
        
        transaction_value_quote = amount * current_price
        transaction_value_usd = self._convert_value_to_usd(transaction_value_quote, instrument, current_price)

        if is_buy:
            if transaction_value_usd > self.balance:
                 return {"error": f"Insufficient funds. Cost: ${transaction_value_usd:,.2f}, Available: ${self.balance:,.2f}"}

            self.balance -= transaction_value_usd

            if instrument in self.positions:
                pos = self.positions[instrument]
                total_shares = pos['amount'] + amount
                new_avg_price = ((pos['amount'] * pos['open_price']) + (amount * current_price)) / total_shares
                
                self.positions[instrument]['amount'] = total_shares
                self.positions[instrument]['open_price'] = new_avg_price
                msg = f"Averaged {symbol}. New Price: {new_avg_price:.4f}"
            else:
                self.positions[instrument] = {
                    "amount": amount,
                    "open_price": current_price,
                    "symbol": symbol,
                    "opened_time": datetime.now()
                }
                msg = f"Bought {amount} {symbol} @ {current_price:.4f} (Cost: ${transaction_value_usd:,.2f})"

            return {"OrderId": f"PAPER_{int(time.time())}", "Status": "Filled", "Message": msg}

        else: # SELL
            if instrument not in self.positions:
                return {"error": "Cannot Sell: No position open"}
            
            pos = self.positions[instrument]
            if amount > pos['amount']:
                amount = pos['amount']
            
            sell_value_quote = amount * current_price
            sell_value_usd = self._convert_value_to_usd(sell_value_quote, instrument, current_price)
            
            self.balance += sell_value_usd
            
            self.positions[instrument]['amount'] -= amount
            if self.positions[instrument]['amount'] <= 0:
                del self.positions[instrument]
                
            return {
                "OrderId": f"PAPER_{int(time.time())}", 
                "Status": "Filled", 
                "Message": f"Sold {symbol}. Received: ${sell_value_usd:,.2f}"
            }

    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        return {"Message": "Order cancelled"}