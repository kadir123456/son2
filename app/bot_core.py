import asyncio
import json
import websockets
from .config import settings
from .binance_client import binance_client
from .trading_strategy import trading_strategy
from .firebase_manager import firebase_manager
from .position_manager import position_manager
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import math
import time
import traceback

class BotCore:
    def __init__(self):
        self.status = {
            "is_running": False, 
            "symbols": [],
            "active_symbol": None,
            "position_side": None, 
            "status_message": "Bot başlatılmadı.",
            "account_balance": 0.0,
            "position_pnl": 0.0,
            "order_size": 0.0,
            "dynamic_sizing": True,
            "position_monitor_active": False,
            "last_signals": {},
            "signal_filters_active": True,
            "filtered_signals_count": 0,
            "current_timeframe": settings.TIMEFRAME,
            "daily_pnl": 0.0,
            "daily_positions": 0,
            "risk_management_active": True
        }
        self.multi_klines = {}
        self._stop_requested = False
        self.quantity_precision = {}
        self.price_precision = {}
        self._last_status_update = 0
        self._websocket_connections = {}
        self._websocket_tasks = []
        self._max_reconnect_attempts = 10
        
        # 🔧 DEBUG ÖZELLİKLERİ
        self.debug_mode = False
        self._debug_message_count = {}
        self._debug_last_analysis_time = {}
        self._debug_signal_history = {}
        self._debug_websocket_stats = {}
        
        print("🛡️ Gelişmiş Risk Yönetimi ve Dinamik TP/SL Destekli Bot Core başlatıldı")
        print("🔧 DEBUG özellikler hazır - enable_debug_mode() ile aktif edin")

    def enable_debug_mode(self):
        """🔧 Debug modunu aktif et"""
        self.debug_mode = True
        print("\n🔧 BOT CORE DEBUG MODU AKTİF!")
        print("=" * 50)
        print("⚠️  Bu mod SADECE test içindir")
        print("📊 Detaylı loglar aktif edildi")
        print("🎯 Sinyal takibi geliştirildi")
        print("🌐 WebSocket debug aktif")
        print("=" * 50)
        
        # Debug verilerini sıfırla
        self._debug_message_count.clear()
        self._debug_last_analysis_time.clear()
        self._debug_signal_history.clear()
        self._debug_websocket_stats.clear()
        
        # Trading strategy debug modunu da aç
        if hasattr(trading_strategy, 'debug_mode'):
            trading_strategy.debug_mode = True
            print("✅ Trading Strategy debug modu da aktif edildi")

    def disable_debug_mode(self):
        """🔧 Debug modunu kapat"""
        self.debug_mode = False
        print("🔄 Bot Core debug modu kapatıldı")
        
        if hasattr(trading_strategy, 'debug_mode'):
            trading_strategy.debug_mode = False
            print("✅ Trading Strategy debug modu da kapatıldı")

    def _get_precision_from_filter(self, symbol_info, filter_type, key):
        for f in symbol_info['filters']:
            if f['filterType'] == filter_type:
                size_str = f[key]
                if '.' in size_str:
                    return len(size_str.split('.')[1].rstrip('0'))
                return 0
        return 0

    async def _calculate_dynamic_order_size(self):
        """Gelişmiş dinamik pozisyon boyutu hesaplama - risk yönetimiyle"""
        try:
            current_balance = await binance_client.get_account_balance(use_cache=False)
            
            max_risk_amount = current_balance * 0.02
            
            timeframe_multipliers = {
                "1m": 0.8,
                "3m": 0.85,
                "5m": 0.9,
                "15m": 0.95,
                "30m": 1.0,
                "1h": 1.05
            }
            
            multiplier = timeframe_multipliers.get(settings.TIMEFRAME, 0.95)
            
            sl_percent = settings.STOP_LOSS_PERCENT
            max_position_size = max_risk_amount / (settings.LEVERAGE * sl_percent)
            
            dynamic_size = max_position_size * multiplier
            
            min_size = 5.0
            max_size = current_balance * 0.9
            
            final_size = max(min(dynamic_size, max_size), min_size)
            
            if self.debug_mode:
                print(f"💰 DEBUG: Dinamik pozisyon hesaplama:")
                print(f"   Bakiye: {current_balance:.2f} USDT")
                print(f"   Risk: {max_risk_amount:.2f} USDT")
                print(f"   Multiplier: {multiplier}")
                print(f"   Final boyut: {final_size:.2f} USDT")
            
            self.status["order_size"] = final_size
            return final_size
            
        except Exception as e:
            print(f"❌ Dinamik pozisyon hesaplama hatası: {e}")
            fallback_size = 25.0
            self.status["order_size"] = fallback_size
            return fallback_size

    def set_timeframe(self, timeframe: str) -> bool:
        """Zaman dilimini değiştir"""
        if self.status["is_running"]:
            print("⚠️ Bot çalışırken zaman dilimi değiştirilemez")
            return False
            
        if settings.set_timeframe(timeframe):
            self.status["current_timeframe"] = timeframe
            if self.debug_mode:
                print(f"🔧 DEBUG: Zaman dilimi güncellendi: {timeframe}")
            return True
        return False

    async def start(self, symbols: list, timeframe: str = None):
        """🔧 DEBUG destekli bot başlatma"""
        if self.status["is_running"]:
            print("Bot zaten çalışıyor.")
            return
            
        if not symbols or len(symbols) == 0:
            print("❌ Hiç symbol verilmedi!")
            return
        
        if timeframe and not self.set_timeframe(timeframe):
            print(f"❌ Geçersiz zaman dilimi: {timeframe}")
            return
            
        self._stop_requested = False
        self.status.update({
            "is_running": True, 
            "symbols": symbols,
            "active_symbol": None,
            "position_side": None, 
            "status_message": f"{len(symbols)} coin için başlatılıyor...",
            "dynamic_sizing": True,
            "position_monitor_active": False,
            "last_signals": {symbol: "HOLD" for symbol in symbols},
            "signal_filters_active": True,
            "filtered_signals_count": 0,
            "current_timeframe": settings.TIMEFRAME,
            "daily_pnl": 0.0,
            "daily_positions": 0,
            "risk_management_active": True
        })
        
        if self.debug_mode:
            print(f"\n🔧 DEBUG BOT BAŞLATMA")
            print(f"="*50)
            print(f"📊 Symboller: {', '.join(symbols)}")
            print(f"🕐 Zaman dilimi: {settings.TIMEFRAME}")
            print(f"📈 TP/SL: %{settings.TAKE_PROFIT_PERCENT*100:.2f}/%{settings.STOP_LOSS_PERCENT*100:.2f}")
            print(f"⚖️ Risk/Reward: 1:{settings.get_risk_reward_ratio():.1f}")
            print(f"🔧 Debug modu: AKTİF")
            print(f"="*50)
        else:
            print(f"🚀 Gelişmiş Multi-coin bot başlatılıyor: {', '.join(symbols)}")
        
        try:
            # 1. Binance bağlantısı
            print("1. Binance bağlantısı kuruluyor...")
            try:
                await binance_client.initialize()
                print("✅ Binance bağlantısı başarılı")
            except Exception as binance_error:
                print(f"❌ Binance bağlantı hatası: {binance_error}")
                raise binance_error
            
            # 2. Yetim emir temizliği
            if self.debug_mode:
                print("\n🔧 DEBUG: Yetim emir temizliği atlanıyor (test modu)")
            else:
                print("2. 🧹 Tüm symboller için yetim emir temizliği yapılıyor...")
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
            print("3. Hesap bakiyesi ve risk kontrolü yapılıyor...")
            try:
                self.status["account_balance"] = await binance_client.get_account_balance(use_cache=False)
                initial_order_size = await self._calculate_dynamic_order_size()
                print(f"✅ Hesap bakiyesi: {self.status['account_balance']} USDT")
                print(f"✅ Risk bazlı pozisyon boyutu: {initial_order_size} USDT")
            except Exception as balance_error:
                print(f"❌ Bakiye kontrol hatası: {balance_error}")
                raise balance_error
            
            # 4. Symbol bilgileri ve geçmiş veri
            print(f"4. {len(symbols)} symbol için bilgiler alınıyor...")
            for symbol in symbols:
                try:
                    symbol_info = await binance_client.get_symbol_info(symbol)
                    if not symbol_info:
                        print(f"❌ {symbol} için borsa bilgileri alınamadı. Atlanıyor...")
                        continue
                    
                    self.quantity_precision[symbol] = self._get_precision_from_filter(symbol_info, 'LOT_SIZE', 'stepSize')
                    self.price_precision[symbol] = self._get_precision_from_filter(symbol_info, 'PRICE_FILTER', 'tickSize')
                    
                    # Debug modu için daha az veri
                    limit = 50 if self.debug_mode else 200
                    klines = await binance_client.get_historical_klines(symbol, settings.TIMEFRAME, limit=limit)
                    
                    if klines:
                        self.multi_klines[symbol] = klines
                        if self.debug_mode:
                            print(f"🔧 DEBUG: {symbol} -> {len(klines)} mum (precision: Q:{self.quantity_precision[symbol]}, P:{self.price_precision[symbol]})")
                        else:
                            print(f"✅ {symbol} bilgileri alındı (Q:{self.quantity_precision[symbol]}, P:{self.price_precision[symbol]})")
                    else:
                        print(f"❌ {symbol} için geçmiş veri alınamadı. Atlanıyor...")
                        continue
                        
                    await asyncio.sleep(0.2)
                    
                except Exception as symbol_error:
                    print(f"❌ {symbol} hazırlık hatası: {symbol_error} - Atlanıyor...")
                    continue
            
            # 5. Mevcut pozisyon kontrolü
            print("5. Mevcut açık pozisyonlar kontrolü...")
            try:
                await binance_client._rate_limit_delay()
                all_positions = await binance_client.client.futures_position_information()
                open_positions = [p for p in all_positions if float(p['positionAmt']) != 0]
                
                if open_positions:
                    active_position = open_positions[0]
                    active_symbol = active_position['symbol']
                    position_amt = float(active_position['positionAmt'])
                    
                    if position_amt > 0:
                        self.status["position_side"] = "LONG"
                    elif position_amt < 0:
                        self.status["position_side"] = "SHORT"
                        
                    self.status["active_symbol"] = active_symbol
                    print(f"⚠️ Mevcut {self.status['position_side']} pozisyonu tespit edildi: {active_symbol}")
                    
                    if not self.debug_mode:
                        print(f"🧹 {active_symbol} mevcut pozisyon için yetim emir temizliği...")
                        await binance_client.cancel_all_orders_safe(active_symbol)
                        await position_manager.manual_scan_symbol(active_symbol)
                else:
                    print("✅ Açık pozisyon bulunamadı")
                    if not self.debug_mode:
                        print("6. Tüm symboller için kaldıraç ayarlanıyor...")
                        for symbol in symbols:
                            if symbol in self.multi_klines:
                                if await binance_client.set_leverage(symbol, settings.LEVERAGE):
                                    print(f"✅ {symbol} kaldıracı {settings.LEVERAGE}x olarak ayarlandı")
                                else:
                                    print(f"⚠️ {symbol} kaldıracı ayarlanamadı")
                                await asyncio.sleep(0.3)
                                
            except Exception as position_error:
                print(f"❌ Pozisyon kontrolü hatası: {position_error}")
                raise position_error
                
            # 6. Position Monitoring
            if not self.debug_mode:
                print("7. 🛡️ Otomatik TP/SL monitoring başlatılıyor...")
                try:
                    asyncio.create_task(position_manager.start_monitoring())
                    self.status["position_monitor_active"] = True
                    print("✅ Otomatik TP/SL koruması aktif")
                except Exception as monitor_error:
                    print(f"⚠️ Position monitoring başlatılamadı: {monitor_error}")
            else:
                print("🔧 DEBUG: Position monitoring atlandı (test modu)")
            
            # 7. WebSocket bağlantıları
            valid_symbols = [s for s in symbols if s in self.multi_klines]
            self.status["symbols"] = valid_symbols
            
            if not valid_symbols:
                raise Exception("Hiç geçerli symbol bulunamadı!")
            
            # Debug durum mesajı
            if self.debug_mode:
                self.status["status_message"] = (f"🔧 DEBUG: {len(valid_symbols)} coin test edilyor ({settings.TIMEFRAME}) "
                                               f"[TÜM FİLTRELER DEVRE DIŞI - SADECE TEST!]")
            else:
                rr_ratio = settings.get_risk_reward_ratio()
                self.status["status_message"] = (f"{len(valid_symbols)} coin izleniyor ({settings.TIMEFRAME}) "
                                               f"[🛡️ GELİŞMİŞ SAHTEKİ SİNYAL + DİNAMİK TP/SL (1:{rr_ratio:.1f}) + "
                                               f"RİSK YÖNETİMİ + OTOMATIK TP/SL AKTİF]")
            
            print(f"✅ {self.status['status_message']}")
            
            # WebSocket döngüsünü başlat
            await self._start_multi_websocket_loop(valid_symbols)
                        
        except Exception as e:
            error_msg = f"❌ Bot başlatılırken beklenmeyen hata: {e}"
            print(error_msg)
            if self.debug_mode:
                print(f"🔧 DEBUG Full traceback:\n{traceback.format_exc()}")
            self.status["status_message"] = error_msg
        
        print("Bot durduruluyor...")
        await self.stop()

    async def _start_multi_websocket_loop(self, symbols: list):
        """Multi-coin WebSocket bağlantı döngüsü"""
        if self.debug_mode:
            print(f"\n🔧 DEBUG WEBSOCKET BAŞLATMA")
            print(f"🌐 {len(symbols)} symbol için WebSocket başlatılıyor...")
        else:
            print(f"🌐 {len(symbols)} symbol için WebSocket bağlantıları başlatılıyor...")
        
        # Her symbol için ayrı task
        self._websocket_tasks = []
        for symbol in symbols:
            task = asyncio.create_task(self._single_websocket_loop(symbol))
            self._websocket_tasks.append(task)
        
        try:
            await asyncio.gather(*self._websocket_tasks)
        except Exception as e:
            print(f"❌ Multi-WebSocket hatası: {e}")

    async def _single_websocket_loop(self, symbol: str):
        """Tek symbol için WebSocket döngüsü - DEBUG destekli"""
        ws_url = f"{settings.WEBSOCKET_URL}/ws/{symbol.lower()}@kline_{settings.TIMEFRAME}"
        reconnect_attempts = 0
        
        if self.debug_mode:
            print(f"🔧 DEBUG: {symbol} WebSocket başlatılıyor -> {ws_url}")
            self._debug_websocket_stats[symbol] = {
                'messages_received': 0,
                'klines_processed': 0,
                'signals_generated': 0,
                'last_message_time': None,
                'connection_attempts': 0
            }
        else:
            print(f"🔗 {symbol} WebSocket bağlantısı başlatılıyor...")
        
        while not self._stop_requested and reconnect_attempts < self._max_reconnect_attempts:
            try:
                self._debug_websocket_stats[symbol]['connection_attempts'] += 1
                
                async with websockets.connect(
                    ws_url, 
                    ping_interval=30, 
                    ping_timeout=15,
                    close_timeout=10
                ) as ws:
                    
                    if self.debug_mode:
                        print(f"🔧 DEBUG: {symbol} WebSocket bağlandı (deneme: {self._debug_websocket_stats[symbol]['connection_attempts']})")
                    else:
                        print(f"✅ {symbol} WebSocket bağlantısı kuruldu")
                        
                    reconnect_attempts = 0
                    self._websocket_connections[symbol] = ws
                    
                    while not self._stop_requested:
                        try:
                            message = await asyncio.wait_for(ws.recv(), timeout=65.0)
                            
                            if self.debug_mode:
                                self._debug_websocket_stats[symbol]['messages_received'] += 1
                                self._debug_websocket_stats[symbol]['last_message_time'] = time.time()
                            
                            await self._handle_single_websocket_message(symbol, message)
                            
                        except asyncio.TimeoutError:
                            if self.debug_mode:
                                print(f"🔧 DEBUG: {symbol} WebSocket timeout - ping...")
                            else:
                                print(f"⏰ {symbol} WebSocket timeout - ping gönderiliyor...")
                            try:
                                await ws.ping()
                                await asyncio.sleep(1)
                            except:
                                print(f"❌ {symbol} WebSocket ping başarısız - yeniden bağlanılıyor...")
                                break
                        except websockets.exceptions.ConnectionClosed:
                            if self.debug_mode:
                                print(f"🔧 DEBUG: {symbol} WebSocket bağlantısı koptu")
                            else:
                                print(f"🔌 {symbol} WebSocket bağlantısı koptu...")
                            break
                        except Exception as e:
                            print(f"❌ {symbol} WebSocket mesaj işleme hatası: {e}")
                            if self.debug_mode:
                                print(f"🔧 DEBUG traceback:\n{traceback.format_exc()}")
                            await asyncio.sleep(1)
                            
            except Exception as e:
                if not self._stop_requested:
                    reconnect_attempts += 1
                    backoff_time = min(5 * reconnect_attempts, 30)
                    if self.debug_mode:
                        print(f"🔧 DEBUG: {symbol} WebSocket bağlantı hatası (deneme {reconnect_attempts}): {e}")
                    else:
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
        """🔧 DEBUG destekli WebSocket mesaj işleme"""
        try:
            if self.debug_mode:
                print(f"\n📨 🔧 DEBUG WEBSOCKET: {symbol}")
                print(f"="*40)
            
            data = json.loads(message)
            kline_data = data.get('k', {})
            
            if self.debug_mode:
                print(f"📊 DEBUG Kline Verisi:")
                print(f"   Mum kapalı: {kline_data.get('x', False)}")
                print(f"   Açılış: {kline_data.get('o', 'N/A')}")
                print(f"   Kapanış: {kline_data.get('c', 'N/A')}")
                print(f"   Yüksek: {kline_data.get('h', 'N/A')}")
                print(f"   Düşük: {kline_data.get('l', 'N/A')}")
                print(f"   Hacim: {kline_data.get('v', 'N/A')}")
                print(f"   İşlem Sayısı: {kline_data.get('n', 'N/A')}")
            
            # Durum güncellemesi
            current_time = time.time()
            if current_time - self._last_status_update > 10:
                await self._update_status_info()
                self._last_status_update = current_time
            
            # Sadece kapanan mumları işle
            if not kline_data.get('x', False):
                if self.debug_mode:
                    print(f"⏭️ DEBUG: {symbol} mum henüz kapanmadı - atlanıyor")
                return
                
            if self.debug_mode:
                print(f"✅ DEBUG: {symbol} yeni mum kapandı - işleniyor...")
                self._debug_websocket_stats[symbol]['klines_processed'] += 1
            else:
                print(f"📊 {symbol} yeni mum kapandı ({settings.TIMEFRAME}) - Kapanış: {kline_data['c']}")
            
            # Kline data güncelleme
            if symbol not in self.multi_klines:
                self.multi_klines[symbol] = []
                if self.debug_mode:
                    print(f"🆕 DEBUG: {symbol} için yeni kline array oluşturuldu")
            
            old_count = len(self.multi_klines[symbol])
            limit = 50 if self.debug_mode else 200
            
            if len(self.multi_klines[symbol]) >= limit:
                self.multi_klines[symbol].pop(0)
                
            new_kline = [
                kline_data[key] for key in ['t','o','h','l','c','v','T','q','n','V','Q']
            ] + ['0']
            
            self.multi_klines[symbol].append(new_kline)
            new_count = len(self.multi_klines[symbol])
            
            if self.debug_mode:
                print(f"📈 DEBUG: {symbol} kline güncellendi ({old_count} -> {new_count} mum, limit: {limit})")
            
            # Bot durum kontrolleri
            if self.debug_mode:
                print(f"🤖 DEBUG Bot Durumu:")
                print(f"   Bot çalışıyor: {self.status['is_running']}")
                print(f"   {symbol} izleniyor: {symbol in self.status.get('symbols', [])}")
                print(f"   İzlenen liste: {self.status.get('symbols', [])}")
                print(f"   Aktif symbol: {self.status.get('active_symbol', 'None')}")
                print(f"   Pozisyon: {self.status.get('position_side', 'None')}")
                print(f"   Kline sayısı: {len(self.multi_klines[symbol])}")
            
            # Temel kontroller
            if not self.status['is_running']:
                if self.debug_mode:
                    print(f"❌ DEBUG: Bot çalışmıyor - analiz atlandı")
                return
                
            if symbol not in self.status.get('symbols', []):
                if self.debug_mode:
                    print(f"❌ DEBUG: {symbol} izlenen listede değil - analiz atlandı")
                return
            
            # Yeterli veri kontrolü
            min_data = 30 if self.debug_mode else 200
            if len(self.multi_klines[symbol]) < min_data:
                if self.debug_mode:
                    print(f"⚠️ DEBUG: {symbol} yetersiz veri ({len(self.multi_klines[symbol])}/{min_data})")
                return
                
            if self.debug_mode:
                print(f"✅ DEBUG: {symbol} analiz için hazır - veri yeterli")
            
            # 🎯 SİNYAL ANALİZİ
            if self.debug_mode:
                print(f"\n🔍 DEBUG SİNYAL ANALİZİ BAŞLIYOR: {symbol}")
                print(f"-" * 30)
                self._debug_last_analysis_time[symbol] = time.time()
            
            # Strateji analizi
            signal = trading_strategy.analyze_klines(self.multi_klines[symbol], symbol)
            
            if self.debug_mode:
                print(f"🎯 DEBUG ANALİZ SONUCU: {symbol} -> {signal}")
                
                # Sinyal geçmişini takip et
                if symbol not in self._debug_signal_history:
                    self._debug_signal_history[symbol] = []
                self._debug_signal_history[symbol].append({
                    'time': datetime.now().isoformat(),
                    'signal': signal,
                    'price': float(kline_data['c'])
                })
                
                # Son 10 sinyali tut
                if len(self._debug_signal_history[symbol]) > 10:
                    self._debug_signal_history[symbol] = self._debug_signal_history[symbol][-10:]
                
                if signal != "HOLD":
                    self._debug_websocket_stats[symbol]['signals_generated'] += 1
                    print(f"🚀 DEBUG: {symbol} AKTİF SİNYAL ÜRETİLDİ! ({signal})")
                    print(f"📊 DEBUG: Toplam sinyal sayısı: {self._debug_websocket_stats[symbol]['signals_generated']}")
            
            # Önceki sinyal ile karşılaştırma
            previous_signal = self.status["last_signals"].get(symbol, "HOLD")
            
            if self.debug_mode:
                print(f"🔄 DEBUG Sinyal Karşılaştırma:")
                print(f"   Önceki: {previous_signal}")
                print(f"   Yeni: {signal}")
                print(f"   Değişti mi: {signal != previous_signal}")
            
            if signal != previous_signal:
                if signal == "HOLD":
                    self.status["filtered_signals_count"] += 1
                    if self.debug_mode:
                        print(f"🛡️ DEBUG: {symbol} sinyal HOLD'a dönüştü - toplam filtre: {self.status['filtered_signals_count']}")
                    else:
                        print(f"🛡️ {symbol} sinyal GELİŞMİŞ filtreler tarafından engellendi - toplam: {self.status['filtered_signals_count']}")
                else:
                    if self.debug_mode:
                        print(f"🎯 DEBUG: {symbol} SİNYAL DEĞİŞTİ: {previous_signal} -> {signal}")
                    else:
                        print(f"🎯 {symbol} KALİTELİ sinyal onaylandı: {previous_signal} -> {signal}")
            
            self.status["last_signals"][symbol] = signal
            
            if self.debug_mode:
                print(f"📝 DEBUG: {symbol} son sinyal güncellendi -> {signal}")
            else:
                print(f"🔍 {symbol} gelişmiş analiz sonucu: {signal}")

            # Pozisyon yönetimi
            if self.debug_mode:
                print(f"\n🎭 DEBUG POZİSYON YÖNETİMİ SİMÜLASYONU")
                print(f"-" * 35)
                await self._debug_position_logic_simulation(symbol, signal)
            else:
                await self._handle_enhanced_multi_coin_position_logic(symbol, signal)
                
            if self.debug_mode:
                print(f"="*40)
                print(f"✅ DEBUG: {symbol} WebSocket işlem tamamlandı")
                print(f"="*40)
                
        except Exception as e:
            print(f"❌ {symbol} WebSocket mesaj işlenirken hata: {e}")
            if self.debug_mode:
                print(f"🔧 DEBUG Full Traceback:\n{traceback.format_exc()}")

    async def _debug_position_logic_simulation(self, symbol: str, signal: str):
        """🎭 DEBUG: Pozisyon mantığı simülasyonu - gerçek işlem yapmaz"""
        current_active = self.status.get("active_symbol")
        current_side = self.status.get("position_side")
        
        print(f"🎭 DEBUG Pozisyon Simülasyonu:")
        print(f"   Mevcut aktif symbol: {current_active}")
        print(f"   Mevcut pozisyon: {current_side}")
        print(f"   Gelen sinyal: {signal}")
        
        if signal == "HOLD":
            print(f"⚪ DEBUG: {symbol} HOLD sinyali - işlem yapılmayacak")
            return
        
        # DURUM 1: Hiç pozisyon yok
        if not current_active and not current_side:
            print(f"✅ DEBUG: {symbol} yeni pozisyon açmaya uygun!")
            print(f"💡 DEBUG SİMÜLASYON: {symbol} {signal} pozisyonu açılacaktı")
            print(f"   -> Entry fiyat: {self.multi_klines[symbol][-1][4] if symbol in self.multi_klines else 'N/A'}")
            print(f"   -> TP/SL hesaplanacaktı")
            print(f"   -> Risk yönetimi uygulanacaktı")
            
        # DURUM 2: Aynı symbol, ters sinyal
        elif current_active == symbol and current_side != signal:
            print(f"🔄 DEBUG: {symbol} pozisyon değişimi gerekli!")
            print(f"💡 DEBUG SİMÜLASYON: {current_side} -> {signal} pozisyon değişimi yapılacaktı")
            print(f"   -> Mevcut pozisyon kapatılacaktı")
            print(f"   -> Yeni {signal} pozisyonu açılacaktı")
            
        # DURUM 3: Farklı symbol
        elif current_active and current_active != symbol:
            print(f"⚠️ DEBUG: {current_active} aktif, {symbol} beklemede")
            print(f"💡 DEBUG SİMÜLASYON: Coin değişimi değerlendirilecekti")
            print(f"   -> Mevcut {current_active} pozisyonu analiz edilecekti")
            print(f"   -> Risk/reward karşılaştırması yapılacaktı")
            
        # DURUM 4: Aynı sinyal
        elif current_active == symbol and current_side == signal:
            print(f"📊 DEBUG: {symbol} aynı yönde sinyal - mevcut pozisyon devam")
            print(f"💡 DEBUG SİMÜLASYON: İşlem yapılmayacaktı")
        
        print(f"🎭 DEBUG Simülasyon tamamlandı")

    async def stop(self):
        """Bot durdurma - DEBUG bilgileri ile"""
        self._stop_requested = True
        if self.status["is_running"]:
            if self.debug_mode:
                print("\n🔧 DEBUG BOT DURDURULUYOR...")
                print("="*50)
                self._print_debug_summary()
                print("="*50)
            else:
                print("🛑 Gelişmiş multi-coin bot durduruluyor...")
            
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
            if self.status.get("position_monitor_active") and not self.debug_mode:
                print("🛡️ Otomatik TP/SL monitoring durduruluyor...")
                await position_manager.stop_monitoring()
                self.status["position_monitor_active"] = False
            
            # Son temizlik (debug modda atla)
            if not self.debug_mode and self.status.get("symbols"):
                print(f"🧹 Bot durduruluyor - tüm symboller için son yetim emir temizliği...")
                for symbol in self.status["symbols"]:
                    try:
                        await binance_client.cancel_all_orders_safe(symbol)
                        await asyncio.sleep(0.1)
                    except Exception as final_cleanup_error:
                        print(f"⚠️ {symbol} son temizlik hatası: {final_cleanup_error}")
            
            self.status.update({
                "is_running": False, 
                "symbols": [],
                "active_symbol": None,
                "status_message": "Bot durduruldu." + (" (DEBUG MODU)" if self.debug_mode else ""),
                "account_balance": 0.0,
                "position_pnl": 0.0,
                "order_size": 0.0,
                "position_monitor_active": False,
                "last_signals": {},
                "signal_filters_active": False,
                "filtered_signals_count": 0,
                "current_timeframe": settings.TIMEFRAME,
                "risk_management_active": False
            })
            
            print(self.status["status_message"])
            await binance_client.close()

    def _print_debug_summary(self):
        """🔧 DEBUG özeti yazdır"""
        print("📊 DEBUG ÖZET RAPORU:")
        
        if self._debug_websocket_stats:
            print("\n🌐 WebSocket İstatistikleri:")
            for symbol, stats in self._debug_websocket_stats.items():
                print(f"   {symbol}:")
                print(f"     📨 Mesaj: {stats['messages_received']}")
                print(f"     📊 İşlenen mum: {stats['klines_processed']}")
                print(f"     🎯 Üretilen sinyal: {stats['signals_generated']}")
                print(f"     🔄 Bağlantı denemesi: {stats['connection_attempts']}")
        
        if self._debug_signal_history:
            print("\n🎯 Son Sinyal Geçmişi:")
            for symbol, history in self._debug_signal_history.items():
                print(f"   {symbol}: {len(history)} sinyal kaydı")
                if history:
                    last = history[-1]
                    print(f"     Son: {last['signal']} @ {last['price']} ({last['time'][:19]})")
        
        print(f"\n📈 Kline Veri Durumu:")
        for symbol, klines in self.multi_klines.items():
            print(f"   {symbol}: {len(klines)} mum")
        
        print(f"\n🔧 DEBUG süreci tamamlandı!")

    # Geri kalan metodlar aynen korunuyor...
    async def _handle_enhanced_multi_coin_position_logic(self, signal_symbol: str, signal: str):
        """Gelişmiş multi-coin pozisyon yönetim mantığı"""
        if self.debug_mode:
            return  # Debug modda gerçek pozisyon yönetimi yapma
            
        try:
            current_active_symbol = self.status.get("active_symbol")
            current_position_side = self.status.get("position_side")
            
            if not await self._check_risk_management():
                print(f"🚫 Risk yönetimi: Yeni pozisyon açılamaz")
                return
            
            if not current_active_symbol and not current_position_side and signal != "HOLD":
                print(f"🚀 Yeni kaliteli pozisyon fırsatı: {signal_symbol} -> {signal}")
                await self._open_new_enhanced_position(signal_symbol, signal)
                return
            
            if (current_active_symbol == signal_symbol and 
                current_position_side and 
                signal != "HOLD" and 
                signal != current_position_side):
                print(f"🔄 {signal_symbol} kaliteli ters sinyal geldi: {current_position_side} -> {signal}")
                await self._flip_enhanced_position(signal_symbol, signal)
                return
            
            if (current_active_symbol and 
                current_active_symbol != signal_symbol and 
                current_position_side and 
                signal != "HOLD"):
                
                if await self._should_switch_position(current_active_symbol, signal_symbol, signal):
                    print(f"💡 Daha iyi fırsat: {signal_symbol} -> {signal} (Mevcut: {current_active_symbol})")
                    await self._switch_to_new_enhanced_coin(current_active_symbol, signal_symbol, signal)
                return
            
            if current_active_symbol and current_position_side:
                open_positions = await binance_client.get_open_positions(current_active_symbol, use_cache=True)
                if not open_positions:
                    print(f"✅ {current_active_symbol} pozisyonu SL/TP ile kapandı")
                    pnl = await binance_client.get_last_trade_pnl(current_active_symbol)
                    
                    trading_strategy.update_trade_result(current_active_symbol, pnl)
                    
                    firebase_manager.log_trade({
                        "symbol": current_active_symbol, 
                        "pnl": pnl, 
                        "status": "CLOSED_BY_SL_TP", 
                        "timestamp": datetime.now(timezone.utc),
                        "timeframe": settings.TIMEFRAME,
                        "risk_reward_ratio": settings.get_risk_reward_ratio()
                    })
                    
                    self.status["active_symbol"] = None
                    self.status["position_side"] = None
                    self.status["daily_pnl"] += pnl
                    
                    print(f"🧹 {current_active_symbol} pozisyon kapandı - yetim emir temizliği yapılıyor...")
                    await binance_client.cancel_all_orders_safe(current_active_symbol)
                    await self._calculate_dynamic_order_size()
                    
                    if signal != "HOLD":
                        print(f"🚀 Pozisyon kapandıktan sonra hemen yeni fırsat: {signal_symbol} -> {signal}")
                        await self._open_new_enhanced_position(signal_symbol, signal)
                        
        except Exception as e:
            print(f"❌ Gelişmiş multi-coin pozisyon mantığı hatası: {e}")

    async def _check_risk_management(self) -> bool:
        """Risk yönetimi kontrolleri"""
        try:
            total_daily_positions = sum(trading_strategy.daily_positions.values())
            if total_daily_positions >= settings.MAX_DAILY_POSITIONS:
                print(f"🚫 Günlük pozisyon limiti aşıldı: {total_daily_positions}/{settings.MAX_DAILY_POSITIONS}")
                return False
            
            total_daily_loss = sum(trading_strategy.daily_loss.values())
            current_balance = await binance_client.get_account_balance(use_cache=True)
            max_daily_loss = current_balance * settings.MAX_DAILY_LOSS_PERCENT
            
            if total_daily_loss >= max_daily_loss:
                print(f"🚫 Günlük kayıp limiti aşıldı: {total_daily_loss:.2f}/{max_daily_loss:.2f} USDT")
                return False
            
            return True
            
        except Exception as e:
            print(f"⚠️ Risk yönetimi kontrolü hatası: {e}")
            return True

    async def _should_switch_position(self, current_symbol: str, new_symbol: str, new_signal: str) -> bool:
        """Pozisyon değişimi kontrol"""
        try:
            current_pnl = await binance_client.get_position_pnl(current_symbol, use_cache=True)
            
            if current_pnl > 0:
                print(f"💰 {current_symbol} karlı ({current_pnl:.2f}), pozisyon değiştirme yapılmayacak")
                return False
            
            current_consecutive_losses = trading_strategy.consecutive_losses.get(current_symbol, 0)
            new_consecutive_losses = trading_strategy.consecutive_losses.get(new_symbol, 0)
            
            if current_consecutive_losses > new_consecutive_losses:
                print(f"📉 {current_symbol} ardışık kayıp yüksek ({current_consecutive_losses}), {new_symbol} tercih edildi")
                return True
            
            return False
            
        except Exception as e:
            print(f"⚠️ Pozisyon değişimi kontrolü hatası: {e}")
            return False

    # Diğer pozisyon yönetimi metodları aynı kalır...
    async def _open_new_enhanced_position(self, symbol: str, signal: str):
        """Yeni pozisyon açma"""
        try:
            print(f"🎯 {symbol} için yeni {signal} pozisyonu açılıyor... (TF: {settings.TIMEFRAME})")
            
            print(f"🧹 {symbol} pozisyon öncesi yetim emir temizliği...")
            await binance_client.cancel_all_orders_safe(symbol)
            await asyncio.sleep(0.3)
            
            dynamic_order_size = await self._calculate_dynamic_order_size()
            
            side = "BUY" if signal == "LONG" else "SELL"
            price = await binance_client.get_market_price(symbol)
            if not price:
                print(f"❌ {symbol} için fiyat alınamadı.")
                return False
                
            quantity = self._format_quantity(symbol, (dynamic_order_size * settings.LEVERAGE) / price)
            if quantity <= 0:
                print(f"❌ {symbol} için hesaplanan miktar çok düşük.")
                return False

            order = await binance_client.create_market_order_with_sl_tp(
                symbol, side, quantity, price, self.price_precision.get(symbol, 2)
            )
            
            if order:
                self.status["active_symbol"] = symbol
                self.status["position_side"] = signal
                self.status["daily_positions"] += 1
                
                rr_ratio = settings.get_risk_reward_ratio()
                sl_percent = settings.STOP_LOSS_PERCENT * 100
                tp_percent = settings.TAKE_PROFIT_PERCENT * 100
                
                self.status["status_message"] = (f"YENİ {signal} POZİSYONU: {symbol} @ {price} "
                                                f"(RR: 1:{rr_ratio:.1f} | SL:%{sl_percent:.2f} TP:%{tp_percent:.2f} | "
                                                f"TF: {settings.TIMEFRAME})")
                print(f"✅ {self.status['status_message']}")
                
                try:
                    if hasattr(binance_client, '_cached_positions'):
                        binance_client._cached_positions.clear()
                    if hasattr(binance_client, '_last_position_check'):
                        binance_client._last_position_check.clear()
                except:
                    pass
                    
                await asyncio.sleep(2)
                print(f"🛡️ {symbol} yeni pozisyon otomatik TP/SL sisteme bildiriliyor...")
                await position_manager.manual_scan_symbol(symbol)
                return True
            else:
                print(f"❌ {symbol} pozisyonu açılamadı.")
                await binance_client.force_cleanup_orders(symbol)
                return False
                
        except Exception as e:
            print(f"❌ {symbol} yeni pozisyon açma hatası: {e}")
            await binance_client.force_cleanup_orders(symbol)
            return False

    async def _flip_enhanced_position(self, symbol: str, new_signal: str):
        """Pozisyon çevirme"""
        try:
            print(f"🧹 {symbol} pozisyon değişimi öncesi yetim emir temizliği...")
            await binance_client.cancel_all_orders_safe(symbol)
            await asyncio.sleep(0.2)
            
            open_positions = await binance_client.get_open_positions(symbol, use_cache=False)
            if open_positions:
                position = open_positions[0]
                position_amt = float(position['positionAmt'])
                side_to_close = 'SELL' if position_amt > 0 else 'BUY'
                print(f"--> Ters kaliteli sinyal geldi. Mevcut {self.status['position_side']} pozisyonu kapatılıyor...")
                
                pnl = await binance_client.get_last_trade_pnl(symbol)
                trading_strategy.update_trade_result(symbol, pnl)
                
                firebase_manager.log_trade({
                    "symbol": symbol, 
                    "pnl": pnl, 
                    "status": "CLOSED_BY_FLIP", 
                    "timestamp": datetime.now(timezone.utc),
                    "timeframe": settings.TIMEFRAME,
                    "risk_reward_ratio": settings.get_risk_reward_ratio()
                })

                self.status["daily_pnl"] += pnl

                close_result = await binance_client.close_position(symbol, position_amt, side_to_close)
                if not close_result:
                    print("❌ Pozisyon kapatma başarısız - yeni pozisyon açılmayacak")
                    return
                    
                await asyncio.sleep(1)

            success = await self._open_new_enhanced_position(symbol, new_signal)
            if not success:
                self.status["active_symbol"] = None
                self.status["position_side"] = None
                
        except Exception as e:
            print(f"❌ {symbol} gelişmiş pozisyon değiştirme hatası: {e}")
            try:
                await binance_client.force_cleanup_orders(symbol)
            except:
                pass
            self.status["active_symbol"] = None
            self.status["position_side"] = None

    async def _switch_to_new_enhanced_coin(self, current_symbol: str, new_symbol: str, new_signal: str):
        """Farklı coin'e geçiş"""
        try:
            print(f"🔄 Gelişmiş coin değişimi: {current_symbol} -> {new_symbol} ({new_signal})")
            
            open_positions = await binance_client.get_open_positions(current_symbol, use_cache=False)
            if open_positions:
                position = open_positions[0]
                position_amt = float(position['positionAmt'])
                side_to_close = 'SELL' if position_amt > 0 else 'BUY'
                
                print(f"📉 {current_symbol} pozisyonu kapatılıyor (coin değişimi)...")
                
                pnl = await binance_client.get_last_trade_pnl(current_symbol)
                trading_strategy.update_trade_result(current_symbol, pnl)
                
                firebase_manager.log_trade({
                    "symbol": current_symbol, 
                    "pnl": pnl, 
                    "status": "CLOSED_FOR_COIN_SWITCH", 
                    "timestamp": datetime.now(timezone.utc),
                    "timeframe": settings.TIMEFRAME,
                    "risk_reward_ratio": settings.get_risk_reward_ratio(),
                    "switched_to": new_symbol
                })

                self.status["daily_pnl"] += pnl

                close_result = await binance_client.close_position(current_symbol, position_amt, side_to_close)
                if not close_result:
                    print(f"❌ {current_symbol} pozisyon kapatma başarısız - coin değişimi iptal")
                    return
                    
                await asyncio.sleep(1)

            success = await self._open_new_enhanced_position(new_symbol, new_signal)
            if not success:
                print(f"❌ {new_symbol} yeni pozisyon açılamadı")
                self.status["active_symbol"] = None
                self.status["position_side"] = None
                
        except Exception as e:
            print(f"❌ Gelişmiş coin değişimi hatası: {e}")
            try:
                await binance_client.force_cleanup_orders(current_symbol)
                await binance_client.force_cleanup_orders(new_symbol)
            except:
                pass
            self.status["active_symbol"] = None
            self.status["position_side"] = None

    async def _update_status_info(self):
        """Durum bilgilerini güncelle"""
        try:
            if self.status["is_running"]:
                self.status["account_balance"] = await binance_client.get_account_balance(use_cache=True)
                if self.status["active_symbol"] and self.status["position_side"]:
                    self.status["position_pnl"] = await binance_client.get_position_pnl(
                        self.status["active_symbol"], use_cache=True
                    )
                else:
                    self.status["position_pnl"] = 0.0
                
                await self._calculate_dynamic_order_size()
                
                monitor_status = position_manager.get_status()
                self.status["position_monitor_active"] = monitor_status["is_running"]
                self.status["daily_positions"] = sum(trading_strategy.daily_positions.values())
                
        except Exception as e:
            if self.debug_mode:
                print(f"🔧 DEBUG: Durum güncelleme hatası: {e}")
            else:
                print(f"Durum güncelleme hatası: {e}")

    def _format_quantity(self, symbol: str, quantity: float):
        precision = self.quantity_precision.get(symbol, 0)
        if precision == 0:
            return math.floor(quantity)
        factor = 10 ** precision
        return math.floor(quantity * factor) / factor

    def get_multi_status(self):
        """Multi-coin bot durumunu döndür - DEBUG bilgileri ile"""
        base_status = {
            "is_running": self.status["is_running"],
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
            "current_timeframe": self.status["current_timeframe"],
            "daily_pnl": self.status["daily_pnl"],
            "daily_positions": self.status["daily_positions"],
            "risk_management_active": self.status["risk_management_active"],
            "filter_status": {
                "trend_filter": settings.TREND_FILTER_ENABLED,
                "momentum_filter": settings.MOMENTUM_FILTER_ENABLED,
                "trend_strength_filter": settings.TREND_STRENGTH_FILTER_ENABLED,
                "price_movement_filter": settings.MIN_PRICE_MOVEMENT_ENABLED,
                "rsi_filter": settings.RSI_FILTER_ENABLED,
                "cooldown_filter": settings.SIGNAL_COOLDOWN_ENABLED,
                "volatility_filter": settings.VOLATILITY_FILTER_ENABLED,
                "volume_filter": settings.VOLUME_FILTER_ENABLED
            },
            "risk_management": {
                "risk_reward_ratio": settings.get_risk_reward_ratio(),
                "stop_loss_percent": settings.STOP_LOSS_PERCENT * 100,
                "take_profit_percent": settings.TAKE_PROFIT_PERCENT * 100,
                "max_daily_positions": settings.MAX_DAILY_POSITIONS,
                "max_daily_loss_percent": settings.MAX_DAILY_LOSS_PERCENT * 100,
                "consecutive_losses": {symbol: trading_strategy.consecutive_losses.get(symbol, 0) 
                                     for symbol in self.status["symbols"]}
            }
        }
        
        # DEBUG bilgileri ekle
        if self.debug_mode:
            base_status["debug_mode"] = True
            base_status["debug_stats"] = {
                "websocket_stats": self._debug_websocket_stats,
                "signal_history": {k: len(v) for k, v in self._debug_signal_history.items()},
                "kline_counts": {k: len(v) for k, v in self.multi_klines.items()},
                "last_analysis_times": self._debug_last_analysis_time
            }
        
        return base_status

    # Utility metodlar aynı...
    def get_available_timeframes(self):
        return list(settings.TIMEFRAME_SETTINGS.keys())
    
    async def change_timeframe(self, timeframe: str):
        if self.status["is_running"]:
            return {
                "success": False, 
                "message": "Bot çalışırken zaman dilimi değiştirilemez"
            }
        
        if self.set_timeframe(timeframe):
            return {
                "success": True,
                "message": f"Zaman dilimi {timeframe} olarak ayarlandı",
                "new_settings": {
                    "timeframe": settings.TIMEFRAME,
                    "stop_loss_percent": settings.STOP_LOSS_PERCENT * 100,
                    "take_profit_percent": settings.TAKE_PROFIT_PERCENT * 100,
                    "risk_reward_ratio": settings.get_risk_reward_ratio()
                }
            }
        else:
            return {"success": False, "message": f"Geçersiz zaman dilimi: {timeframe}"}

    async def add_symbol(self, symbol: str):
        """Symbol ekleme"""
        if not self.status["is_running"]:
            return {"success": False, "message": "Bot çalışmıyor"}
            
        if symbol in self.status["symbols"]:
            return {"success": False, "message": f"{symbol} zaten izleniyor"}
            
        try:
            symbol_info = await binance_client.get_symbol_info(symbol)
            if not symbol_info:
                return {"success": False, "message": f"{symbol} için borsa bilgileri alınamadı"}
            
            self.quantity_precision[symbol] = self._get_precision_from_filter(symbol_info, 'LOT_SIZE', 'stepSize')
            self.price_precision[symbol] = self._get_precision_from_filter(symbol_info, 'PRICE_FILTER', 'tickSize')
            
            limit = 50 if self.debug_mode else 200
            klines = await binance_client.get_historical_klines(symbol, settings.TIMEFRAME, limit=limit)
            if not klines:
                return {"success": False, "message": f"{symbol} için geçmiş veri alınamadı"}
            
            self.multi_klines[symbol] = klines
            
            if not self.debug_mode:
                await binance_client.set_leverage(symbol, settings.LEVERAGE)
            
            self.status["symbols"].append(symbol)
            self.status["last_signals"][symbol] = "HOLD"
            
            task = asyncio.create_task(self._single_websocket_loop(symbol))
            self._websocket_tasks.append(task)
            
            if self.debug_mode:
                print(f"🔧 DEBUG: {symbol} eklendi ({limit} mum)")
            else:
                print(f"✅ {symbol} bot'a eklendi ({settings.TIMEFRAME})")
            return {"success": True, "message": f"{symbol} başarıyla eklendi"}
            
        except Exception as e:
            return {"success": False, "message": f"{symbol} eklenirken hata: {e}"}

    async def remove_symbol(self, symbol: str):
        """Symbol çıkarma"""
        if not self.status["is_running"]:
            return {"success": False, "message": "Bot çalışmıyor"}
            
        if symbol not in self.status["symbols"]:
            return {"success": False, "message": f"{symbol} zaten izlenmiyor"}
            
        if self.status["active_symbol"] == symbol:
            return {"success": False, "message": f"{symbol} şu anda aktif pozisyonda"}
            
        try:
            self.status["symbols"].remove(symbol)
            if symbol in self.status["last_signals"]:
                del self.status["last_signals"][symbol]
            if symbol in self.multi_klines:
                del self.multi_klines[symbol]
            if symbol in self.quantity_precision:
                del self.quantity_precision[symbol]
            if symbol in self.price_precision:
                del self.price_precision[symbol]
            
            if symbol in self._websocket_connections:
                try:
                    await self._websocket_connections[symbol].close()
                except:
                    pass
                del self._websocket_connections[symbol]
            
            if self.debug_mode:
                # Debug verilerini temizle
                if symbol in self._debug_websocket_stats:
                    del self._debug_websocket_stats[symbol]
                if symbol in self._debug_signal_history:
                    del self._debug_signal_history[symbol]
                if symbol in self._debug_last_analysis_time:
                    del self._debug_last_analysis_time[symbol]
                print(f"🔧 DEBUG: {symbol} çıkarıldı ve debug verileri temizlendi")
            else:
                print(f"✅ {symbol} bot'tan çıkarıldı")
            
            return {"success": True, "message": f"{symbol} başarıyla çıkarıldı"}
            
        except Exception as e:
            return {"success": False, "message": f"{symbol} çıkarılırken hata: {e}"}

    # Position management metodları aynı...
    async def scan_all_positions(self):
        if not self.status["is_running"]:
            return {"success": False, "message": "Bot çalışmıyor"}
            
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
        try:
            if self.debug_mode:
                print(f"🔧 DEBUG: {symbol} için TP/SL kontrolü simülasyonu...")
                return {
                    "success": True,
                    "symbol": symbol,
                    "message": f"{symbol} DEBUG TP/SL kontrolü simülasyonu tamamlandı"
                }
            else:
                print(f"🎯 {symbol} için manuel TP/SL kontrolü...")
                success = await position_manager.manual_scan_symbol(symbol)
                
                return {
                    "success": success,
                    "symbol": symbol,
                    "message": f"{symbol} için TP/SL kontrolü tamamlandı"
                }
        except Exception as e:
            return {"success": False, "message": f"{symbol} kontrolü hatası: {e}"}

    # 🔧 DEBUG özel metodlar
    def get_debug_status(self):
        """DEBUG için detaylı durum bilgisi"""
        debug_info = {
            "debug_mode": self.debug_mode,
            "websocket_connections": len(self._websocket_connections),
            "websocket_active_symbols": list(self._websocket_connections.keys()),
            "klines_data_count": {symbol: len(klines) for symbol, klines in self.multi_klines.items()},
            "last_signals": self.status.get("last_signals", {}),
            "bot_running": self.status["is_running"],
            "monitored_symbols": self.status.get("symbols", []),
            "active_symbol": self.status.get("active_symbol"),
            "position_side": self.status.get("position_side"),
            "filtered_signals_count": self.status.get("filtered_signals_count", 0),
            "debug_stats": {
                "websocket_stats": self._debug_websocket_stats,
                "signal_history": {k: len(v) for k, v in self._debug_signal_history.items()},
                "last_analysis_times": self._debug_last_analysis_time
            }
        }
        
        return debug_info

    def print_debug_status(self):
        """DEBUG durumunu yazdır"""
        debug = self.get_debug_status()
        
        print(f"\n{'='*50}")
        print("🔧 BOT DEBUG DURUMU")
        print(f"{'='*50}")
        print(f"🤖 Bot Çalışıyor: {debug['bot_running']}")
        print(f"🔧 Debug Modu: {debug['debug_mode']}")
        print(f"🌐 WebSocket Bağlantı: {debug['websocket_connections']}")
        print(f"📊 İzlenen Symboller: {debug['monitored_symbols']}")
        print(f"🎯 Aktif Symbol: {debug['active_symbol']}")
        print(f"📈 Pozisyon: {debug['position_side']}")
        print(f"🛡️ Filtrelenen Sinyal: {debug['filtered_signals_count']}")
        
        print(f"\n📊 KLINE VERİ DURUMLARI:")
        for symbol, count in debug['klines_data_count'].items():
            print(f"   {symbol}: {count} mum")
            
        print(f"\n🎯 SON SİNYALLER:")
        for symbol, signal in debug['last_signals'].items():
            print(f"   {symbol}: {signal}")
            
        if debug['debug_stats']['websocket_stats']:
            print(f"\n🌐 WEBSOCKET İSTATİSTİKLERİ:")
            for symbol, stats in debug['debug_stats']['websocket_stats'].items():
                print(f"   {symbol}:")
                print(f"     📨 Mesaj: {stats['messages_received']}")
                print(f"     📊 Mum: {stats['klines_processed']}")
                print(f"     🎯 Sinyal: {stats['signals_generated']}")
                
        print(f"{'='*50}")

bot_core = BotCore()
