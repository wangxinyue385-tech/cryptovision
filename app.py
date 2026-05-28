from flask import Flask, request, jsonify, render_template_string
import requests
import os
import datetime
import json

app = Flask(__name__)

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
}

SYMBOL_MAP = {
    "bitcoin": "BTC", "ethereum": "ETH", "binancecoin": "BNB",
    "dogecoin": "DOGE", "solana": "SOL", "ripple": "XRP",
    "cardano": "ADA", "avalanche-2": "AVAX", "polkadot": "DOT",
    "shiba-inu": "SHIB", "litecoin": "LTC", "chainlink": "LINK",
    "uniswap": "UNI", "tron": "TRX", "matic-network": "MATIC",
}

NAME_MAP = {
    "bitcoin": "Bitcoin", "ethereum": "Ethereum", "binancecoin": "BNB",
    "dogecoin": "Dogecoin", "solana": "Solana", "ripple": "XRP",
    "cardano": "Cardano", "avalanche-2": "Avalanche", "polkadot": "Polkadot",
    "shiba-inu": "Shiba Inu", "litecoin": "Litecoin", "chainlink": "Chainlink",
    "uniswap": "Uniswap", "tron": "TRON", "matic-network": "Polygon",
}

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
    "tron": "TRXUSDT",
    "matic-network": "POLUSDT",
}


def get_binance_prices(coin_ids):
    try:
        symbols = [BINANCE_SYMBOLS[cid] for cid in coin_ids if cid in BINANCE_SYMBOLS]
        if not symbols:
            return []

        res = requests.get(
            "https://api.binance.com/api/v3/ticker/24hr",
            params={"symbols": json.dumps(symbols)},
            timeout=HTTP_TIMEOUT,
        )
        res.raise_for_status()

        rows = res.json()
        by_symbol = {row.get("symbol"): row for row in rows if isinstance(row, dict)}
        result = []

        for cid in coin_ids:
            row = by_symbol.get(BINANCE_SYMBOLS.get(cid))
            if not row:
                continue

            result.append({
                "symbol": SYMBOL_MAP.get(cid, cid.upper()),
                "name": NAME_MAP.get(cid, SYMBOL_MAP.get(cid, cid.upper())),
                "price": float(row.get("lastPrice", 0)),
                "change": round(float(row.get("priceChangePercent", 0)), 2),
                "volume": float(row.get("quoteVolume", 0)),
            })

        return result
    except Exception:
        return []


def get_top_prices():
    coin_ids = [
        "bitcoin", "ethereum", "solana", "binancecoin",
        "ripple", "cardano", "dogecoin", "avalanche-2",
    ]

    try:
        res = requests.get(
            "https://api.coingecko.com/api/v3/coins/markets",
            params={
                "vs_currency": "usd",
                "ids": ",".join(coin_ids),
                "order": "market_cap_desc",
                "sparkline": "false",
            },
            timeout=HTTP_TIMEOUT,
        )
        res.raise_for_status()

        data = res.json()
        if not isinstance(data, list):
            return get_binance_prices(coin_ids)

        result = []
        for d in data:
            result.append({
                "symbol": SYMBOL_MAP.get(d["id"], d["symbol"].upper()),
                "name": d["name"],
                "price": d["current_price"],
                "change": round(d["price_change_percentage_24h"] or 0, 2),
                "volume": d["total_volume"],
            })

        return result
    except Exception:
        return get_binance_prices(coin_ids)


def get_binance_kline(coin_id, days=1):
    try:
        symbol = BINANCE_SYMBOLS.get(coin_id)
        if not symbol:
            return [], []

        interval = "1h" if days <= 7 else "4h"

        res = requests.get(
            "https://api.binance.com/api/v3/klines",
            params={
                "symbol": symbol,
                "interval": interval,
                "limit": 72,
            },
            timeout=HTTP_TIMEOUT,
        )
        res.raise_for_status()

        labels = []
        vals = []

        for row in res.json()[-72:]:
            t = datetime.datetime.fromtimestamp(row[0] / 1000)
            labels.append(t.strftime("%m/%d %H:%M") if days > 1 else t.strftime("%H:%M"))
            vals.append(round(float(row[4]), 4))

        return labels, vals
    except Exception:
        return [], []


