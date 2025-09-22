import asyncio
import json
import websockets
from .config import settings
from .binance_client import binance_client
from .trading_strategy import trading_strategy
from .firebase_manager import firebase_manager
from .position_manager import position_manager
from datetime import datetime, timezone
import math
import time
import traceback
from threading import Lock

class BotCore:
    def __init__(self):
        self.status = {
            "is_running": False, 
            "symbols": [],  # Multi-coin support
            "active_symbol": None,  # Şu anda pozisyonu olan symbol
            "position_side": None, 
            "status_message": "EMA Cross Scalping Bot başlatılmadı.",
            "account_balance": 0.0,
            "position_pnl": 0.0,
            "order_size": 0.0,
            "dynamic_sizing": True,
            "position_monitor_active": False,
            "last_signals": {},  # Her coin için son sinyal
            "signal_filters_active": True,
            "filtered_signals_count": 0,
            "ema_cross_signals_count": 0,  # EMA Cross sinyalleri için
            "successful_trades": 0,
            "failed_trades": 0
        }
        self.multi_klines = {}  # Her symbol için ayrı kline data
        self._stop_requested = False
        self.quantity_precision = {}  # Her symbol için precision
        self.price_precision = {}
        self._last_status_update = 0
        self._websocket_connections = {}  # Her symbol için WebSocket bağlantısı
        self._websocket_tasks = []  # WebSocket task'ları
        self._max_reconnect_attempts = 10
        self._debug_enabled = settings.DEBUG_MODE if hasattr(settings, 'DEBUG_MODE') else True
        
        # ✅ PERFORMANCE OPTIMIZATION EKLEMELER
        self._calculation_lock = Lock()  # Thread safety için
        self._last_balance_calculation = 0  # Son hesaplama zamanı
        self._cached_order_size = 0.0  # Cache'lenmiş order size
        self._balance_calculation_interval = 45  # 45 saniye interval
        self._calculation_in_progress = False  # Hesaplama devam ediyor mu?
        self._last_signal_time = {}  # Signal throttling için
        self._signal_count_per_minute = {}  # Dakikada sinyal sayısı
        
        print("🚀 PERFORMANCE OPTIMIZED EMA Cross Scalping Bot v3.2 başlatıldı")
        print(f"📊 Strateji: EMA {settings.EMA_FAST_PERIOD}/{settings.EMA_SLOW_PERIOD}/{settings.EMA_TREND_PERIOD} + RSI + Volume")
        print(f"💰 Risk/Reward: SL=%{settings.STOP_LOSS_PERCENT*100:.1f} / TP=%{settings.TAKE_PROFIT_PERCENT*100:.1f}")
        print(f"⚡ Performance: Cache={self._balance_calculation_interval}s, Rate Limit Protected")

    def _get_precision_from_filter(self, symbol_info, filter_type, key):
        for f in symbol_info['filters']:
            if f['filterType'] == filter_type:
                size_str = f[key]
                if '.' in size_str:
                    return len(size_str.split('.')[1].rstrip('0'))
                return 0
        return 0

    async def _calculate_dynamic_order_size(self):
        """✅ OPTIMIZE: Dinamik pozisyon boyutu hesapla - Cache ve rate limit korumalı"""
        
        # Thread safety kontrolü
        if self._calculation_in_progress:
            return self._cached_order_size if self._cached_order_size > 0 else settings.ORDER_SIZE_USDT
        
        current_time = time.time()
        
        # Cache kontrolü - 45 saniyede bir hesapla
        if (current_time - self._last_balance_calculation < self._balance_calculation_interval and 
            self._cached_order_size > 0):
            return self._cached_order_size
        
        # Hesaplama başlat - thread safe
        with self._calculation_lock:
            self._calculation_in_progress = True
            
            try:
                current_balance = await binance_client.get_account_balance(use_cache=True)
                dynamic_size = current_balance * 0.9
                
                min_size = 15.0  # Minimum
                max_size = 1000.0
                
                final_size = max(min(dynamic_size, max_size), min_size)
                
                # Cache güncelle
                self._cached_order_size = final_size
                self._last_balance_calculation = current_time
                self.status["order_size"] = final_size
                
                if self._debug_enabled:
                    print(f"💰 Dinamik pozisyon hesaplandı: {final_size:.2f} USDT (Sonraki: {self._balance_calculation_interval}s)")
                
                return final_size
                
            except Exception as e:
                print(f"❌ Dinamik pozisyon hesaplama hatası: {e}")
                fallback_size = settings.ORDER_SIZE_USDT
                self._cached_order_size = fallback_size
                self.status["order_size"] = fallback_size
                return fallback_size
            finally:
                self._calculation_in_progress = False

    async def start(self, symbols: list):
        """Multi-coin EMA Cross Scalping bot başlatma - Performance Optimized"""
        if self.status["is_running"]:
            print("⚠️ EMA Cross Scalping bot zaten çalışıyor.")
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
            "status_message": f"🎯 EMA Cross Scalping: {len(symbols)} coin için başlatılıyor...",
            "dynamic_sizing": True,
            "position_monitor_active": False,
            "last_signals": {symbol: "HOLD" for symbol in symbols},
            "signal_filters_active": True,
            "filtered_signals_count": 0,
            "ema_cross_signals_count": 0
        })
        print(f"🚀 EMA CROSS SCALPING Multi-coin bot başlatılıyor: {', '.join(symbols)}")
        
        try:
            # 1. Binance bağlantısı
            print("1️⃣ Binance futures bağlantısı kuruluyor...")
            try:
                await binance_client.initialize()
                print("✅ Binance futures bağlantısı başarılı")
            except Exception as binance_error:
                print(f"❌ Binance bağlantı hatası: {binance_error}")
                raise binance_error
            
            # 2. Tüm symboller için yetim emir temizliği
            print("2️⃣ 🧹 Tüm symboller için yetim emir temizliği...")
            for symbol in symbols:
                try:
                    cleanup_result = await binance_client.cancel_all_orders_safe(symbol)
                    await asyncio.sleep(0.2)
                except Exception as cleanup_error:
                    print(f"⚠️ {symbol} temizlik hatası: {cleanup_error} - devam ediliyor")
            
            # 3. Hesap bakiyesi kontrolü
            print("3️⃣ Hesap bakiyesi ve kaldıraç kontrolü...")
            try:
                self.status["account_balance"] = await binance_client.get_account_balance(use_cache=False)
                initial_order_size = await self._calculate_dynamic_order_size()
                print(f"✅ Hesap bakiyesi: {self.status['account_balance']:.2f} USDT")
                print(f"✅ EMA Cross Scalping pozisyon boyutu: {initial_order_size:.2f} USDT")
                print(f"✅ Kaldıraçlı işlem gücü: {initial_order_size * settings.LEVERAGE:.2f} USDT")
            except Exception as balance_error:
                print(f"❌ Bakiye kontrol hatası: {balance_error}")
                raise balance_error
            
            # 4. Tüm symboller için bilgi alma ve EMA Cross Scalping hazırlık
            print(f"4️⃣ {len(symbols)} symbol için EMA Cross Scalping analizi hazırlığı...")
            for symbol in symbols:
                try:
                    symbol_info = await binance_client.get_symbol_info(symbol)
                    if not symbol_info:
                        print(f"❌ {symbol} için borsa bilgileri alınamadı. Atlanıyor...")
                        continue
                    
                    # Precision hesaplama
                    self.quantity_precision[symbol] = self._get_precision_from_filter(symbol_info, 'LOT_SIZE', 'stepSize')
                    self.price_precision[symbol] = self._get_precision_from_filter(symbol_info, 'PRICE_FILTER', 'tickSize')
                    
                    # EMA Cross Scalping için geçmiş veri çek
                    required_candles = max(settings.EMA_TREND_PERIOD + 20, 70)  # EMA50 için 70 mum
                    klines = await binance_client.get_historical_klines(symbol, settings.TIMEFRAME, limit=required_candles)
                    if klines and len(klines) >= required_candles - 10:
                        self.multi_klines[symbol] = klines
                        print(f"✅ {symbol} hazır ({len(klines)} mum)")
                        
                        # İlk EMA Cross analizi test et
                        test_signal = trading_strategy.analyze_klines(klines, symbol)
                    else:
                        print(f"❌ {symbol} yetersiz veri. Atlanıyor...")
                        continue
                        
                    await asyncio.sleep(0.2)  # Rate limit koruması
                    
                except Exception as symbol_error:
                    print(f"❌ {symbol} hazırlık hatası: {symbol_error} - Atlanıyor...")
                    continue
            
            # 5. Mevcut açık pozisyon kontrolü
            print("5️⃣ Mevcut açık pozisyonlar kontrol ediliyor...")
            try:
                await binance_client._rate_limit_delay()
                all_positions = await binance_client.client.futures_position_information()
                open_positions = [p for p in all_positions if float(p['positionAmt']) != 0]
                
                if open_positions:
                    # İlk bulunan açık pozisyonu aktif yap
                    active_position = open_positions[0]
                    active_symbol = active_position['symbol']
                    position_amt = float(active_position['positionAmt'])
                    
                    if position_amt > 0:
                        self.status["position_side"] = "LONG"
                    elif position_amt < 0:
                        self.status["position_side"] = "SHORT"
                        
                    self.status["active_symbol"] = active_symbol
                    print(f"⚠️ Mevcut {self.status['position_side']} pozisyonu tespit edildi: {active_symbol}")
                    
                    # Mevcut pozisyon için TP/SL kontrol et
                    print(f"🛡️ {active_symbol} mevcut pozisyon için TP/SL kontrolü...")
                    await position_manager.manual_scan_symbol(active_symbol)
                else:
                    print("✅ Açık pozisyon bulunamadı")
                    # Tüm symboller için kaldıraç ayarlama
                    print("6️⃣ Tüm symboller için kaldıraç ayarlanıyor...")
                    for symbol in symbols:
                        if symbol in self.multi_klines:  # Sadece başarılı symboller için
                            if await binance_client.set_leverage(symbol, settings.LEVERAGE):
                                print(f"✅ {symbol} kaldıracı {settings.LEVERAGE}x")
                            await asyncio.sleep(0.3)
                            
            except Exception as position_error:
                print(f"❌ Pozisyon kontrolü hatası: {position_error}")
                raise position_error
                
            # 7. Pozisyon Monitoring Başlat
            print("7️⃣ 🛡️ Otomatik TP/SL monitoring başlatılıyor...")
            try:
                asyncio.create_task(position_manager.start_monitoring())
                self.status["position_monitor_active"] = True
                print("✅ Otomatik TP/SL koruması aktif")
            except Exception as monitor_error:
                print(f"⚠️ Position monitoring başlatılamadı: {monitor_error}")
                
            # 8. Multi-WebSocket bağlantıları başlat
            print("8️⃣ 🌐 EMA Cross Scalping Multi-coin WebSocket kuruluyor...")
            valid_symbols = [s for s in symbols if s in self.multi_klines]
            self.status["symbols"] = valid_symbols
            
            if not valid_symbols:
                raise Exception("Hiç geçerli symbol bulunamadı!")
                
            self.status["status_message"] = f"🎯 EMA CROSS SCALPING: {len(valid_symbols)} coin izleniyor ({settings.TIMEFRAME}) [⚡ PERFORMANCE OPTIMIZED + TRIPLE CONFIRMATION + OTOMATIK TP/SL]"
            print(f"✅ {self.status['status_message']}")
            
            await self._start_multi_websocket_loop(valid_symbols)
                        
        except Exception as e:
            error_msg = f"❌ EMA Cross Scalping bot başlatılırken beklenmeyen hata: {e}"
            print(error_msg)
            print(f"❌ Full traceback: {traceback.format_exc()}")
            self.status["status_message"] = error_msg
        
        print("🛑 EMA Cross Scalping bot durduruluyor...")
        await self.stop()

    async def _start_multi_websocket_loop(self, symbols: list):
        """Multi-coin WebSocket bağlantı döngüsü"""
        print(f"🌐 {len(symbols)} symbol için EMA Cross Scalping WebSocket başlatılıyor...")
        
        # Her symbol için ayrı WebSocket task oluştur
        self._websocket_tasks = []
        for symbol in symbols:
            task = asyncio.create_task(self._single_websocket_loop(symbol))
            self._websocket_tasks.append(task)
        
        # Tüm WebSocket task'larını bekle
        try:
            await asyncio.gather(*self._websocket_tasks)
        except Exception as e:
            print(f"❌ Multi-WebSocket hatası: {e}")

    async def _single_websocket_loop(self, symbol: str):
        """Tek symbol için WebSocket döngüsü"""
        ws_url = f"{settings.WEBSOCKET_URL}/ws/{symbol.lower()}@kline_{settings.TIMEFRAME}"
        reconnect_attempts = 0
        
        print(f"🔗 {symbol} EMA Cross WebSocket başlatılıyor...")
        
        while not self._stop_requested and reconnect_attempts < self._max_reconnect_attempts:
            try:
                async with websockets.connect(
                    ws_url, 
                    ping_interval=settings.WEBSOCKET_PING_INTERVAL, 
                    ping_timeout=settings.WEBSOCKET_PING_TIMEOUT,
                    close_timeout=settings.WEBSOCKET_CLOSE_TIMEOUT
                ) as ws:
                    print(f"✅ {symbol} EMA Cross WebSocket bağlandı")
                    reconnect_attempts = 0
                    self._websocket_connections[symbol] = ws
                    
                    while not self._stop_requested:
                        try:
                            message = await asyncio.wait_for(ws.recv(), timeout=65.0)
                            await self._handle_single_websocket_message(symbol, message)
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
                if symbol in self._websocket_connections:
                    del self._websocket_connections[symbol]
        
        if reconnect_attempts >= self._max_reconnect_attempts:
            print(f"❌ {symbol} WebSocket maksimum deneme aşıldı")

    async def _handle_single_websocket_message(self, symbol: str, message: str):
        """✅ OPTIMIZE: WebSocket mesaj işleme - Performance optimized"""
        try:
            data = json.loads(message)
            kline_data = data.get('k', {})
            
            # Daha az sıklıkla status update
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
            
            # Memory optimization - max klines sınırı
            max_klines = getattr(settings, 'MAX_KLINES_PER_SYMBOL', 150)
            if len(self.multi_klines[symbol]) >= max_klines:
                self.multi_klines[symbol].pop(0)
                
            # Yeni kline verisini ekle
            new_kline = [
                int(kline_data['t']),      # open_time
                float(kline_data['o']),    # open
                float(kline_data['h']),    # high
                float(kline_data['l']),    # low
                float(kline_data['c']),    # close
                float(kline_data['v']),    # volume
                int(kline_data['T']),      # close_time
                float(kline_data['q']),    # quote_asset_volume
                int(kline_data['n']),      # number_of_trades
                float(kline_data['V']),    # taker_buy_base_asset_volume
                float(kline_data['Q']),    # taker_buy_quote_asset_volume
                '0'                        # ignore
            ]
            
            self.multi_klines[symbol].append(new_kline)
            
            # Minimum veri kontrolü
            min_required = max(settings.EMA_TREND_PERIOD + 10, 60)  # EMA50 için 60 mum
            if len(self.multi_klines[symbol]) < min_required:
                return
            
            # Signal throttling kontrolü
            if not self._can_generate_signal(symbol):
                return
            
            # EMA Cross Scalping analizi
            signal = trading_strategy.analyze_klines(self.multi_klines[symbol], symbol)
            
            # Önceki sinyal ile karşılaştır
            previous_signal = self.status["last_signals"].get(symbol, "HOLD")
            
            # Sadece sinyal değişikliğinde işlem yap
            if signal != previous_signal:
                if signal == "HOLD":
                    self.status["filtered_signals_count"] += 1
                    if self._debug_enabled:
                        print(f"🛡️ {symbol} filtrelendi - toplam: {self.status['filtered_signals_count']}")
                else:
                    self.status["ema_cross_signals_count"] += 1
                    self._record_signal(symbol)
                    print(f"🚨 {symbol} YENİ EMA CROSS: {previous_signal} -> {signal}")
                    
                self.status["last_signals"][symbol] = signal
                
                # Pozisyon mantığı
                await self._handle_multi_coin_position_logic(symbol, signal)
                
        except Exception as e:
            print(f"❌ {symbol} WebSocket hatası: {e}")

    def _can_generate_signal(self, symbol: str) -> bool:
        """Signal throttling kontrolü"""
        if not getattr(settings, 'SIGNAL_THROTTLE', True):
            return True
            
        current_time = time.time()
        max_signals = getattr(settings, 'MAX_SIGNALS_PER_MINUTE', 6)
        
        # Bu symbol için son 1 dakikadaki sinyal sayısını kontrol et
        if symbol not in self._signal_count_per_minute:
            self._signal_count_per_minute[symbol] = []
        
        # 1 dakikadan eski sinyalleri temizle
        minute_ago = current_time - 60
        self._signal_count_per_minute[symbol] = [
            t for t in self._signal_count_per_minute[symbol] 
            if t > minute_ago
        ]
        
        return len(self._signal_count_per_minute[symbol]) < max_signals
    
    def _record_signal(self, symbol: str):
        """Sinyal kaydı"""
        current_time = time.time()
        if symbol not in self._signal_count_per_minute:
            self._signal_count_per_minute[symbol] = []
        self._signal_count_per_minute[symbol].append(current_time)

    async def _handle_multi_coin_position_logic(self, signal_symbol: str, signal: str):
        """Multi-coin pozisyon yönetim mantığı - EMA Cross Scalping optimize"""
        try:
            # Mevcut durum kontrolü
            current_active_symbol = self.status.get("active_symbol")
            current_position_side = self.status.get("position_side")
            
            # DURUM 1: Hiç pozisyon yok, yeni EMA Cross sinyali geldi
            if not current_active_symbol and not current_position_side and signal != "HOLD":
                print(f"🚀 Yeni EMA Cross fırsatı: {signal_symbol} -> {signal}")
                await self._open_new_position(signal_symbol, signal)
                return
            
            # DURUM 2: Mevcut pozisyon var, aynı symbol'den ters EMA Cross sinyali geldi
            if (current_active_symbol == signal_symbol and 
                current_position_side and 
                signal != "HOLD" and 
                signal != current_position_side):
                print(f"🔄 {signal_symbol} EMA Cross ters sinyali: {current_position_side} -> {signal}")
                await self._flip_position(signal_symbol, signal)
                return
            
            # DURUM 3: Mevcut pozisyon var, başka symbol'den EMA Cross sinyali geldi
            if (current_active_symbol and 
                current_active_symbol != signal_symbol and 
                current_position_side and 
                signal != "HOLD"):
                print(f"💡 Yeni EMA Cross coin fırsatı: {signal_symbol} -> {signal}")
                await self._switch_to_new_coin(current_active_symbol, signal_symbol, signal)
                return
            
            # DURUM 4: Pozisyon kapanmış mı kontrol et (SL/TP)
            if current_active_symbol and current_position_side:
                open_positions = await binance_client.get_open_positions(current_active_symbol, use_cache=True)
                if not open_positions:
                    print(f"✅ {current_active_symbol} pozisyonu SL/TP ile kapandı")
                    pnl = await binance_client.get_last_trade_pnl(current_active_symbol)
                    
                    # Trade sonucunu kaydet
                    if pnl > 0:
                        self.status["successful_trades"] += 1
                        print(f"🎉 KAZANÇ: {pnl:.2f} USDT - Toplam başarılı: {self.status['successful_trades']}")
                    else:
                        self.status["failed_trades"] += 1
                        print(f"📉 ZARAR: {pnl:.2f} USDT - Toplam başarısız: {self.status['failed_trades']}")
                    
                    firebase_manager.log_trade({
                        "symbol": current_active_symbol, 
                        "strategy": "ema_cross_scalping",
                        "pnl": pnl, 
                        "status": "CLOSED_BY_SL_TP", 
                        "timestamp": datetime.now(timezone.utc)
                    })
                    
                    # Pozisyon kapandı, durumu temizle
                    self.status["active_symbol"] = None
                    self.status["position_side"] = None
                    
                    # Cache'i güncelle
                    self._cached_order_size = 0.0  # Yeni hesaplama için
                    
                    # Eğer bu mesajı gönderen symbol'de aktif EMA Cross sinyali varsa pozisyon aç
                    if signal != "HOLD":
                        print(f"🚀 Pozisyon kapandıktan sonra yeni EMA Cross fırsatı: {signal_symbol} -> {signal}")
                        await self._open_new_position(signal_symbol, signal)
                        
        except Exception as e:
            print(f"❌ EMA Cross multi-coin pozisyon mantığı hatası: {e}")

    async def _open_new_position(self, symbol: str, signal: str):
        """✅ OPTIMIZE: Yeni pozisyon açma - Performance optimized"""
        try:
            print(f"🎯 {symbol} -> {signal} EMA Cross pozisyonu açılıyor...")
            
            # Test modu kontrolü
            if hasattr(settings, 'TEST_MODE') and settings.TEST_MODE:
                print(f"🧪 TEST: {symbol} {signal} EMA Cross simüle edildi")
                self.status["active_symbol"] = symbol
                self.status["position_side"] = signal
                self.status["status_message"] = f"TEST EMA CROSS: {signal} @ {symbol}"
                return True
            
            # Rate limit delay
            if hasattr(settings, 'API_CALL_DELAY'):
                await asyncio.sleep(settings.API_CALL_DELAY)
            
            # Yetim emir temizliği
            await binance_client.cancel_all_orders_safe(symbol)
            await asyncio.sleep(0.2)
            
            # Dinamik order size - cache kullan
            dynamic_order_size = await self._calculate_dynamic_order_size()
            
            if dynamic_order_size < 15.0:
                print(f"❌ {symbol} pozisyon boyutu çok düşük: {dynamic_order_size}")
                return False
            
            # Fiyat al
            price = await binance_client.get_market_price(symbol)
            if not price:
                print(f"❌ {symbol} fiyat alınamadı")
                return False
                
            # Pozisyon detayları
            side = "BUY" if signal == "LONG" else "SELL"
            quantity = self._format_quantity(symbol, (dynamic_order_size * settings.LEVERAGE) / price)
            
            if quantity <= 0:
                print(f"❌ {symbol} miktar çok düşük: {quantity}")
                return False

            print(f"📊 {symbol} EMA Cross Pozisyon: {side} {quantity} @ {price:.6f}")
            print(f"💰 Tutar: {dynamic_order_size:.2f} USDT ({settings.LEVERAGE}x kaldıraç)")
            
            # Pozisyon aç
            order = await binance_client.create_market_order_with_sl_tp(
                symbol, side, quantity, price, self.price_precision.get(symbol, 2)
            )
            
            if order:
                self.status["active_symbol"] = symbol
                self.status["position_side"] = signal
                self.status["status_message"] = f"🎯 EMA CROSS {signal}: {symbol} @ {price:.6f} ({dynamic_order_size:.2f} USDT) 🛡️"
                
                print(f"✅ {symbol} {signal} EMA Cross pozisyonu açıldı!")
                
                # Cache temizle
                try:
                    if hasattr(binance_client, '_cached_positions'):
                        binance_client._cached_positions.clear()
                except:
                    pass
                    
                # Position manager'a bildir
                await asyncio.sleep(1)
                await position_manager.manual_scan_symbol(symbol)
                return True
            else:
                print(f"❌ {symbol} EMA Cross pozisyonu açılamadı")
                await binance_client.force_cleanup_orders(symbol)
                return False
                
        except Exception as e:
            print(f"❌ {symbol} EMA Cross pozisyon açma hatası: {e}")
            try:
                await binance_client.force_cleanup_orders(symbol)
            except:
                pass
            return False

    async def _flip_position(self, symbol: str, new_signal: str):
        """Aynı coin'de EMA Cross pozisyon çevirme"""
        try:
            print(f"🔄 EMA CROSS POZİSYON ÇEVİRME: {symbol} -> {new_signal}")
            
            # Pozisyon değişiminden önce yetim emir kontrolü
            await binance_client.cancel_all_orders_safe(symbol)
            await asyncio.sleep(0.2)
            
            # Mevcut pozisyonu kapat
            open_positions = await binance_client.get_open_positions(symbol, use_cache=False)
            if open_positions:
                position = open_positions[0]
                position_amt = float(position['positionAmt'])
                side_to_close = 'SELL' if position_amt > 0 else 'BUY'
                
                pnl = await binance_client.get_last_trade_pnl(symbol)
                firebase_manager.log_trade({
                    "symbol": symbol,
                    "strategy": "ema_cross_scalping", 
                    "pnl": pnl, 
                    "status": "CLOSED_BY_EMA_CROSS_FLIP", 
                    "timestamp": datetime.now(timezone.utc)
                })

                # Pozisyonu kapat
                close_result = await binance_client.close_position(symbol, position_amt, side_to_close)
                if not close_result:
                    print("❌ Pozisyon kapatma başarısız")
                    return
                    
                await asyncio.sleep(1)

            # Yeni EMA Cross pozisyonu aç
            success = await self._open_new_position(symbol, new_signal)
            if not success:
                self.status["active_symbol"] = None
                self.status["position_side"] = None
                
        except Exception as e:
            print(f"❌ {symbol} EMA Cross pozisyon çevirme hatası: {e}")
            try:
                await binance_client.force_cleanup_orders(symbol)
            except:
                pass
            self.status["active_symbol"] = None
            self.status["position_side"] = None

    async def _switch_to_new_coin(self, current_symbol: str, new_symbol: str, new_signal: str):
        """Farklı coin'e EMA Cross geçişi"""
        try:
            print(f"🔄 EMA CROSS COİN DEĞİŞİMİ: {current_symbol} -> {new_symbol} ({new_signal})")
            
            # Mevcut pozisyonu kapat
            open_positions = await binance_client.get_open_positions(current_symbol, use_cache=False)
            if open_positions:
                position = open_positions[0]
                position_amt = float(position['positionAmt'])
                side_to_close = 'SELL' if position_amt > 0 else 'BUY'
                
                pnl = await binance_client.get_last_trade_pnl(current_symbol)
                firebase_manager.log_trade({
                    "symbol": current_symbol, 
                    "strategy": "ema_cross_scalping",
                    "pnl": pnl, 
                    "status": "CLOSED_FOR_EMA_CROSS_COIN_SWITCH", 
                    "timestamp": datetime.now(timezone.utc)
                })

                # Mevcut pozisyonu kapat
                close_result = await binance_client.close_position(current_symbol, position_amt, side_to_close)
                if not close_result:
                    print(f"❌ {current_symbol} pozisyon kapatma başarısız")
                    return
                    
                await asyncio.sleep(1)

            # Yeni coin'de EMA Cross pozisyonu aç
            success = await self._open_new_position(new_symbol, new_signal)
            if not success:
                self.status["active_symbol"] = None
                self.status["position_side"] = None
                
        except Exception as e:
            print(f"❌ EMA Cross coin değişimi hatası: {e}")
            try:
                await binance_client.force_cleanup_orders(current_symbol)
                await binance_client.force_cleanup_orders(new_symbol)
            except:
                pass
            self.status["active_symbol"] = None
            self.status["position_side"] = None

    async def _update_status_info(self):
        """✅ OPTIMIZE: Durum bilgilerini günceller - Performance optimized"""
        try:
            if not self.status["is_running"]:
                return
                
            # Bakiye güncellemesi - cache kullan
            self.status["account_balance"] = await binance_client.get_account_balance(use_cache=True)
            
            # Aktif pozisyon PnL kontrolü
            if self.status["active_symbol"] and self.status["position_side"]:
                self.status["position_pnl"] = await binance_client.get_position_pnl(
                    self.status["active_symbol"], use_cache=True
                )
            else:
                self.status["position_pnl"] = 0.0
            
            # Order size sadece gerektiğinde güncelle
            current_time = time.time()
            if self._cached_order_size == 0 or current_time - self._last_balance_calculation > self._balance_calculation_interval:
                await self._calculate_dynamic_order_size()
            
            # Position monitor durumu
            monitor_status = position_manager.get_status()
            self.status["position_monitor_active"] = monitor_status["is_running"]
            
        except Exception as e:
            print(f"❌ Status güncelleme hatası: {e}")

    async def stop(self):
        """EMA Cross Scalping bot durdurma - Performance optimized"""
        self._stop_requested = True
        if self.status["is_running"]:
            print("🛑 EMA Cross Scalping multi-coin bot durduruluyor...")
            
            # WebSocket task'larını iptal et
            for task in self._websocket_tasks:
                if not task.done():
                    task.cancel()
            
            # WebSocket bağlantılarını kapat
            for symbol, ws in self._websocket_connections.items():
                try:
                    await ws.close()
                except:
                    pass
            self._websocket_connections.clear()
            
            # Position monitoring'i durdur
            if self.status.get("position_monitor_active"):
                await position_manager.stop_monitoring()
                self.status["position_monitor_active"] = False
            
            # Final statistics
            total_signals = self.status["ema_cross_signals_count"]
            successful = self.status["successful_trades"]
            failed = self.status["failed_trades"]
            if total_signals > 0:
                success_rate = (successful / (successful + failed) * 100) if (successful + failed) > 0 else 0
                print(f"📊 EMA CROSS SCALPING İSTATİSTİKLERİ:")
                print(f"   🎯 Toplam sinyal: {total_signals}")
                print(f"   ✅ Başarılı: {successful}")
                print(f"   ❌ Başarısız: {failed}")
                print(f"   📈 Başarı oranı: %{success_rate:.1f}")
            
            self.status.update({
                "is_running": False, 
                "symbols": [],
                "active_symbol": None,
                "status_message": "EMA Cross Scalping bot durduruldu.",
                "account_balance": 0.0,
                "position_pnl": 0.0,
                "order_size": 0.0,
                "position_monitor_active": False,
                "last_signals": {},
                "signal_filters_active": False,
                "filtered_signals_count": 0,
                "ema_cross_signals_count": 0
            })
            print(f"✅ {self.status['status_message']}")
            await binance_client.close()

    def _format_quantity(self, symbol: str, quantity: float):
        precision = self.quantity_precision.get(symbol, 0)
        if precision == 0:
            return math.floor(quantity)
        factor = 10 ** precision
        return math.floor(quantity * factor) / factor

    # MEVCUT METODLAR - GERİYE UYUMLULUK İÇİN KORUNDU
    async def add_symbol(self, symbol: str):
        """Çalışan bot'a yeni symbol ekle"""
        if not self.status["is_running"]:
            return {"success": False, "message": "EMA Cross bot çalışmıyor"}
            
        if symbol in self.status["symbols"]:
            return {"success": False, "message": f"{symbol} zaten izleniyor"}
            
        try:
            # Symbol bilgilerini al ve hazırla
            symbol_info = await binance_client.get_symbol_info(symbol)
            if not symbol_info:
                return {"success": False, "message": f"{symbol} için borsa bilgileri alınamadı"}
            
            # Precision hesaplama
            self.quantity_precision[symbol] = self._get_precision_from_filter(symbol_info, 'LOT_SIZE', 'stepSize')
            self.price_precision[symbol] = self._get_precision_from_filter(symbol_info, 'PRICE_FILTER', 'tickSize')
            
            # EMA Cross Scalping için geçmiş veri çekme
            required_candles = max(settings.EMA_TREND_PERIOD + 20, 70)  # EMA50 için 70 mum
            klines = await binance_client.get_historical_klines(symbol, settings.TIMEFRAME, limit=required_candles)
            if not klines or len(klines) < required_candles - 10:
                return {"success": False, "message": f"{symbol} için yetersiz EMA Cross Scalping verisi"}
            
            self.multi_klines[symbol] = klines
            
            # Kaldıraç ayarla
            await binance_client.set_leverage(symbol, settings.LEVERAGE)
            
            # Symbol listesine ekle
            self.status["symbols"].append(symbol)
            self.status["last_signals"][symbol] = "HOLD"
            
            # Yeni WebSocket bağlantısı başlat
            task = asyncio.create_task(self._single_websocket_loop(symbol))
            self._websocket_tasks.append(task)
            
            print(f"✅ {symbol} EMA Cross bot'a eklendi")
            return {"success": True, "message": f"{symbol} EMA Cross Scalping bot'a başarıyla eklendi"}
            
        except Exception as e:
            return {"success": False, "message": f"{symbol} eklenirken hata: {e}"}

    async def remove_symbol(self, symbol: str):
        """Çalışan bot'tan symbol çıkar"""
        if not self.status["is_running"]:
            return {"success": False, "message": "EMA Cross bot çalışmıyor"}
            
        if symbol not in self.status["symbols"]:
            return {"success": False, "message": f"{symbol} zaten izlenmiyor"}
            
        if self.status["active_symbol"] == symbol:
            return {"success": False, "message": f"{symbol} şu anda aktif EMA Cross pozisyonunda"}
            
        try:
            # Symbol'ü listeden çıkar
            self.status["symbols"].remove(symbol)
            if symbol in self.status["last_signals"]:
                del self.status["last_signals"][symbol]
            if symbol in self.multi_klines:
                del self.multi_klines[symbol]
            if symbol in self.quantity_precision:
                del self.quantity_precision[symbol]
            if symbol in self.price_precision:
                del self.price_precision[symbol]
            
            # WebSocket bağlantısını kapat
            if symbol in self._websocket_connections:
                try:
                    await self._websocket_connections[symbol].close()
                except:
                    pass
                del self._websocket_connections[symbol]
            
            print(f"✅ {symbol} EMA Cross bot'tan çıkarıldı")
            return {"success": True, "message": f"{symbol} EMA Cross bot'tan başarıyla çıkarıldı"}
            
        except Exception as e:
            return {"success": False, "message": f"{symbol} çıkarılırken hata: {e}"}

    def get_multi_status(self):
        """🎯 EMA Cross Scalping multi-coin bot durumunu döndür - Performance optimized"""
        win_rate = 0
        total_trades = self.status["successful_trades"] + self.status["failed_trades"]
        if total_trades > 0:
            win_rate = (self.status["successful_trades"] / total_trades) * 100
        
        return {
            "is_running": self.status["is_running"],
            "strategy": "ema_cross_scalping",
            "symbols": self.status["symbols"],
            "active_symbol": self.status["active_symbol"],
            "position_side": self.status["position_side"],
            "status_message": self.status["status_message"],
            "account_balance": self.status["account_balance"],
            "position_pnl": self.status["position_pnl"],
            "order_size": self.status["order_size"],
            "last_signals": self.status["last_signals"],
            "position_monitor_active": self.status["position_monitor_active"],
            "websocket_connections": len(self._websocket_connections),
            "position_manager": position_manager.get_status(),
            "signal_filters_active": self.status["signal_filters_active"],
            "filtered_signals_count": self.status["filtered_signals_count"],
            "ema_cross_signals_count": self.status["ema_cross_signals_count"],
            "successful_trades": self.status["successful_trades"],
            "failed_trades": self.status["failed_trades"],
            "win_rate": f"{win_rate:.1f}%",
            "ema_cross_config": {
                "fast_ema": settings.EMA_FAST_PERIOD,
                "slow_ema": settings.EMA_SLOW_PERIOD,
                "trend_ema": settings.EMA_TREND_PERIOD,
                "rsi_period": settings.RSI_PERIOD,
                "volume_period": settings.VOLUME_PERIOD,
                "timeframe": settings.TIMEFRAME,
                "leverage": settings.LEVERAGE,
                "stop_loss": f"{settings.STOP_LOSS_PERCENT*100:.1f}%",
                "take_profit": f"{settings.TAKE_PROFIT_PERCENT*100:.1f}%"
            },
            "performance": {
                "cache_hit_rate": f"{((time.time() - self._last_balance_calculation) / self._balance_calculation_interval * 100):.1f}%",
                "cached_order_size": self._cached_order_size,
                "calculation_in_progress": self._calculation_in_progress
            }
        }

    # Diğer mevcut metodlar aynı kalabilir...
    async def scan_all_positions(self):
        """Tüm açık pozisyonları manuel tarayıp TP/SL ekle"""
        if not self.status["is_running"]:
            return {"success": False, "message": "EMA Cross bot çalışmıyor"}
            
        try:
            await position_manager._scan_and_protect_positions()
            return {
                "success": True, 
                "message": "Tüm pozisyonlar tarandı ve gerekli TP/SL eklendi",
                "monitor_status": position_manager.get_status()
            }
        except Exception as e:
            return {"success": False, "message": f"Tarama hatası: {e}"}
    
    async def scan_specific_symbol(self, symbol: str):
        """Belirli bir coin için manuel TP/SL kontrolü"""
        try:
            success = await position_manager.manual_scan_symbol(symbol)
            return {
                "success": success,
                "symbol": symbol,
                "message": f"{symbol} için TP/SL kontrolü tamamlandı"
            }
        except Exception as e:
            return {"success": False, "message": f"{symbol} kontrolü hatası: {e}"}

bot_core = BotCore()
