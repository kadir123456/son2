# app/bollinger_bot_core.py
# BOLLINGER BANDS BOT - HER DAKİKA 1 LONG + 1 SHORT
# Tam, eksiksiz ve çalışmaya hazır versiyon — doğrudan kopyala-yapıştır yapabilirsiniz.

import asyncio
import json
import websockets
from .config import settings
from .binance_client import binance_client
from .trading_strategy import trading_strategy
from .firebase_manager import firebase_manager
from datetime import datetime, timezone
import math
import time


class ProfitOptimizedBotCore:
    """
    📊 Bollinger Bands Bot - Her Dakika 1 LONG + 1 SHORT

    Çalışma Mantığı:
    1. WebSocket ile 1m kline'ları dinle
    2. Her kapanan mumda Bollinger hesapla
    3. Eş zamanlı 1 LONG + 1 SHORT pozisyon aç
    4. Her pozisyona ayrı TP/SL kur
    """

    def __init__(self):
        self.status = {
            "is_running": False,
            "symbols": [],  # Geriye uyumluluk
            "active_symbol": None,
            "position_side": None,
            "status_message": "📊 Bollinger Bot başlatılmadı",
            "account_balance": 0.0,
            "position_pnl": 0.0,
            "order_size": settings.POSITION_SIZE_USDT,
            "last_signals": {},
            "successful_trades": 0,
            "failed_trades": 0,
            "daily_pnl": 0.0,
            "total_profit": 0.0,
            "websocket_connections": 0
        }

        self.klines = []
        self._stop_requested = False
        self._websocket = None
        self._websocket_connections = {}
        self._last_status_update = 0

        self.quantity_precision = 0
        self.price_precision = 2

        print("=" * 70)
        print("📊 BOLLİNGER BANDS AL-SAT BOT")
        print("=" * 70)
        print(f"⏰ Timeframe: {settings.TIMEFRAME}")
        print(f"💰 Pozisyon: {settings.POSITION_SIZE_USDT} USDT (sabit)")
        print(f"📈 Kaldıraç: {settings.LEVERAGE}x")
        print(f"📊 Bollinger: {settings.BB_PERIOD} period, {settings.BB_STD_DEV} std")
        print("=" * 70)

    async def start(self, symbols: list):
        """
        Bot başlatma - tek symbol kabul eder
        symbols: list veya str (geriye uyumluluk)
        """
        if self.status["is_running"]:
            print("⚠️ Bot zaten çalışıyor")
            return

        # Tek symbol'e çevir
        if isinstance(symbols, list):
            symbol = symbols[0] if symbols else None
        else:
            symbol = symbols

        if not symbol:
            print("❌ Symbol gerekli!")
            return

        # USDT ekleme
        if not symbol.endswith('USDT'):
            symbol += 'USDT'

        self._stop_requested = False
        self.status.update({
            "is_running": True,
            "symbols": [symbol],
            "active_symbol": symbol,
            "status_message": f"📊 {symbol} için Bollinger Bot başlatılıyor..."
        })

        print(f"🚀 Bollinger Bot başlatılıyor: {symbol}")

        try:
            # 1. Binance bağlantısı
            print("1️⃣ Binance bağlantısı kuruluyor...")
            await binance_client.initialize()

            # 2. Hesap bakiyesi
            print("2️⃣ Hesap bakiyesi kontrol ediliyor...")
            self.status["account_balance"] = await binance_client.get_account_balance()
            print(f"   Bakiye: {self.status['account_balance']:.2f} USDT")

            if self.status["account_balance"] < 50:
                raise Exception(f"Yetersiz bakiye! Min: 50 USDT")

            # 3. Symbol bilgileri
            print(f"3️⃣ {symbol} bilgileri alınıyor...")
            symbol_info = await binance_client.get_symbol_info(symbol)
            if not symbol_info:
                raise Exception(f"{symbol} bilgileri alınamadı")

            self.quantity_precision = self._get_precision(symbol_info, 'LOT_SIZE', 'stepSize')
            self.price_precision = self._get_precision(symbol_info, 'PRICE_FILTER', 'tickSize')
            print(f"   Quantity precision: {self.quantity_precision}")
            print(f"   Price precision: {self.price_precision}")

            # 4. Geçmiş veri al
            print(f"4️⃣ Geçmiş {settings.TIMEFRAME} verileri alınıyor...")
            required_candles = settings.BB_PERIOD + 10
            self.klines = await binance_client.get_historical_klines(
                symbol, settings.TIMEFRAME, limit=required_candles
            )

            if not self.klines or len(self.klines) < settings.BB_PERIOD + 5:
                raise Exception(f"Yetersiz geçmiş veri")

            print(f"   ✅ {len(self.klines)} mum yüklendi")

            # 5. Kaldıraç ayarla
            print(f"5️⃣ Kaldıraç {settings.LEVERAGE}x ayarlanıyor...")
            if await binance_client.set_leverage(symbol, settings.LEVERAGE):
                print(f"   ✅ Kaldıraç başarılı")

            # 6. WebSocket başlat
            print(f"6️⃣ WebSocket başlatılıyor...")
            self.status["status_message"] = f"📊 {symbol} Bollinger Bot aktif"
            self.status["websocket_connections"] = 1

            await self._start_websocket(symbol)

        except Exception as e:
            error_msg = f"❌ Bot başlatma hatası: {e}"
            print(error_msg)
            self.status["status_message"] = error_msg
            try:
                await self.stop()
            except Exception:
                pass

    async def _start_websocket(self, symbol: str):
        """WebSocket bağlantısı"""
        # Binance kombine WebSocket URL formatı veya settings.WEBSOCKET_URL olabilir
        ws_url = f"{settings.WEBSOCKET_URL}/ws/{symbol.lower()}@kline_{settings.TIMEFRAME}"
        reconnect_attempts = 0
        max_attempts = 10

        print(f"🔗 WebSocket: {ws_url}")

        while not self._stop_requested and reconnect_attempts < max_attempts:
            try:
                async with websockets.connect(
                    ws_url,
                    ping_interval=settings.WEBSOCKET_PING_INTERVAL,
                    ping_timeout=settings.WEBSOCKET_PING_TIMEOUT
                ) as ws:
                    print(f"✅ WebSocket bağlandı")
                    reconnect_attempts = 0
                    self._websocket = ws
                    self._websocket_connections[symbol] = ws

                    while not self._stop_requested:
                        try:
                            message = await asyncio.wait_for(ws.recv(), timeout=65.0)
                            await self._handle_websocket_message(symbol, message)
                        except asyncio.TimeoutError:
                            # ping gönder
                            try:
                                await ws.ping()
                            except Exception:
                                pass
                        except websockets.exceptions.ConnectionClosed:
                            break
                        except Exception as e:
                            print(f"❌ WebSocket mesaj hatası: {e}")
                            await asyncio.sleep(1)

            except Exception as e:
                if not self._stop_requested:
                    reconnect_attempts += 1
                    backoff = min(5 * reconnect_attempts, 30)
                    print(f"⏳ Yeniden bağlanılıyor... ({backoff}s)")
                    await asyncio.sleep(backoff)

        print("🛑 WebSocket kapatıldı")

    async def _handle_websocket_message(self, symbol: str, message: str):
        """WebSocket mesaj işleme"""
        try:
            data = json.loads(message)
            kline_data = data.get('k', {})

            # Status update
            current_time = time.time()
            if current_time - self._last_status_update > settings.STATUS_UPDATE_INTERVAL:
                await self._update_status_info()
                self._last_status_update = current_time

            # Sadece kapanan mumları işle
            if not kline_data.get('x', False):
                return

            print(f"\n🕐 {symbol} MUM KAPANDI - Bollinger analizi başlıyor...")

            # Yeni kline ekle
            new_kline = [
                int(kline_data['t']),
                float(kline_data['o']),
                float(kline_data['h']),
                float(kline_data['l']),
                float(kline_data['c']),
                float(kline_data['v']),
                int(kline_data['T']),
                float(kline_data['q']),
                int(kline_data['n']),
                float(kline_data['V']),
                float(kline_data['Q']),
                '0'
            ]

            # Memory management
            if len(self.klines) >= settings.MAX_KLINES_PER_SYMBOL:
                self.klines.pop(0)

            self.klines.append(new_kline)

            # Bollinger analizi
            analysis = trading_strategy.analyze_and_calculate_levels(self.klines, symbol)

            if not analysis or not analysis.get('should_trade', False):
                print(f"⚠️ {symbol}: Trade yapılmıyor")
                return

            # İki pozisyon aç (LONG + SHORT)
            await self._open_dual_positions(symbol, analysis)

        except Exception as e:
            print(f"❌ Mesaj işleme hatası: {e}")

    async def _open_dual_positions(self, symbol: str, analysis: dict):
        """🎯 Eş zamanlı LONG + SHORT pozisyon açma"""
        try:
            print(f"\n🎯 {symbol} için ÇİFT POZİSYON açılıyor...")

            # Test modu kontrolü
            if settings.TEST_MODE:
                print(f"🧪 TEST: {symbol} pozisyonlar simüle edildi")
                self.status["successful_trades"] += 2
                return

            # Quantity hesaplama
            long_quantity = self._calculate_quantity(analysis['long_entry'])
            short_quantity = self._calculate_quantity(analysis['short_entry'])

            if long_quantity <= 0 or short_quantity <= 0:
                print(f"❌ Quantity çok düşük")
                return

            print(f"💰 LONG Quantity: {long_quantity} @ {analysis['long_entry']:.4f}")
            print(f"💰 SHORT Quantity: {short_quantity} @ {analysis['short_entry']:.4f}")

            # Market fiyatı al
            current_price = await binance_client.get_market_price(symbol)
            if not current_price:
                print(f"❌ Fiyat alınamadı")
                return

            # 1. LONG POZİSYON AÇ
            print(f"\n📈 LONG pozisyonu açılıyor...")
            long_success = await self._open_single_position(
                symbol=symbol,
                side='BUY',
                quantity=long_quantity,
                entry_price=current_price,
                tp_price=analysis['long_tp'],
                sl_price=analysis['long_sl'],
                position_type='LONG'
            )

            await asyncio.sleep(1.0)

            # 2. SHORT POZİSYON AÇ
            print(f"\n📉 SHORT pozisyonu açılıyor...")
            short_success = await self._open_single_position(
                symbol=symbol,
                side='SELL',
                quantity=short_quantity,
                entry_price=current_price,
                tp_price=analysis['short_tp'],
                sl_price=analysis['short_sl'],
                position_type='SHORT'
            )

            # Sonuç
            if long_success and short_success:
                print(f"\n✅ {symbol} ÇİFT POZİSYON BAŞARILI!")
                self.status["successful_trades"] += 2
            elif long_success or short_success:
                print(f"\n⚠️ {symbol} TEK POZİSYON AÇILDI")
                self.status["successful_trades"] += 1
                self.status["failed_trades"] += 1
            else:
                print(f"\n❌ {symbol} POZİSYONLAR AÇILAMADI")
                self.status["failed_trades"] += 2

        except Exception as e:
            print(f"❌ Çift pozisyon hatası: {e}")
            self.status["failed_trades"] += 2

    async def _open_single_position(
        self,
        symbol: str,
        side: str,
        quantity: float,
        entry_price: float,
        tp_price: float,
        sl_price: float,
        position_type: str
    ) -> bool:
        """Tek pozisyon açma (TP/SL ile)"""
        try:
            print(f"🎯 {position_type} pozisyon detayları:")
            print(f"   Yön: {side}")
            print(f"   Miktar: {quantity}")
            print(f"   Entry: {entry_price:.4f}")
            print(f"   TP: {tp_price:.4f}")
            print(f"   SL: {sl_price:.4f}")

            # Ana pozisyonu aç
            await binance_client._rate_limit_delay()
            main_order = await binance_client.client.futures_create_order(
                symbol=symbol,
                side=side,
                type='MARKET',
                quantity=quantity
            )

            if not main_order or 'orderId' not in main_order:
                print(f"❌ Ana emir başarısız")
                return False

            print(f"✅ Ana pozisyon: {side} {quantity}")
            await asyncio.sleep(1.0)

            # Karşı yön
            opposite_side = 'SELL' if side == 'BUY' else 'BUY'

            # TP/SL formatlama
            formatted_tp = f"{tp_price:.{self.price_precision}f}"
            formatted_sl = f"{sl_price:.{self.price_precision}f}"

            # Stop Loss
            sl_order = await binance_client._create_stop_loss(
                symbol, opposite_side, quantity, formatted_sl
            )

            # Take Profit
            tp_order = await binance_client._create_take_profit(
                symbol, opposite_side, quantity, formatted_tp
            )

            success = bool(sl_order) and bool(tp_order)

            if success:
                print(f"✅ {position_type} tam korumalı!")

                # Firebase'e kaydet
                try:
                    firebase_manager.log_trade({
                        "symbol": symbol,
                        "strategy": "bollinger_bands_dual",
                        "position_type": position_type,
                        "side": side,
                        "entry_price": entry_price,
                        "quantity": quantity,
                        "tp": tp_price,
                        "sl": sl_price,
                        "position_size_usdt": settings.POSITION_SIZE_USDT,
                        "leverage": settings.LEVERAGE,
                        "status": "OPENED",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                except Exception as e:
                    print(f"⚠️ Firebase log hatası: {e}")
            else:
                print(f"⚠️ {position_type} kısmi koruma")

            return True

        except Exception as e:
            print(f"❌ {position_type} pozisyon hatası: {e}")
            return False

    def _calculate_quantity(self, price: float) -> float:
        """Quantity hesaplama"""
        try:
            notional_value = settings.POSITION_SIZE_USDT * settings.LEVERAGE
            quantity = notional_value / price

            # Precision uygula
            if self.quantity_precision == 0:
                quantity = math.floor(quantity)
            else:
                factor = 10 ** self.quantity_precision
                quantity = math.floor(quantity * factor) / factor

            return quantity

        except Exception as e:
            print(f"❌ Quantity hesaplama hatası: {e}")
            return 0.0

    def _get_precision(self, symbol_info: dict, filter_type: str, key: str) -> int:
        """Precision hesaplama"""
        try:
            for f in symbol_info.get('filters', []):
                if f.get('filterType') == filter_type:
                    size_str = f.get(key, "")
                    if '.' in str(size_str):
                        return len(str(size_str).split('.')[1].rstrip('0'))
            return 0
        except Exception:
            return 0

    async def _update_status_info(self):
        """Status güncelleme"""
        try:
            self.status["account_balance"] = await binance_client.get_account_balance()
        except Exception:
            pass

    def get_multi_status(self) -> dict:
        """Bot durumu"""
        return {
            "is_running": self.status["is_running"],
            "strategy": "bollinger_bands_dual_position",
            "version": "1.0",
            "symbols": self.status["symbols"],
            "active_symbol": self.status["active_symbol"],
            "position_side": self.status["position_side"],
            "status_message": self.status["status_message"],
            "account_balance": self.status["account_balance"],
            "position_pnl": self.status["position_pnl"],
            "order_size": self.status["order_size"],
            "last_signals": self.status["last_signals"],
            "websocket_connections": len(self._websocket_connections),
            "successful_trades": self.status["successful_trades"],
            "failed_trades": self.status["failed_trades"],
            "config": {
                "timeframe": settings.TIMEFRAME,
                "position_size": f"{settings.POSITION_SIZE_USDT} USDT",
                "leverage": f"{settings.LEVERAGE}x",
                "bb_period": settings.BB_PERIOD,
                "bb_std": settings.BB_STD_DEV
            }
        }

    async def stop(self):
        """Bot durdurma"""
        self._stop_requested = True

        if self._websocket:
            try:
                await self._websocket.close()
            except Exception:
                pass

        for ws in list(self._websocket_connections.values()):
            try:
                await ws.close()
            except Exception:
                pass

        self._websocket_connections.clear()

        self.status.update({
            "is_running": False,
            "symbols": [],
            "active_symbol": None,
            "status_message": "📊 Bollinger Bot durduruldu",
            "websocket_connections": 0
        })

        print("🛑 Bollinger Bot durduruldu")
        try:
            await binance_client.close()
        except Exception:
            pass


# Global instance — main.py bu değişkeni import eder
bollinger_bot = ProfitOptimizedBotCore()
