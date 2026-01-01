"""
Orders module - Functions to retrieve and manage orders via Saxo API.
"""

import requests

BASE_URL = "https://gateway.saxobank.com/sim/openapi"


def get_orders(headers, client_key):
    """
    Get all open orders for the account.
    
    Returns:
        dict: Orders data from Saxo API
    """
    url = f"{BASE_URL}/port/v1/orders?ClientKey={client_key}&FieldGroups=DisplayAndFormat,ExchangeInfo"
    try:
        response = requests.get(url, headers=headers)
        return response.json()
    except Exception as e:
        return {"error": str(e)}


def cancel_order(headers, account_key, order_id):
    """
    Cancel an open order.
    
    Args:
        headers: API authentication headers
        account_key: Account key
        order_id: ID of the order to cancel
        
    Returns:
        dict: Response from Saxo API
    """
    url = f"{BASE_URL}/trade/v2/orders/{order_id}?AccountKey={account_key}"
    try:
        response = requests.delete(url, headers=headers)
        return response.json() if response.text else {"Message": "Order cancelled"}
    except Exception as e:
        return {"error": str(e)}


def modify_order(headers, account_key, order_id, new_price=None, new_amount=None):
    """
    Modify an existing order.
    
    Args:
        headers: API authentication headers
        account_key: Account key
        order_id: ID of the order to modify
        new_price: New order price (optional)
        new_amount: New order amount (optional)
        
    Returns:
        dict: Response from Saxo API
    """
    url = f"{BASE_URL}/trade/v2/orders/{order_id}"
    
    data = {
        "AccountKey": account_key
    }
    
    if new_price is not None:
        data["OrderPrice"] = new_price
    
    if new_amount is not None:
        data["Amount"] = new_amount
    
    try:
        response = requests.patch(url, json=data, headers=headers)
        return response.json()
    except Exception as e:
        return {"error": str(e)}