def get_kline(coin_id, days=1):
    try:
        res = requests.get(
            "https://api.coingecko.com/api/v3/coins/" + coin_id + "/market_chart",
            params={
                "vs_currency": "usd",
                "days": str(days),
            },
            timeout=HTTP_TIMEOUT,
        )
        res.raise_for_status()

        data = res.json()
        prices = data.get("prices", [])
        if not prices:
            return get_binance_kline(coin_id, days)

        step = max(1, len(prices) // 72)
        sampled = prices[::step][-72:]

        labels = []
        vals = []

        for p in sampled:
            t = datetime.datetime.fromtimestamp(p[0] / 1000)
            labels.append(t.strftime("%m/%d %H:%M") if days > 1 else t.strftime("%H:%M"))
            vals.append(round(p[1], 4))

        return labels, vals
    except Exception:
        return get_binance_kline(coin_id, days)


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
  background: #eef1f6;
  color: #172033;
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.header {
  background: rgba(255,255,255,0.94);
  border-bottom: 1px solid #e2e7f0;
  box-shadow: 0 1px 14px rgba(22,32,51,0.06);
  flex-shrink: 0;
}
.header-inner {
  max-width: 1180px;
  margin: 0 auto;
  padding: 16px 28px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.brand { display: flex; align-items: center; gap: 12px; }
.brand-mark {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fff3df;
  color: #f7931a;
  font-weight: 800;
  border: 1px solid #ffd9a3;
}
.logo { font-size: 20px; font-weight: 800; }
.subtitle { color: #7c879a; font-size: 12px; margin-top: 2px; }
.live {
  color: #15803d;
  font-size: 12px;
  background: #ecfdf3;
  padding: 5px 12px;
  border-radius: 999px;
  border: 1px solid #bbf7d0;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  white-space: nowrap;
}
.live-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #22c55e;
  box-shadow: 0 0 0 4px rgba(34,197,94,0.12);
}
.content {
  flex: 1;
  overflow-y: auto;
  padding: 24px 28px 28px;
}
.workspace {
  max-width: 1180px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 330px;
  gap: 18px;
  align-items: start;
}
.main-panel { min-width: 0; }
.side-panel { display: flex; flex-direction: column; gap: 14px; }
.top-cards {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 18px;
}
.price-card {
  background: white;
  border: 1px solid #e3e8f2;
  border-radius: 8px;
  padding: 18px;
  min-height: 136px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  cursor: pointer;
  box-shadow: 0 8px 22px rgba(22,32,51,0.06);
  transition: 0.2s ease;
}
.price-card:hover {
  transform: translateY(-2px);
  border-color: #f7931a;
  box-shadow: 0 12px 26px rgba(22,32,51,0.10);
}
.card-sym {
  color: #798498;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 1.2px;
  margin-bottom: 10px;
}
.card-price {
  font-size: 24px;
  font-weight: 800;
  letter-spacing: 0;
}
.card-change {
  font-size: 12px;
  font-weight: 800;
  padding: 5px 9px;
  border-radius: 999px;
  align-self: flex-start;
}
.up { color: #16a34a; background: #f0fdf4; }
.down { color: #dc2626; background: #fef2f2; }
.muted { color: #7c879a; background: #f2f4f7; }
.agent-card {
  background: white;
  border: 1px solid #e3e8f2;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 8px 22px rgba(22,32,51,0.06);
}
.agent-head {
  padding: 16px 18px;
  border-bottom: 1px solid #edf0f5;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}
.agent-title { font-size: 14px; font-weight: 800; }
.agent-note { font-size: 12px; color: #7c879a; margin-top: 2px; }
.chat-area {
  min-height: 430px;
  padding: 18px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.msg-row { display: flex; gap: 10px; align-items: flex-start; width: 100%; }
.msg-row.user { flex-direction: row-reverse; }
.av {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  flex-shrink: 0;
  font-weight: 800;
}
.ai-av { background: #fff3df; color: #f7931a; border: 1px solid #ffd9a3; }
.u-av { background: #e9eefb; color: #425caa; border: 1px solid #d5ddf5; }
.bubble {
  max-width: min(680px, calc(100% - 54px));
  padding: 13px 15px;
  border-radius: 8px;
  font-size: 14px;
  line-height: 1.65;
}
.ai-b { background: #f8fafc; color: #2f394a; border: 1px solid #edf0f5; }
.u-b { background: #172033; color: white; }
.chart-box, .table-box {
  background: white;
  border-radius: 8px;
  padding: 18px;
  width: 100%;
  max-width: 780px;
  border: 1px solid #e3e8f2;
  box-shadow: 0 8px 22px rgba(22,32,51,0.06);
}
.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.chart-title, .table-header {
  color: #172033;
  font-size: 15px;
  font-weight: 800;
}
.chart-badge {
  font-size: 11px;
  font-weight: 800;
  padding: 4px 10px;
  border-radius: 999px;
}
.chart-wrap { position: relative; height: 260px; }
.chart-sum {
  color: #7c879a;
  font-size: 12px;
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px solid #edf0f5;
  display: flex;
  gap: 16px;
}
.dtable {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.dtable th {
  color: #7c879a;
  font-weight: 700;
  padding: 8px 10px;
  text-align: right;
  font-size: 11px;
  border-bottom: 1px solid #edf0f5;
}
.dtable th:first-child, .dtable td:first-child { text-align: left; }
.dtable td {
  padding: 11px 10px;
  border-top: 1px solid #f3f5f8;
  text-align: right;
}
.coin-name { font-weight: 800; color: #172033; }
.coin-sub { color: #7c879a; font-size: 11px; }
.insight-card {
  background: white;
  border: 1px solid #e3e8f2;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 8px 22px rgba(22,32,51,0.06);
}
.insight-kicker {
  color: #7c879a;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 1px;
  margin-bottom: 8px;
}
.insight-title {
  font-size: 18px;
  font-weight: 800;
  margin-bottom: 8px;
}
.insight-copy {
  color: #5d687b;
  font-size: 13px;
  line-height: 1.65;
}
.watch-list { display: flex; flex-direction: column; gap: 8px; }
.watch-item {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 0;
  border-top: 1px solid #edf0f5;
  font-size: 13px;
}
.watch-symbol { font-weight: 800; }
.watch-meta { color: #7c879a; }
.input-area {
  background: rgba(255,255,255,0.96);
  padding: 14px 28px 18px;
  border-top: 1px solid #e2e7f0;
  flex-shrink: 0;
  box-shadow: 0 -8px 24px rgba(22,32,51,0.05);
}
.input-shell {
  max-width: 1180px;
  margin: 0 auto;
}
.chips {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  margin-bottom: 10px;
  scrollbar-width: none;
}
.chips::-webkit-scrollbar { display: none; }
.chip {
  background: #f8fafc;
  border: 1px solid #e3e8f2;
  color: #465266;
  border-radius: 999px;
  padding: 8px 13px;
  font-size: 13px;
  cursor: pointer;
  white-space: nowrap;
  transition: 0.2s ease;
}
.chip:hover {
  background: #fff3df;
  border-color: #f7931a;
  color: #a95d00;
}
.chip:disabled { opacity: 0.45; cursor: not-allowed; }
.irow {
  display: flex;
  gap: 10px;
  align-items: center;
}
.irow input {
  flex: 1;
  min-width: 0;
  background: #f8fafc;
  border: 1px solid #d9e0eb;
  border-radius: 8px;
  padding: 14px 16px;
  font-size: 14px;
  color: #172033;
  outline: none;
  transition: 0.2s ease;
}
.irow input:focus {
  border-color: #f7931a;
  background: white;
  box-shadow: 0 0 0 3px rgba(247,147,26,0.12);
}
.sbtn {
  background: #f7931a;
  border: none;
  border-radius: 8px;
  width: 50px;
  height: 48px;
  color: white;
  font-size: 18px;
  cursor: pointer;
  flex-shrink: 0;
  box-shadow: 0 10px 20px rgba(247,147,26,0.24);
  transition: 0.2s ease;
}
.sbtn:hover:not(:disabled) { transform: scale(1.04); }
.sbtn:disabled { opacity: 0.45; cursor: not-allowed; transform: none; }
.dots span {
  display: inline-block;
  width: 6px;
  height: 6px;
  background: #f7931a;
  border-radius: 50%;
  animation: bounce 1.2s infinite;
  margin: 0 2px;
}
.dots span:nth-child(2) { animation-delay: 0.2s; }
.dots span:nth-child(3) { animation-delay: 0.4s; }
@keyframes bounce {
  0%,60%,100% { transform: translateY(0); }
  30% { transform: translateY(-5px); }
}
@media (max-width: 980px) {
  .workspace { grid-template-columns: 1fr; }
  .side-panel { display: none; }
}
@media (max-width: 720px) {
  .header-inner, .content, .input-area { padding-left: 16px; padding-right: 16px; }
  .subtitle { display: none; }
  .top-cards { grid-template-columns: 1fr; }
  .price-card { min-height: 116px; }
  .chat-area { min-height: 360px; padding: 14px; }
  .chart-sum { flex-wrap: wrap; }
}
</style>
</head>
<body>
<div class="header">
  <div class="header-inner">
    <div class="brand">
      <div class="brand-mark">&#8383;</div>
      <div>
        <div class="logo">CryptoVision</div>
        <div class="subtitle">AI market desk for crypto moves</div>
      </div>
    </div>
    <div class="live"><span class="live-dot"></span>Live market</div>
  </div>
</div>

<div class="content" id="content">
  <div class="workspace">
    <div class="main-panel">
      <div class="top-cards">
        <div class="price-card" onclick="doSend('BTC chart')">
          <div>
            <div class="card-sym">BITCOIN</div>
            <div class="card-price" style="color:#f7931a" id="p-btc">Loading</div>
          </div>
          <div class="card-change muted" id="c-btc">Waiting</div>
        </div>
        <div class="price-card" onclick="doSend('ETH chart')">
          <div>
            <div class="card-sym">ETHEREUM</div>
            <div class="card-price" style="color:#627eea" id="p-eth">Loading</div>
          </div>
          <div class="card-change muted" id="c-eth">Waiting</div>
        </div>
        <div class="price-card" onclick="doSend('SOL chart')">
          <div>
            <div class="card-sym">SOLANA</div>
            <div class="card-price" style="color:#9945ff" id="p-sol">Loading</div>
          </div>
          <div class="card-change muted" id="c-sol">Waiting</div>
        </div>
      </div>

      <div class="agent-card">
        <div class="agent-head">
          <div>
            <div class="agent-title">CryptoVision AI</div>
            <div class="agent-note">Ask in English or Chinese. Charts and market tables render inline.</div>
          </div>
          <div class="live"><span class="live-dot"></span>Ready</div>
        </div>
        <div class="chat-area" id="chatArea">
          <div class="msg-row">
            <div class="av ai-av">AI</div>
            <div class="bubble ai-b">Hi, I am online. Start with a coin, a chart request, or a market overview.</div>
          </div>
        </div>
      </div>
    </div>

    <div class="side-panel">
      <div class="insight-card">
        <div class="insight-kicker">MARKET DESK</div>
        <div class="insight-title">Watch the majors first.</div>
        <div class="insight-copy">BTC, ETH, and SOL anchor the first screen. Click any card to pull a live chart into the conversation.</div>
      </div>
      <div class="insight-card">
        <div class="insight-kicker">QUICK WATCH</div>
        <div class="watch-list" id="watchList">
          <div class="watch-item"><span class="watch-symbol">BTC</span><span class="watch-meta">Loading</span></div>
          <div class="watch-item"><span class="watch-symbol">ETH</span><span class="watch-meta">Loading</span></div>
          <div class="watch-item"><span class="watch-symbol">SOL</span><span class="watch-meta">Loading</span></div>
        </div>
      </div>
    </div>
  </div>
</div>

<div class="input-area">
  <div class="input-shell">
    <div class="chips">
      <button class="chip" onclick="doSend('BTC chart')">BTC Chart</button>
      <button class="chip" onclick="doSend('ETH chart')">ETH Chart</button>
      <button class="chip" onclick="doSend('market overview')">Market</button>
      <button class="chip" onclick="doSend('SOL chart')">SOL Chart</button>
      <button class="chip" onclick="doSend('top coins')">Top Coins</button>
    </div>
    <div class="irow">
      <input type="text" id="inp" placeholder="Ask about BTC, ETH, SOL, risk, trend, or market overview..." />
      <button class="sbtn" id="sbtn" onclick="doSend()">&#9658;</button>
    </div>
  </div>
</div>

<script>
var chatHistory = [];
var busy = false;

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

function setBusy(v) {
  busy = v;
  document.getElementById('sbtn').disabled = v;
  document.getElementById('inp').disabled = v;

  var chips = document.querySelectorAll('.chip');
  for (var i = 0; i < chips.length; i++) {
    chips[i].disabled = v;
  }
}

function setUnavailable() {
  var pairs = [['btc','BTC'], ['eth','ETH'], ['sol','SOL']];

  for (var i = 0; i < pairs.length; i++) {
    var pe = document.getElementById('p-' + pairs[i][0]);
    var ce = document.getElementById('c-' + pairs[i][0]);

    if (pe) pe.textContent = 'Unavailable';
    if (ce) {
      ce.textContent = 'Retry later';
      ce.className = 'card-change muted';
    }
  }

  updateWatchList([]);
}

function loadPrices() {
  fetch('/top_prices')
    .then(function(r) {
      if (!r.ok) throw new Error('price load failed');
      return r.json();
    })
    .then(function(data) {
      if (!Array.isArray(data) || data.length === 0) {
        setUnavailable();
        return;
      }

      var map = {};
      for (var i = 0; i < data.length; i++) {
        map[data[i].symbol] = data[i];
      }

      var pairs = [['BTC','btc'], ['ETH','eth'], ['SOL','sol']];

      for (var j = 0; j < pairs.length; j++) {
        var s = pairs[j][0];
        var id = pairs[j][1];

        if (map[s]) {
          var pe = document.getElementById('p-' + id);
          var ce = document.getElementById('c-' + id);

          if (pe) {
            pe.textContent = '$' + Number(map[s].price).toLocaleString('en-US', {
              maximumFractionDigits: 2
            });
          }

          if (ce) {
            var up = map[s].change >= 0;
            ce.textContent = (up ? '+' : '') + map[s].change + '%';
            ce.className = 'card-change ' + (up ? 'up' : 'down');
          }
        }
      }

      updateWatchList(data);
    })
    .catch(function() {
      setUnavailable();
    });
}

function updateWatchList(data) {
  var box = document.getElementById('watchList');
  if (!box) return;

  var keep = ['BTC', 'ETH', 'SOL', 'BNB', 'XRP'];
  var map = {};

  for (var i = 0; i < data.length; i++) {
    map[data[i].symbol] = data[i];
  }

  var html = '';

  for (var j = 0; j < keep.length; j++) {
    var item = map[keep[j]];
    if (!item) continue;

    var up = item.change >= 0;
    html += '<div class="watch-item"><span class="watch-symbol">' +
      escapeHtml(item.symbol) +
      '</span><span class="watch-meta ' +
      (up ? 'up' : 'down') +
      '">' +
      (up ? '+' : '') +
      item.change +
      '%</span></div>';
  }

  if (!html) {
    html = '<div class="watch-item"><span class="watch-symbol">Market</span><span class="watch-meta">Temporarily unavailable</span></div>';
  }

  box.innerHTML = html;
}

function doSend(text) {
  if (busy) return;

  var inp = document.getElementById('inp');
  var msg = text || inp.value.trim();

  if (!msg) return;

  inp.value = '';
  addUserMsg(msg);
  chatHistory.push({ role: 'user', content: msg });

  setBusy(true);
  var typing = addTyping();

  fetch('/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ messages: chatHistory })
  })
    .then(function(r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    })
    .then(function(data) {
      typing.remove();

      if (data.type === 'chart') {
        addChart(data);
      } else if (data.type === 'table') {
        addTable(data);
      } else {
        addAIMsg(data.reply || 'No response received. Please retry.');
      }

      chatHistory.push({
        role: 'assistant',
        content: data.reply || data.summary || ''
      });

      setBusy(false);
    })
    .catch(function() {
      typing.remove();
      addAIMsg('Network error, please retry.');
      chatHistory.pop();
      setBusy(false);
    });
}

document.getElementById('inp').addEventListener('keydown', function(e) {
  if (e.key === 'Enter' && !busy) {
    doSend();
  }
});

function addUserMsg(text) {
  var area = document.getElementById('chatArea');
  var d = document.createElement('div');

  d.className = 'msg-row user';
  d.innerHTML = '<div class="av u-av">U</div><div class="bubble u-b">' + nl2br(text) + '</div>';

  area.appendChild(d);
  scrollDown();
}

function addAIMsg(text) {
  var area = document.getElementById('chatArea');
  var d = document.createElement('div');

  d.className = 'msg-row';
  d.innerHTML = '<div class="av ai-av">AI</div><div class="bubble ai-b">' + nl2br(text) + '</div>';

  area.appendChild(d);
  scrollDown();
}

function addTyping() {
  var area = document.getElementById('chatArea');
  var d = document.createElement('div');

  d.className = 'msg-row';
  d.innerHTML = '<div class="av ai-av">AI</div><div class="bubble ai-b"><div class="dots"><span></span><span></span><span></span></div></div>';

  area.appendChild(d);
  scrollDown();

  return d;
}

function addChart(data) {
  var area = document.getElementById('chatArea');
  var id = 'ch' + Date.now();
  var prices = data.prices;

  if (!prices || !prices.length) {
    addAIMsg(data.reply || 'Chart data is unavailable right now.');
    return;
  }

  var up = prices[prices.length - 1] >= prices[0];
  var color = up ? '#16a34a' : '#dc2626';
  var badge = up
    ? '<span class="chart-badge up">+' + data.change + '%</span>'
    : '<span class="chart-badge down">' + data.change + '%</span>';

  var d = document.createElement('div');
  d.className = 'msg-row';

  d.innerHTML =
    '<div class="av ai-av">AI</div>' +
    '<div class="chart-box">' +
      '<div class="chart-header">' +
        '<div class="chart-title">' + escapeHtml(data.title) + '</div>' +
        badge +
      '</div>' +
      '<div class="chart-wrap"><canvas id="' + id + '"></canvas></div>' +
      '<div class="chart-sum">' +
        '<span>Current: <b>$' + parseFloat(prices[prices.length - 1]).toLocaleString('en-US', { maximumFractionDigits: 4 }) + '</b></span>' +
        '<span>High: <b>$' + data.high + '</b></span>' +
        '<span>Low: <b>$' + data.low + '</b></span>' +
        '<span style="margin-left:auto;color:#9aa3b2">Live data</span>' +
      '</div>' +
    '</div>';

  area.appendChild(d);
  scrollDown();

  setTimeout(function() {
    var ctx = document.getElementById(id);
    if (!ctx) return;

    new Chart(ctx.getContext('2d'), {
      type: 'line',
      data: {
        labels: data.labels,
        datasets: [{
          data: prices,
          borderColor: color,
          backgroundColor: up ? 'rgba(22,163,74,0.06)' : 'rgba(220,38,38,0.06)',
          borderWidth: 2,
          pointRadius: 0,
          tension: 0.35,
          fill: true
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: function(ctx) {
                return '$' + ctx.parsed.y.toLocaleString('en-US', {
                  maximumFractionDigits: 4
                });
              }
            }
          }
        },
        scales: {
          x: {
            display: true,
            grid: { display: false },
            ticks: { color: '#9aa3b2', font: { size: 10 }, maxTicksLimit: 6 }
          },
          y: {
            grid: { color: '#edf0f5' },
            ticks: {
              color: '#9aa3b2',
              font: { size: 10 },
              maxTicksLimit: 5,
              callback: function(v) {
                return '$' + (v >= 1000 ? (v / 1000).toFixed(1) + 'k' : v.toFixed(2));
              }
            }
          }
        }
      }
    });
  }, 100);
}

function addTable(data) {
  var area = document.getElementById('chatArea');
  var d = document.createElement('div');
  var rows = '';

  d.className = 'msg-row';

  for (var i = 0; i < data.rows.length; i++) {
    var r = data.rows[i];
    var up = r.change >= 0;

    rows += '<tr>' +
      '<td><div class="coin-name">' + escapeHtml(r.symbol) + '</div><div class="coin-sub">' + escapeHtml(r.name) + '</div></td>' +
      '<td>$' + Number(r.price).toLocaleString('en-US', { maximumFractionDigits: 4 }) + '</td>' +
      '<td><span class="' + (up ? 'up' : 'down') + '" style="padding:4px 8px;border-radius:999px;">' + (up ? '+' : '') + r.change + '%</span></td>' +
      '<td style="color:#7c879a">$' + (Number(r.volume) / 1e9).toFixed(1) + 'B</td>' +
    '</tr>';
  }

  d.innerHTML =
    '<div class="av ai-av">AI</div>' +
    '<div class="table-box">' +
      '<div class="table-header">Top Coins - Live Market</div>' +
      '<table class="dtable"><tr><th>Coin</th><th>Price</th><th>24h</th><th>Volume</th></tr>' + rows + '</table>' +
      '<div style="color:#9aa3b2;font-size:12px;margin-top:10px;padding-top:8px;border-top:1px solid #edf0f5;">' + escapeHtml(data.summary) + '</div>' +
    '</div>';

  area.appendChild(d);
  scrollDown();
}

function scrollDown() {
  var c = document.getElementById('content');
  setTimeout(function() {
    c.scrollTop = c.scrollHeight;
  }, 80);
}

loadPrices();
setInterval(loadPrices, 60000);
</script>
</body>
</html>"""


@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/top_prices")
def top_prices():
    return jsonify(get_top_prices())


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
        return jsonify({
            "type": "text",
            "reply": "Please enter a question about crypto, a coin symbol, or a chart request."
        })

    msg_lower = user_msg.lower()

    chart_kw = [
        "chart", "trend", "btc", "eth", "sol", "bnb", "doge", "xrp",
        "ada", "avax", "dot", "shib", "ltc", "link", "图", "走势", "价格"
    ]
    table_kw = [
        "market", "top", "overview", "all", "coins", "list",
        "市场", "排行", "概览", "全部"
    ]

    is_chart = any(k in msg_lower for k in chart_kw)
    is_table = any(k in msg_lower for k in table_kw)

    found_id = None
    found_symbol = None

    for name, cid in COIN_MAP.items():
        if name in msg_lower:
            found_id = cid
            found_symbol = SYMBOL_MAP.get(cid, cid.upper())
            break

    if is_chart and found_id:
        days = 30 if any(k in msg_lower for k in ["30", "month", "月"]) else 7 if any(k in msg_lower for k in ["7", "week", "周"]) else 1
        labels, prices = get_kline(found_id, days=days)

        if labels and prices:
            change = round((prices[-1] - prices[0]) / prices[0] * 100, 2) if prices[0] else 0
            high = max(prices)
            low = min(prices)
            period = "30D" if days == 30 else "7D" if days == 7 else "24H"

            return jsonify({
                "type": "chart",
                "title": found_symbol + "/USDT " + period,
                "labels": labels,
                "prices": prices,
                "change": change,
                "high": round(high, 2),
                "low": round(low, 2),
                "summary": "Current $" + str(round(prices[-1], 4)) + " | " + ("+" if change >= 0 else "") + str(change) + "%",
                "reply": found_symbol + " chart"
            })

        return jsonify({
            "type": "text",
            "reply": "I could not load chart data right now. Please try again in a moment."
        })

    if is_table:
        top = get_top_prices()

        if top:
            return jsonify({
                "type": "table",
                "title": "Top Coins",
                "rows": top,
                "summary": str(len(top)) + " coins | Updated " + datetime.datetime.now().strftime("%H:%M"),
                "reply": "Market overview"
            })

        return jsonify({
            "type": "text",
            "reply": "Market data is temporarily unavailable. Please retry in a moment."
        })

    price_context = ""

    if found_id:
        top = get_top_prices()
        for t in top:
            if t["symbol"] == found_symbol:
                price_context = " [Live] " + found_symbol + ": $" + str(t["price"]) + ", 24h=" + str(t["change"]) + "%"
                break

    if not DEEPSEEK_API_KEY:
        return jsonify({
            "type": "text",
            "reply": "CryptoVision is running, but AI chat is not configured yet. Add DEEPSEEK_API_KEY in Render Environment settings, then redeploy. Crypto investing involves risk."
        })

    system = (
        "You are CryptoVision AI. Answer in the same language the user writes in. "
        "Be concise, useful, and professional. No direct buy/sell instructions. "
        "When discussing investing or trading, remind users that crypto investing involves risk."
    )

    api_msgs = [{"role": "system", "content": system}]

    for h in messages[:-1]:
        if isinstance(h, dict) and h.get("role") in ["user", "assistant"] and isinstance(h.get("content"), str):
            api_msgs.append({
                "role": h["role"],
                "content": h["content"][:2000],
            })

    api_msgs.append({
        "role": "user",
        "content": user_msg + price_context,
    })

    try:
        res = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers={
                "Authorization": "Bearer " + DEEPSEEK_API_KEY,
                "Content-Type": "application/json",
            },
            json={
                "model": "deepseek-chat",
                "messages": api_msgs,
                "max_tokens": 500,
                "temperature": 0.4,
            },
            timeout=LLM_TIMEOUT,
        )
        res.raise_for_status()
        payload = res.json()
        reply = payload["choices"][0]["message"]["content"]

    except requests.exceptions.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "unknown"
        reply = "AI service returned an error (" + str(status) + "). Please check the DeepSeek API key, billing, and Render environment settings."

    except requests.exceptions.Timeout:
        reply = "AI service timed out. Please retry in a moment."

    except Exception:
        reply = "AI service is temporarily unavailable. Please retry in a moment."

    return jsonify({
        "type": "text",
        "reply": reply,
    })


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
    )
