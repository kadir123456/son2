# app/bot_core.py - KAR ODAKLI OPTIMIZE EDILMIŞ BOT v2.0

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
import traceback

class ProfitOptimizedBotCore:
    def __init__(self):
        self.status = {
            "is_running": False, 
            "symbols": [],
            "active_symbol": None,
            "position_side": None, 
            "status_message": "💰 Kar Odaklı Bot başlatılmadı.",
            "account_balance": 0.0,
            "position_pnl": 0.0,
            "order_size": 0.0,
            "last_signals": {},
            "successful_trades": 0,
            "failed_trades": 0,
            "daily_pnl": 0.0,
            "total_profit": 0.0
        }
        
        self.multi_klines = {}
        self._stop_requested = False
        self.quantity_precision = {}
        self.price_precision = {}
        self._last_status_update = 0
        self._websocket_connections = {}
        self._websocket_tasks = []
        self._max_reconnect_attempts = 10
        self._connection_lock = asyncio.Lock()
        
        # 💰 Kar takibi
        self.initial_balance = 0.0
        self.daily_reset_date = datetime.now(timezone.utc).date()
        self.max_daily_loss = -200.0  # Maksimum günlük zarar limiti
        
        print("=" * 70)
        print("💰 KAR ODAKLI EMA CROSS BOT v2.0 başlatıldı")
        print("=" * 70)
        print(f"🎯 Strateji: EMA {settings.EMA_FAST_PERIOD}/{settings.EMA_SLOW_PERIOD} kesişimi")
        print(f"⏰ Timeframe: {settings.TIMEFRAME} (SIK İŞLEM)")
        print(f"📈 Kaldıraç: {settings.LEVERAGE}x")
        print(f"💰 Pozisyon: Bakiyenin %{settings.MAX_POSITION_SIZE_PERCENT*100:.0f}'i")
        print(f"🎯 TP: %{settings.TAKE_PROFIT_PERCENT*100:.1f} | SL: %{settings.STOP_LOSS_PERCENT*100:.1f}")
        print(f"⚡ Risk/Reward: 1:{settings.TAKE_PROFIT_PERCENT/settings.STOP_LOSS_PERCENT:.1f}")
        print(f"🔥 Günlük İşlem Limiti: {settings.MAX_DAILY_TRADES}")
        print("=" * 70)

    async def start(self, symbols: list):
        """💰 Kar odaklı multi-coin bot başlatma"""
        if self.status["is_running"]:
            print("⚠️ Bot zaten çalışıyor.")
            return
            
        if not symbols or len(symbols) == 0:
            print("❌ Hiç symbol verilmedi!")
            return
            
        self._stop_requested = False
        self.status.update({
            "is_running": True, 
            "symbols": symbols,
            "active_symbol": None,
            "position_side": None, 
            "status_message": f"🎯 Kar Odaklı Bot: {len(symbols)} coin başlatılıyor...",
        })
        
        print(f"🚀 KAR ODAKLI Multi-coin bot başlatılıyor: {', '.join(symbols)}")
        
        try:
            # 1. Binance bağlantısı
            print("1️⃣ Binance bağlantısı kuruluyor...")
            await binance_client.initialize()
            print("✅ Binance bağlantısı başarılı")
            
            # 2. Açık emirleri temizle
            print("2️⃣ 🧹 Açık emirler temizleniyor...")
            for symbol in symbols:
                try:
                    await binance_client.cancel_all_orders_safe(symbol)
                    await asyncio.sleep(0.2)
                except Exception as cleanup_error:
                    print(f"⚠️ {symbol} temizlik hatası: {cleanup_error}")
            
            # 3. Hesap bakiyesi ve başlangıç durumu
            print("3️⃣ Hesap bakiyesi hesaplanıyor...")
            self.status["account_balance"] = await binance_client.get_account_balance()
            self.initial_balance = self.status["account_balance"]
            print(f"✅ Başlangıç bakiyesi: {self.initial_balance:.2f} USDT")
            
            if self.initial_balance < settings.MIN_BALANCE_USDT:
                raise Exception(f"❌ Yetersiz bakiye! Min: {settings.MIN_BALANCE_USDT} USDT")
            
            # 4. Symboller için hazırlık
            print(f"4️⃣ {len(symbols)} symbol için EMA analizi hazırlığı...")
            for symbol in symbols:
                try:
                    symbol_info = await binance_client.get_symbol_info(symbol)
                    if not symbol_info:
                        print(f"❌ {symbol} bilgileri alınamadı")
                        continue
                    
                    # Precision hesaplama
                    self.quantity_precision[symbol] = self._get_precision_from_filter(symbol_info, 'LOT_SIZE', 'stepSize')
                    self.price_precision[symbol] = self._get_precision_from_filter(symbol_info, 'PRICE_FILTER', 'tickSize')
                    
                    # EMA için geçmiş veri (daha az mum, hızlı başlangıç)
                    required_candles = settings.EMA_SLOW_PERIOD + 10
                    klines = await binance_client.get_historical_klines(symbol, settings.TIMEFRAME, limit=required_candles)
                    
                    if klines and len(klines) >= required_candles - 5:
                        self.multi_klines[symbol] = klines
                        print(f"✅ {symbol} analiz hazır ({len(klines)} mum)")
                        
                        # İlk analizi test et
                        test_signal = trading_strategy.analyze_klines(klines, symbol)
                        print(f"   📊 İlk sinyal: {test_signal}")
                    else:
                        print(f"❌ {symbol} yetersiz veri")
                        continue
                        
                    await asyncio.sleep(0.2)
                    
                except Exception as symbol_error:
                    print(f"❌ {symbol} hazırlık hatası: {symbol_error}")
                    continue
            
            # 5. Mevcut açık pozisyon kontrolü
            print("5️⃣ Mevcut açık pozisyonlar kontrol ediliyor...")
            try:
                await binance_client._rate_limit_delay()
                all_positions = await binance_client.client.futures_position_information()
                open_positions = [p for p in all_positions if float(p['positionAmt']) != 0]
                
                if open_positions:
                    active_position = open_positions[0]
                    active_symbol = active_position['symbol']
                    position_amt = float(active_position['positionAmt'])
                    
                    self.status["active_symbol"] = active_symbol
                    self.status["position_side"] = "LONG" if position_amt > 0 else "SHORT"
                    
                    print(f"⚠️ Mevcut {self.status['position_side']} pozisyonu: {active_symbol}")
                else:
                    print("✅ Açık pozisyon bulunamadı")
                    # Kaldıraç ayarlama
                    print("6️⃣ Tüm symboller için kaldıraç ayarlanıyor...")
                    for symbol in symbols:
                        if symbol in self.multi_klines:
                            if await binance_client.set_leverage(symbol, settings.LEVERAGE):
                                print(f"✅ {symbol} kaldıracı {settings.LEVERAGE}x")
                            await asyncio.sleep(0.3)
                            
            except Exception as position_error:
                print(f"❌ Pozisyon kontrolü hatası: {position_error}")
                
            # 7. Multi-WebSocket bağlantıları
            print("7️⃣ 🌐 Multi-coin WebSocket başlatılıyor...")
            valid_symbols = [s for s in symbols if s in self.multi_klines]
            self.status["symbols"] = valid_symbols
            
            if not valid_symbols:
                raise Exception("Hiç geçerli symbol bulunamadı!")
            
            self.status["status_message"] = f"💰 KAR ODAKLI: {len(valid_symbols)} coin izleniyor"
            
            print("=" * 70)
            print(f"✅ {self.status['status_message']}")
            print(f"🎯 Hedef: Günlük %5-10 kar")
            print(f"⚡ Beklenen işlem sayısı: 10-30")
            print("=" * 70)
            
            await self._start_multi_websocket_loop(valid_symbols)
                        
        except Exception as e:
            error_msg = f"❌ Bot başlatma hatası: {e}"
            print(error_msg)
            print(f"❌ Traceback: {traceback.format_exc()}")
            self.status["status_message"] = error_msg
        
        print("🛑 Bot durduruluyor...")
        await self.stop()

    async def _start_multi_websocket_loop(self, symbols: list):
        """Multi-coin WebSocket döngüsü"""
        print(f"🌐 {len(symbols)} symbol için WebSocket başlatılıyor...")
        
        self._websocket_tasks = []
        for symbol in symbols:
            task = asyncio.create_task(self._single_websocket_loop(symbol))
            self._websocket_tasks.append(task)
        
        try:
            await asyncio.gather(*self._websocket_tasks, return_exceptions=True)
        except Exception as e:
            print(f"❌ Multi-WebSocket hatası: {e}")

    async def _single_websocket_loop(self, symbol: str):
        """Tek symbol için WebSocket döngüsü"""
        ws_url = f"{settings.WEBSOCKET_URL}/ws/{symbol.lower()}@kline_{settings.TIMEFRAME}"
        reconnect_attempts = 0
        
        print(f"🔗 {symbol} WebSocket başlatılıyor...")
        
        while not self._stop_requested and reconnect_attempts < self._max_reconnect_attempts:
            try:
                async with websockets.connect(
                    ws_url, 
                    ping_interval=settings.WEBSOCKET_PING_INTERVAL, 
                    ping_timeout=settings.WEBSOCKET_PING_TIMEOUT,
                    close_timeout=settings.WEBSOCKET_CLOSE_TIMEOUT
                ) as ws:
                    print(f"✅ {symbol} WebSocket bağlandı")
                    reconnect_attempts = 0
                    
                    async with self._connection_lock:
                        self._websocket_connections[symbol] = ws
                    
                    while not self._stop_requested:
                        try:
                            message = await asyncio.wait_for(ws.recv(), timeout=65.0)
                            await self._handle_websocket_message(symbol, message)
                        except asyncio.TimeoutError:
                            try:
                                await ws.ping()
                                await asyncio.sleep(1)
                            except:
                                break
                        except websockets.exceptions.ConnectionClosed:
                            break
                        except Exception as e:
                            print(f"❌ {symbol} WebSocket mesaj hatası: {e}")
                            await asyncio.sleep(1)
                            
            except Exception as e:
                if not self._stop_requested:
                    reconnect_attempts += 1
                    backoff_time = min(5 * reconnect_attempts, 30)
                    if reconnect_attempts < self._max_reconnect_attempts:
                        print(f"⏳ {symbol} yeniden bağlanılıyor... ({backoff_time}s)")
                        await asyncio.sleep(backoff_time)
            finally:
                async with self._connection_lock:
                    if symbol in self._websocket_connections:
                        del self._websocket_connections[symbol]
        
        if reconnect_attempts >= self._max_reconnect_attempts:
            print(f"❌ {symbol} WebSocket maksimum deneme aşıldı")

    async def _handle_websocket_message(self, symbol: str, message: str):
        """WebSocket mesaj işleme - KAR ODAKLI"""
        try:
            data = json.loads(message)
            kline_data = data.get('k', {})
            
            # Günlük reset kontrolü
            self._check_daily_reset()
            
            # Günlük zarar limiti kontrolü
            if await self._check_daily_loss_limit():
                return
            
            # Status update kontrolü
            current_time = time.time()
            if current_time - self._last_status_update > settings.STATUS_UPDATE_INTERVAL:
                await self._update_status_info()
                self._last_status_update = current_time
            
            # Sadece kapanan mumları işle
            if not kline_data.get('x', False):
                return
                
            # Kline data güncelle
            if symbol not in self.multi_klines:
                self.multi_klines[symbol] = []
            
            # Memory optimization
            max_klines = settings.MAX_KLINES_PER_SYMBOL
            if len(self.multi_klines[symbol]) >= max_klines:
                self.multi_klines[symbol].pop(0)
                
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
            
            self.multi_klines[symbol].append(new_kline)
            
            # Minimum veri kontrolü
            min_required = settings.EMA_SLOW_PERIOD + 5
            if len(self.multi_klines[symbol]) < min_required:
                return
            
            # ✅ EMA analizi
            signal = trading_strategy.analyze_klines(self.multi_klines[symbol], symbol)
            
            # Önceki sinyal ile karşılaştır
            previous_signal = self.status["last_signals"].get(symbol, "HOLD")
            
            # Sinyal değişikliğinde işlem yap
            if signal != previous_signal and signal != "HOLD":
                print(f"🚨 {symbol} YENİ EMA CROSS: {previous_signal} -> {signal}")
                self.status["last_signals"][symbol] = signal
                
                # Pozisyon mantığı
                await self._handle_position_logic_profit_focused(symbol, signal)
            
        except Exception as e:
            print(f"❌ {symbol} WebSocket hatası: {e}")

    async def _handle_position_logic_profit_focused(self, signal_symbol: str, signal: str):
        """💰 KAR ODAKLI pozisyon yönetim mantığı"""
        try:
            current_active_symbol = self.status.get("active_symbol")
            current_position_side = self.status.get("position_side")
            
            # DURUM 1: Hiç pozisyon yok, yeni sinyal geldi
            if not current_active_symbol and not current_position_side:
                print(f"🚀 Yeni fırsat: {signal_symbol} -> {signal}")
                success = await self._open_position_profit_focused(signal_symbol, signal)
                if success:
                    self.status["successful_trades"] += 1
                else:
                    self.status["failed_trades"] += 1
                return
            
            # DURUM 2: Mevcut pozisyon var, aynı symbol'den ters sinyal geldi
            if (current_active_symbol == signal_symbol and 
                current_position_side and 
                signal != current_position_side):
                print(f"🔄 {signal_symbol} Ters sinyal: {current_position_side} -> {signal}")
                success = await self._close_and_reverse_position_safe(signal_symbol, signal)
                if success:
                    self.status["successful_trades"] += 1
                else:
                    self.status["failed_trades"] += 1
                return
            
            # DURUM 3: Mevcut pozisyon var, başka symbol'den sinyal geldi
            if (current_active_symbol and 
                current_active_symbol != signal_symbol and 
                current_position_side):
                print(f"💡 Yeni coin fırsatı: {signal_symbol} -> {signal}")
                success = await self._switch_to_new_coin_safe(current_active_symbol, signal_symbol, signal)
                if success:
                    self.status["successful_trades"] += 1
                else:
                    self.status["failed_trades"] += 1
                return
            
            # DURUM 4: Pozisyon kapanmış mı kontrol et
            if current_active_symbol and current_position_side:
                if time.time() % 30 < 1:
                    open_positions = await binance_client.get_open_positions(current_active_symbol)
                    if not open_positions:
                        print(f"✅ {current_active_symbol} pozisyonu TP/SL ile kapandı")
                        await self._handle_position_closed_safe(current_active_symbol, signal_symbol, signal)
                        
        except Exception as e:
            print(f"❌ Pozisyon mantığı hatası: {e}")
            self.status["failed_trades"] += 1

    async def _open_position_profit_focused(self, symbol: str, signal: str) -> bool:
        """💰 KAR ODAKLI pozisyon açma - %90 BAKIYE"""
        try:
            print(f"💰 {symbol} -> {signal} pozisyonu açılıyor (Bakiyenin %90'ı)...")
            
            if settings.TEST_MODE:
                print(f"🧪 TEST: {symbol} {signal} simüle edildi")
                self.status["active_symbol"] = symbol
                self.status["position_side"] = signal
                return True
            
            await asyncio.sleep(settings.API_CALL_DELAY)
            
            # Açık emirleri temizle
            await binance_client.cancel_all_orders_safe(symbol)
            await asyncio.sleep(0.5)
            
            # 💰 Order size hesapla - %90 BAKIYE
            order_size = await self._calculate_order_size_profit_focused()
            if order_size < 15.0:
                print(f"❌ {symbol} pozisyon boyutu çok düşük: {order_size}")
                return False
            
            # Güncel fiyat al
            price = await binance_client.get_market_price(symbol)
            if not price:
                print(f"❌ {symbol} fiyat alınamadı")
                return False
                
            # Pozisyon detayları
            side = "BUY" if signal == "LONG" else "SELL"
            quantity = self._format_quantity(symbol, (order_size * settings.LEVERAGE) / price)
            
            if quantity <= 0:
                print(f"❌ {symbol} miktar çok düşük: {quantity}")
                return False

            print(f"💰 {symbol} Pozisyon Detayları:")
            print(f"   📊 Yön: {side}")
            print(f"   💵 Miktar: {quantity}")
            print(f"   💲 Fiyat: {price:.6f}")
            print(f"   💰 Kullanılan bakiye: {order_size:.2f} USDT (%90)")
            print(f"   📈 Kaldıraç: {settings.LEVERAGE}x")
            print(f"   🎯 Pozisyon gücü: {order_size * settings.LEVERAGE:.2f} USDT")
            
            # Pozisyon oluştur
            order = await binance_client.create_simple_position(
                symbol, side, quantity, price, 
                self.price_precision.get(symbol, 2)
            )
            
            if order:
                self.status["active_symbol"] = symbol
                self.status["position_side"] = signal
                self.status["status_message"] = f"💰 {signal}: {symbol} @ {price:.6f} (%90 bakiye)"
                
                # Firebase'e kaydet
                firebase_manager.log_trade({
                    "symbol": symbol,
                    "strategy": "profit_focused_ema_cross",
                    "side": signal,
                    "entry_price": price,
                    "quantity": quantity,
                    "order_size_usdt": order_size,
                    "leverage": settings.LEVERAGE,
                    "position_power_usdt": order_size * settings.LEVERAGE,
                    "tp_percent": settings.TAKE_PROFIT_PERCENT * 100,
                    "sl_percent": settings.STOP_LOSS_PERCENT * 100,
                    "status": "OPENED",
                    "timestamp": datetime.now(timezone.utc)
                })
                
                print(f"✅ {symbol} {signal} pozisyonu BAŞARIile açıldı!")
                print(f"   🎯 TP: %{settings.TAKE_PROFIT_PERCENT*100:.1f}")
                print(f"   🛑 SL: %{settings.STOP_LOSS_PERCENT*100:.1f}")
                return True
            else:
                print(f"❌ {symbol} pozisyonu açılamadı")
                return False
                
        except Exception as e:
            print(f"❌ {symbol} pozisyon açma hatası: {e}")
            return False

    async def _calculate_order_size_profit_focused(self) -> float:
        """💰 BAKİYENİN %90'INI KULLAN"""
        try:
            current_balance = await binance_client.get_account_balance()
            
            # %90'ını kullan
            order_size = current_balance * settings.MAX_POSITION_SIZE_PERCENT
            
            # Minimum kontrol
            min_size = 50.0
            
            final_size = max(order_size, min_size)
            self.status["order_size"] = final_size
            
            print(f"💰 Order size hesaplandı:")
            print(f"   📊 Mevcut bakiye: {current_balance:.2f} USDT")
            print(f"   💰 Kullanılacak: {final_size:.2f} USDT (%{settings.MAX_POSITION_SIZE_PERCENT*100:.0f})")
            print(f"   📈 Pozisyon gücü: {final_size * settings.LEVERAGE:.2f} USDT ({settings.LEVERAGE}x)")
            
            return final_size
            
        except Exception as e:
            print(f"❌ Order size hesaplama hatası: {e}")
            return 50.0

    async def _close_and_reverse_position_safe(self, symbol: str, new_signal: str) -> bool:
        """Pozisyonu kapat ve ters yöne aç"""
        try:
            print(f"🔄 {symbol} pozisyon tersine çeviriliyor -> {new_signal}")
            
            open_positions = await binance_client.get_open_positions(symbol)
            if open_positions:
                position = open_positions[0]
                position_amt = float(position['positionAmt'])
                side_to_close = 'SELL' if position_amt > 0 else 'BUY'
                
                # PnL kaydet
                pnl = float(position['unRealizedProfit'])
                self.status["daily_pnl"] += pnl
                self.status["total_profit"] += pnl
                
                print(f"💰 Pozisyon PnL: {pnl:.2f} USDT")
                print(f"📊 Günlük PnL: {self.status['daily_pnl']:.2f} USDT")
                
                firebase_manager.log_trade({
                    "symbol": symbol,
                    "strategy": "profit_focused_ema_cross",
                    "pnl": pnl, 
                    "status": "CLOSED_FOR_REVERSE", 
                    "timestamp": datetime.now(timezone.utc)
                })

                await binance_client.cancel_all_orders_safe(symbol)
                await asyncio.sleep(0.8)
                
                try:
                    await binance_client._rate_limit_delay()
                    close_order = await binance_client.client.futures_create_order(
                        symbol=symbol,
                        side=side_to_close,
                        type='MARKET',
                        quantity=abs(position_amt),
                        reduceOnly=True
                    )
                    print(f"✅ {symbol} eski pozisyon kapatıldı")
                    await asyncio.sleep(1.5)
                except Exception as close_error:
                    print(f"❌ {symbol} pozisyon kapatma hatası: {close_error}")
                    return False
                
            # Yeni pozisyonu aç
            success = await self._open_position_profit_focused(symbol, new_signal)
            if success:
                print(f"✅ {symbol} Ters pozisyon başarılı: {new_signal}")
                return True
            else:
                self.status["active_symbol"] = None
                self.status["position_side"] = None
                return False
                
        except Exception as e:
            print(f"❌ {symbol} ters pozisyon hatası: {e}")
            return False

    async def _switch_to_new_coin_safe(self, current_symbol: str, new_symbol: str, new_signal: str) -> bool:
        """Yeni coin'e geç"""
        try:
            print(f"🔄 COİN DEĞİŞİMİ: {current_symbol} -> {new_symbol} ({new_signal})")
            
            open_positions = await binance_client.get_open_positions(current_symbol)
            if open_positions:
                position = open_positions[0]
                pnl = float(position['unRealizedProfit'])
                self.status["daily_pnl"] += pnl
                self.status["total_profit"] += pnl
                
                print(f"💰 {current_symbol} PnL: {pnl:.2f} USDT")
                
                firebase_manager.log_trade({
                    "symbol": current_symbol, 
                    "strategy": "profit_focused_ema_cross",
                    "pnl": pnl, 
                    "status": "CLOSED_FOR_COIN_SWITCH", 
                    "timestamp": datetime.now(timezone.utc)
                })
                
                await binance_client.cancel_all_orders_safe(current_symbol)
                await asyncio.sleep(1.2)

                position_amt = float(position['positionAmt'])
                side_to_close = 'SELL' if position_amt > 0 else 'BUY'
                
                try:
                    await binance_client._rate_limit_delay()
                    close_order = await binance_client.client.futures_create_order(
                        symbol=current_symbol,
                        side=side_to_close,
                        type='MARKET',
                        quantity=abs(position_amt),
                        reduceOnly=True
                    )
                    print(f"✅ {current_symbol} pozisyon kapatıldı")
                    await asyncio.sleep(1.5)
                except Exception as close_error:
                    print(f"❌ {current_symbol} kapatma hatası: {close_error}")
                    return False

            success = await self._open_position_profit_focused(new_symbol, new_signal)
            if not success:
                self.status["active_symbol"] = None
                self.status["position_side"] = None
                return False
            
            return True
                
        except Exception as e:
            print(f"❌ Coin değişimi hatası: {e}")
            return False

    async def _handle_position_closed_safe(self, closed_symbol: str, signal_symbol: str, signal: str):
        """Pozisyon kapandığında işlemler"""
        try:
            self.status["active_symbol"] = None
            self.status["position_side"] = None
            
            print(f"✅ {closed_symbol} pozisyonu TP/SL ile başarıyla kapandı")
            
            # Yeni sinyal varsa pozisyon aç
            if signal != "HOLD":
                print(f"🚀 Yeni fırsat: {signal_symbol} -> {signal}")
                success = await self._open_position_profit_focused(signal_symbol, signal)
                if success:
                    print(f"✅ Yeni pozisyon {signal_symbol} için açıldı")
                
        except Exception as e:
            print(f"❌ Position closed handling hatası: {e}")

    def _check_daily_reset(self):
        """Günlük reset kontrolü"""
        today = datetime.now(timezone.utc).date()
        if today != self.daily_reset_date:
            print("=" * 70)
            print(f"📅 YENİ GÜN - İstatistikler sıfırlanıyor")
            print(f"📊 Dünkü PnL: {self.status['daily_pnl']:.2f} USDT")
            print(f"💰 Toplam kar: {self.status['total_profit']:.2f} USDT")
            print("=" * 70)
            
            self.status["daily_pnl"] = 0.0
            self.daily_reset_date = today

    async def _check_daily_loss_limit(self) -> bool:
        """Günlük zarar limiti kontrolü"""
        if self.status["daily_pnl"] <= self.max_daily_loss:
            print("=" * 70)
            print(f"🛑 GÜNLÜK ZARAR LİMİTİ AŞILDI!")
            print(f"📊 Günlük PnL: {self.status['daily_pnl']:.2f} USDT")
            print(f"🚨 Limit: {self.max_daily_loss:.2f} USDT")
            print(f"🛑 Bot güvenlik için durduruldu!")
            print("=" * 70)
            
            await self.stop()
            return True
        return False

    def _get_precision_from_filter(self, symbol_info, filter_type, key):
        for f in symbol_info['filters']:
            if f['filterType'] == filter_type:
                size_str = f[key]
                if '.' in size_str:
                    return len(size_str.split('.')[1].rstrip('0'))
                return 0
        return 0

    def _format_quantity(self, symbol: str, quantity: float):
        precision = self.quantity_precision.get(symbol, 0)
        if precision == 0:
            return math.floor(quantity)
        factor = 10 ** precision
        return math.floor(quantity * factor) / factor

    async def _update_status_info(self):
        """Status güncelleme"""
        try:
            if not self.status["is_running"]:
                return
                
            # Bakiye güncelle
            if time.time() % 45 < 1:
                self.status["account_balance"] = await binance_client.get_account_balance()
            
            if self.status["active_symbol"] and self.status["position_side"]:
                # Position PnL
                if time.time() % 30 < 1:
                    positions = await binance_client.get_open_positions(self.status["active_symbol"])
                    if positions:
                        self.status["position_pnl"] = float(positions[0]['unRealizedProfit'])
                    else:
                        self.status["position_pnl"] = 0.0
            else:
                self.status["position_pnl"] = 0.0
            
        except Exception as e:
            print(f"❌ Status güncelleme hatası: {e}")

    def get_multi_status(self):
        """Bot durumunu döndür"""
        win_rate = 0
        total_trades = self.status["successful_trades"] + self.status["failed_trades"]
        if total_trades > 0:
            win_rate = (self.status["successful_trades"] / total_trades) * 100
        
        # Günlük kar yüzdesi
        daily_profit_percent = 0.0
        if self.initial_balance > 0:
            daily_profit_percent = (self.status["daily_pnl"] / self.initial_balance) * 100
        
        # Toplam kar yüzdesi
        total_profit_percent = 0.0
        if self.initial_balance > 0:
            total_profit_percent = (self.status["total_profit"] / self.initial_balance) * 100
        
        return {
            "is_running": self.status["is_running"],
            "strategy": "profit_focused_ema_cross_v2",
            "version": "2.0_profit_optimized",
            "symbols": self.status["symbols"],
            "active_symbol": self.status["active_symbol"],
            "position_side": self.status["position_side"],
            "status_message": self.status["status_message"],
            "account_balance": self.status["account_balance"],
            "initial_balance": self.initial_balance,
            "position_pnl": self.status["position_pnl"],
            "order_size": self.status["order_size"],
            "last_signals": self.status["last_signals"],
            "websocket_connections": len(self._websocket_connections),
            "successful_trades": self.status["successful_trades"],
            "failed_trades": self.status["failed_trades"],
            "win_rate": f"{win_rate:.1f}%",
            "daily_pnl": self.status["daily_pnl"],
            "daily_profit_percent": f"{daily_profit_percent:.2f}%",
            "total_profit": self.status["total_profit"],
            "total_profit_percent": f"{total_profit_percent:.2f}%",
            "max_daily_loss": self.max_daily_loss,
            "config": {
                "ema_fast": settings.EMA_FAST_PERIOD,
                "ema_slow": settings.EMA_SLOW_PERIOD,
                "timeframe": settings.TIMEFRAME,
                "leverage": settings.LEVERAGE,
                "stop_loss": f"{settings.STOP_LOSS_PERCENT*100:.1f}%",
                "take_profit": f"{settings.TAKE_PROFIT_PERCENT*100:.1f}%",
                "position_size": f"{settings.MAX_POSITION_SIZE_PERCENT*100:.0f}% of balance",
                "risk_reward": f"1:{settings.TAKE_PROFIT_PERCENT/settings.STOP_LOSS_PERCENT:.1f}"
            },
            "profit_optimizations": [
                "✅ Bakiyenin %90'ı kullanılıyor",
                "✅ 15x kaldıraç (kar potansiyeli yüksek)",
                "✅ 1m timeframe (sık işlem)",
                "✅ R/R 1:3 (optimize)",
                "✅ Günlük zarar limiti aktif",
                "✅ Whipsaw koruması minimal",
                "✅ Kalite filtreleri hafif"
            ]
        }

    async def stop(self):
        """Bot durdurma"""
        self._stop_requested = True
        if self.status["is_running"]:
            print("=" * 70)
            print("🛑 KAR ODAKLI BOT DURDURULUYOR...")
            print("=" * 70)
            
            # WebSocket task'larını iptal et
            for task in self._websocket_tasks:
                if not task.done():
                    task.cancel()
            
            # WebSocket bağlantılarını kapat
            async with self._connection_lock:
                connections_copy = dict(self._websocket_connections)
                
            for symbol, ws in connections_copy.items():
                try:
                    await ws.close()
                    print(f"🔌 {symbol} WebSocket kapatıldı")
                except Exception as close_error:
                    print(f"⚠️ {symbol} WebSocket kapatma hatası: {close_error}")
            
            async with self._connection_lock:
                self._websocket_connections.clear()
            
            # Final istatistikler
            successful = self.status["successful_trades"]
            failed = self.status["failed_trades"]
            total = successful + failed
            
            print("=" * 70)
            print("📊 FINAL İSTATİSTİKLER:")
            print("=" * 70)
            print(f"💰 Başlangıç Bakiyesi: {self.initial_balance:.2f} USDT")
            print(f"💵 Güncel Bakiye: {self.status['account_balance']:.2f} USDT")
            print(f"📈 Günlük PnL: {self.status['daily_pnl']:.2f} USDT ({self.status['daily_pnl']/max(self.initial_balance,1)*100:.2f}%)")
            print(f"💎 Toplam Kar: {self.status['total_profit']:.2f} USDT ({self.status['total_profit']/max(self.initial_balance,1)*100:.2f}%)")
            print(f"✅ Başarılı İşlem: {successful}")
            print(f"❌ Başarısız İşlem: {failed}")
            if total > 0:
                print(f"📊 Win Rate: %{(successful/total*100):.1f}")
            print("=" * 70)
            
            self.status.update({
                "is_running": False, 
                "symbols": [],
                "active_symbol": None,
                "status_message": "💰 Kar Odaklı Bot durduruldu.",
                "position_pnl": 0.0,
                "last_signals": {}
            })
            
            await binance_client.close()

# Global instance
bot_core = ProfitOptimizedBotCore()
