import threading
import time
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import uuid

@dataclass
class PendingOrder:
    trigger_price: float
    order_id: str
    side: str        
    uic: int
    symbol: str
    amount: int
    trigger_condition: str 
    created_at: datetime = field(default_factory=datetime.now)

class OrderMonitor:
    def __init__(self, bot, app=None):
        self.bot = bot
        self.app = app 
        self.running = False
        self.monitor_thread = None
        self.orders: Dict[str, PendingOrder] = {}
        self.lock = threading.Lock()
    
    def start(self):
        if self.running: return
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
    
    def stop(self):
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
    
    def add_limit_order(self, uic: int, symbol: str, side: str, amount: int, 
                        limit_price: float) -> str:
        if side.lower() != 'buy':
            return None

        current_price = self._get_current_price(uic)
        
        if current_price is None:
            trigger_condition = 'le' 
        else:
            if limit_price > current_price:
                trigger_condition = 'ge' 
                type_str = "Stop/Breakout"
            else:
                trigger_condition = 'le'
                type_str = "Limit/Dip"

        order_id = str(uuid.uuid4())
        order = PendingOrder(
            trigger_price=limit_price,
            order_id=order_id,
            side='Buy', 
            uic=uic,
            symbol=symbol,
            amount=amount,
            trigger_condition=trigger_condition
        )
        
        with self.lock:
            self.orders[order_id] = order
        
        return order_id

    def get_pending_orders(self) -> List[PendingOrder]:
        with self.lock:
            return list(self.orders.values())

    def _get_current_price(self, uic: int) -> Optional[float]:
        try:
            prices = self.bot.get_fx_prices_unified([uic])
            if 'Data' in prices and len(prices['Data']) > 0:
                return prices['Data'][0]['Quote']['Mid']
        except Exception:
            pass
        return None

    def _monitor_loop(self):
        print("Order monitor loop started...")
        while self.running:
            try:
                with self.lock:
                    if not self.orders:
                        time.sleep(1)
                        continue
                    active_orders = list(self.orders.values())
                    uics_to_monitor = {order.uic for order in active_orders}
                
                try:
                    prices = self.bot.get_fx_prices_unified(list(uics_to_monitor))
                    if 'Data' not in prices:
                        time.sleep(0.5)
                        continue
                    
                    price_map = {}
                    for data in prices['Data']:
                        uic = data['Uic']
                        mid_price = data['Quote']['Mid']
                        price_map[uic] = mid_price
                    
                    self._check_triggers(active_orders, price_map)
                    
                except Exception as e:
                    print(f"[ERROR] {e}")
                
                time.sleep(0.5)
                
            except Exception as e:
                print(f"[ERROR] {e}")
    
    def _check_triggers(self, orders: List[PendingOrder], price_map: Dict[int, float]):
        for order in orders:
            current_price = price_map.get(order.uic)
            if current_price is None:
                continue

            triggered = False
            
            if order.trigger_condition == 'le': 
                if current_price <= order.trigger_price:
                    triggered = True
            
            elif order.trigger_condition == 'ge': 
                if current_price >= order.trigger_price:
                    triggered = True
            
            if triggered:
                self._execute_order(order, current_price)

    def _execute_order(self, order: PendingOrder, current_price: float):
        with self.lock:
            if order.order_id in self.orders:
                del self.orders[order.order_id]
            else:
                return 

        try:
            resp = self.bot.data_source.place_order(
                instrument=order.uic,
                amount=order.amount,
                buy_sell=order.side,
                order_type="Market"
            )
            
            if 'error' in resp:
                if self.app: 
                    self.app.notify(f"Order Failed: {resp['error']}", severity="error")
            else:
                msg = f"FILLED: {order.side} {order.symbol} at {current_price:.4f}"
                print(msg)
                if self.app: 
                    self.app.notify(msg, severity="information")
                
        except Exception as e:
            print(f"Execution Error: {e}")