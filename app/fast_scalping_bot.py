# app/fast_scalping_bot.py
# HIZLI SCALPING BOT - 30 SANİYE VE 1 DAKİKA

import asyncio
import json
import websockets
from .config import settings
from .binance_client import binance_client
from .fast_scalping_strategy import fast_scalping_strategy
from .firebase_manager import firebase_manager
from datetime import datetime, timezone
import math
import time


class FastScalpingBot:
    """
    ⚡ HIZLI SCALPING BOT
    
    - 30 saniye ve 1 dakikalık mumlar
    - Sürekli pozisyon aç-kapa
    - Dakikada 1-2 işlem hedefi
    - Filtre YOK - Agresif trade
    """
    
    def __init__(self):
        self.status = {
            "is_running": False,
            "symbol": None,
            "status_message": "⚡ Hızlı Scalping Bot başlatılmadı",
            "account_balance": 0.0,
            "successful_trades": 0,
            "failed_trades": 0,
            "total_trades": 0,
            "websocket_connections": 0
        }
        
        self.klines_30s = []  # 30 saniyelik mumlar
        self.klines_1m = []   # 1 dakikalık mumlar
        
        self._stop_requested = False
        self._websocket_30s = None
        self._websocket_1m = None
        self._last_trade_time = 0
        self._trade_cooldown = 30  # 30 saniye minimum aralık
        
        self.quantity_precision = 0
        self.price_precision = 2
        
        print("=" * 70)
        print("⚡ HIZLI SCALPING BOT")
        print("=" * 70)
        print(f"⏰ Timeframe: 30s + 1m")
        print(f"💰 Pozisyon: 10 USDT")
        print(f"📈 Kaldıraç: 15x")
        print(f"🎯 TP: %0.4 | SL: %0.2")
        print("=" * 70)
    
    async def start(self, symbol: str):
        """Bot başlatma"""
        if self.status["is_running"]:
            print("⚠️ Bot zaten çalışıyor")
            return
        
        # Symbol formatı
        if not symbol.endswith('USDT'):
            symbol += 'USDT'
        
        self._stop_requested = False
        self.status.update({
            "is_running": True,
            "symbol": symbol,
            "status_message": f"⚡ {symbol} Hızlı Scalping başlatılıyor..."
        })
        
        print(f"🚀 Hızlı Scalping Bot başlatılıyor: {symbol}")
        
        try:
            # 1. Binance bağlantısı
            print("1️⃣ Binance bağlantısı...")
            await binance_client.initialize()
            
            # 2. Bakiye kontrolü
            print("2️⃣ Bakiye kontrolü...")
            self.status["account_balance"] = await binance_client.get_account_balance()
            print(f"   Bakiye: {self.status['account_balance']:.2f} USDT")
            
            if self.status["account_balance"] < 10:
                raise Exception("Yetersiz bakiye! Min: 10 USDT")
            
            # 3. Symbol bilgileri
            print(f"3️⃣ {symbol} bilgileri...")
            symbol_info = await binance_client.get_symbol_info(symbol)
            if not symbol_info:
                raise Exception(f"{symbol} bilgileri alınamadı")
            
            self.quantity_precision = self._get_precision(symbol_info, 'LOT_SIZE', 'stepSize')
            self.price_precision = self._get_precision(symbol_info, 'PRICE_FILTER', 'tickSize')
            
            # 4. Geçmiş veri
            print(f"4️⃣ Geçmiş veriler...")
            self.klines_1m = await binance_client.get_historical_klines(symbol, "1m", limit=50)
            
            if not self.klines_1m or len(self.klines_1m) < 15:
                raise Exception("Yetersiz geçmiş veri")
            
            print(f"   ✅ {len(self.klines_1m)} mum yüklendi")
            
            # 5. Kaldıraç
            print(f"5️⃣ Kaldıraç 15x...")
            await binance_client.set_leverage(symbol, 15)
            
            # 6. WebSocket başlat
            print(f"6️⃣ WebSocket başlatılıyor...")
            self.status["status_message"] = f"⚡ {symbol} Hızlı Scalping AKTIF"
            self.status["websocket_connections"] = 1
            
            # Sadece 1 dakikalık WebSocket kullan (daha stabil)
            await self._start_websocket_1m(symbol)
            
        except Exception as e:
            error_msg = f"❌ Bot başlatma hatası: {e}"
            print(error_msg)
            self.status["status_message"] = error_msg
            try:
                await self.stop()
            except:
                pass
    
    async def _start_websocket_1m(self, symbol: str):
        """1 dakikalık WebSocket"""
        ws_url = f"{settings.WEBSOCKET_URL}/ws/{symbol.lower()}@kline_1m"
        reconnect_attempts = 0
        max_attempts = 10
        
        print(f"🔗 WebSocket (1m): {ws_url}")
        
        while not self._stop_requested and reconnect_attempts < max_attempts:
            try:
                async with websockets.connect(
                    ws_url,
                    ping_interval=settings.WEBSOCKET_PING_INTERVAL,
                    ping_timeout=settings.WEBSOCKET_PING_TIMEOUT
                ) as ws:
                    print(f"✅ WebSocket (1m) bağlandı")
                    reconnect_attempts = 0
                    self._websocket_1m = ws
                    
                    while not self._stop_requested:
                        try:
                            message = await asyncio.wait_for(ws.recv(), timeout=65.0)
                            await self._handle_websocket_message(symbol, message)
                        except asyncio.TimeoutError:
                            try:
                                await ws.ping()
                            except:
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
            
            # Sadece kapanan mumları işle
            if not kline_data.get('x', False):
                return
            
            print(f"\n🕐 {symbol} MUM KAPANDI - Analiz başlıyor...")
            
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
            if len(self.klines_1m) >= 100:
                self.klines_1m.pop(0)
            
            self.klines_1m.append(new_kline)
            
            # Cooldown kontrolü
            current_time = time.time()
            if current_time - self._last_trade_time < self._trade_cooldown:
                remaining = int(self._trade_cooldown - (current_time - self._last_trade_time))
                print(f"⏳ Cooldown aktif: {remaining}s kaldı")
                return
            
            # Strateji analizi
            analysis = fast_scalping_strategy.analyze_and_calculate_levels(
                self.klines_1m, symbol
            )
            
            if not analysis or not analysis.get('should_trade', False):
                print(f"⚠️ {symbol}: Analiz başarısız")
                return
            
            # Pozisyon aç
            await self._open_position(symbol, analysis)
            self._last_trade_time = current_time
            
        except Exception as e:
            print(f"❌ Mesaj işleme hatası: {e}")
    
    async def _open_position(self, symbol: str, analysis: dict):
        """Pozisyon açma"""
        try:
            print(f"\n⚡ {symbol} POZİSYON AÇILIYOR...")
            print(f"   Sinyal: {analysis['signal']}")
            print(f"   Entry: {analysis['entry_price']:.4f}")
            print(f"   TP: {analysis['tp_price']:.4f} (+%{analysis['tp_percent']*100:.2f})")
            print(f"   SL: {analysis['sl_price']:.4f} (-%{analysis['sl_percent']*100:.2f})")
            
            # Test modu kontrolü
            if settings.TEST_MODE:
                print(f"🧪 TEST: {symbol} pozisyon simüle edildi")
                self.status["successful_trades"] += 1
                self.status["total_trades"] += 1
                return
            
            # Quantity hesapla
            entry_price = analysis['entry_price']
            position_size_usdt = 10.0  # Sabit 10 USDT
            leverage = 15
            
            quantity = (position_size_usdt * leverage) / entry_price
            
            # Precision uygula
            if self.quantity_precision == 0:
                quantity = math.floor(quantity)
            else:
                factor = 10 ** self.quantity_precision
                quantity = math.floor(quantity * factor) / factor
            
            if quantity <= 0:
                print(f"❌ Quantity çok düşük: {quantity}")
                return
            
            print(f"💰 Quantity: {quantity}")
            
            # Ana pozisyon aç
            signal = analysis['signal']
            side = 'BUY' if signal == 'LONG' else 'SELL'
            
            await binance_client._rate_limit_delay()
            main_order = await binance_client.client.futures_create_order(
                symbol=symbol,
                side=side,
                type='MARKET',
                quantity=quantity
            )
            
            if not main_order or 'orderId' not in main_order:
                print(f"❌ Ana emir başarısız")
                self.status["failed_trades"] += 1
                self.status["total_trades"] += 1
                return
            
            print(f"✅ Ana pozisyon: {side} {quantity}")
            await asyncio.sleep(1.0)
            
            # TP/SL ekle
            opposite_side = 'SELL' if side == 'BUY' else 'BUY'
            
            formatted_tp = f"{analysis['tp_price']:.{self.price_precision}f}"
            formatted_sl = f"{analysis['sl_price']:.{self.price_precision}f}"
            
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
                print(f"✅ {signal} POZİSYON TAM KORUMALI!")
                self.status["successful_trades"] += 1
                
                # Firebase'e kaydet
                try:
                    firebase_manager.log_trade({
                        "symbol": symbol,
                        "strategy": "fast_scalping",
                        "side": side,
                        "entry_price": entry_price,
                        "quantity": quantity,
                        "tp": analysis['tp_price'],
                        "sl": analysis['sl_price'],
                        "position_size_usdt": position_size_usdt,
                        "leverage": leverage,
                        "status": "OPENED",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                except Exception as e:
                    print(f"⚠️ Firebase log hatası: {e}")
            else:
                print(f"⚠️ {signal} kısmi koruma")
                self.status["failed_trades"] += 1
            
            self.status["total_trades"] += 1
            
        except Exception as e:
            print(f"❌ Pozisyon açma hatası: {e}")
            self.status["failed_trades"] += 1
            self.status["total_trades"] += 1
    
    def _get_precision(self, symbol_info: dict, filter_type: str, key: str) -> int:
        """Precision hesaplama"""
        try:
            for f in symbol_info.get('filters', []):
                if f.get('filterType') == filter_type:
                    size_str = f.get(key, "")
                    if '.' in str(size_str):
                        return len(str(size_str).split('.')[1].rstrip('0'))
            return 0
        except:
            return 0
    
    def get_status(self) -> dict:
        """Bot durumu"""
        return {
            "is_running": self.status["is_running"],
            "strategy": "fast_scalping",
            "version": "1.0",
            "symbol": self.status["symbol"],
            "status_message": self.status["status_message"],
            "account_balance": self.status["account_balance"],
            "successful_trades": self.status["successful_trades"],
            "failed_trades": self.status["failed_trades"],
            "total_trades": self.status["total_trades"],
            "win_rate": f"{(self.status['successful_trades']/max(self.status['total_trades'],1)*100):.1f}%",
            "websocket_connections": self.status["websocket_connections"],
            "config": {
                "timeframe": "1m",
                "position_size": "10 USDT",
                "leverage": "15x",
                "tp": "%0.4",
                "sl": "%0.2"
            }
        }
    
    async def stop(self):
        """Bot durdurma"""
        self._stop_requested = True
        
        if self._websocket_1m:
            try:
                await self._websocket_1m.close()
            except:
                pass
        
        self.status.update({
            "is_running": False,
            "symbol": None,
            "status_message": "⚡ Hızlı Scalping Bot durduruldu",
            "websocket_connections": 0
        })
        
        print("🛑 Hızlı Scalping Bot durduruldu")
        try:
            await binance_client.close()
        except:
            pass


# Global instance
fast_scalping_bot = FastScalpingBot()
