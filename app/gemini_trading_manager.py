import asyncio
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional
import google.generativeai as genai
import json
import os

from .binance_client import binance_client
from .firebase_manager import firebase_manager
from .config import settings

class GeminiTradingManager:
    """
    AI-Powered Autonomous Trading Manager

    Gemini AI tum trading kararlarini verir:
    - Coin secimi (otomatik)
    - Pozisyon acma/kapatma
    - TP/SL belirleme
    - Para yonetimi
    - Risk yonetimi
    """

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            print("GEMINI_API_KEY bulunamadi!")
            self.enabled = False
            return

        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        self.enabled = True

        # Trading state
        self.is_running = False
        self.active_positions = {}  # {symbol: position_data}
        self.last_analysis_time = {}
        self.daily_trade_count = 0
        self.daily_reset_date = datetime.now(timezone.utc).date()

        # Risk parameters
        self.max_positions = 2
        self.capital_per_position = 0.45  # %45 her pozisyon icin
        self.min_confidence = 80
        self.analysis_interval = 60  # 60 saniye

        # Performance tracking
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0

        print("AI Trading Manager initialized")

    async def start_autonomous_trading(self):
        """Otonom trading baslatir"""
        if not self.enabled:
            print("Gemini API aktif degil!")
            return

        self.is_running = True
        print("Autonomous AI Trading STARTED")

        try:
            while self.is_running:
                await self._trading_cycle()
                await asyncio.sleep(self.analysis_interval)

        except Exception as e:
            print(f"Trading cycle error: {e}")
        finally:
            self.is_running = False

    async def stop_autonomous_trading(self):
        """Trading'i durdurur"""
        self.is_running = False
        print("Autonomous AI Trading STOPPED")

    async def _trading_cycle(self):
        """Ana trading dongusu"""
        try:
            # Gunluk limit reset
            self._check_daily_reset()

            # 1. Mevcut pozisyonlari kontrol et
            await self._check_existing_positions()

            # 2. Yeni pozisyon acilabilir mi?
            if len(self.active_positions) < self.max_positions:
                await self._find_and_open_position()

        except Exception as e:
            print(f"Trading cycle error: {e}")

    def _check_daily_reset(self):
        """Gunluk sayaci resetler"""
        today = datetime.now(timezone.utc).date()
        if today != self.daily_reset_date:
            self.daily_trade_count = 0
            self.daily_reset_date = today
            print(f"Daily trade counter reset: {today}")

    async def _check_existing_positions(self):
        """Mevcut pozisyonlari kontrol eder"""
        try:
            all_positions = await binance_client.client.futures_position_information()
            open_positions = [p for p in all_positions if float(p['positionAmt']) != 0]

            current_symbols = {p['symbol'] for p in open_positions}

            # Kapatilmis pozisyonlari tespit et
            for symbol in list(self.active_positions.keys()):
                if symbol not in current_symbols:
                    print(f"Position closed by TP/SL: {symbol}")
                    await self._handle_position_closed(symbol)

            # Yeni acilan pozisyonlari ekle
            for pos in open_positions:
                symbol = pos['symbol']
                if symbol not in self.active_positions:
                    self.active_positions[symbol] = {
                        'entry_time': datetime.now(timezone.utc),
                        'entry_price': float(pos['entryPrice']),
                        'size': abs(float(pos['positionAmt'])),
                        'side': 'LONG' if float(pos['positionAmt']) > 0 else 'SHORT'
                    }

        except Exception as e:
            print(f"Position check error: {e}")

    async def _handle_position_closed(self, symbol: str):
        """Kapanan pozisyon islemleri"""
        try:
            pos_data = self.active_positions.pop(symbol, None)
            if not pos_data:
                return

            # PnL hesapla (Firebase'den al)
            firebase_manager.log_trade({
                'symbol': symbol,
                'strategy': 'gemini_autonomous',
                'side': pos_data['side'],
                'entry_price': pos_data['entry_price'],
                'close_time': datetime.now(timezone.utc).isoformat(),
                'status': 'CLOSED'
            })

            print(f"Position {symbol} logged to Firebase")

        except Exception as e:
            print(f"Handle position close error: {e}")

    async def _find_and_open_position(self):
        """Gemini AI'ye yeni pozisyon sorgusu"""
        try:
            # Bakiye kontrolu
            balance = await binance_client.get_account_balance()
            if balance < 50:
                print(f"Insufficient balance: {balance} USDT")
                return

            # AI'dan coin onerisi al
            selected_coin = await self._ask_gemini_for_coin()
            if not selected_coin:
                return

            symbol = selected_coin['symbol']

            # Rate limit
            last_time = self.last_analysis_time.get(symbol, 0)
            if time.time() - last_time < 120:  # 2 dakika cooldown
                return

            self.last_analysis_time[symbol] = time.time()

            # Market verilerini al
            klines_1m = await binance_client.get_historical_klines(symbol, "1m", limit=100)
            klines_15m = await binance_client.get_historical_klines(symbol, "15m", limit=50)

            if not klines_1m or not klines_15m:
                return

            current_price = await binance_client.get_market_price(symbol)
            if not current_price:
                return

            # AI analizini al
            analysis = await self._analyze_with_gemini(
                symbol, current_price, klines_1m, klines_15m, balance
            )

            if not analysis or not analysis['should_trade']:
                return

            if analysis['confidence'] < self.min_confidence:
                print(f"{symbol} confidence too low: {analysis['confidence']}")
                return

            # Pozisyon ac
            await self._open_position(symbol, analysis, balance)

        except Exception as e:
            print(f"Find and open position error: {e}")

    async def _ask_gemini_for_coin(self) -> Optional[Dict]:
        """Gemini AI'dan coin onerisi alir"""
        try:
            prompt = """
Sen bir profesyonel kripto trader'sin. BINANCE FUTURES'ta scalping yapiyorsun.

GOREV: Simdi islem yapilabilecek EN IYI 1 coin onerisinde bulun.

Kriterler:
1. Yuksek likidite (BTC, ETH, BNB, SOL, ADA gibi major coinler)
2. Iyi volatilite (scalping icin uygun)
3. Aktif hacim
4. Trend belirgin

SADECE JSON dondur:
{
  "symbol": "BTCUSDT",
  "reasoning": "Neden bu coin?"
}

NOT: Sadece USDT parity'leri oner (BTCUSDT, ETHUSDT gibi).
"""

            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt,
                generation_config={
                    "temperature": 0.5,
                    "max_output_tokens": 256,
                }
            )

            result = self._parse_json_response(response.text)
            if result and 'symbol' in result:
                print(f"AI selected coin: {result['symbol']}")
                return result

            return None

        except Exception as e:
            print(f"Ask Gemini for coin error: {e}")
            return None

    async def _analyze_with_gemini(
        self,
        symbol: str,
        price: float,
        klines_1m: List,
        klines_15m: List,
        balance: float
    ) -> Optional[Dict]:
        """Gemini AI ile tam analiz"""
        try:
            # Market context hazirlama
            candles_1m = []
            for k in klines_1m[-10:]:
                candles_1m.append({
                    'open': float(k[1]),
                    'high': float(k[2]),
                    'low': float(k[3]),
                    'close': float(k[4]),
                    'volume': float(k[5])
                })

            candles_15m = []
            for k in klines_15m[-5:]:
                candles_15m.append({
                    'open': float(k[1]),
                    'high': float(k[2]),
                    'low': float(k[3]),
                    'close': float(k[4]),
                    'volume': float(k[5])
                })

            # Volume analizi
            avg_volume_1m = sum(c['volume'] for c in candles_1m) / len(candles_1m)
            current_volume = candles_1m[-1]['volume']
            volume_ratio = current_volume / avg_volume_1m if avg_volume_1m > 0 else 1.0

            # Volatilite
            ranges = [c['high'] - c['low'] for c in candles_1m]
            avg_range = sum(ranges) / len(ranges)
            volatility_pct = (avg_range / price * 100) if price > 0 else 0

            prompt = f"""
Sen bir profesyonel scalping trader'sin. MULTI-TIMEFRAME analiz yapiyorsun.

COIN: {symbol}
PRICE: ${price:.4f}
BALANCE: {balance:.2f} USDT
POSITION SIZE: %45 of balance = {balance * 0.45:.2f} USDT

1 DAKiKA VERILER:
"""
            for i, c in enumerate(candles_1m[-5:], 1):
                candle_type = "BULLISH" if c['close'] > c['open'] else "BEARISH"
                prompt += f"{i}. {candle_type} | O:{c['open']:.2f} H:{c['high']:.2f} L:{c['low']:.2f} C:{c['close']:.2f}\n"

            prompt += f"""
15 DAKiKA VERILER:
"""
            for i, c in enumerate(candles_15m[-3:], 1):
                candle_type = "BULLISH" if c['close'] > c['open'] else "BEARISH"
                prompt += f"{i}. {candle_type} | O:{c['open']:.2f} H:{c['high']:.2f} L:{c['low']:.2f} C:{c['close']:.2f}\n"

            prompt += f"""
MARKET METRICS:
- Volume Ratio: {volume_ratio:.2f}x (>1.3 = iyi)
- Volatility: {volatility_pct:.3f}% (0.1-0.5% ideal)

SCALPING KURALLARI:
1. Multi-timeframe uyum ZORUNLU (1m ve 15m ayni yonde)
2. Volume >1.3x olmali
3. TP: %0.5-1.5, SL: %0.3-0.8
4. Risk/Reward minimum 1:2
5. Confidence >80% olmali

KARAR VER (SADECE JSON):
{{
  "should_trade": true/false,
  "signal": "LONG" | "SHORT" | "HOLD",
  "confidence": 0-100,
  "entry_price": {price},
  "take_profit_percent": 0.5-1.5,
  "stop_loss_percent": 0.3-0.8,
  "position_size_usdt": bakiyenin %45'i,
  "reasoning": "Aciklama (max 150 karakter)",
  "risk_score": 0-10
}}

ONEMLI: Volume veya volatilite uygun degilse should_trade=false dondur!
"""

            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt,
                generation_config={
                    "temperature": 0.3,
                    "top_p": 0.8,
                    "max_output_tokens": 512,
                }
            )

            analysis = self._parse_json_response(response.text)
            if analysis:
                print(f"{symbol} AI Analysis: {analysis['signal']} (Confidence: {analysis['confidence']}%)")
                print(f"  Reasoning: {analysis.get('reasoning', 'N/A')}")
                return analysis

            return None

        except Exception as e:
            print(f"Analyze with Gemini error: {e}")
            return None

    async def _open_position(self, symbol: str, analysis: Dict, balance: float):
        """Pozisyon acar"""
        try:
            print(f"Opening position: {symbol} {analysis['signal']}")

            # Leverage ayarla
            await binance_client.set_leverage(symbol, settings.LEVERAGE)

            # Position size hesapla
            position_size_usdt = balance * self.capital_per_position
            entry_price = analysis['entry_price']

            # Quantity hesapla
            symbol_info = await binance_client.get_symbol_info(symbol)
            if not symbol_info:
                print(f"Symbol info bulunamadi: {symbol}")
                return

            quantity_precision = binance_client._get_precision_from_filter(
                symbol_info, 'LOT_SIZE', 'stepSize'
            )
            price_precision = binance_client._get_precision_from_filter(
                symbol_info, 'PRICE_FILTER', 'tickSize'
            )

            quantity = (position_size_usdt * settings.LEVERAGE) / entry_price
            quantity = binance_client._format_quantity(symbol, quantity)

            if quantity <= 0:
                print(f"Quantity too small: {quantity}")
                return

            # TP/SL hesapla
            signal = analysis['signal']
            side = 'BUY' if signal == 'LONG' else 'SELL'

            tp_pct = analysis.get('take_profit_percent', 1.0) / 100
            sl_pct = analysis.get('stop_loss_percent', 0.5) / 100

            if signal == 'LONG':
                stop_loss = entry_price * (1 - sl_pct)
                take_profit = entry_price * (1 + tp_pct)
            else:
                stop_loss = entry_price * (1 + sl_pct)
                take_profit = entry_price * (1 - tp_pct)

            # Pozisyon ac (TP/SL ile)
            result = await binance_client.create_simple_position(
                symbol, side, quantity, entry_price, price_precision
            )

            if result:
                self.active_positions[symbol] = {
                    'entry_time': datetime.now(timezone.utc),
                    'entry_price': entry_price,
                    'size': quantity,
                    'side': signal,
                    'tp': take_profit,
                    'sl': stop_loss,
                    'ai_confidence': analysis['confidence']
                }

                self.total_trades += 1
                self.daily_trade_count += 1

                # Firebase'e kaydet
                firebase_manager.log_trade({
                    'symbol': symbol,
                    'strategy': 'gemini_autonomous',
                    'side': signal,
                    'entry_price': entry_price,
                    'quantity': quantity,
                    'take_profit': take_profit,
                    'stop_loss': stop_loss,
                    'position_size_usdt': position_size_usdt,
                    'leverage': settings.LEVERAGE,
                    'ai_confidence': analysis['confidence'],
                    'ai_reasoning': analysis.get('reasoning', ''),
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'status': 'OPENED'
                })

                print(f"Position OPENED: {symbol} {signal} @ {entry_price}")
                print(f"  TP: {take_profit:.4f}, SL: {stop_loss:.4f}")

        except Exception as e:
            print(f"Open position error: {e}")

    def _parse_json_response(self, text: str) -> Optional[Dict]:
        """JSON response parse eder"""
        try:
            # Markdown kod blogu varsa temizle
            if '```json' in text:
                start = text.find('```json') + 7
                end = text.find('```', start)
                text = text[start:end].strip()
            elif '```' in text:
                start = text.find('```') + 3
                end = text.find('```', start)
                text = text[start:end].strip()

            return json.loads(text.strip())

        except Exception as e:
            print(f"JSON parse error: {e}")
            return None

    def get_status(self) -> Dict:
        """Trading manager durumunu dondurur"""
        return {
            'is_running': self.is_running,
            'enabled': self.enabled,
            'active_positions': len(self.active_positions),
            'positions': list(self.active_positions.keys()),
            'total_trades': self.total_trades,
            'daily_trades': self.daily_trade_count,
            'win_rate': f"{(self.winning_trades / max(self.total_trades, 1) * 100):.1f}%",
            'max_positions': self.max_positions,
            'min_confidence': self.min_confidence,
            'analysis_interval': self.analysis_interval
        }

# Global instance
gemini_trading_manager = GeminiTradingManager()
