from flask import Flask, request, jsonify, render_template_string
import requests
import os
import json
import re
import datetime

app = Flask(__name__)

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "").strip()
HTTP_TIMEOUT = 8
LLM_TIMEOUT = 20

COIN_MAP = {
    "btc": "BTCUSDT", "bitcoin": "BTCUSDT", "比特币": "BTCUSDT",
    "eth": "ETHUSDT", "ethereum": "ETHUSDT", "以太坊": "ETHUSDT",
    "sol": "SOLUSDT", "solana": "SOLUSDT",
    "bnb": "BNBUSDT",
    "xrp": "XRPUSDT", "ripple": "XRPUSDT",
    "ada": "ADAUSDT", "doge": "DOGEUSDT", "avax": "AVAXUSDT",
    "link": "LINKUSDT", "ltc": "LTCUSDT", "trx": "TRXUSDT",
    "dot": "DOTUSDT", "shib": "SHIBUSDT", "uni": "UNIUSDT",
}

SYMBOL_NAME = {
    "BTCUSDT": "Bitcoin", "ETHUSDT": "Ethereum", "SOLUSDT": "Solana",
    "BNBUSDT": "BNB", "XRPUSDT": "XRP", "ADAUSDT": "Cardano",
    "DOGEUSDT": "Dogecoin", "AVAXUSDT": "Avalanche",
    "LINKUSDT": "Chainlink", "LTCUSDT": "Litecoin", "TRXUSDT": "TRON",
    "DOTUSDT": "Polkadot", "SHIBUSDT": "Shiba Inu", "UNIUSDT": "Uniswap",
}

DEFAULT_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT",
    "DOGEUSDT", "AVAXUSDT", "LINKUSDT", "LTCUSDT", "TRXUSDT", "DOTUSDT",
]

PRODUCT_GROUPS = [
    {
        "id": "buy",
        "title": "买币与换币",
        "items": [
            {"name": "Convert 闪兑", "key": "convert", "desc": "快速币币兑换，适合小额、低操作成本的换币场景。"},
            {"name": "P2P 交易", "key": "p2p", "desc": "用户之间用法币买卖数字资产，重点看商家信誉和付款安全。"},
            {"name": "银行卡买币", "key": "fiat", "desc": "通过银行卡或第三方通道买币，费用和可用地区会变化。"},
        ],
    },
    {
        "id": "base",
        "title": "基础交易",
        "items": [
            {"name": "Spot 现货", "key": "spot", "desc": "买卖真实持仓资产，适合基础交易和长期观察。"},
            {"name": "Margin 杠杆", "key": "margin", "desc": "借贷放大仓位，有利息、强平和爆仓风险。"},
        ],
    },
    {
        "id": "derivatives",
        "title": "衍生品",
        "items": [
            {"name": "USD-M Futures U本位合约", "key": "usdm", "desc": "以 USDT/USDC 计价结算的永续或交割合约。"},
            {"name": "COIN-M Futures 币本位合约", "key": "coinm", "desc": "以币本身作为保证金和结算资产。"},
            {"name": "Options 期权", "key": "options", "desc": "用权利金表达方向、波动率和保护策略。"},
        ],
    },
    {
        "id": "automation",
        "title": "策略与自动化",
        "items": [
            {"name": "Trading Bots 交易机器人", "key": "bots", "desc": "网格、定投、套利等自动化策略入口。"},
            {"name": "Copy Trading 跟单", "key": "copy", "desc": "跟随交易员策略，重点看回撤、周期和仓位。"},
            {"name": "API Trading", "key": "api", "desc": "程序化下单和风控，适合有开发能力的用户。"},
        ],
    },
    {
        "id": "capital",
        "title": "资金与收益",
        "items": [
            {"name": "Earn 理财", "key": "earn", "desc": "活期、定期、质押等收益产品，不等同于无风险。"},
            {"name": "Loans 借贷", "key": "loans", "desc": "抵押借币或资金周转，需要关注质押率和清算风险。"},
        ],
    },
]


def binance_get(url, params=None):
    res = requests.get(url, params=params or {}, timeout=HTTP_TIMEOUT)
    res.raise_for_status()
    return res.json()


