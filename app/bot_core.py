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

class BotCore:
    def __init__(self):
        self.status = {
            "is_running": False, 
            "symbols": [],  # Multi-coin support
            "active_symbol": None,  # Şu anda pozisyonu olan symbol
            "position_side": None, 
            "status_message": "Bollinger Bands Bot başlatılmadı.",
            "account_balance": 0.0,
            "position_pnl": 0.0,
            "order_size": 0.0,
            "dynamic_sizing": True,
            "position_monitor_active": False,
            "last_signals": {},  # Her coin için son sinyal
            "signal_filters_active": True,
            "filtered_signals_count": 0,
            "bollinger_signals_count": 0,  # Bollinger sinyalleri için
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
        self._debug_enabled = settings.DEBUG_MODE
        print("🎯 BOLLINGER BANDS TRADING BOT v3.1 başlatıldı")
        print(f"📊 Strateji: BB Period={settings.BOLLINGER_PERIOD}, StdDev={settings.BOLLINGER_STD_DEV}")
        print(f"💰 Risk/Reward: SL=%{settings.STOP_LOSS_PERCENT*100:.1f} / TP=%{settings.TAKE_PROFIT_PERCENT*100:.1f}")

    def _get_precision_from_filter(self, symbol_info, filter_type, key):
        for f in symbol_info['filters']:
            if f['filterType'] == filter_type:
                size_str = f[key]
                if '.' in size_str:
                    return len(size_str.split('.')[1].rstrip('0'))
                return 0
        return 0

    async def _calculate_dynamic_order_size(self):
        """Dinamik pozisyon boyutu hesapla - bakiyenin %90'ı"""
        try:
            current_balance = await binance_client.get_account_balance(use_cache=False)
            dynamic_size = current_balance * 0.9
            
            min_size = 10.0  # Bollinger Bands için minimum arttırıldı
            max_size = 2000.0  # Maksimum arttırıldı
            
            final_size = max(min(dynamic_size, max_size), min_size)
            
            if self._debug_enabled:
                print(f"💰 BOLLINGER BANDS Dinamik pozisyon hesaplama:")
                print(f"   Mevcut bakiye: {current_balance:.2f} USDT")
                print(f"   %90'ı: {dynamic_size:.2f} USDT")
                print(f"   Kullanılacak tutar: {final_size:.2f} USDT")
                print(f"   Kaldıraçlı pozisyon: {final_size * settings.LEVERAGE:.2f} USDT")
            
            self.status["order_size"] = final_size
            return final_size
            
        except Exception as e:
            print(f"❌ Dinamik pozisyon hesaplama hatası: {e}")
            fallback_size = settings.ORDER_SIZE_USDT
            self.status["order_size"] = fallback_size
            return fallback_size

    async def start(self, symbols: list):
        """Multi-coin Bollinger Bands bot başlatma"""
        if self.status["is_running"]:
            print("⚠️ Bollinger Bands bot zaten çalışıyor.")
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
            "status_message": f"🎯 Bollinger Bands: {len(symbols)} coin için başlatılıyor...",
            "dynamic_sizing": True,
            "position_monitor_active": False,
            "last_signals": {symbol: "HOLD" for symbol in symbols},
            "signal_filters_active": True,
            "filtered_signals_count": 0,
            "bollinger_signals_count": 0
        })
        print(f"🚀 BOLLINGER BANDS Multi-coin bot başlatılıyor: {', '.join(symbols)}")
        
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
                    if cleanup_result:
                        print(f"✅ {symbol} yetim emir temizliği başarılı")
                    else:
                        print(f"⚠️ {symbol} yetim emir temizliği eksik - devam ediliyor")
                    await asyncio.sleep(0.2)
                except Exception as cleanup_error:
                    print(f"⚠️ {symbol} temizlik hatası: {cleanup_error} - devam ediliyor")
            
            # 3. Hesap bakiyesi kontrolü
            print("3️⃣ Hesap bakiyesi ve kaldıraç kontrolü...")
            try:
                self.status["account_balance"] = await binance_client.get_account_balance(use_cache=False)
                initial_order_size = await self._calculate_dynamic_order_size()
                print(f"✅ Hesap bakiyesi: {self.status['account_balance']:.2f} USDT")
                print(f"✅ Bollinger Bands pozisyon boyutu: {initial_order_size:.2f} USDT")
                print(f"✅ Kaldıraçlı işlem gücü: {initial_order_size * settings.LEVERAGE:.2f} USDT")
            except Exception as balance_error:
                print(f"❌ Bakiye kontrol hatası: {balance_error}")
                raise balance_error
            
            # 4. Tüm symboller için bilgi alma ve Bollinger Bands hazırlık
            print(f"4️⃣ {len(symbols)} symbol için Bollinger Bands analizi hazırlığı...")
            for symbol in symbols:
                try:
                    symbol_info = await binance_client.get_symbol_info(symbol)
                    if not symbol_info:
                        print(f"❌ {symbol} için borsa bilgileri alınamadı. Atlanıyor...")
                        continue
                    
                    # Precision hesaplama
                    self.quantity_precision[symbol] = self._get_precision_from_filter(symbol_info, 'LOT_SIZE', 'stepSize')
                    self.price_precision[symbol] = self._get_precision_from_filter(symbol_info, 'PRICE_FILTER', 'tickSize')
                    print(f"✅ {symbol} precision: Miktar={self.quantity_precision[symbol]}, Fiyat={self.price_precision[symbol]}")
                    
                    # Bollinger Bands için yeterli geçmiş veri çek
                    required_candles = max(settings.BOLLINGER_PERIOD + 20, 60)  # En az 60 mum
                    klines = await binance_client.get_historical_klines(symbol, settings.TIMEFRAME, limit=required_candles)
                    if klines and len(klines) >= required_candles - 10:
                        self.multi_klines[symbol] = klines
                        print(f"✅ {symbol} için {len(klines)} geçmiş mum verisi alındı")
                        
                        # İlk Bollinger Bands analizi test et
                        test_signal = trading_strategy.analyze_klines(klines, symbol)
                        print(f"🧪 {symbol} ilk Bollinger analizi: {test_signal}")
                    else:
                        print(f"❌ {symbol} için yetersiz geçmiş veri ({len(klines) if klines else 0}/{required_candles}). Atlanıyor...")
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
                    print("Bollinger Bands stratejisi mevcut pozisyonla devam ediyor...")
                    
                    # Mevcut pozisyon için yetim emirleri temizle ve TP/SL kontrol et
                    print(f"🧹 {active_symbol} mevcut pozisyon için ekstra yetim emir temizliği...")
                    await binance_client.cancel_all_orders_safe(active_symbol)
                    
                    print(f"🛡️ {active_symbol} mevcut pozisyon için TP/SL kontrolü...")
                    await position_manager.manual_scan_symbol(active_symbol)
                else:
                    print("✅ Açık pozisyon bulunamadı")
                    # Tüm symboller için kaldıraç ayarlama
                    print("6️⃣ Tüm symboller için kaldıraç ayarlanıyor...")
                    for symbol in symbols:
                        if symbol in self.multi_klines:  # Sadece başarılı symboller için
                            if await binance_client.set_leverage(symbol, settings.LEVERAGE):
                                print(f"✅ {symbol} kaldıracı {settings.LEVERAGE}x olarak ayarlandı")
                            else:
                                print(f"⚠️ {symbol} kaldıracı ayarlanamadı, mevcut kaldıraçla devam ediliyor")
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
            print("8️⃣ 🌐 Bollinger Bands Multi-coin WebSocket bağlantıları kuruluyor...")
            valid_symbols = [s for s in symbols if s in self.multi_klines]
            self.status["symbols"] = valid_symbols
            
            if not valid_symbols:
                raise Exception("Hiç geçerli symbol bulunamadı!")
                
            self.status["status_message"] = f"🎯 BOLLINGER BANDS: {len(valid_symbols)} coin izleniyor ({settings.TIMEFRAME}) [SL:%{settings.STOP_LOSS_PERCENT*100:.1f} TP:%{settings.TAKE_PROFIT_PERCENT*100:.1f} | ULTRA ESNEK FİLTRELER + DİNAMİK SİZING + OTOMATIK TP/SL]"
            print(f"✅ {self.status['status_message']}")
            
            await self._start_multi_websocket_loop(valid_symbols)
                        
        except Exception as e:
            error_msg = f"❌ Bollinger Bands bot başlatılırken beklenmeyen hata: {e}"
            print(error_msg)
            print(f"❌ Full traceback: {traceback.format_exc()}")
            self.status["status_message"] = error_msg
        
        print("🛑 Bollinger Bands bot durduruluyor...")
        await self.stop()

    async def _start_multi_websocket_loop(self, symbols: list):
        """Multi-coin WebSocket bağlantı döngüsü"""
        print(f"🌐 {len(symbols)} symbol için Bollinger Bands WebSocket başlatılıyor...")
        
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
        
        print(f"🔗 {symbol} Bollinger WebSocket bağlantısı başlatılıyor...")
        
        while not self._stop_requested and reconnect_attempts < self._max_reconnect_attempts:
            try:
                async with websockets.connect(
                    ws_url, 
                    ping_interval=30, 
                    ping_timeout=15,
                    close_timeout=10
                ) as ws:
                    print(f"✅ {symbol} Bollinger WebSocket bağlantısı kuruldu")
                    reconnect_attempts = 0
                    self._websocket_connections[symbol] = ws
                    
                    while not self._stop_requested:
                        try:
                            message = await asyncio.wait_for(ws.recv(), timeout=65.0)
                            await self._handle_single_websocket_message(symbol, message)
                        except asyncio.TimeoutError:
                            print(f"⏰ {symbol} WebSocket timeout - ping gönderiliyor...")
                            try:
                                await ws.ping()
                                await asyncio.sleep(1)
                            except:
                                print(f"❌ {symbol} WebSocket ping başarısız - yeniden bağlanılıyor...")
                                break
                        except websockets.exceptions.ConnectionClosed:
                            print(f"🔌 {symbol} WebSocket bağlantısı koptu...")
                            break
                        except Exception as e:
                            print(f"❌ {symbol} WebSocket mesaj işleme hatası: {e}")
                            await asyncio.sleep(1)
                            
            except Exception as e:
                if not self._stop_requested:
                    reconnect_attempts += 1
                    backoff_time = min(5 * reconnect_attempts, 30)
                    print(f"❌ {symbol} WebSocket bağlantı hatası (Deneme {reconnect_attempts}/{self._max_reconnect_attempts}): {e}")
                    if reconnect_attempts < self._max_reconnect_attempts:
                        print(f"⏳ {symbol} için {backoff_time} saniye sonra yeniden deneniyor...")
                        await asyncio.sleep(backoff_time)
            finally:
                if symbol in self._websocket_connections:
                    del self._websocket_connections[symbol]
        
        if reconnect_attempts >= self._max_reconnect_attempts:
            print(f"❌ {symbol} WebSocket maksimum yeniden bağlanma denemesi aşıldı")

    async def _handle_single_websocket_message(self, symbol: str, message: str):
        """🎯 BOLLINGER BANDS: Gelişmiş WebSocket mesaj işleme + Debug"""
        try:
            data = json.loads(message)
            kline_data = data.get('k', {})
            
            # Durum bilgilerini güncelle
            current_time = time.time()
            if current_time - self._last_status_update > 10:
                await self._update_status_info()
                self._last_status_update = current_time
            
            # Sadece kapanan mumları işle
            if not kline_data.get('x', False):
                return
                
            if self._debug_enabled:
                print(f"🕯️ {symbol} YENİ MUM KAPANDI ({settings.TIMEFRAME})")
                print(f"   📊 OHLCV: O:{kline_data['o']} H:{kline_data['h']} L:{kline_data['l']} C:{kline_data['c']} V:{kline_data['v']}")
            
            # Kline data güncelle
            if symbol not in self.multi_klines:
                self.multi_klines[symbol] = []
            
            # Eski veriyi sil (max 200 mum tut)
            if len(self.multi_klines[symbol]) >= 200:
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
            
            if self._debug_enabled:
                print(f"📊 {symbol} Toplam mum sayısı: {len(self.multi_klines[symbol])}")
            
            # Minimum veri kontrolü - Bollinger Bands için
            min_required = max(settings.BOLLINGER_PERIOD + 15, 40)
            if len(self.multi_klines[symbol]) < min_required:
                if self._debug_enabled:
                    print(f"⏳ {symbol} Bollinger Bands için henüz yeterli veri yok ({len(self.multi_klines[symbol])}/{min_required})")
                return
            
            # 🎯 BOLLINGER BANDS STRATEJİSİ ANALİZİ
            if self._debug_enabled:
                print(f"🔍 {symbol} BOLLINGER BANDS ANALİZİ BAŞLATIYOR...")
                print(f"    BB Period: {settings.BOLLINGER_PERIOD}")
                print(f"    Std Dev: {settings.BOLLINGER_STD_DEV}")
                print(f"    Entry Levels: Lower<{settings.BB_ENTRY_LOWER} Upper>{settings.BB_ENTRY_UPPER}")
            
            signal = trading_strategy.analyze_klines(self.multi_klines[symbol], symbol)
            
            # Önceki sinyal ile karşılaştır
            previous_signal = self.status["last_signals"].get(symbol, "HOLD")
            
            if self._debug_enabled:
                print(f"📊 {symbol} BOLLINGER SİNYAL RAPORU:")
                print(f"    Önceki: {previous_signal}")
                print(f"    Yeni: {signal}")
            
            if signal != previous_signal:
                if signal == "HOLD":
                    self.status["filtered_signals_count"] += 1
                    print(f"🛡️ {symbol} Bollinger sinyali filtrelendi - toplam filtrelenen: {self.status['filtered_signals_count']}")
                else:
                    self.status["bollinger_signals_count"] += 1
                    print(f"🚨 {symbol} YENİ BOLLINGER BANDS SİNYALİ: {previous_signal} -> {signal}")
                    print(f"🎯 Toplam Bollinger sinyalleri: {self.status['bollinger_signals_count']}")
                    print(f"🔄 {symbol} için pozisyon yönetimi kontrolü başlatılıyor...")
            else:
                if self._debug_enabled:
                    print(f"↔️ {symbol} sinyal değişikliği yok: {signal}")
            
            self.status["last_signals"][symbol] = signal
            
            # 🎯 POZİSYON YÖNETİM MANTITI
            if self._debug_enabled:
                print(f"🔄 {symbol} için Bollinger pozisyon mantığı kontrol ediliyor...")
            await self._handle_multi_coin_position_logic(symbol, signal)
                
        except Exception as e:
            print(f"❌ {symbol} Bollinger WebSocket mesaj işlenirken HATA: {e}")
            if self._debug_enabled:
                print(f"🔍 HATA DETAYI:\n{traceback.format_exc()}")

    async def _handle_multi_coin_position_logic(self, signal_symbol: str, signal: str):
        """Multi-coin pozisyon yönetim mantığı - Bollinger Bands optimize"""
        try:
            # Mevcut durum kontrolü
            current_active_symbol = self.status.get("active_symbol")
            current_position_side = self.status.get("position_side")
            
            if self._debug_enabled:
                print(f"🔍 Bollinger pozisyon mantığı: {signal_symbol} -> {signal}")
                print(f"    Mevcut aktif: {current_active_symbol}")
                print(f"    Mevcut pozisyon: {current_position_side}")
            
            # DURUM 1: Hiç pozisyon yok, yeni Bollinger sinyali geldi
            if not current_active_symbol and not current_position_side and signal != "HOLD":
                print(f"🚀 Yeni Bollinger fırsatı: {signal_symbol} -> {signal}")
                await self._open_new_position(signal_symbol, signal)
                return
            
            # DURUM 2: Mevcut pozisyon var, aynı symbol'den ters Bollinger sinyali geldi
            if (current_active_symbol == signal_symbol and 
                current_position_side and 
                signal != "HOLD" and 
                signal != current_position_side):
                print(f"🔄 {signal_symbol} Bollinger ters sinyali: {current_position_side} -> {signal}")
                await self._flip_position(signal_symbol, signal)
                return
            
            # DURUM 3: Mevcut pozisyon var, başka symbol'den Bollinger sinyali geldi
            if (current_active_symbol and 
                current_active_symbol != signal_symbol and 
                current_position_side and 
                signal != "HOLD"):
                print(f"💡 Yeni Bollinger coin fırsatı: {signal_symbol} -> {signal} (Mevcut: {current_active_symbol})")
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
                        "strategy": "bollinger_bands",
                        "pnl": pnl, 
                        "status": "CLOSED_BY_SL_TP", 
                        "timestamp": datetime.now(timezone.utc)
                    })
                    
                    # Pozisyon kapandı, durumu temizle
                    self.status["active_symbol"] = None
                    self.status["position_side"] = None
                    
                    # Pozisyon kapandıktan sonra yetim emir temizliği
                    print(f"🧹 {current_active_symbol} pozisyon kapandı - yetim emir temizliği...")
                    await binance_client.cancel_all_orders_safe(current_active_symbol)
                    
                    # Yeni bakiye ile order size güncelle
                    await self._calculate_dynamic_order_size()
                    
                    # Eğer bu mesajı gönderen symbol'de aktif Bollinger sinyali varsa hemen pozisyon aç
                    if signal != "HOLD":
                        print(f"🚀 Pozisyon kapandıktan sonra hemen yeni Bollinger fırsatı: {signal_symbol} -> {signal}")
                        await self._open_new_position(signal_symbol, signal)
                        
        except Exception as e:
            print(f"❌ Bollinger multi-coin pozisyon mantığı hatası: {e}")
            if self._debug_enabled:
                print(f"🔍 Detay: {traceback.format_exc()}")

    async def _open_new_position(self, symbol: str, signal: str):
        """BOLLINGER BANDS: Yeni pozisyon açma - Gelişmiş Debug"""
        try:
            print(f"=" * 70)
            print(f"🎯 {symbol} İÇİN YENİ BOLLINGER BANDS {signal} POZİSYONU AÇILIYOR...")
            print(f"=" * 70)
            
            # Test modu kontrolü
            if hasattr(settings, 'TEST_MODE') and settings.TEST_MODE:
                print(f"🧪 TEST MODU: {symbol} {signal} Bollinger pozisyonu simüle edildi")
                self.status["active_symbol"] = symbol
                self.status["position_side"] = signal
                self.status["status_message"] = f"TEST BOLLINGER: {signal} @ {symbol}"
                return True
            
            # Yetim emir temizliği
            print(f"🧹 ADIM 1: {symbol} pozisyon öncesi yetim emir temizliği...")
            await binance_client.cancel_all_orders_safe(symbol)
            await asyncio.sleep(0.3)
            
            # Dinamik order size hesapla
            print(f"💰 ADIM 2: Bollinger Bands dinamik pozisyon boyutu hesaplanıyor...")
            dynamic_order_size = await self._calculate_dynamic_order_size()
            
            if dynamic_order_size < 10.0:
                print(f"❌ {symbol} için hesaplanan pozisyon boyutu çok düşük: {dynamic_order_size}")
                return False
            
            # Fiyat al
            print(f"💱 ADIM 3: {symbol} market fiyatı alınıyor...")
            price = await binance_client.get_market_price(symbol)
            if not price:
                print(f"❌ {symbol} için fiyat alınamadı.")
                return False
                
            print(f"📊 BOLLINGER BANDS POZİSYON DETAYLARI:")
            print(f"   🎯 Strateji: BOLLINGER BANDS")
            print(f"   📈 BB Parameters: Period={settings.BOLLINGER_PERIOD}, StdDev={settings.BOLLINGER_STD_DEV}")
            print(f"   🔄 Sinyal: {signal}")
            print(f"   💰 Fiyat: {price}")
            print(f"   💵 Tutar: {dynamic_order_size} USDT")
            print(f"   ⚡ Kaldıraç: {settings.LEVERAGE}x")
            print(f"   🛑 Stop Loss: %{settings.STOP_LOSS_PERCENT*100:.1f}")
            print(f"   🎯 Take Profit: %{settings.TAKE_PROFIT_PERCENT*100:.1f}")
            
            # Miktar hesapla
            side = "BUY" if signal == "LONG" else "SELL"
            quantity = self._format_quantity(symbol, (dynamic_order_size * settings.LEVERAGE) / price)
            
            if quantity <= 0:
                print(f"❌ {symbol} için hesaplanan miktar çok düşük: {quantity}")
                return False

            print(f"   📊 Miktar: {quantity}")
            print(f"   ↗️ Yön: {side}")
            print(f"   💪 Toplam Pozisyon Değeri: {quantity * price:.2f} USDT")
            
            print(f"🎯 ADIM 4: {symbol} Bollinger piyasa emri + TP/SL koruması...")
            
            # Pozisyon aç (TP/SL ile birlikte)
            order = await binance_client.create_market_order_with_sl_tp(
                symbol, side, quantity, price, self.price_precision.get(symbol, 2)
            )
            
            if order:
                self.status["active_symbol"] = symbol
                self.status["position_side"] = signal
                self.status["status_message"] = f"🎯 BOLLINGER {signal}: {symbol} @ {price:.6f} ({dynamic_order_size:.2f} USDT) [SL:%{settings.STOP_LOSS_PERCENT*100:.1f} TP:%{settings.TAKE_PROFIT_PERCENT*100:.1f}] 🛡️"
                
                print(f"✅ BOLLINGER BANDS POZİSYON AÇILDI!")
                print(f"🎉 {symbol} {signal} pozisyonu başarıyla oluşturuldu!")
                print(f"💼 Yeni durum: {self.status['status_message']}")
                print(f"🔄 Risk/Reward Oranı: 1:{settings.TAKE_PROFIT_PERCENT/settings.STOP_LOSS_PERCENT:.1f}")
                print(f"=" * 70)
                
                # Cache temizle
                try:
                    if hasattr(binance_client, '_cached_positions'):
                        binance_client._cached_positions.clear()
                    if hasattr(binance_client, '_last_position_check'):
                        binance_client._last_position_check.clear()
                except Exception as cache_error:
                    print(f"⚠️ Cache temizleme hatası: {cache_error}")
                    
                # Position manager'a bildir
                await asyncio.sleep(2)
                print(f"🛡️ {symbol} Bollinger pozisyonu otomatik TP/SL sisteme bildiriliyor...")
                await position_manager.manual_scan_symbol(symbol)
                return True
            else:
                print(f"❌ {symbol} Bollinger pozisyonu açılamadı.")
                print(f"🧹 Acil yetim emir temizliği yapılıyor...")
                await binance_client.force_cleanup_orders(symbol)
                return False
                
        except Exception as e:
            print(f"❌ {symbol} Bollinger yeni pozisyon açma BEKLENMEYEN HATA: {e}")
            if self._debug_enabled:
                print(f"🔍 HATA DETAYI:\n{traceback.format_exc()}")
            try:
                await binance_client.force_cleanup_orders(symbol)
            except:
                pass
            return False

    async def _flip_position(self, symbol: str, new_signal: str):
        """Aynı coin'de Bollinger pozisyon çevirme"""
        try:
            print(f"🔄 BOLLINGER POZISYON ÇEVİRME: {symbol} -> {new_signal}")
            
            # Pozisyon değişiminden önce yetim emir kontrolü
            print(f"🧹 {symbol} pozisyon değişimi öncesi yetim emir temizliği...")
            await binance_client.cancel_all_orders_safe(symbol)
            await asyncio.sleep(0.2)
            
            # Mevcut pozisyonu kapat
            open_positions = await binance_client.get_open_positions(symbol, use_cache=False)
            if open_positions:
                position = open_positions[0]
                position_amt = float(position['positionAmt'])
                side_to_close = 'SELL' if position_amt > 0 else 'BUY'
                print(f"📉 Bollinger ters sinyal - Mevcut {self.status['position_side']} pozisyonu kapatılıyor...")
                
                pnl = await binance_client.get_last_trade_pnl(symbol)
                firebase_manager.log_trade({
                    "symbol": symbol,
                    "strategy": "bollinger_bands", 
                    "pnl": pnl, 
                    "status": "CLOSED_BY_BOLLINGER_FLIP", 
                    "timestamp": datetime.now(timezone.utc)
                })

                # Pozisyonu kapat
                close_result = await binance_client.close_position(symbol, position_amt, side_to_close)
                if not close_result:
                    print("❌ Pozisyon kapatma başarısız - yeni Bollinger pozisyonu açılmayacak")
                    return
                    
                await asyncio.sleep(1)

            # Yeni Bollinger pozisyonu aç
            success = await self._open_new_position(symbol, new_signal)
            if not success:
                self.status["active_symbol"] = None
                self.status["position_side"] = None
                
        except Exception as e:
            print(f"❌ {symbol} Bollinger pozisyon değiştirme hatası: {e}")
            try:
                await binance_client.force_cleanup_orders(symbol)
            except Exception as cleanup_error:
                print(f"⚠️ Acil temizlik de başarısız: {cleanup_error}")
            self.status["active_symbol"] = None
            self.status["position_side"] = None

    async def _switch_to_new_coin(self, current_symbol: str, new_symbol: str, new_signal: str):
        """Farklı coin'e Bollinger geçişi"""
        try:
            print(f"🔄 BOLLINGER COİN DEĞİŞİMİ: {current_symbol} -> {new_symbol} ({new_signal})")
            
            # Mevcut pozisyonu kapat
            open_positions = await binance_client.get_open_positions(current_symbol, use_cache=False)
            if open_positions:
                position = open_positions[0]
                position_amt = float(position['positionAmt'])
                side_to_close = 'SELL' if position_amt > 0 else 'BUY'
                
                print(f"📉 {current_symbol} pozisyonu kapatılıyor (Bollinger coin değişimi)...")
                
                pnl = await binance_client.get_last_trade_pnl(current_symbol)
                firebase_manager.log_trade({
                    "symbol": current_symbol, 
                    "strategy": "bollinger_bands",
                    "pnl": pnl, 
                    "status": "CLOSED_FOR_BOLLINGER_COIN_SWITCH", 
                    "timestamp": datetime.now(timezone.utc)
                })

                # Mevcut pozisyonu kapat
                close_result = await binance_client.close_position(current_symbol, position_amt, side_to_close)
                if not close_result:
                    print(f"❌ {current_symbol} pozisyon kapatma başarısız - Bollinger coin değişimi iptal")
                    return
                    
                await asyncio.sleep(1)

            # Yeni coin'de Bollinger pozisyonu aç
            success = await self._open_new_position(new_symbol, new_signal)
            if not success:
                print(f"❌ {new_symbol} yeni Bollinger pozisyonu açılamadı")
                self.status["active_symbol"] = None
                self.status["position_side"] = None
                
        except Exception as e:
            print(f"❌ Bollinger coin değişimi hatası: {e}")
            try:
                await binance_client.force_cleanup_orders(current_symbol)
                await binance_client.force_cleanup_orders(new_symbol)
            except Exception as cleanup_error:
                print(f"⚠️ Bollinger coin değişimi acil temizlik hatası: {cleanup_error}")
            self.status["active_symbol"] = None
            self.status["position_side"] = None

    async def _update_status_info(self):
        """Durum bilgilerini günceller - Bollinger Bands optimize"""
        try:
            if self.status["is_running"]:
                # Cache kullanarak sorgu sayısını azalt
                self.status["account_balance"] = await binance_client.get_account_balance(use_cache=True)
                if self.status["active_symbol"] and self.status["position_side"]:
                    self.status["position_pnl"] = await binance_client.get_position_pnl(
                        self.status["active_symbol"], use_cache=True
                    )
                else:
                    self.status["position_pnl"] = 0.0
                # Order size'ı dinamik tut
                await self._calculate_dynamic_order_size()
                
                # Position monitor durumunu güncelle
                monitor_status = position_manager.get_status()
                self.status["position_monitor_active"] = monitor_status["is_running"]
                
        except Exception as e:
            print(f"❌ Bollinger durum güncelleme hatası: {e}")

    async def stop(self):
        """Bollinger Bands bot durdurma"""
        self._stop_requested = True
        if self.status["is_running"]:
            print("🛑 Bollinger Bands multi-coin bot durduruluyor...")
            
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
                print("🛡️ Otomatik TP/SL monitoring durduruluyor...")
                await position_manager.stop_monitoring()
                self.status["position_monitor_active"] = False
            
            # Bot durdururken son temizlik
            if self.status.get("symbols"):
                print(f"🧹 Bollinger bot durduruluyor - tüm symboller için son yetim emir temizliği...")
                for symbol in self.status["symbols"]:
                    try:
                        await binance_client.cancel_all_orders_safe(symbol)
                        await asyncio.sleep(0.1)
                    except Exception as final_cleanup_error:
                        print(f"⚠️ {symbol} son temizlik hatası: {final_cleanup_error}")
            
            # Final statistics
            total_signals = self.status["bollinger_signals_count"]
            successful = self.status["successful_trades"]
            failed = self.status["failed_trades"]
            if total_signals > 0:
                success_rate = (successful / (successful + failed) * 100) if (successful + failed) > 0 else 0
                print(f"📊 BOLLINGER BANDS İSTATİSTİKLERİ:")
                print(f"   🎯 Toplam sinyal: {total_signals}")
                print(f"   ✅ Başarılı: {successful}")
                print(f"   ❌ Başarısız: {failed}")
                print(f"   📈 Başarı oranı: %{success_rate:.1f}")
            
            self.status.update({
                "is_running": False, 
                "symbols": [],
                "active_symbol": None,
                "status_message": "Bollinger Bands bot durduruldu.",
                "account_balance": 0.0,
                "position_pnl": 0.0,
                "order_size": 0.0,
                "position_monitor_active": False,
                "last_signals": {},
                "signal_filters_active": False,
                "filtered_signals_count": 0,
                "bollinger_signals_count": 0
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
            return {"success": False, "message": "Bollinger bot çalışmıyor"}
            
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
            
            # Bollinger Bands için geçmiş veri çekme
            required_candles = max(settings.BOLLINGER_PERIOD + 20, 60)
            klines = await binance_client.get_historical_klines(symbol, settings.TIMEFRAME, limit=required_candles)
            if not klines or len(klines) < required_candles - 10:
                return {"success": False, "message": f"{symbol} için yetersiz Bollinger Bands verisi"}
            
            self.multi_klines[symbol] = klines
            
            # Kaldıraç ayarla
            await binance_client.set_leverage(symbol, settings.LEVERAGE)
            
            # Symbol listesine ekle
            self.status["symbols"].append(symbol)
            self.status["last_signals"][symbol] = "HOLD"
            
            # Yeni WebSocket bağlantısı başlat
            task = asyncio.create_task(self._single_websocket_loop(symbol))
            self._websocket_tasks.append(task)
            
            print(f"✅ {symbol} Bollinger bot'a eklendi")
            return {"success": True, "message": f"{symbol} Bollinger Bands bot'a başarıyla eklendi"}
            
        except Exception as e:
            return {"success": False, "message": f"{symbol} eklenirken hata: {e}"}

    async def remove_symbol(self, symbol: str):
        """Çalışan bot'tan symbol çıkar"""
        if not self.status["is_running"]:
            return {"success": False, "message": "Bollinger bot çalışmıyor"}
            
        if symbol not in self.status["symbols"]:
            return {"success": False, "message": f"{symbol} zaten izlenmiyor"}
            
        if self.status["active_symbol"] == symbol:
            return {"success": False, "message": f"{symbol} şu anda aktif Bollinger pozisyonunda - önce pozisyonu kapatın"}
            
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
            
            print(f"✅ {symbol} Bollinger bot'tan çıkarıldı")
            return {"success": True, "message": f"{symbol} Bollinger bot'tan başarıyla çıkarıldı"}
            
        except Exception as e:
            return {"success": False, "message": f"{symbol} çıkarılırken hata: {e}"}

    def get_multi_status(self):
        """🎯 Bollinger Bands multi-coin bot durumunu döndür"""
        win_rate = 0
        total_trades = self.status["successful_trades"] + self.status["failed_trades"]
        if total_trades > 0:
            win_rate = (self.status["successful_trades"] / total_trades) * 100
        
        return {
            "is_running": self.status["is_running"],
            "strategy": "bollinger_bands",
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
            "bollinger_signals_count": self.status["bollinger_signals_count"],
            "successful_trades": self.status["successful_trades"],
            "failed_trades": self.status["failed_trades"],
            "win_rate": f"{win_rate:.1f}%",
            "bollinger_config": {
                "period": settings.BOLLINGER_PERIOD,
                "std_dev": settings.BOLLINGER_STD_DEV,
                "entry_lower": settings.BB_ENTRY_LOWER,
                "entry_upper": settings.BB_ENTRY_UPPER,
                "timeframe": settings.TIMEFRAME,
                "leverage": settings.LEVERAGE,
                "stop_loss": f"{settings.STOP_LOSS_PERCENT*100:.1f}%",
                "take_profit": f"{settings.TAKE_PROFIT_PERCENT*100:.1f}%"
            }
        }

    # Diğer mevcut metodlar aynı kalabilir...
    async def scan_all_positions(self):
        """Tüm açık pozisyonları manuel tarayıp TP/SL ekle"""
        if not self.status["is_running"]:
            return {"success": False, "message": "Bollinger bot çalışmıyor"}
            
        try:
            print("🔍 Manuel pozisyon taraması başlatılıyor...")
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
            print(f"🎯 {symbol} için manuel TP/SL kontrolü...")
            success = await position_manager.manual_scan_symbol(symbol)
            return {
                "success": success,
                "symbol": symbol,
                "message": f"{symbol} için TP/SL kontrolü tamamlandı"
            }
        except Exception as e:
            return {"success": False, "message": f"{symbol} kontrolü hatası: {e}"}

bot_core = BotCore()
