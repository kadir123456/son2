# app/fast_scalping_bot.py - OPTİMİZE EDİLMİŞ
"""
DEĞİŞİKLİKLER:
1. Dinamik pozisyon boyutu (bakiyeye göre)
2. Trade cooldown (90 saniye)
3. Minimum momentum filtresi
4. Günlük trade limiti
5. Daha iyi TP/SL yönetimi
"""

import asyncio
import json
import websockets
from datetime import datetime, timezone
import math
import time

class OptimizedScalpingBot:
    def __init__(self, settings, binance_client, strategy, firebase_manager):
        self.settings = settings
        self.binance_client = binance_client
        self.strategy = strategy
        self.firebase = firebase_manager
        
        self.status = {
            "is_running": False,
            "symbol": None,
            "status_message": "⚡ Bot başlatılmadı",
            "account_balance": 0.0,
            "successful_trades": 0,
            "failed_trades": 0,
            "total_trades": 0,
            "daily_trades": 0,
            "websocket_connections": 0
        }
        
        self.klines_1m = []
        self._stop_requested = False
        self._websocket_1m = None
        self._last_trade_time = 0
        self._daily_reset_date = datetime.now(timezone.utc).date()
        
        self.quantity_precision = 0
        self.price_precision = 2
        
        print("=" * 70)
        print("⚡ OPTİMİZE EDİLMİŞ SCALPING BOT")
        print("=" * 70)
        print(f"📊 Dinamik Pozisyon: %{settings.BALANCE_USAGE_PERCENT*100:.0f} bakiye")
        print(f"📈 Kaldıraç: {settings.LEVERAGE}x")
        print(f"🎯 TP: %{settings.TAKE_PROFIT_PERCENT*100:.2f}")
        print(f"🛑 SL: %{settings.STOP_LOSS_PERCENT*100:.2f}")
        print(f"⏳ Trade Cooldown: {settings.TRADE_COOLDOWN_SECONDS}s")
        print(f"🔢 Günlük Max: {settings.MAX_DAILY_TRADES} trade")
        print("=" * 70)
    
    async def start(self, symbol: str):
        """Bot başlatma"""
        if self.status["is_running"]:
            print("⚠️ Bot zaten çalışıyor")
            return
        
        if not symbol.endswith('USDT'):
            symbol += 'USDT'
        
        self._stop_requested = False
        self.status.update({
            "is_running": True,
            "symbol": symbol,
            "status_message": f"⚡ {symbol} başlatılıyor..."
        })
        
        print(f"🚀 Optimized Bot başlatılıyor: {symbol}")
        
        try:
            # 1. Binance bağlantısı
            print("1️⃣ Binance bağlantısı...")
            await self.binance_client.initialize()
            
            # 2. Bakiye kontrolü
            print("2️⃣ Bakiye kontrolü...")
            self.status["account_balance"] = await self.binance_client.get_account_balance()
            print(f"   Bakiye: {self.status['account_balance']:.2f} USDT")
            
            if self.status["account_balance"] < self.settings.MIN_BALANCE_USDT:
                raise Exception(f"Yetersiz bakiye! Min: {self.settings.MIN_BALANCE_USDT} USDT")
            
            # Pozisyon boyutu hesapla
            position_size = self.settings.calculate_position_size(self.status["account_balance"])
            if position_size == 0:
                raise Exception(f"Pozisyon boyutu çok küçük! Bakiye: {self.status['account_balance']}")
            
            print(f"   Pozisyon Boyutu: {position_size} USDT")
            print(f"   Notional Değer: {position_size * self.settings.LEVERAGE} USDT")
            
            # 3. Symbol bilgileri
            print(f"3️⃣ {symbol} bilgileri...")
            symbol_info = await self.binance_client.get_symbol_info(symbol)
            if not symbol_info:
                raise Exception(f"{symbol} bilgileri alınamadı")
            
            self.quantity_precision = self.binance_client._get_precision(
                symbol_info, 'LOT_SIZE', 'stepSize'
            )
            self.price_precision = self.binance_client._get_precision(
                symbol_info, 'PRICE_FILTER', 'tickSize'
            )
            
            # 4. Geçmiş veri
            print(f"4️⃣ Geçmiş veriler...")
            self.klines_1m = await self.binance_client.get_historical_klines(
                symbol, "1m", limit=50
            )
            
            if not self.klines_1m or len(self.klines_1m) < 15:
                raise Exception("Yetersiz geçmiş veri")
            
            print(f"   ✅ {len(self.klines_1m)} mum yüklendi")
            
            # 5. Kaldıraç
            print(f"5️⃣ Kaldıraç {self.settings.LEVERAGE}x...")
            await self.binance_client.set_leverage(symbol, self.settings.LEVERAGE)
            
            # 6. WebSocket başlat
            print(f"6️⃣ WebSocket başlatılıyor...")
            self.status["status_message"] = f"⚡ {symbol} AKTIF"
            self.status["websocket_connections"] = 1
            
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
        ws_url = f"{self.settings.WEBSOCKET_URL}/ws/{symbol.lower()}@kline_1m"
        reconnect_attempts = 0
        max_attempts = 10
        
        print(f"🔗 WebSocket (1m): {ws_url}")
        
        while not self._stop_requested and reconnect_attempts < max_attempts:
            try:
                async with websockets.connect(
                    ws_url,
                    ping_interval=self.settings.WEBSOCKET_PING_INTERVAL,
                    ping_timeout=self.settings.WEBSOCKET_PING_TIMEOUT
                ) as ws:
                    print(f"✅ WebSocket bağlandı")
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
            
            # Günlük limit kontrolü
            self._check_daily_reset()
            if self.status["daily_trades"] >= self.settings.MAX_DAILY_TRADES:
                print(f"⚠️ Günlük trade limiti aşıldı: {self.status['daily_trades']}/{self.settings.MAX_DAILY_TRADES}")
                return
            
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
            cooldown_remaining = self.settings.TRADE_COOLDOWN_SECONDS - (current_time - self._last_trade_time)
            
            if cooldown_remaining > 0:
                print(f"⏳ Cooldown aktif: {int(cooldown_remaining)}s kaldı")
                return
            
            # Strateji analizi
            analysis = self.strategy.analyze_and_calculate_levels(
                self.klines_1m, symbol
            )
            
            if not analysis or not analysis.get('should_trade', False):
                print(f"⚠️ {symbol}: Trade sinyali yok")
                return
            
            # Momentum kontrolü
            if analysis.get('momentum', 0) < self.settings.MIN_MOMENTUM_PERCENT:
                print(f"⚠️ {symbol}: Yetersiz momentum (%{analysis.get('momentum', 0)*100:.3f})")
                return
            
            # Pozisyon aç
            await self._open_position(symbol, analysis)
            self._last_trade_time = current_time
            
        except Exception as e:
            print(f"❌ Mesaj işleme hatası: {e}")
    
    def _check_daily_reset(self):
        """Günlük sayacı resetle"""
        today = datetime.now(timezone.utc).date()
        if today != self._daily_reset_date:
            print(f"\n📅 YENİ GÜN: {today}")
            print(f"   Dün: {self.status['daily_trades']} trade yapıldı")
            self.status['daily_trades'] = 0
            self._daily_reset_date = today
    
    async def _open_position(self, symbol: str, analysis: dict):
        """Pozisyon açma"""
        try:
            print(f"\n{'='*60}")
            print(f"⚡ {symbol} POZİSYON AÇILIYOR")
            print(f"{'='*60}")
            print(f"   Sinyal: {analysis['signal']}")
            print(f"   Entry: {analysis['entry_price']:.4f}")
            print(f"   TP: {analysis['tp_price']:.4f} (+%{analysis['tp_percent']*100:.2f})")
            print(f"   SL: {analysis['sl_price']:.4f} (-%{analysis['sl_percent']*100:.2f})")
            print(f"   Momentum: %{analysis.get('momentum', 0)*100:.3f}")
            
            # Test modu kontrolü
            if self.settings.TEST_MODE:
                print(f"🧪 TEST: {symbol} pozisyon simüle edildi")
                self.status["successful_trades"] += 1
                self.status["total_trades"] += 1
                self.status["daily_trades"] += 1
                return
            
            # Bakiye kontrolü ve pozisyon boyutu
            balance = await self.binance_client.get_account_balance()
            position_size = self.settings.calculate_position_size(balance)
            
            if position_size == 0:
                print(f"❌ Yetersiz bakiye: {balance} USDT")
                return
            
            print(f"💰 Bakiye: {balance:.2f} USDT")
            print(f"💼 Pozisyon Boyutu: {position_size} USDT")
            
            # ÖNEMLİ: Açık pozisyon kontrolü
            print(f"🔍 {symbol} açık pozisyon kontrolü...")
            open_positions = await self.binance_client.get_open_positions(symbol)
            if open_positions:
                print(f"⚠️ {symbol} için zaten açık pozisyon var!")
                print(f"   Miktar: {abs(float(open_positions[0]['positionAmt']))}")
                print(f"   Giriş: {float(open_positions[0]['entryPrice'])}")
                print(f"   PnL: {float(open_positions[0]['unRealizedProfit']):.2f} USDT")
                return
            
            # Quantity hesapla
            entry_price = analysis['entry_price']
            quantity = (position_size * self.settings.LEVERAGE) / entry_price
            
            # Precision uygula
            if self.quantity_precision == 0:
                quantity = math.floor(quantity)
            else:
                factor = 10 ** self.quantity_precision
                quantity = math.floor(quantity * factor) / factor
            
            if quantity <= 0:
                print(f"❌ Quantity çok düşük: {quantity}")
                return
            
            print(f"📊 Quantity: {quantity}")
            
            # Pozisyon aç (TP/SL ile)
            signal = analysis['signal']
            side = 'BUY' if signal == 'LONG' else 'SELL'
            
            result = await self.binance_client.create_position_with_tpsl(
                symbol=symbol,
                side=side,
                quantity=quantity,
                entry_price=entry_price,
                price_precision=self.price_precision,
                tp_percent=analysis['tp_percent'],
                sl_percent=analysis['sl_percent']
            )
            
            if result and 'orderId' in result:
                self.status["successful_trades"] += 1
                print(f"✅ {signal} POZİSYON BAŞARILI!")
                
                # Firebase'e kaydet
                try:
                    self.firebase.log_trade({
                        "symbol": symbol,
                        "strategy": "optimized_scalping",
                        "side": side,
                        "entry_price": entry_price,
                        "quantity": quantity,
                        "tp": analysis['tp_price'],
                        "sl": analysis['sl_price'],
                        "position_size_usdt": position_size,
                        "leverage": self.settings.LEVERAGE,
                        "momentum": analysis.get('momentum', 0),
                        "status": "OPENED",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                except Exception as e:
                    print(f"⚠️ Firebase log hatası: {e}")
            else:
                self.status["failed_trades"] += 1
                print(f"❌ {signal} POZİSYON BAŞARISIZ")
            
            self.status["total_trades"] += 1
            self.status["daily_trades"] += 1
            
        except Exception as e:
            print(f"❌ Pozisyon açma hatası: {e}")
            self.status["failed_trades"] += 1
            self.status["total_trades"] += 1
            self.status["daily_trades"] += 1
    
    def get_status(self) -> dict:
        """Bot durumu"""
        return {
            "is_running": self.status["is_running"],
            "strategy": "optimized_scalping",
            "version": "2.0",
            "symbol": self.status["symbol"],
            "status_message": self.status["status_message"],
            "account_balance": self.status["account_balance"],
            "successful_trades": self.status["successful_trades"],
            "failed_trades": self.status["failed_trades"],
            "total_trades": self.status["total_trades"],
            "daily_trades": self.status["daily_trades"],
            "win_rate": f"{(self.status['successful_trades']/max(self.status['total_trades'],1)*100):.1f}%",
            "websocket_connections": self.status["websocket_connections"],
            "config": {
                "timeframe": "1m",
                "position_size": f"%{self.settings.BALANCE_USAGE_PERCENT*100:.0f} bakiye",
                "leverage": f"{self.settings.LEVERAGE}x",
                "tp": f"%{self.settings.TAKE_PROFIT_PERCENT*100:.2f}",
                "sl": f"%{self.settings.STOP_LOSS_PERCENT*100:.2f}",
                "cooldown": f"{self.settings.TRADE_COOLDOWN_SECONDS}s",
                "daily_limit": self.settings.MAX_DAILY_TRADES
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
            "status_message": "⚡ Bot durduruldu",
            "websocket_connections": 0
        })
        
        print("🛑 Optimized Bot durduruldu")
        try:
            await self.binance_client.close()
        except:
            pass


# ÖNEMLİ: main.py'nin import edebilmesi için bot instance'ı oluştur
# Bu satır main.py'deki "from .fast_scalping_bot import fast_scalping_bot" import'unu çözer
fast_scalping_bot = None  # Bot başlatıldığında doldurulacak


def create_bot(settings, binance_client, strategy, firebase_manager):
    """Bot instance'ı oluştur"""
    global fast_scalping_bot
    fast_scalping_bot = OptimizedScalpingBot(settings, binance_client, strategy, firebase_manager)
    return fast_scalping_bot