def parse_symbol(text):
    lower = text.lower()
    for key, symbol in COIN_MAP.items():
        if key in lower:
            return symbol

    match = re.search(r"\b([a-z]{2,10})(?:usdt|/usdt)?\b", lower)
    if match:
        base = match.group(1).upper()
        return base if base.endswith("USDT") else base + "USDT"

    return "BTCUSDT"


def detect_market_type(text):
    lower = text.lower()
    if any(k in lower for k in ["币本位", "coinm", "coin-m"]):
        return "coinm"
    if any(k in lower for k in ["u本位", "usdm", "usd-m", "永续", "perp", "futures", "合约"]):
        return "usdm"
    if any(k in lower for k in ["杠杆", "margin"]):
        return "margin"
    return "spot"


def market_endpoint(market_type):
    if market_type == "usdm":
        return "https://fapi.binance.com/fapi/v1/ticker/24hr"
    if market_type == "coinm":
        return "https://dapi.binance.com/dapi/v1/ticker/24hr"
    return "https://api.binance.com/api/v3/ticker/24hr"


def kline_endpoint(market_type):
    if market_type == "usdm":
        return "https://fapi.binance.com/fapi/v1/klines"
    if market_type == "coinm":
        return "https://dapi.binance.com/dapi/v1/klines"
    return "https://api.binance.com/api/v3/klines"


def coinm_symbol(symbol):
    return symbol.replace("USDT", "") + "USD_PERP"


def normalize_symbol(symbol, market_type):
    return coinm_symbol(symbol) if market_type == "coinm" else symbol


def get_market_rows(market_type="spot"):
    if market_type not in ["spot", "margin", "usdm", "coinm"]:
        market_type = "spot"

    try:
        if market_type == "coinm":
            symbols = [coinm_symbol(s) for s in DEFAULT_SYMBOLS[:8]]
            rows = binance_get(market_endpoint(market_type))
            rows = [r for r in rows if r.get("symbol") in set(symbols)]
        else:
            symbols = DEFAULT_SYMBOLS
            rows = binance_get(market_endpoint(market_type), {"symbols": json.dumps(symbols)})

        result = []
        for row in rows:
            raw_symbol = row.get("symbol", "")
            display_symbol = raw_symbol.replace("USD_PERP", "USDT")
            result.append({
                "symbol": display_symbol,
                "marketSymbol": raw_symbol,
                "name": SYMBOL_NAME.get(display_symbol, display_symbol.replace("USDT", "")),
                "price": float(row.get("lastPrice", 0)),
                "change": round(float(row.get("priceChangePercent", 0)), 2),
                "volume": float(row.get("quoteVolume", row.get("volume", 0))),
                "category": market_type,
            })

        return sorted(result, key=lambda x: x["volume"], reverse=True)[:12]
    except Exception:
        return []


def get_kline(symbol, market_type="spot", days=1):
    try:
        target = normalize_symbol(symbol, market_type)
        interval = "1h" if days <= 7 else "4h"
        rows = binance_get(
            kline_endpoint(market_type),
            {"symbol": target, "interval": interval, "limit": 72},
        )

        labels = []
        prices = []
        for row in rows[-72:]:
            t = datetime.datetime.fromtimestamp(row[0] / 1000)
            labels.append(t.strftime("%m/%d %H:%M") if days > 1 else t.strftime("%H:%M"))
            prices.append(round(float(row[4]), 4))

        return labels, prices
    except Exception:
        return [], []


def product_text(key):
    for group in PRODUCT_GROUPS:
        for item in group["items"]:
            if item["key"] == key:
                return (
                    item["name"] + "\n\n" +
                    item["desc"] + "\n\n" +
                    "我可以继续帮你按 BTC/ETH/SOL 等币种做行情、风险、适用场景和操作注意点分析。"
                )
    return ""


