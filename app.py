
from flask import Flask, request, jsonify, render_template_string
import requests
import datetime
import json
import os
import datetime
import re

import requests


app = Flask(__name__)
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "").strip()
HTTP_TIMEOUT = 8
LLM_TIMEOUT = 20


COIN_MAP = {
    "bitcoin": "bitcoin", "btc": "bitcoin",
    "ethereum": "ethereum", "eth": "ethereum",
    "solana": "solana", "sol": "solana",
    "bnb": "binancecoin",
    "doge": "dogecoin", "dogecoin": "dogecoin",
    "xrp": "ripple", "ripple": "ripple",
    "ada": "cardano", "cardano": "cardano",
    "avax": "avalanche-2",
    "dot": "polkadot",
    "shib": "shiba-inu",
    "ltc": "litecoin",
    "link": "chainlink",
    "uni": "uniswap",
    "trx": "tron",
    "matic": "matic-network",
    "bitcoin": "BTCUSDT", "btc": "BTCUSDT", "比特币": "BTCUSDT",
    "ethereum": "ETHUSDT", "eth": "ETHUSDT", "以太坊": "ETHUSDT",
    "solana": "SOLUSDT", "sol": "SOLUSDT",
    "bnb": "BNBUSDT",
    "xrp": "XRPUSDT", "ripple": "XRPUSDT",
    "ada": "ADAUSDT", "cardano": "ADAUSDT",
    "doge": "DOGEUSDT", "dogecoin": "DOGEUSDT",
    "avax": "AVAXUSDT",
    "link": "LINKUSDT",
    "ltc": "LTCUSDT",
    "trx": "TRXUSDT",
    "dot": "DOTUSDT",
    "shib": "SHIBUSDT",
    "uni": "UNIUSDT",
}

SYMBOL_MAP = {
    "bitcoin": "BTC", "ethereum": "ETH", "binancecoin": "BNB",
    "dogecoin": "DOGE", "solana": "SOL", "ripple": "XRP",
    "cardano": "ADA", "avalanche-2": "AVAX", "polkadot": "DOT",
    "shiba-inu": "SHIB", "litecoin": "LTC", "chainlink": "LINK",
    "uniswap": "UNI", "tron": "TRX", "matic-network": "MATIC",
SYMBOL_NAME = {
    "BTCUSDT": "Bitcoin",
    "ETHUSDT": "Ethereum",
    "SOLUSDT": "Solana",
    "BNBUSDT": "BNB",
    "XRPUSDT": "XRP",
    "ADAUSDT": "Cardano",
    "DOGEUSDT": "Dogecoin",
    "AVAXUSDT": "Avalanche",
    "LINKUSDT": "Chainlink",
    "LTCUSDT": "Litecoin",
    "TRXUSDT": "TRON",
    "DOTUSDT": "Polkadot",
    "SHIBUSDT": "Shiba Inu",
    "UNIUSDT": "Uniswap",
}

NAME_MAP = {
    "bitcoin": "Bitcoin", "ethereum": "Ethereum", "binancecoin": "BNB",
    "dogecoin": "Dogecoin", "solana": "Solana", "ripple": "XRP",
    "cardano": "Cardano", "avalanche-2": "Avalanche", "polkadot": "Polkadot",
    "shiba-inu": "Shiba Inu", "litecoin": "Litecoin", "chainlink": "Chainlink",
    "uniswap": "Uniswap", "tron": "TRON", "matic-network": "Polygon",
}
DEFAULT_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT",
    "DOGEUSDT", "AVAXUSDT", "LINKUSDT", "LTCUSDT", "TRXUSDT", "DOTUSDT",
]

BINANCE_SYMBOLS = {
    "bitcoin": "BTCUSDT",
    "ethereum": "ETHUSDT",
    "solana": "SOLUSDT",
    "binancecoin": "BNBUSDT",
    "ripple": "XRPUSDT",
    "cardano": "ADAUSDT",
    "dogecoin": "DOGEUSDT",
    "avalanche-2": "AVAXUSDT",
    "polkadot": "DOTUSDT",
    "shiba-inu": "SHIBUSDT",
    "litecoin": "LTCUSDT",
    "chainlink": "LINKUSDT",
    "uniswap": "UNIUSDT",
