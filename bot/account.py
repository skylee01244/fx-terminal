import requests

BASE_URL = "https://gateway.saxobank.com/sim/openapi"


def get_user_info(headers):
    url = f"{BASE_URL}/port/v1/users/me"
    return requests.get(url, headers=headers).json()

def get_client_info(headers):
    url = f"{BASE_URL}/port/v1/clients/me"
    return requests.get(url, headers=headers).json()

def get_accounts(headers):
    url = f"{BASE_URL}/port/v1/accounts/me"
    return requests.get(url, headers=headers).json()

def get_balance(headers, client_key, account_key):
    url = f"{BASE_URL}/port/v1/balances?ClientKey={client_key}&AccountKey={account_key}"
    return requests.get(url, headers=headers).json()

def get_positions(headers, client_key):
    url = f"{BASE_URL}/port/v1/positions?ClientKey={client_key}&FieldGroups=DisplayAndFormat,PositionBase,PositionView"
    return requests.get(url, headers=headers).json()