HTML = """<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CryptoVision</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js"></script>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  background: #0f172a;
  color: #172033;
  height: 100vh;
  overflow: hidden;
}
.app {
  height: 100vh;
  display: grid;
  grid-template-rows: auto 1fr auto;
  background:
    radial-gradient(circle at top left, rgba(247,147,26,.20), transparent 28rem),
    linear-gradient(135deg, #eef2f8 0%, #f8fafc 42%, #e8edf6 100%);
}
.topbar {
  border-bottom: 1px solid rgba(148,163,184,.22);
  background: rgba(255,255,255,.92);
  backdrop-filter: blur(18px);
}
.topbar-inner {
  max-width: 1440px;
  margin: 0 auto;
  padding: 14px 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.brand { display: flex; align-items: center; gap: 12px; }
.brand-mark {
  width: 42px;
  height: 42px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  color: #f7931a;
  background: #fff7ed;
  border: 1px solid #fed7aa;
  font-weight: 900;
}
.brand-title { font-size: 21px; font-weight: 900; color: #111827; }
.brand-sub { color: #64748b; font-size: 12px; margin-top: 2px; }
.status-pill {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  color: #15803d;
  background: #ecfdf3;
  border: 1px solid #bbf7d0;
  padding: 6px 11px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
}
.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #22c55e;
  box-shadow: 0 0 0 4px rgba(34,197,94,.12);
}
.main {
  min-height: 0;
  max-width: 1440px;
  width: 100%;
  margin: 0 auto;
  padding: 18px 24px;
  display: grid;
  grid-template-columns: 270px minmax(0, 1fr) 350px;
  gap: 16px;
}
.panel {
  background: rgba(255,255,255,.94);
  border: 1px solid rgba(148,163,184,.24);
  border-radius: 14px;
  box-shadow: 0 18px 40px rgba(15,23,42,.08);
  overflow: hidden;
}
.panel-head {
  padding: 14px 15px;
  border-bottom: 1px solid #e8edf5;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.panel-title { font-weight: 900; color: #111827; font-size: 14px; }
.panel-note { color: #64748b; font-size: 12px; margin-top: 2px; }
.tabs {
  display: grid;
  gap: 8px;
  padding: 12px;
}
.tab {
  width: 100%;
  text-align: left;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  color: #334155;
  border-radius: 10px;
  padding: 10px 11px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 800;
}
.tab span {
  display: block;
  color: #64748b;
  font-size: 11px;
  font-weight: 600;
  margin-top: 3px;
}
.tab:hover, .tab.active {
  border-color: #f7931a;
  background: #fff7ed;
  color: #9a4b00;
}
.product-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0,1fr));
  gap: 10px;
  padding: 12px;
  max-height: 355px;
  overflow: auto;
}
.product-card {
  border: 1px solid #e2e8f0;
  background: #fff;
  border-radius: 12px;
  padding: 11px;
  cursor: pointer;
}
.product-card:hover {
  border-color: #f7931a;
  box-shadow: 0 8px 18px rgba(247,147,26,.12);
}
.product-name {
  font-size: 12px;
  font-weight: 900;
  color: #111827;
  line-height: 1.35;
}
.product-desc {
  color: #64748b;
  font-size: 11px;
  line-height: 1.45;
  margin-top: 5px;
}
.hero {
  display: grid;
  grid-template-columns: repeat(4, minmax(0,1fr));
  gap: 10px;
  margin-bottom: 14px;
}
.market-card {
  background: rgba(255,255,255,.96);
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  padding: 14px;
  cursor: pointer;
  min-height: 112px;
  box-shadow: 0 12px 28px rgba(15,23,42,.07);
}
.market-card:hover { border-color: #f7931a; }
.market-symbol {
  color: #64748b;
  font-size: 11px;
  font-weight: 900;
  letter-spacing: .08em;
}
.market-price {
  margin-top: 9px;
  color: #111827;
  font-size: 22px;
  font-weight: 950;
}
.change {
  display: inline-flex;
  margin-top: 8px;
  padding: 4px 8px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 900;
}
.up { color: #15803d; background: #ecfdf3; }
.down { color: #dc2626; background: #fef2f2; }
.muted { color: #64748b; background: #f1f5f9; }
.chat-panel {
  height: calc(100vh - 295px);
  min-height: 450px;
  display: grid;
  grid-template-rows: auto 1fr;
}
.chat-scroll {
  overflow: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  background:
    linear-gradient(#fff, #fff) padding-box,
    radial-gradient(circle at top right, rgba(99,102,241,.08), transparent 24rem);
}
.msg { display: flex; gap: 10px; align-items: flex-start; }
.msg.user { flex-direction: row-reverse; }
.avatar {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  display: grid;
  place-items: center;
  font-size: 12px;
  font-weight: 900;
  flex: 0 0 auto;
}
.ai-avatar {
  color: #f7931a;
  background: #fff7ed;
  border: 1px solid #fed7aa;
}
.user-avatar {
  color: #334155;
  background: #e2e8f0;
  border: 1px solid #cbd5e1;
}
.bubble {
  max-width: min(820px, calc(100% - 52px));
  padding: 13px 15px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.65;
}
.ai-bubble {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  color: #283447;
}
.user-bubble { background: #111827; color: #fff; }
.chart-box, .table-box {
  max-width: 860px;
  width: 100%;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 15px;
}
.chart-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.chart-title, .table-title { font-weight: 900; color: #111827; }
.chart-wrap { height: 250px; position: relative; }
.chart-meta {
  display: flex;
  gap: 14px;
  flex-wrap: wrap;
  color: #64748b;
  font-size: 12px;
  border-top: 1px solid #e2e8f0;
  padding-top: 10px;
  margin-top: 10px;
}
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th, td {
  padding: 10px 8px;
  border-top: 1px solid #eef2f7;
  text-align: right;
}
th { color: #64748b; font-size: 11px; }
th:first-child, td:first-child { text-align: left; }
.ticker { font-weight: 900; color: #111827; }
.ticker-name { color: #64748b; font-size: 11px; margin-top: 2px; }
.market-table {
  overflow: auto;
  max-height: 315px;
  padding: 0 12px 12px;
}
.quick-card {
  padding: 13px;
  border-top: 1px solid #e8edf5;
}
.quick-title {
  font-size: 12px;
  color: #64748b;
  font-weight: 900;
  letter-spacing: .08em;
  margin-bottom: 9px;
}
.quick-list { display: grid; gap: 8px; }
.quick-btn {
  border: 1px solid #e2e8f0;
  background: #f8fafc;
  color: #334155;
  border-radius: 10px;
  padding: 10px;
  font-size: 13px;
  cursor: pointer;
  text-align: left;
}
.quick-btn:hover {
  border-color: #f7931a;
  background: #fff7ed;
}
.input-area {
  border-top: 1px solid rgba(148,163,184,.28);
  background: rgba(255,255,255,.94);
  backdrop-filter: blur(18px);
}
.input-inner {
  max-width: 1440px;
  margin: 0 auto;
  padding: 12px 24px 16px;
}
.chips {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  margin-bottom: 10px;
}
.chip {
  border: 1px solid #e2e8f0;
  background: #f8fafc;
  color: #334155;
  border-radius: 999px;
  padding: 8px 12px;
  font-size: 13px;
  cursor: pointer;
  white-space: nowrap;
}
.chip:hover {
  background: #fff7ed;
  border-color: #f7931a;
  color: #9a4b00;
}
.ask-row { display: flex; gap: 10px; }
#inp {
  flex: 1;
  min-width: 0;
  height: 48px;
  border: 1px solid #cbd5e1;
  background: #f8fafc;
  border-radius: 12px;
  padding: 0 15px;
  font-size: 14px;
  outline: none;
}
#inp:focus {
  border-color: #f7931a;
  box-shadow: 0 0 0 3px rgba(247,147,26,.13);
  background: #fff;
}
#send {
  width: 54px;
  border: 0;
  border-radius: 12px;
  background: #f7931a;
  color: #fff;
  font-size: 18px;
  cursor: pointer;
  box-shadow: 0 10px 22px rgba(247,147,26,.25);
}
#send:disabled, .chip:disabled, .quick-btn:disabled, .tab:disabled {
  opacity: .45;
  cursor: not-allowed;
}
.dots span {
  display: inline-block;
  width: 6px;
  height: 6px;
  margin: 0 2px;
  border-radius: 50%;
  background: #f7931a;
  animation: bounce 1.1s infinite;
}
.dots span:nth-child(2) { animation-delay: .18s; }
.dots span:nth-child(3) { animation-delay: .36s; }
@keyframes bounce {
  0%,60%,100% { transform: translateY(0); }
  30% { transform: translateY(-5px); }
}
@media (max-width: 1180px) {
  .main { grid-template-columns: 240px 1fr; }
  .side-right { display: none; }
  .hero { grid-template-columns: repeat(2, minmax(0,1fr)); }
}
@media (max-width: 820px) {
  body { overflow: auto; }
  .app { min-height: 100vh; height: auto; }
  .main { grid-template-columns: 1fr; padding: 12px; }
  .side-left { order: 2; }
  .center { order: 1; }
  .chat-panel { height: auto; min-height: 440px; }
  .hero { grid-template-columns: 1fr; }
  .product-grid { grid-template-columns: 1fr; max-height: none; }
  .topbar-inner, .input-inner { padding-left: 14px; padding-right: 14px; }
  .brand-sub { display: none; }
}
</style>
</head>
<body>
<div class="app">
  <header class="topbar">
    <div class="topbar-inner">
      <div class="brand">
        <div class="brand-mark">B</div>
        <div>
          <div class="brand-title">CryptoVision</div>
          <div class="brand-sub">Binance-style AI market workstation</div>
        </div>
      </div>
      <div class="status-pill"><span class="dot"></span>Binance market data</div>
    </div>
  </header>

  <main class="main">
    <aside class="panel side-left">
      <div class="panel-head">
        <div>
          <div class="panel-title">交易分类</div>
          <div class="panel-note">覆盖 Binance 常见入口</div>
        </div>
      </div>
      <div class="tabs" id="groupTabs"></div>
      <div class="product-grid" id="productGrid"></div>
    </aside>

    <section class="center">
      <div class="hero" id="heroCards">
        <div class="market-card"><div class="market-symbol">BTCUSDT</div><div class="market-price">Loading</div><div class="change muted">Waiting</div></div>
        <div class="market-card"><div class="market-symbol">ETHUSDT</div><div class="market-price">Loading</div><div class="change muted">Waiting</div></div>
        <div class="market-card"><div class="market-symbol">SOLUSDT</div><div class="market-price">Loading</div><div class="change muted">Waiting</div></div>
        <div class="market-card"><div class="market-symbol">BNBUSDT</div><div class="market-price">Loading</div><div class="change muted">Waiting</div></div>
      </div>

      <div class="panel chat-panel">
        <div class="panel-head">
          <div>
            <div class="panel-title">CryptoVision AI</div>
            <div class="panel-note">问现货、杠杆、U本位、币本位、期权、机器人、P2P、Earn 都可以</div>
          </div>
          <div class="status-pill"><span class="dot"></span>Ready</div>
        </div>
        <div class="chat-scroll" id="chatArea">
          <div class="msg">
            <div class="avatar ai-avatar">AI</div>
            <div class="bubble ai-bubble">我已经按 Binance 的交易入口整理好了：买币换币、基础交易、衍生品、策略自动化、资金收益。你可以直接问「BTC U本位合约图」「现货市场排行」「杠杆和合约区别」「P2P 风险」等。</div>
          </div>
        </div>
      </div>
    </section>

    <aside class="panel side-right">
      <div class="panel-head">
        <div>
          <div class="panel-title">市场排行</div>
          <div class="panel-note" id="tableTitle">SPOT</div>
        </div>
      </div>
      <div class="market-table" id="marketTable"></div>
      <div class="quick-card">
        <div class="quick-title">快速分析</div>
        <div class="quick-list">
          <button class="quick-btn" onclick="doSend('现货 market overview')">现货市场概览</button>
          <button class="quick-btn" onclick="doSend('BTC U本位合约 chart')">BTC U本位合约图</button>
          <button class="quick-btn" onclick="doSend('杠杆和合约有什么区别')">杠杆 vs 合约</button>
          <button class="quick-btn" onclick="doSend('P2P交易有什么风险')">P2P 风险清单</button>
          <button class="quick-btn" onclick="doSend('Trading Bots适合什么行情')">机器人适用行情</button>
        </div>
      </div>
    </aside>
  </main>

  <footer class="input-area">
    <div class="input-inner">
      <div class="chips">
        <button class="chip" onclick="loadMarket('spot'); doSend('现货 market overview')">Spot 现货</button>
        <button class="chip" onclick="loadMarket('margin'); doSend('Margin 杠杆说明')">Margin 杠杆</button>
        <button class="chip" onclick="loadMarket('usdm'); doSend('BTC U本位合约 chart')">U本位合约</button>
        <button class="chip" onclick="loadMarket('coinm'); doSend('BTC 币本位合约 chart')">币本位合约</button>
        <button class="chip" onclick="doSend('Options 期权适合什么场景')">Options 期权</button>
        <button class="chip" onclick="doSend('Binance所有交易类型分类')">全部类型</button>
      </div>
      <div class="ask-row">
        <input id="inp" placeholder="例如：BTC U本位合约图 / SOL 现货趋势 / Binance所有交易类型分类 / P2P风险..." />
        <button id="send" onclick="doSend()">&#9658;</button>
      </div>
    </div>
  </footer>
</div>

<script>
var busy = false;
var activeGroup = 'buy';
var activeMarket = 'spot';
var chatHistory = [];
var productGroups = PRODUCT_GROUPS_PLACEHOLDER;

function escapeHtml(value) {
  return String(value == null ? '' : value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function nl2br(value) {
  return escapeHtml(value).replace(/\\n/g, '<br>');
}

function setBusy(value) {
  busy = value;
  document.getElementById('send').disabled = value;
  document.getElementById('inp').disabled = value;
  document.querySelectorAll('.chip,.quick-btn,.tab').forEach(function(el) {
    el.disabled = value;
  });
}

function renderGroups() {
  var box = document.getElementById('groupTabs');
  box.innerHTML = productGroups.map(function(group) {
    var active = group.id === activeGroup ? ' active' : '';
    return '<button class="tab' + active + '" onclick="selectGroup(\\'' + group.id + '\\')">' +
      escapeHtml(group.title) + '<span>' + group.items.length + ' products</span></button>';
  }).join('');
  renderProducts();
}

function selectGroup(id) {
  activeGroup = id;
  renderGroups();
}

function renderProducts() {
  var group = productGroups.find(function(item) { return item.id === activeGroup; }) || productGroups[0];
  var box = document.getElementById('productGrid');

  box.innerHTML = group.items.map(function(item) {
    return '<div class="product-card" onclick="doSend(\\'' + item.name.replace(/'/g, '') + ' 是什么，适合什么场景\\')">' +
      '<div class="product-name">' + escapeHtml(item.name) + '</div>' +
      '<div class="product-desc">' + escapeHtml(item.desc) + '</div>' +
    '</div>';
  }).join('');
}

function loadMarket(type) {
  activeMarket = type || 'spot';
  document.getElementById('tableTitle').textContent = activeMarket.toUpperCase();

  fetch('/markets?type=' + encodeURIComponent(activeMarket))
    .then(function(r) { return r.json(); })
    .then(function(rows) {
      renderHero(rows);
      renderMarketTable(rows);
    })
    .catch(function() {
      renderHero([]);
      renderMarketTable([]);
    });
}

function renderHero(rows) {
  var wanted = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT'];
  var map = {};
  rows.forEach(function(row) { map[row.symbol] = row; });

  document.getElementById('heroCards').innerHTML = wanted.map(function(symbol) {
    var row = map[symbol];

    if (!row) {
      return '<div class="market-card" onclick="doSend(\\'' + symbol + ' chart\\')"><div class="market-symbol">' + symbol + '</div><div class="market-price">Unavailable</div><div class="change muted">Retry later</div></div>';
    }

    var up = row.change >= 0;

    return '<div class="market-card" onclick="doSend(\\'' + symbol.replace('USDT','') + ' ' + activeMarket + ' chart\\')">' +
      '<div class="market-symbol">' + escapeHtml(symbol) + '</div>' +
      '<div class="market-price">$' + Number(row.price).toLocaleString('en-US', { maximumFractionDigits: 4 }) + '</div>' +
      '<div class="change ' + (up ? 'up' : 'down') + '">' + (up ? '+' : '') + row.change + '%</div>' +
    '</div>';
  }).join('');
}

function renderMarketTable(rows) {
  var box = document.getElementById('marketTable');

  if (!rows || !rows.length) {
    box.innerHTML = '<div style="padding:14px;color:#64748b;font-size:13px;">Market data temporarily unavailable.</div>';
    return;
  }

  var html = '<table><tr><th>Pair</th><th>Price</th><th>24h</th><th>Volume</th></tr>';

  rows.slice(0, 10).forEach(function(row) {
    var up = row.change >= 0;

    html += '<tr onclick="doSend(\\'' + row.symbol.replace('USDT','') + ' ' + activeMarket + ' chart\\')" style="cursor:pointer;">' +
      '<td><div class="ticker">' + escapeHtml(row.symbol) + '</div><div class="ticker-name">' + escapeHtml(row.name) + '</div></td>' +
      '<td>$' + Number(row.price).toLocaleString('en-US', { maximumFractionDigits: 4 }) + '</td>' +
      '<td><span class="change ' + (up ? 'up' : 'down') + '">' + (up ? '+' : '') + row.change + '%</span></td>' +
      '<td>$' + (Number(row.volume) / 1e9).toFixed(2) + 'B</td>' +
    '</tr>';
  });

  html += '</table>';
  box.innerHTML = html;
}

function doSend(text) {
  if (busy) return;

  var input = document.getElementById('inp');
  var msg = text || input.value.trim();

  if (!msg) return;

  input.value = '';
  addUser(msg);
  chatHistory.push({role: 'user', content: msg});
  setBusy(true);

  var typing = addTyping();

  fetch('/chat', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({messages: chatHistory})
  })
    .then(function(r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    })
    .then(function(data) {
      typing.remove();

      if (data.type === 'chart') addChart(data);
      else if (data.type === 'table') addTable(data);
      else addAI(data.reply || 'No response received.');

      chatHistory.push({role: 'assistant', content: data.reply || data.summary || ''});
      setBusy(false);
    })
    .catch(function() {
      typing.remove();
      addAI('Network error, please retry.');
      chatHistory.pop();
      setBusy(false);
    });
}

document.getElementById('inp').addEventListener('keydown', function(e) {
  if (e.key === 'Enter' && !busy) doSend();
});

function addUser(text) {
  var row = document.createElement('div');
  row.className = 'msg user';
  row.innerHTML = '<div class="avatar user-avatar">U</div><div class="bubble user-bubble">' + nl2br(text) + '</div>';
  document.getElementById('chatArea').appendChild(row);
  scrollChat();
}

function addAI(text) {
  var row = document.createElement('div');
  row.className = 'msg';
  row.innerHTML = '<div class="avatar ai-avatar">AI</div><div class="bubble ai-bubble">' + nl2br(text) + '</div>';
  document.getElementById('chatArea').appendChild(row);
  scrollChat();
}

function addTyping() {
  var row = document.createElement('div');
  row.className = 'msg';
  row.innerHTML = '<div class="avatar ai-avatar">AI</div><div class="bubble ai-bubble"><div class="dots"><span></span><span></span><span></span></div></div>';
  document.getElementById('chatArea').appendChild(row);
  scrollChat();
  return row;
}

function addChart(data) {
  var prices = data.prices || [];

  if (!prices.length) {
    addAI('Chart data is unavailable right now.');
    return;
  }

  var id = 'chart' + Date.now();
  var up = prices[prices.length - 1] >= prices[0];
  var row = document.createElement('div');

  row.className = 'msg';
  row.innerHTML =
    '<div class="avatar ai-avatar">AI</div><div class="chart-box">' +
    '<div class="chart-head"><div class="chart-title">' + escapeHtml(data.title) + '</div><span class="change ' + (up ? 'up' : 'down') + '">' + (up ? '+' : '') + data.change + '%</span></div>' +
    '<div class="chart-wrap"><canvas id="' + id + '"></canvas></div>' +
    '<div class="chart-meta"><span>Current: $' + Number(prices[prices.length - 1]).toLocaleString('en-US', { maximumFractionDigits: 4 }) + '</span><span>High: $' + data.high + '</span><span>Low: $' + data.low + '</span><span>' + escapeHtml(data.marketLabel) + '</span></div>' +
    '</div>';

  document.getElementById('chatArea').appendChild(row);
  scrollChat();

  setTimeout(function() {
    var canvas = document.getElementById(id);
    if (!canvas) return;

    new Chart(canvas.getContext('2d'), {
      type: 'line',
      data: {
        labels: data.labels,
        datasets: [{
          data: prices,
          borderColor: up ? '#16a34a' : '#dc2626',
          backgroundColor: up ? 'rgba(22,163,74,.08)' : 'rgba(220,38,38,.08)',
          borderWidth: 2,
          pointRadius: 0,
          tension: .35,
          fill: true
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { display: false }, ticks: { color: '#94a3b8', maxTicksLimit: 6 } },
          y: { grid: { color: '#eef2f7' }, ticks: { color: '#94a3b8', maxTicksLimit: 5 } }
        }
      }
    });
  }, 80);
}

function addTable(data) {
  var row = document.createElement('div');
  row.className = 'msg';

  var html = '<div class="avatar ai-avatar">AI</div><div class="table-box"><div class="table-title">' + escapeHtml(data.title || 'Market') + '</div><table><tr><th>Pair</th><th>Price</th><th>24h</th><th>Volume</th></tr>';

  (data.rows || []).forEach(function(item) {
    var up = item.change >= 0;

    html += '<tr><td><div class="ticker">' + escapeHtml(item.symbol) + '</div><div class="ticker-name">' + escapeHtml(item.name) + '</div></td><td>$' + Number(item.price).toLocaleString('en-US', { maximumFractionDigits: 4 }) + '</td><td><span class="change ' + (up ? 'up' : 'down') + '">' + (up ? '+' : '') + item.change + '%</span></td><td>$' + (Number(item.volume) / 1e9).toFixed(2) + 'B</td></tr>';
  });

  html += '</table><div class="chart-meta">' + escapeHtml(data.summary || '') + '</div></div>';

  row.innerHTML = html;
  document.getElementById('chatArea').appendChild(row);
  scrollChat();
}

function scrollChat() {
  var area = document.getElementById('chatArea');
  setTimeout(function() {
    area.scrollTop = area.scrollHeight;
  }, 60);
}

renderGroups();
loadMarket('spot');
</script>
</body>
</html>"""

