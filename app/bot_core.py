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
            "symbol": None, 
            "position_side": None, 
            "status_message": "Bot başlatılmadı.",
            "account_balance": 0.0,
            "position_pnl": 0.0,
            "order_size": 0.0,
            "dynamic_sizing": True,
            "position_monitor_active": False
        }
        self.klines = []
        self._stop_requested = False
        self.quantity_precision = 0
        self.price_precision = 0
        self._last_status_update = 0
        self._websocket_reconnect_attempts = 0
        self._max_reconnect_attempts = 10

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
            
            min_size = 5.0
            max_size = 1000.0
            
            final_size = max(min(dynamic_size, max_size), min_size)
            
            print(f"💰 Dinamik pozisyon hesaplama:")
            print(f"   Mevcut bakiye: {current_balance:.2f} USDT")
            print(f"   %90'ı: {dynamic_size:.2f} USDT")
            print(f"   Kullanılacak tutar: {final_size:.2f} USDT")
            
            self.status["order_size"] = final_size
            return final_size
            
        except Exception as e:
            print(f"Dinamik pozisyon hesaplama hatası: {e}")
            fallback_size = 35.0
            self.status["order_size"] = fallback_size
            return fallback_size

    async def start(self, symbol: str):
        if self.status["is_running"]:
            print("Bot zaten çalışıyor.")
            return
            
        self._stop_requested = False
        self._websocket_reconnect_attempts = 0
        self.status.update({
            "is_running": True, 
            "symbol": symbol, 
            "position_side": None, 
            "status_message": f"{symbol} için başlatılıyor...",
            "dynamic_sizing": True,
            "position_monitor_active": False
        })
        print(self.status["status_message"])
        
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
            print("2. 🧹 İlk yetim emir temizliği yapılıyor...")
            try:
                cleanup_result = await binance_client.cancel_all_orders_safe(symbol)
                if cleanup_result:
                    print("✅ İlk yetim emir temizliği başarılı")
                else:
                    print("⚠️ İlk yetim emir temizliği eksik - devam ediliyor")
            except Exception as cleanup_error:
                print(f"⚠️ İlk temizlik hatası: {cleanup_error} - devam ediliyor")
            
            # 3. Hesap bakiyesi kontrolü
            print("3. Hesap bakiyesi kontrol ediliyor...")
            try:
                self.status["account_balance"] = await binance_client.get_account_balance(use_cache=False)
                initial_order_size = await self._calculate_dynamic_order_size()
                print(f"✅ Hesap bakiyesi: {self.status['account_balance']} USDT")
                print(f"✅ İlk pozisyon boyutu: {initial_order_size} USDT")
            except Exception as balance_error:
                print(f"❌ Bakiye kontrol hatası: {balance_error}")
                raise balance_error
            
            # 4. Symbol bilgileri
            print(f"4. {symbol} sembol bilgileri alınıyor...")
            try:
                symbol_info = await binance_client.get_symbol_info(symbol)
                if not symbol_info:
                    error_msg = f"❌ {symbol} için borsa bilgileri alınamadı. Sembol doğru mu?"
                    print(error_msg)
                    self.status["status_message"] = error_msg
                    await self.stop()
                    return
                print(f"✅ {symbol} sembol bilgileri alındı")
            except Exception as symbol_error:
                print(f"❌ Symbol bilgisi hatası: {symbol_error}")
                raise symbol_error
                
            # 5. Precision hesaplama
            print("5. Hassasiyet bilgileri hesaplanıyor...")
            try:
                self.quantity_precision = self._get_precision_from_filter(symbol_info, 'LOT_SIZE', 'stepSize')
                self.price_precision = self._get_precision_from_filter(symbol_info, 'PRICE_FILTER', 'tickSize')
                print(f"✅ Miktar Hassasiyeti: {self.quantity_precision}, Fiyat Hassasiyeti: {self.price_precision}")
            except Exception as precision_error:
                print(f"❌ Precision hesaplama hatası: {precision_error}")
                raise precision_error
            
            # 6. Açık pozisyon kontrolü
            print("6. Açık pozisyonlar kontrol ediliyor...")
            try:
                open_positions = await binance_client.get_open_positions(symbol, use_cache=False)
                if open_positions:
                    position = open_positions[0]
                    position_amt = float(position['positionAmt'])
                    if position_amt > 0:
                        self.status["position_side"] = "LONG"
                    elif position_amt < 0:
                        self.status["position_side"] = "SHORT"
                    print(f"⚠️ {symbol} için açık pozisyon tespit edildi: {self.status['position_side']}")
                    print("Mevcut kaldıraçla devam ediliyor...")
                    
                    # Mevcut pozisyon için yetim emirleri temizle
                    print("🧹 Mevcut pozisyon için ekstra yetim emir temizliği...")
                    await binance_client.cancel_all_orders_safe(symbol)
                    
                    # Mevcut pozisyon için TP/SL kontrol et
                    print("🛡️ Mevcut pozisyon için TP/SL kontrolü yapılıyor...")
                    await position_manager.manual_scan_symbol(symbol)
                    
                else:
                    print(f"✅ {symbol} için açık pozisyon yok")
                    # Kaldıraç ayarlama
                    print("7. Kaldıraç ayarlanıyor...")
                    if await binance_client.set_leverage(symbol, settings.LEVERAGE):
                        print(f"✅ Kaldıraç {settings.LEVERAGE}x olarak ayarlandı")
                    else:
                        print("⚠️ Kaldıraç ayarlanamadı, mevcut kaldıraçla devam ediliyor")
            except Exception as position_error:
                print(f"❌ Pozisyon kontrolü hatası: {position_error}")
                raise position_error
                
            # 8. Geçmiş veri çekme
            print("8. Geçmiş mum verileri çekiliyor...")
            try:
                self.klines = await binance_client.get_historical_klines(symbol, settings.TIMEFRAME, limit=50)
                if not self.klines:
                    error_msg = f"❌ {symbol} için geçmiş veri alınamadı"
                    print(error_msg)
                    self.status["status_message"] = error_msg
                    await self.stop()
                    return
                print(f"✅ {len(self.klines)} adet geçmiş mum verisi alındı")
            except Exception as klines_error:
                print(f"❌ Geçmiş veri çekme hatası: {klines_error}")
                raise klines_error
            
            # 9. Pozisyon Monitoring Başlat
            print("9. 🛡️ Otomatik TP/SL monitoring başlatılıyor...")
            try:
                asyncio.create_task(position_manager.start_monitoring())
                self.status["position_monitor_active"] = True
                print("✅ Otomatik TP/SL koruması aktif")
            except Exception as monitor_error:
                print(f"⚠️ Position monitoring başlatılamadı: {monitor_error}")
                
            # 10. WebSocket bağlantısı
            print("10. WebSocket bağlantısı kuruluyor...")
            self.status["status_message"] = f"{symbol} ({settings.TIMEFRAME}) için sinyal bekleniyor... [DİNAMİK SİZING + YETİM EMİR KORUMASII + OTOMATIK TP/SL AKTİF]"
            print(f"✅ {self.status['status_message']}")
            
            await self._start_websocket_loop()
                        
        except Exception as e:
            error_msg = f"❌ Bot başlatılırken beklenmeyen hata: {e}"
            print(error_msg)
            print(f"❌ Full traceback: {traceback.format_exc()}")
            self.status["status_message"] = error_msg
        
        print("Bot durduruluyor...")
        await self.stop()

    async def _start_websocket_loop(self):
        """WebSocket bağlantı döngüsü - otomatik yeniden bağlanma ile"""
        ws_url = f"{settings.WEBSOCKET_URL}/ws/{self.status['symbol'].lower()}@kline_{settings.TIMEFRAME}"
        print(f"WebSocket URL: {ws_url}")
        
        while not self._stop_requested and self._websocket_reconnect_attempts < self._max_reconnect_attempts:
            try:
                async with websockets.connect(
                    ws_url, 
                    ping_interval=30, 
                    ping_timeout=15,
                    close_timeout=10
                ) as ws:
                    print(f"✅ WebSocket bağlantısı kuruldu (Deneme: {self._websocket_reconnect_attempts + 1})")
                    self._websocket_reconnect_attempts = 0
                    
                    while not self._stop_requested:
                        try:
                            message = await asyncio.wait_for(ws.recv(), timeout=65.0)
                            await self._handle_websocket_message(message)
                        except asyncio.TimeoutError:
                            print("WebSocket timeout - bağlantı kontrol ediliyor...")
                            try:
                                await ws.ping()
                                await asyncio.sleep(1)
                            except:
                                print("WebSocket ping başarısız - yeniden bağlanılıyor...")
                                break
                        except websockets.exceptions.ConnectionClosed:
                            print("WebSocket bağlantısı koptu...")
                            break
                        except Exception as e:
                            print(f"WebSocket mesaj işleme hatası: {e}")
                            await asyncio.sleep(1)
                            
            except Exception as e:
                if not self._stop_requested:
                    self._websocket_reconnect_attempts += 1
                    backoff_time = min(5 * self._websocket_reconnect_attempts, 30)
                    print(f"WebSocket bağlantı hatası (Deneme {self._websocket_reconnect_attempts}/{self._max_reconnect_attempts}): {e}")
                    print(f"{backoff_time} saniye sonra yeniden deneniyor...")
                    await asyncio.sleep(backoff_time)
        
        if self._websocket_reconnect_attempts >= self._max_reconnect_attempts:
            print(f"❌ WebSocket maksimum yeniden bağlanma denemesi ({self._max_reconnect_attempts}) aşıldı")
            self.status["status_message"] = "WebSocket bağlantısı kurulamadı - Bot durduruluyor"

    async def stop(self):
        self._stop_requested = True
        if self.status["is_running"]:
            # Position monitoring'i durdur
            if self.status.get("position_monitor_active"):
                print("🛡️ Otomatik TP/SL monitoring durduruluyor...")
                await position_manager.stop_monitoring()
                self.status["position_monitor_active"] = False
            
            # Bot durdururken son temizlik
            if self.status.get("symbol"):
                print(f"🧹 Bot durduruluyor - {self.status['symbol']} için son yetim emir temizliği...")
                try:
                    await binance_client.cancel_all_orders_safe(self.status["symbol"])
                except Exception as final_cleanup_error:
                    print(f"⚠️ Son temizlik hatası: {final_cleanup_error}")
            
            self.status.update({
                "is_running": False, 
                "status_message": "Bot durduruldu.",
                "account_balance": 0.0,
                "position_pnl": 0.0,
                "order_size": 0.0,
                "position_monitor_active": False
            })
            print(self.status["status_message"])
            await binance_client.close()

    async def _handle_websocket_message(self, message: str):
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
                
            print(f"Yeni mum kapandı: {self.status['symbol']} ({settings.TIMEFRAME}) - Kapanış: {kline_data['c']}")
            self.klines.pop(0)
            self.klines.append([
                kline_data[key] for key in ['t','o','h','l','c','v','T','q','n','V','Q']
            ] + ['0'])
            
            # Pozisyon kontrolü
            open_positions = await binance_client.get_open_positions(self.status["symbol"], use_cache=True)
            if self.status["position_side"] is not None and not open_positions:
                print(f"--> Pozisyon SL/TP ile kapandı. Yeni sinyal bekleniyor.")
                pnl = await binance_client.get_last_trade_pnl(self.status["symbol"])
                firebase_manager.log_trade({
                    "symbol": self.status["symbol"], 
                    "pnl": pnl, 
                    "status": "CLOSED_BY_SL_TP", 
                    "timestamp": datetime.now(timezone.utc)
                })
                
                self.status["position_side"] = None
                
                # Pozisyon kapandıktan sonra yetim emir temizliği
                print("🧹 Pozisyon kapandı - yetim emir temizliği yapılıyor...")
                await binance_client.cancel_all_orders_safe(self.status["symbol"])
                
                # Pozisyon kapandıktan sonra yeni bakiye ile order size güncelle
                await self._calculate_dynamic_order_size()

            # Sinyal analizi
            signal = trading_strategy.analyze_klines(self.klines)
            print(f"Strateji analizi sonucu: {signal}")

            # Pozisyon yönetimi
            if signal != "HOLD" and signal != self.status.get("position_side"):
                await self._flip_position(signal)
                
        except Exception as e:
            print(f"WebSocket mesaj işlenirken hata: {e}")

    async def _update_status_info(self):
        """Durum bilgilerini günceller - rate limit korumalı"""
        try:
            if self.status["is_running"]:
                # Cache kullanarak sorgu sayısını azalt
                self.status["account_balance"] = await binance_client.get_account_balance(use_cache=True)
                if self.status["position_side"]:
                    self.status["position_pnl"] = await binance_client.get_position_pnl(
                        self.status["symbol"], use_cache=True
                    )
                else:
                    self.status["position_pnl"] = 0.0
                # Order size'ı dinamik tut
                await self._calculate_dynamic_order_size()
                
                # Position monitor durumunu güncelle
                monitor_status = position_manager.get_status()
                self.status["position_monitor_active"] = monitor_status["is_running"]
                
        except Exception as e:
            print(f"Durum güncelleme hatası: {e}")

    def _format_quantity(self, quantity: float):
        if self.quantity_precision == 0:
            return math.floor(quantity)
        factor = 10 ** self.quantity_precision
        return math.floor(quantity * factor) / factor

    async def _flip_position(self, new_signal: str):
        symbol = self.status["symbol"]
        
        try:
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
                print(f"--> Ters sinyal geldi. Mevcut {self.status['position_side']} pozisyonu kapatılıyor...")
                
                pnl = await binance_client.get_last_trade_pnl(symbol)
                firebase_manager.log_trade({
                    "symbol": symbol, 
                    "pnl": pnl, 
                    "status": "CLOSED_BY_FLIP", 
                    "timestamp": datetime.now(timezone.utc)
                })

                # Pozisyonu kapat
                close_result = await binance_client.close_position(symbol, position_amt, side_to_close)
                if not close_result:
                    print("❌ Pozisyon kapatma başarısız - yeni pozisyon açılmayacak")
                    return
                    
                await asyncio.sleep(1)

            # Dinamik order size hesapla
            print(f"--> Yeni {new_signal} pozisyonu için dinamik boyut hesaplanıyor...")
            dynamic_order_size = await self._calculate_dynamic_order_size()
            
            # Yeni pozisyon açmadan önce son kontrol
            print(f"🧹 {symbol} yeni pozisyon öncesi final yetim emir temizliği...")
            final_cleanup = await binance_client.cancel_all_orders_safe(symbol)
            if not final_cleanup:
                print("⚠️ Final temizlik başarısız - devam ediliyor...")
            
            await asyncio.sleep(0.3)
            
            # Yeni pozisyon aç
            print(f"--> Yeni {new_signal} pozisyonu açılıyor... (Tutar: {dynamic_order_size} USDT)")
            side = "BUY" if new_signal == "LONG" else "SELL"
            price = await binance_client.get_market_price(symbol)
            if not price:
                print("❌ Yeni pozisyon için fiyat alınamadı.")
                return
                
            quantity = self._format_quantity((dynamic_order_size * settings.LEVERAGE) / price)
            if quantity <= 0:
                print("❌ Hesaplanan miktar çok düşük.")
                return

            # YETİM EMİR KORUMASLI pozisyon açma
            order = await binance_client.create_market_order_with_sl_tp(
                symbol, side, quantity, price, self.price_precision
            )
            
            if order:
                self.status["position_side"] = new_signal
                self.status["status_message"] = f"Yeni {new_signal} pozisyonu {price} fiyattan açıldı. (Tutar: {dynamic_order_size:.2f} USDT) [OTOMATIK TP/SL KORUMASII AKTİF]"
                print(f"✅ {self.status['status_message']}")
                
                # Cache temizle
                try:
                    if hasattr(binance_client, '_cached_positions'):
                        binance_client._cached_positions.clear()
                    if hasattr(binance_client, '_last_position_check'):
                        binance_client._last_position_check.clear()
                except Exception as cache_error:
                    print(f"Cache temizleme hatası: {cache_error}")
                    
                # Yeni pozisyon için position manager'a bildir
                await asyncio.sleep(2)
                print("🛡️ Yeni pozisyon otomatik TP/SL sisteme bildiriliyor...")
                await position_manager.manual_scan_symbol(symbol)
                
            else:
                self.status["position_side"] = None
                self.status["status_message"] = "Yeni pozisyon açılamadı."
                print(f"❌ {self.status['status_message']}")
                
                # Pozisyon açılmadıysa da temizlik yap
                print("🧹 Başarısız pozisyon sonrası acil temizlik...")
                await binance_client.force_cleanup_orders(symbol)
                
        except Exception as e:
            print(f"❌ Pozisyon değiştirme hatası: {e}")
            print(f"🧹 Hata sonrası acil yetim emir temizliği...")
            try:
                await binance_client.force_cleanup_orders(symbol)
            except Exception as cleanup_error:
                print(f"⚠️ Acil temizlik de başarısız: {cleanup_error}")
            self.status["position_side"] = None

    # YENİ METODLAR
    async def scan_all_positions(self):
        """Tüm açık pozisyonları manuel tarayıp TP/SL ekle"""
        if not self.status["is_running"]:
            return {"success": False, "message": "Bot çalışmıyor"}
            
        try:
            print("🔍 Manuel pozisyon taraması başlatılıyor...")
            
            # Position manager ile tam tarama yap
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
