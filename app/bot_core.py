# app/bot_core.py - TP/SL KORUMA ENTEGRASYONU ile

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

class EnhancedBotCore:
    def __init__(self):
        self.status = {
            "is_running": False, 
            "symbols": [],
            "active_symbol": None,
            "position_side": None, 
            "status_message": "Enhanced EMA Cross Bot başlatılmadı.",
            "account_balance": 0.0,
            "position_pnl": 0.0,
            "order_size": 0.0,
            "dynamic_sizing": True,
            "position_monitor_active": False,
            "last_signals": {},
            "signal_filters_active": True,
            "filtered_signals_count": 0,
            "clean_ema_signals_count": 0,
            "successful_trades": 0,
            "failed_trades": 0,
            # 🎯 Enhanced özellikler
            "position_reverses": 0,
            "partial_exits_executed": 0,
            "sl_tightenings": 0,
            "timeframe": settings.TIMEFRAME,
            "using_partial_exits": False,
            "reverse_detection_active": settings.ENABLE_POSITION_REVERSE,
            # 🛡️ TP/SL Koruma istatistikleri
            "tp_sl_protection_active": True,
            "tp_sl_restorations": 0,
            "orphan_orders_cleaned": 0
        }
        
        self.multi_klines = {}
        self._stop_requested = False
        self.quantity_precision = {}
        self.price_precision = {}
        self._last_status_update = 0
        self._websocket_connections = {}
        self._websocket_tasks = []
        self._max_reconnect_attempts = 10
        self._debug_enabled = settings.DEBUG_MODE
        
        # 🎯 Enhanced özellikleri
        self._position_reverse_tracking = {}  # Symbol -> reverse count
        self._last_sl_tightening_check = {}   # Symbol -> last check time
        self._performance_monitoring = {
            "total_signals": 0,
            "clean_signals": 0,
            "reverse_signals": 0,
            "partial_exit_profits": 0.0,
            "sl_tightening_saves": 0.0,
            "tp_sl_protection_saves": 0.0  # YENİ!
        }
        
        # Performance optimization (önceki sürümden)
        self._calculation_lock = Lock()
        self._last_balance_calculation = 0
        self._cached_order_size = 0.0
        self._balance_calculation_interval = 60  # 60 saniye
        self._calculation_in_progress = False
        
        print("🚀 ENHANCED EMA Cross Bot v4.1 başlatıldı")
        print(f"🎯 Strateji: Basitleştirilmiş EMA {settings.EMA_FAST_PERIOD}/{settings.EMA_SLOW_PERIOD}/{settings.EMA_TREND_PERIOD}")
        print(f"✅ Position Reverse: {'Aktif' if settings.ENABLE_POSITION_REVERSE else 'Deaktif'}")
        print(f"✅ Kademeli Satış: {'Aktif' if settings.ENABLE_PARTIAL_EXITS else 'Deaktif'}")
        print(f"✅ SL Tightening: {'Aktif' if settings.ENABLE_SL_TIGHTENING else 'Deaktif'}")
        print(f"🛡️ TP/SL Koruma Sistemi: Aktif")
        print(f"⏰ Timeframe: {settings.TIMEFRAME}")

    async def start(self, symbols: list):
        """Enhanced multi-coin bot başlatma - TP/SL korumalı"""
        if self.status["is_running"]:
            print("⚠️ Enhanced bot zaten çalışıyor.")
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
            "status_message": f"🎯 Enhanced EMA Cross: {len(symbols)} coin başlatılıyor...",
            "timeframe": settings.TIMEFRAME,
            "using_partial_exits": settings.ENABLE_PARTIAL_EXITS,
            "reverse_detection_active": settings.ENABLE_POSITION_REVERSE,
            "tp_sl_protection_active": True
        })
        
        print(f"🚀 ENHANCED EMA CROSS Multi-coin bot başlatılıyor: {', '.join(symbols)}")
        
        try:
            # 1. Binance bağlantısı (Enhanced TP/SL koruma ile)
            print("1️⃣ Enhanced Binance bağlantısı kuruluyor...")
            await binance_client.initialize()
            print("✅ Enhanced Binance bağlantısı başarılı")
            print("🛡️ TP/SL koruma sistemi otomatik başlatıldı")
            
            # 2. 🛡️ SADECE YETİM EMİRLERİ TEMİZ (TP/SL koruma ile)
            print("2️⃣ 🧹 Enhanced yetim emir temizliği (TP/SL korunur)...")
            for symbol in symbols:
                try:
                    await binance_client._safe_cancel_orphan_orders(symbol)
                    self.status["orphan_orders_cleaned"] += 1
                    await asyncio.sleep(0.2)
                except Exception as cleanup_error:
                    print(f"⚠️ {symbol} enhanced temizlik hatası: {cleanup_error}")
            
            # 3. Hesap bakiyesi ve dinamik sizing
            print("3️⃣ Hesap bakiyesi ve dinamik pozisyon hesaplaması...")
            self.status["account_balance"] = await binance_client.get_account_balance(use_cache=False)
            initial_order_size = await self._calculate_dynamic_order_size()
            print(f"✅ Hesap bakiyesi: {self.status['account_balance']:.2f} USDT")
            print(f"✅ Enhanced pozisyon boyutu: {initial_order_size:.2f} USDT")
            
            # 4. Symboller için hazırlık ve EMA verisi
            print(f"4️⃣ {len(symbols)} symbol için Enhanced EMA analizi hazırlığı...")
            for symbol in symbols:
                try:
                    symbol_info = await binance_client.get_symbol_info(symbol)
                    if not symbol_info:
                        print(f"❌ {symbol} bilgileri alınamadı")
                        continue
                    
                    # Precision hesaplama
                    self.quantity_precision[symbol] = self._get_precision_from_filter(symbol_info, 'LOT_SIZE', 'stepSize')
                    self.price_precision[symbol] = self._get_precision_from_filter(symbol_info, 'PRICE_FILTER', 'tickSize')
                    
                    # Enhanced EMA için geçmiş veri
                    required_candles = max(settings.EMA_TREND_PERIOD + 20, 70)
                    klines = await binance_client.get_historical_klines(symbol, settings.TIMEFRAME, limit=required_candles)
                    
                    if klines and len(klines) >= required_candles - 10:
                        self.multi_klines[symbol] = klines
                        print(f"✅ {symbol} Enhanced analiz hazır ({len(klines)} mum)")
                        
                        # İlk analizi test et
                        test_signal = trading_strategy.analyze_klines(klines, symbol)
                    else:
                        print(f"❌ {symbol} yetersiz veri")
                        continue
                        
                    await asyncio.sleep(0.2)
                    
                except Exception as symbol_error:
                    print(f"❌ {symbol} hazırlık hatası: {symbol_error}")
                    continue
            
            # 5. 🛡️ MEVCUT AÇIK POZİSYON KONTROLÜ ve TP/SL KORUMA
            print("5️⃣ Mevcut açık pozisyonlar ve Enhanced TP/SL koruma kontrol...")
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
                    
                    # 🛡️ Mevcut pozisyon için TP/SL koruma kontrolü
                    await self._ensure_position_protection(active_symbol, active_position)
                    
                    # SL tightening kontrolü başlat
                    if settings.ENABLE_SL_TIGHTENING:
                        await self._check_sl_tightening(active_symbol)
                        
                    # Position manager ile Enhanced kontrol
                    await position_manager.manual_scan_symbol(active_symbol)
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
                
            # 7. Enhanced Position Monitoring başlat
            print("7️⃣ 🛡️ Enhanced Position monitoring başlatılıyor...")
            try:
                asyncio.create_task(position_manager.start_monitoring())
                self.status["position_monitor_active"] = True
                print("✅ Enhanced position koruması aktif (15s interval)")
            except Exception as monitor_error:
                print(f"⚠️ Position monitoring hatası: {monitor_error}")
                
            # 8. Multi-WebSocket bağlantıları
            print("8️⃣ 🌐 Enhanced Multi-coin WebSocket başlatılıyor...")
            valid_symbols = [s for s in symbols if s in self.multi_klines]
            self.status["symbols"] = valid_symbols
            
            if not valid_symbols:
                raise Exception("Hiç geçerli symbol bulunamadı!")
            
            # Kademeli satış durumunu kontrol et
            using_partial = binance_client._should_use_partial_exits(settings.TIMEFRAME)
            self.status["using_partial_exits"] = using_partial
            
            partial_status = "KADEMELİ SATIŞ" if using_partial else "NORMAL TP/SL"
            self.status["status_message"] = f"🎯 ENHANCED EMA: {len(valid_symbols)} coin izleniyor [{partial_status}] [REVERSE+SL_TIGHTENING+TP/SL_PROTECTION]"
            
            print(f"✅ {self.status['status_message']}")
            await self._start_multi_websocket_loop(valid_symbols)
                        
        except Exception as e:
            error_msg = f"❌ Enhanced bot başlatma hatası: {e}"
            print(error_msg)
            print(f"❌ Traceback: {traceback.format_exc()}")
            self.status["status_message"] = error_msg
        
        print("🛑 Enhanced bot durduruluyor...")
        await self.stop()

    async def _ensure_position_protection(self, symbol: str, position: dict):
        """🛡️ Mevcut pozisyon için TP/SL koruması sağla"""
        try:
            print(f"🛡️ {symbol} mevcut pozisyon koruması kontrol ediliyor...")
            
            position_amt = float(position['positionAmt'])
            if position_amt == 0:
                return
                
            # Açık emirleri kontrol et
            await binance_client._rate_limit_delay()
            open_orders = await binance_client.client.futures_get_open_orders(symbol=symbol)
            
            # TP/SL analizi
            is_long = position_amt > 0
            required_side = 'SELL' if is_long else 'BUY'
            
            has_sl = any(order['type'] in ['STOP_MARKET', 'STOP'] and 
                        order.get('side') == required_side and 
                        order.get('reduceOnly') for order in open_orders)
                        
            has_tp = any(order['type'] in ['TAKE_PROFIT_MARKET', 'TAKE_PROFIT', 'LIMIT'] and 
                        order.get('side') == required_side and 
                        order.get('reduceOnly') for order in open_orders)
            
            if has_sl and has_tp:
                print(f"✅ {symbol} mevcut pozisyon zaten korumalı")
                return
                
            print(f"⚠️ {symbol} mevcut pozisyon eksik koruma! SL: {has_sl}, TP: {has_tp}")
            print(f"🛡️ Enhanced koruma sistemi eksik TP/SL'leri ekliyor...")
            
            # Position manager ile eksik korumaları ekle
            success = await position_manager._enhanced_check_and_protect(position, force_scan=True)
            
            if success:
                self.status["tp_sl_restorations"] += 1
                self._performance_monitoring["tp_sl_protection_saves"] += 1
                print(f"✅ {symbol} mevcut pozisyon koruması restore edildi!")
            else:
                print(f"❌ {symbol} mevcut pozisyon koruması restore edilemedi")
                
        except Exception as e:
            print(f"❌ {symbol} pozisyon koruma kontrolü hatası: {e}")

    async def _start_multi_websocket_loop(self, symbols: list):
        """Multi-coin WebSocket döngüsü"""
        print(f"🌐 {len(symbols)} symbol için Enhanced WebSocket başlatılıyor...")
        
        self._websocket_tasks = []
        for symbol in symbols:
            task = asyncio.create_task(self._single_websocket_loop(symbol))
            self._websocket_tasks.append(task)
        
        try:
            await asyncio.gather(*self._websocket_tasks)
        except Exception as e:
            print(f"❌ Multi-WebSocket hatası: {e}")

    async def _single_websocket_loop(self, symbol: str):
        """Tek symbol için WebSocket döngüsü"""
        ws_url = f"{settings.WEBSOCKET_URL}/ws/{symbol.lower()}@kline_{settings.TIMEFRAME}"
        reconnect_attempts = 0
        
        print(f"🔗 {symbol} Enhanced WebSocket başlatılıyor...")
        
        while not self._stop_requested and reconnect_attempts < self._max_reconnect_attempts:
            try:
                async with websockets.connect(
                    ws_url, 
                    ping_interval=settings.WEBSOCKET_PING_INTERVAL, 
                    ping_timeout=settings.WEBSOCKET_PING_TIMEOUT,
                    close_timeout=settings.WEBSOCKET_CLOSE_TIMEOUT
                ) as ws:
                    print(f"✅ {symbol} Enhanced WebSocket bağlandı")
                    reconnect_attempts = 0
                    self._websocket_connections[symbol] = ws
                    
                    while not self._stop_requested:
                        try:
                            message = await asyncio.wait_for(ws.recv(), timeout=65.0)
                            await self._handle_enhanced_websocket_message(symbol, message)
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

    async def _handle_enhanced_websocket_message(self, symbol: str, message: str):
        """Enhanced WebSocket mesaj işleme - TP/SL koruma entegrasyonu ile"""
        try:
            data = json.loads(message)
            kline_data = data.get('k', {})
            
            # Status update kontrolü (daha az sıklık)
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
            max_klines = getattr(settings, 'MAX_KLINES_PER_SYMBOL', 150)
            if len(self.multi_klines[symbol]) >= max_klines:
                self.multi_klines[symbol].pop(0)
                
            # Yeni kline ekle
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
            min_required = max(settings.EMA_TREND_PERIOD + 10, 60)
            if len(self.multi_klines[symbol]) < min_required:
                return
            
            self._performance_monitoring["total_signals"] += 1
            
            # Enhanced EMA analizi
            signal = trading_strategy.analyze_klines(self.multi_klines[symbol], symbol)
            
            # Önceki sinyal ile karşılaştır
            previous_signal = self.status["last_signals"].get(symbol, "HOLD")
            
            # Sadece sinyal değişikliğinde işlem yap
            if signal != previous_signal:
                if signal == "HOLD":
                    self.status["filtered_signals_count"] += 1
                else:
                    self.status["clean_ema_signals_count"] += 1
                    self._performance_monitoring["clean_signals"] += 1
                    print(f"🚨 {symbol} YENİ CLEAN EMA: {previous_signal} -> {signal}")
                    
                self.status["last_signals"][symbol] = signal
                
                # Enhanced pozisyon mantığı (TP/SL koruma entegrasyonu ile)
                await self._handle_enhanced_position_logic_protected(symbol, signal)
            
            # Aktif pozisyon varsa SL tightening kontrol et
            if (self.status["active_symbol"] == symbol and 
                self.status["position_side"] and 
                settings.ENABLE_SL_TIGHTENING):
                await self._periodic_sl_tightening_check(symbol)
                
        except Exception as e:
            print(f"❌ {symbol} Enhanced WebSocket hatası: {e}")

    async def _handle_enhanced_position_logic_protected(self, signal_symbol: str, signal: str):
        """🛡️ Enhanced pozisyon yönetim mantığı - TP/SL koruma entegrasyonu ile"""
        try:
            current_active_symbol = self.status.get("active_symbol")
            current_position_side = self.status.get("position_side")
            
            # DURUM 1: Hiç pozisyon yok, yeni sinyal geldi
            if not current_active_symbol and not current_position_side and signal != "HOLD":
                print(f"🚀 Yeni Enhanced fırsatı: {signal_symbol} -> {signal}")
                await self._open_enhanced_position_protected(signal_symbol, signal)
                return
            
            # DURUM 2: Mevcut pozisyon var, aynı symbol'den ters sinyal geldi (POSITION REVERSE!)
            if (current_active_symbol == signal_symbol and 
                current_position_side and 
                signal != "HOLD" and 
                signal != current_position_side):
                print(f"🔄 {signal_symbol} POSITION REVERSE: {current_position_side} -> {signal}")
                await self._execute_position_reverse_protected(signal_symbol, signal)
                return
            
            # DURUM 3: Mevcut pozisyon var, başka symbol'den güçlü sinyal geldi
            if (current_active_symbol and 
                current_active_symbol != signal_symbol and 
                current_position_side and 
                signal != "HOLD"):
                print(f"💡 Yeni Enhanced coin fırsatı: {signal_symbol} -> {signal}")
                await self._switch_to_enhanced_coin_protected(current_active_symbol, signal_symbol, signal)
                return
            
            # DURUM 4: Pozisyon kapanmış mı kontrol et (SL/TP)
            if current_active_symbol and current_position_side:
                open_positions = await binance_client.get_open_positions(current_active_symbol, use_cache=True)
                if not open_positions:
                    print(f"✅ {current_active_symbol} pozisyonu Enhanced TP/SL ile kapandı")
                    await self._handle_position_closed_protected(current_active_symbol, signal_symbol, signal)
                        
        except Exception as e:
            print(f"❌ Enhanced pozisyon mantığı hatası: {e}")

    async def _open_enhanced_position_protected(self, symbol: str, signal: str):
        """🛡️ Enhanced pozisyon açma - TP/SL koruma entegrasyonu"""
        try:
            print(f"🎯 {symbol} -> {signal} Enhanced pozisyonu açılıyor (TP/SL korumalı)...")
            
            # Test modu kontrolü
            if hasattr(settings, 'TEST_MODE') and settings.TEST_MODE:
                print(f"🧪 TEST: {symbol} {signal} Enhanced simüle edildi")
                self.status["active_symbol"] = symbol
                self.status["position_side"] = signal
                return True
            
            await asyncio.sleep(settings.API_CALL_DELAY)
            
            # 🛡️ TP/SL korumalı yetim emir temizliği
            await binance_client._safe_cancel_orphan_orders(symbol)
            await asyncio.sleep(0.2)
            
            # Dinamik order size
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

            print(f"📊 {symbol} Enhanced Pozisyon: {side} {quantity} @ {price:.6f}")
            
            # 🎯 ENHANCED: TP/SL korumalı akıllı çıkış sistemi
            order = await binance_client.create_market_order_with_smart_exits(
                symbol, side, quantity, price, 
                self.price_precision.get(symbol, 2), 
                settings.TIMEFRAME
            )
            
            if order:
                self.status["active_symbol"] = symbol
                self.status["position_side"] = signal
                
                # Status mesajını güncelle
                exit_type = "KADEMELİ" if self.status["using_partial_exits"] else "NORMAL"
                self.status["status_message"] = f"🎯 ENHANCED {signal}: {symbol} @ {price:.6f} [{exit_type} ÇIKIŞ] 🛡️ TP/SL KORUNUYOR"
                
                print(f"✅ {symbol} {signal} Enhanced pozisyonu açıldı (TP/SL korumalı)!")
                
                # Cache temizle
                try:
                    binance_client._cached_positions.clear()
                except:
                    pass
                    
                # Position manager'a bildir (Enhanced kontrol için)
                await asyncio.sleep(1)
                await position_manager.manual_scan_symbol(symbol)
                return True
            else:
                print(f"❌ {symbol} Enhanced pozisyonu açılamadı")
                return False
                
        except Exception as e:
            print(f"❌ {symbol} Enhanced pozisyon açma hatası: {e}")
            return False

    async def _execute_position_reverse_protected(self, symbol: str, new_signal: str):
        """🔄 TP/SL korumalı Position Reverse"""
        try:
            print(f"🔄 ENHANCED POSITION REVERSE (TP/SL korumalı): {symbol} -> {new_signal}")
            
            # Reverse sayacını artır
            if symbol not in self._position_reverse_tracking:
                self._position_reverse_tracking[symbol] = 0
            self._position_reverse_tracking[symbol] += 1
            self.status["position_reverses"] += 1
            self._performance_monitoring["reverse_signals"] += 1
            
            # Maximum reverse kontrolü
            if self._position_reverse_tracking[symbol] > settings.MAX_REVERSE_COUNT:
                print(f"⚠️ {symbol}: Max reverse count aşıldı ({settings.MAX_REVERSE_COUNT})")
                return
            
            # Mevcut pozisyonu kontrol et
            open_positions = await binance_client.get_open_positions(symbol, use_cache=False)
            if open_positions:
                position = open_positions[0]
                position_amt = float(position['positionAmt'])
                side_to_close = 'SELL' if position_amt > 0 else 'BUY'
                
                # PnL kaydet
                pnl = float(position['unRealizedProfit'])
                firebase_manager.log_trade({
                    "symbol": symbol,
                    "strategy": "enhanced_ema_cross",
                    "pnl": pnl, 
                    "status": "CLOSED_BY_POSITION_REVERSE", 
                    "reverse_count": self._position_reverse_tracking[symbol],
                    "timestamp": datetime.now(timezone.utc)
                })

                # 🛡️ Mevcut pozisyonun TP/SL'lerini koru (sadece yetim emirleri iptal et)
                print(f"🛡️ {symbol} Position reverse - TP/SL korunarak yetim emirler iptal ediliyor...")
                await binance_client._safe_cancel_orphan_orders(symbol)
                await asyncio.sleep(0.5)
                
                print(f"📉 {symbol} eski pozisyon kapatılıyor...")
                # Pozisyonu manuel kapat (market order ile)
                try:
                    close_order = await binance_client.client.futures_create_order(
                        symbol=symbol,
                        side=side_to_close,
                        type='MARKET',
                        quantity=abs(position_amt),
                        reduceOnly=True
                    )
                    print(f"✅ {symbol} eski pozisyon kapatıldı")
                    await asyncio.sleep(1)
                except Exception as close_error:
                    print(f"❌ {symbol} pozisyon kapatma hatası: {close_error}")
                
            # Yeni reverse pozisyonu aç (TP/SL korumalı)
            success = await self._open_enhanced_position_protected(symbol, new_signal)
            if success:
                print(f"✅ {symbol} Position Reverse başarılı: {new_signal} (TP/SL korumalı)")
            else:
                self.status["active_symbol"] = None
                self.status["position_side"] = None
                
        except Exception as e:
            print(f"❌ {symbol} Position Reverse hatası: {e}")

    async def _switch_to_enhanced_coin_protected(self, current_symbol: str, new_symbol: str, new_signal: str):
        """🛡️ Enhanced coin değişimi - TP/SL korumalı"""
        try:
            print(f"🔄 ENHANCED COİN DEĞİŞİMİ (TP/SL korumalı): {current_symbol} -> {new_symbol} ({new_signal})")
            
            # Mevcut pozisyonu kapat
            open_positions = await binance_client.get_open_positions(current_symbol, use_cache=False)
            if open_positions:
                position = open_positions[0]
                pnl = float(position['unRealizedProfit'])
                firebase_manager.log_trade({
                    "symbol": current_symbol, 
                    "strategy": "enhanced_ema_cross",
                    "pnl": pnl, 
                    "status": "CLOSED_FOR_ENHANCED_COIN_SWITCH", 
                    "timestamp": datetime.now(timezone.utc)
                })
                
                # 🛡️ TP/SL korunarak yetim emirleri iptal et
                await binance_client._safe_cancel_orphan_orders(current_symbol)
                await asyncio.sleep(1)

                # Pozisyonu manuel kapat
                position_amt = float(position['positionAmt'])
                side_to_close = 'SELL' if position_amt > 0 else 'BUY'
                
                try:
                    close_order = await binance_client.client.futures_create_order(
                        symbol=current_symbol,
                        side=side_to_close,
                        type='MARKET',
                        quantity=abs(position_amt),
                        reduceOnly=True
                    )
                    print(f"✅ {current_symbol} pozisyon coin switch için kapatıldı")
                    await asyncio.sleep(1)
                except Exception as close_error:
                    print(f"❌ {current_symbol} pozisyon kapatma hatası: {close_error}")

            # Yeni coin'de Enhanced pozisyonu aç (TP/SL korumalı)
            success = await self._open_enhanced_position_protected(new_symbol, new_signal)
            if not success:
                self.status["active_symbol"] = None
                self.status["position_side"] = None
                
        except Exception as e:
            print(f"❌ Enhanced coin değişimi hatası: {e}")

    async def _handle_position_closed_protected(self, closed_symbol: str, signal_symbol: str, signal: str):
        """🛡️ Pozisyon kapandığında işlemler - TP/SL korumalı"""
        try:
            # PnL kaydet (burada last trade PnL alınabilir)
            
            # Pozisyon durumunu temizle
            self.status["active_symbol"] = None
            self.status["position_side"] = None
            
            # Cache temizle
            self._cached_order_size = 0.0
            
            print(f"✅ {closed_symbol} pozisyonu TP/SL ile başarıyla kapandı")
            
            # Eğer yeni sinyal varsa pozisyon aç (TP/SL korumalı)
            if signal != "HOLD":
                print(f"🚀 Pozisyon kapandıktan sonra yeni Enhanced fırsatı: {signal_symbol} -> {signal}")
                await self._open_enhanced_position_protected(signal_symbol, signal)
                
        except Exception as e:
            print(f"❌ Position closed handling hatası: {e}")

    async def _periodic_sl_tightening_check(self, symbol: str):
        """Periyodik SL tightening kontrolü"""
        try:
            if not settings.ENABLE_SL_TIGHTENING:
                return
                
            current_time = time.time()
            last_check = self._last_sl_tightening_check.get(symbol, 0)
            
            # 5 dakikada bir kontrol et
            if current_time - last_check < 300:
                return
                
            self._last_sl_tightening_check[symbol] = current_time
            
            # SL tightening dene (TP korumalı)
            if await self._check_sl_tightening(symbol):
                self.status["sl_tightenings"] += 1
                self._performance_monitoring["sl_tightening_saves"] += 1
                print(f"✅ {symbol} SL tightening başarılı (TP korundu)")
                
        except Exception as e:
            print(f"❌ {symbol} periyodik SL check hatası: {e}")

    async def _check_sl_tightening(self, symbol: str) -> bool:
        """🛡️ SL tightening kontrolü - TP korumalı"""
        try:
            result = await binance_client.check_and_tighten_stop_loss(symbol)
            if result:
                self._performance_monitoring["sl_tightening_saves"] += 1
            return result
        except Exception as e:
            print(f"❌ {symbol} SL tightening hatası: {e}")
            return False

    # Diğer metodlar aynı kalabilir...
    async def _calculate_dynamic_order_size(self):
        """Dinamik pozisyon boyutu hesapla"""
        if self._calculation_in_progress:
            return self._cached_order_size if self._cached_order_size > 0 else settings.ORDER_SIZE_USDT
        
        current_time = time.time()
        
        if (current_time - self._last_balance_calculation < self._balance_calculation_interval and 
            self._cached_order_size > 0):
            return self._cached_order_size
        
        with self._calculation_lock:
            self._calculation_in_progress = True
            
            try:
                current_balance = await binance_client.get_account_balance(use_cache=True)
                dynamic_size = current_balance * 0.9
                
                min_size = 15.0
                max_size = 1000.0
                
                final_size = max(min(dynamic_size, max_size), min_size)
                
                self._cached_order_size = final_size
                self._last_balance_calculation = current_time
                self.status["order_size"] = final_size
                
                return final_size
                
            except Exception as e:
                print(f"❌ Dinamik pozisyon hesaplama hatası: {e}")
                fallback_size = settings.ORDER_SIZE_USDT
                self._cached_order_size = fallback_size
                self.status["order_size"] = fallback_size
                return fallback_size
            finally:
                self._calculation_in_progress = False

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
        """Enhanced status güncelleme"""
        try:
            if not self.status["is_running"]:
                return
                
            self.status["account_balance"] = await binance_client.get_account_balance(use_cache=True)
            
            if self.status["active_symbol"] and self.status["position_side"]:
                # Position PnL al
                positions = await binance_client.get_open_positions(self.status["active_symbol"], use_cache=True)
                if positions:
                    self.status["position_pnl"] = float(positions[0]['unRealizedProfit'])
                else:
                    self.status["position_pnl"] = 0.0
            else:
                self.status["position_pnl"] = 0.0
            
            # Order size güncelle
            current_time = time.time()
            if self._cached_order_size == 0 or current_time - self._last_balance_calculation > self._balance_calculation_interval:
                await self._calculate_dynamic_order_size()
            
            # Position monitor durumu
            monitor_status = position_manager.get_status()
            self.status["position_monitor_active"] = monitor_status["is_running"]
            
        except Exception as e:
            print(f"❌ Enhanced status güncelleme hatası: {e}")

    def get_multi_status(self):
        """Enhanced multi-coin bot durumunu döndür - TP/SL koruma istatistikleri ile"""
        win_rate = 0
        total_trades = self.status["successful_trades"] + self.status["failed_trades"]
        if total_trades > 0:
            win_rate = (self.status["successful_trades"] / total_trades) * 100
        
        return {
            "is_running": self.status["is_running"],
            "strategy": "enhanced_ema_cross",
            "version": "4.1_tp_sl_protected",  # YENİ VERSİYON!
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
            
            # Enhanced features
            "timeframe": self.status["timeframe"],
            "using_partial_exits": self.status["using_partial_exits"],
            "reverse_detection_active": self.status["reverse_detection_active"],
            "tp_sl_protection_active": self.status["tp_sl_protection_active"],  # YENİ!
            "position_reverses": self.status["position_reverses"],
            "partial_exits_executed": self.status["partial_exits_executed"],
            "sl_tightenings": self.status["sl_tightenings"],
            "tp_sl_restorations": self.status["tp_sl_restorations"],  # YENİ!
            "orphan_orders_cleaned": self.status["orphan_orders_cleaned"],  # YENİ!
            
            # Signal stats
            "filtered_signals_count": self.status["filtered_signals_count"],
            "clean_ema_signals_count": self.status["clean_ema_signals_count"],
            "successful_trades": self.status["successful_trades"],
            "failed_trades": self.status["failed_trades"],
            "win_rate": f"{win_rate:.1f}%",
            
            # Enhanced config
            "enhanced_config": {
                "ema_fast": settings.EMA_FAST_PERIOD,
                "ema_slow": settings.EMA_SLOW_PERIOD,
                "ema_trend": settings.EMA_TREND_PERIOD,
                "timeframe": settings.TIMEFRAME,
                "leverage": settings.LEVERAGE,
                "partial_exits": settings.ENABLE_PARTIAL_EXITS,
                "position_reverse": settings.ENABLE_POSITION_REVERSE,
                "sl_tightening": settings.ENABLE_SL_TIGHTENING,
                "tp_sl_protection": True,  # YENİ!
                "tp1_percent": f"{settings.TP1_PERCENT*100:.1f}%",
                "tp2_percent": f"{settings.TP2_PERCENT*100:.1f}%",
                "stop_loss": f"{settings.STOP_LOSS_PERCENT*100:.1f}%"
            },
            
            # Performance monitoring
            "performance": {
                "total_signals": self._performance_monitoring["total_signals"],
                "clean_signals": self._performance_monitoring["clean_signals"],
                "reverse_signals": self._performance_monitoring["reverse_signals"],
                "tp_sl_protection_saves": self._performance_monitoring["tp_sl_protection_saves"],  # YENİ!
                "signal_quality": f"{(self._performance_monitoring['clean_signals'] / max(self._performance_monitoring['total_signals'], 1) * 100):.1f}%",
                "reverse_tracking": dict(self._position_reverse_tracking),
                "binance_client_status": binance_client.get_client_status()
            }
        }

    async def stop(self):
        """Enhanced bot durdurma"""
        self._stop_requested = True
        if self.status["is_running"]:
            print("🛑 Enhanced multi-coin bot durduruluyor...")
            
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
            
            # Enhanced final statistics
            total_signals = self.status["clean_ema_signals_count"]
            successful = self.status["successful_trades"]
            failed = self.status["failed_trades"]
            reverses = self.status["position_reverses"]
            sl_tightenings = self.status["sl_tightenings"]
            tp_sl_restorations = self.status["tp_sl_restorations"]  # YENİ!
            
            if total_signals > 0:
                success_rate = (successful / (successful + failed) * 100) if (successful + failed) > 0 else 0
                print(f"📊 ENHANCED BOT İSTATİSTİKLERİ v4.1:")
                print(f"   🎯 Toplam clean sinyal: {total_signals}")
                print(f"   ✅ Başarılı: {successful}")
                print(f"   ❌ Başarısız: {failed}")
                print(f"   🔄 Position reverse: {reverses}")
                print(f"   🛡️ SL tightening: {sl_tightenings}")
                print(f"   🛡️ TP/SL koruması: {tp_sl_restorations}")  # YENİ!
                print(f"   📈 Başarı oranı: %{success_rate:.1f}")
                print(f"   🎯 Sinyal kalitesi: %{(self._performance_monitoring['clean_signals'] / max(self._performance_monitoring['total_signals'], 1) * 100):.1f}")
                print(f"   🛡️ TP/SL koruma başarısı: {self._performance_monitoring['tp_sl_protection_saves']:.0f}")  # YENİ!
            
            self.status.update({
                "is_running": False, 
                "symbols": [],
                "active_symbol": None,
                "status_message": "Enhanced EMA Cross bot durduruldu (TP/SL korumalı).",
                "account_balance": 0.0,
                "position_pnl": 0.0,
                "order_size": 0.0,
                "position_monitor_active": False,
                "last_signals": {},
                "tp_sl_protection_active": False
            })
            
            print(f"✅ {self.status['status_message']}")
            await binance_client.close()

    # Diğer metodlar aynı kalır...
    async def add_symbol(self, symbol: str):
        # Eski uyumluluk için...
        pass
    
    async def remove_symbol(self, symbol: str):
        # Eski uyumluluk için...
        pass

    async def scan_all_positions(self):
        """Tüm açık pozisyonları manuel tarayıp Enhanced TP/SL ekle"""
        if not self.status["is_running"]:
            return {"success": False, "message": "Enhanced bot çalışmıyor"}
            
        try:
            await position_manager._enhanced_scan_and_protect()
            return {
                "success": True, 
                "message": "Tüm pozisyonlar Enhanced TP/SL protection ile tarandı",
                "monitor_status": position_manager.get_status(),
                "tp_sl_protection": "Aktif"
            }
        except Exception as e:
            return {"success": False, "message": f"Enhanced tarama hatası: {e}"}
    
    async def scan_specific_symbol(self, symbol: str):
        """Belirli bir coin için Enhanced TP/SL kontrolü"""
        try:
            success = await position_manager.manual_scan_symbol(symbol)
            return {
                "success": success,
                "symbol": symbol,
                "message": f"{symbol} için Enhanced TP/SL kontrolü tamamlandı (koruma aktif)"
            }
        except Exception as e:
            return {"success": False, "message": f"{symbol} Enhanced kontrolü hatası: {e}"}

# Global enhanced instance
bot_core = EnhancedBotCore()