HTML = HTML.replace("PRODUCT_GROUPS_PLACEHOLDER", json.dumps(PRODUCT_GROUPS, ensure_ascii=False))


@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/markets")
def markets():
    market_type = request.args.get("type", "spot")
    return jsonify(get_market_rows(market_type))


@app.route("/top_prices")
def top_prices():
    return jsonify(get_market_rows("spot"))


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    messages = data.get("messages", [])

    if not isinstance(messages, list):
        messages = []

    user_msg = messages[-1].get("content", "") if messages and isinstance(messages[-1], dict) else ""

    if not isinstance(user_msg, str):
        user_msg = str(user_msg or "")

    user_msg = user_msg.strip()

    if not user_msg:
        return jsonify({"type": "text", "reply": "请输入一个币种、交易类型或市场问题。"})

    lower = user_msg.lower()
    market_type = detect_market_type(user_msg)
    symbol = parse_symbol(user_msg)

    if "所有交易类型" in user_msg or "全部类型" in user_msg or "分类" in user_msg:
        lines = []
        for group in PRODUCT_GROUPS:
            lines.append(group["title"])
            for item in group["items"]:
                lines.append("- " + item["name"] + ": " + item["desc"])
        return jsonify({"type": "text", "reply": "\n".join(lines)})

    if any(k in lower for k in ["market", "overview", "top", "list", "排行", "市场", "概览"]):
        rows = get_market_rows(market_type
