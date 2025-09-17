import asyncio
from binance import AsyncClient
from binance.exceptions import BinanceAPIException
from .config import settings
import time
from typing import Optional, Dict, Any

class BinanceClient:
    def __init__(self):
        self.api_key = settings.API_KEY
        self.api_secret = settings.API_SECRET
        self.is_testnet = settings.ENVIRONMENT == "TEST"
        self.client: AsyncClient | None = None
        self.exchange_info = None
        self._last_balance_check = 0
        self._cached_balance = 0.0
        self._last_position_check = {}
        self._cached_positions = {}
        self._rate_limit_delay_time = 0.1  # Minimum delay between requests
        self._debug_enabled = settings.DEBUG_MODE if hasattr(settings, 'DEBUG_MODE') else True
        print(f"Binance İstemcisi başlatılıyor. Ortam: {settings.ENVIRONMENT}")
        
    async def _rate_limit_delay(self):
        """Rate limit koruması için bekleme"""
        await asyncio.sleep(self._rate_limit_delay_time)
        
    async def initialize(self):
        """DÜZELTME: Daha iyi hata yakalama ile"""
        if self.client is None:
            try:
                self.client = await AsyncClient.create(self.api_key, self.api_secret, testnet=self.is_testnet)
                await self._rate_limit_delay()
                
                # Exchange info al ve kontrol et
                self.exchange_info = await self.client.get_exchange_info()
                
                if not self.exchange_info or 'symbols' not in self.exchange_info:
                    raise Exception("Exchange info alınamadı veya geçersiz")
                    
                print("✅ Binance AsyncClient başarıyla başlatıldı.")
                print(f"📊 {len(self.exchange_info['symbols'])} sembol bilgisi yüklendi")
                
                # Test connection
                await self._test_connection()
                
            except BinanceAPIException as e:
                print(f"❌ Binance API Hatası: {e}")
                raise e
            except Exception as e:
                print(f"❌ Binance bağlantı hatası: {e}")
                raise e
                
        return self.client
        
    async def _test_connection(self):
        """Bağlantıyı test et"""
        try:
            await self._rate_limit_delay()
            account_info = await self.client.futures_account()
            
            if account_info:
                total_balance = 0.0
                for asset in account_info['assets']:
                    if asset['asset'] == 'USDT':
                        total_balance = float(asset['walletBalance'])
                        break
                        
                print(f"✅ Hesap bağlantısı test edildi. USDT Bakiye: {total_balance}")
                return True
            else:
                print("⚠️ Hesap bilgileri alınamadı")
                return False
                
        except Exception as e:
            print(f"⚠️ Bağlantı testi başarısız: {e}")
            return False
        
    async def get_symbol_info(self, symbol: str):
        """DÜZELTME: Daha iyi hata yakalama"""
        try:
            if not self.exchange_info:
                print("⚠️ Exchange info bulunamadı, yeniden yükleniyor...")
                await self._rate_limit_delay()
                self.exchange_info = await self.client.get_exchange_info()
                
            if not self.exchange_info or 'symbols' not in self.exchange_info:
                print("❌ Exchange info yüklenemedi")
                return None
                
            for s in self.exchange_info['symbols']:
                if s['symbol'] == symbol:
                    if self._debug_enabled:
                        print(f"✅ {symbol} sembol bilgisi bulundu")
                    return s
                    
            print(f"❌ {symbol} sembol bilgisi bulunamadı")
            return None
            
        except Exception as e:
            print(f"❌ {symbol} sembol bilgisi alınırken hata: {e}")
            return None
        
    async def get_open_positions(self, symbol: str, use_cache: bool = True):
        """DÜZELTME: Açık pozisyonları getirir - gelişmiş cache ve hata yakalama"""
        try:
            current_time = time.time()
            cache_key = symbol
            
            # Cache kontrolü (5 saniye cache)
            if use_cache and cache_key in self._last_position_check:
                if current_time - self._last_position_check[cache_key] < 5:
                    cached_result = self._cached_positions.get(cache_key, [])
                    if self._debug_enabled and cached_result:
                        print(f"💾 {symbol} cache'den pozisyon alındı: {len(cached_result)} pozisyon")
                    return cached_result
            
            await self._rate_limit_delay()
            positions = await self.client.futures_position_information(symbol=symbol)
            
            if not positions:
                print(f"⚠️ {symbol} için pozisyon bilgisi alınamadı")
                return []
                
            open_positions = [p for p in positions if float(p['positionAmt']) != 0]
            
            # Cache güncelle
            self._last_position_check[cache_key] = current_time
            self._cached_positions[cache_key] = open_positions
            
            if self._debug_enabled:
                print(f"📊 {symbol} açık pozisyon sayısı: {len(open_positions)}")
            
            return open_positions
            
        except BinanceAPIException as e:
            if "-1003" in str(e):  # Rate limit hatası
                print(f"⚠️ Rate limit - {symbol} pozisyon kontrolü atlanıyor")
                # Cache'den döndür
                return self._cached_positions.get(symbol, [])
            elif "-2013" in str(e):  # Order does not exist
                print(f"⚠️ {symbol} için emir bulunamadı")
                return []
            else:
                print(f"❌ Hata: {symbol} pozisyon bilgileri alınamadı: {e}")
                return []
        except Exception as e:
            print(f"❌ {symbol} pozisyon sorgusu genel hatası: {e}")
            return []

    async def cancel_all_orders_safe(self, symbol: str):
        """DÜZELTME: Tüm açık emirleri güvenli şekilde iptal eder"""
        try:
            await self._rate_limit_delay()
            open_orders = await self.client.futures_get_open_orders(symbol=symbol)
            if open_orders:
                order_count = len(open_orders)
                if self._debug_enabled:
                    print(f"🧹 {symbol} için {order_count} adet yetim emir temizleniyor...")
                    
                await self._rate_limit_delay()
                result = await self.client.futures_cancel_all_open_orders(symbol=symbol)
                await asyncio.sleep(0.5)
                
                if self._debug_enabled:
                    print(f"✅ {symbol} tüm yetim emirler temizlendi.")
                return True
            else:
                if self._debug_enabled:
                    print(f"✅ {symbol} temizlenecek yetim emir yok.")
                return True
                
        except BinanceAPIException as e:
            if "-1003" in str(e):
                print(f"⚠️ Rate limit - {symbol} emir iptali atlanıyor")
                return False
            elif "-2011" in str(e):
                print(f"✅ {symbol} zaten açık emir yok")
                return True
            else:
                print(f"❌ {symbol} emirler iptal edilirken hata: {e}")
                return False
        except Exception as e:
            print(f"❌ {symbol} emir iptali genel hatası: {e}")
            return False

    async def get_market_price(self, symbol: str):
        """DÜZELTME: Daha iyi hata yakalama ile market fiyatı al"""
        try:
            await self._rate_limit_delay()
            ticker = await self.client.futures_symbol_ticker(symbol=symbol)
            
            if not ticker or 'price' not in ticker:
                print(f"❌ {symbol} için fiyat bilgisi alınamadı")
                return None
                
            price = float(ticker['price'])
            
            if price <= 0:
                print(f"❌ {symbol} için geçersiz fiyat: {price}")
                return None
                
            if self._debug_enabled:
                print(f"💰 {symbol} mevcut fiyat: {price}")
                
            return price
            
        except BinanceAPIException as e:
            if "-1003" in str(e):
                print(f"⚠️ Rate limit - {symbol} fiyat sorgusu atlanıyor")
                return None
            else:
                print(f"❌ Hata: {symbol} fiyatı alınamadı: {e}")
                return None
        except Exception as e:
            print(f"❌ {symbol} fiyat sorgusu genel hatası: {e}")
            return None

    async def get_historical_klines(self, symbol: str, interval: str, limit: int = 100):
        """DÜZELTME: Daha iyi hata yakalama ile geçmiş veri al"""
        try:
            if self._debug_enabled:
                print(f"📊 {symbol} için {limit} adet geçmiş mum verisi çekiliyor...")
                
            await self._rate_limit_delay()
            klines = await self.client.get_historical_klines(symbol, interval, limit=limit)
            
            if not klines:
                print(f"❌ {symbol} için geçmiş veri alınamadı")
                return []
                
            if len(klines) < limit * 0.8:  # %80'inden az veri geldiyse uyar
                print(f"⚠️ {symbol} için beklenen veriden az geldi: {len(klines)}/{limit}")
                
            # Veri formatını kontrol et
            if len(klines) > 0:
                first_kline = klines[0]
                if len(first_kline) < 11:
                    print(f"⚠️ {symbol} kline verisi eksik kolonlar içeriyor")
                    return []
                    
            if self._debug_enabled:
                print(f"✅ {symbol} için {len(klines)} mum verisi alındı")
                
            return klines
            
        except BinanceAPIException as e:
            if "-1003" in str(e):
                print(f"⚠️ Rate limit - {symbol} geçmiş veri atlanıyor")
                return []
            else:
                print(f"❌ Hata: {symbol} geçmiş mum verileri çekilemedi: {e}")
                return []
        except Exception as e:
            print(f"❌ {symbol} geçmiş veri sorgusu genel hatası: {e}")
            return []

    async def set_leverage(self, symbol: str, leverage: int):
        """DÜZELTME: Kaldıraç ayarlama - daha iyi hata yakalama"""
        try:
            # Önce açık pozisyon kontrolü yap
            open_positions = await self.get_open_positions(symbol, use_cache=False)
            if open_positions:
                print(f"⚠️ {symbol} için açık pozisyon mevcut. Kaldıraç değiştirilemez.")
                return False
            
            # Margin tipini cross olarak ayarla
            try:
                await self._rate_limit_delay()
                await self.client.futures_change_margin_type(symbol=symbol, marginType='CROSSED')
                print(f"✅ {symbol} margin tipi CROSSED olarak ayarlandı.")
            except BinanceAPIException as margin_error:
                if "No need to change margin type" in str(margin_error) or "-4046" in str(margin_error):
                    if self._debug_enabled:
                        print(f"💡 {symbol} zaten CROSSED margin modunda.")
                else:
                    print(f"⚠️ {symbol} margin tipi değiştirilemedi: {margin_error}")
            
            # Kaldıracı ayarla
            await self._rate_limit_delay()
            result = await self.client.futures_change_leverage(symbol=symbol, leverage=leverage)
            
            if result and 'leverage' in result:
                actual_leverage = result['leverage']
                print(f"✅ {symbol} kaldıracı {actual_leverage}x olarak ayarlandı.")
                return True
            else:
                print(f"⚠️ {symbol} kaldıraç ayarlama sonucu belirsiz")
                return True  # Başarılı kabul et
                
        except BinanceAPIException as e:
            if "-1003" in str(e):
                print(f"⚠️ Rate limit - {symbol} kaldıraç ayarı atlanıyor")
                return False
            elif "-4028" in str(e):
                print(f"⚠️ {symbol} kaldıraç değeri geçersiz veya çok yüksek")
                return False
            else:
                print(f"❌ Hata: {symbol} kaldıracı ayarlanamadı: {e}")
                return False
        except Exception as e:
            print(f"❌ {symbol} kaldıraç ayarlama genel hatası: {e}")
            return False

    async def create_market_order_with_sl_tp(self, symbol: str, side: str, quantity: float, entry_price: float, price_precision: int):
        """
        DÜZELTME: Piyasa emri ile birlikte hem Stop Loss hem de Take Profit emri oluşturur
        Gelişmiş hata yakalama ve logging ile
        """
        def format_price(price):
            return f"{price:.{price_precision}f}"
            
        try:
            if self._debug_enabled:
                print(f"🎯 {symbol} için piyasa emri oluşturuluyor:")
                print(f"   Yön: {side}")
                print(f"   Miktar: {quantity}")
                print(f"   Fiyat: {entry_price}")
                print(f"   Precision: {price_precision}")
            
            # Test modu kontrolü
            if hasattr(settings, 'TEST_MODE') and settings.TEST_MODE:
                print(f"🧪 TEST MODU: {symbol} emri simüle edildi")
                return {"orderId": "TEST_" + str(int(time.time())), "status": "FILLED"}
            
            # 🧹 ADIM 1: Önce tüm açık emirleri temizle
            if self._debug_enabled:
                print(f"🧹 {symbol} için yetim emir kontrolü yapılıyor...")
            cleanup_success = await self.cancel_all_orders_safe(symbol)
            if not cleanup_success:
                print("⚠️ Yetim emir temizliği başarısız - devam ediliyor...")
            
            # Kısa bekleme - emirlerin tamamen iptal olması için
            await asyncio.sleep(0.3)
            
            # 📈 ADIM 2: Ana piyasa emrini oluştur
            print(f"📈 {symbol} {side} {quantity} ana piyasa emri oluşturuluyor...")
            await self._rate_limit_delay()
            
            main_order = await self.client.futures_create_order(
                symbol=symbol,
                side=side,
                type='MARKET',
                quantity=quantity
            )
            
            if not main_order or 'orderId' not in main_order:
                print(f"❌ {symbol} ana emir oluşturulamadı")
                return None
                
            print(f"✅ Ana pozisyon başarılı: {symbol} {side} {quantity} (ID: {main_order['orderId']})")
            
            # Pozisyon açıldıktan sonra bekleme - SL/TP için hazır olması için
            await asyncio.sleep(1.0)
            
            # 🛡️ ADIM 3: Stop Loss ve Take Profit fiyatlarını hesapla
            if side == 'BUY':  # Long pozisyon
                sl_price = entry_price * (1 - settings.STOP_LOSS_PERCENT)
                tp_price = entry_price * (1 + settings.TAKE_PROFIT_PERCENT)
                opposite_side = 'SELL'
            else:  # Short pozisyon
                sl_price = entry_price * (1 + settings.STOP_LOSS_PERCENT)
                tp_price = entry_price * (1 - settings.TAKE_PROFIT_PERCENT)
                opposite_side = 'BUY'
            
            formatted_sl_price = format_price(sl_price)
            formatted_tp_price = format_price(tp_price)
            
            if self._debug_enabled:
                print(f"💡 Hesaplanan fiyatlar:")
                print(f"   Giriş: {entry_price}")
                print(f"   SL: {formatted_sl_price}")
                print(f"   TP: {formatted_tp_price}")
            
            # 🛑 ADIM 4: Stop Loss emrini oluştur
            sl_success = False
            tp_success = False
            
            try:
                print(f"🛑 Stop Loss emri oluşturuluyor: {formatted_sl_price}")
                await self._rate_limit_delay()
                sl_order = await self.client.futures_create_order(
                    symbol=symbol,
                    side=opposite_side,
                    type='STOP_MARKET',
                    quantity=quantity,
                    stopPrice=formatted_sl_price,
                    timeInForce='GTE_GTC',
                    reduceOnly=True
                )
                
                if sl_order and 'orderId' in sl_order:
                    print(f"✅ STOP LOSS başarılı: {formatted_sl_price} (ID: {sl_order['orderId']})")
                    sl_success = True
                else:
                    print(f"⚠️ Stop Loss emri oluştu ama ID alınamadı")
                    
            except BinanceAPIException as e:
                print(f"❌ Stop Loss emri hatası: {e}")
                if self._debug_enabled:
                    print(f"🔍 SL Hata detayı: Code={getattr(e, 'code', 'N/A')}, Message={getattr(e, 'message', str(e))}")
            
            # 🎯 ADIM 5: Take Profit emrini oluştur
            try:
                print(f"🎯 Take Profit emri oluşturuluyor: {formatted_tp_price}")
                await self._rate_limit_delay()
                tp_order = await self.client.futures_create_order(
                    symbol=symbol,
                    side=opposite_side,
                    type='TAKE_PROFIT_MARKET',
                    quantity=quantity,
                    stopPrice=formatted_tp_price,
                    timeInForce='GTE_GTC',
                    reduceOnly=True
                )
                
                if tp_order and 'orderId' in tp_order:
                    print(f"✅ TAKE PROFIT başarılı: {formatted_tp_price} (ID: {tp_order['orderId']})")
                    tp_success = True
                else:
                    print(f"⚠️ Take Profit emri oluştu ama ID alınamadı")
                    
            except BinanceAPIException as e:
                print(f"❌ Take Profit emri hatası: {e}")
                if self._debug_enabled:
                    print(f"🔍 TP Hata detayı: Code={getattr(e, 'code', 'N/A')}, Message={getattr(e, 'message', str(e))}")
            
            # 📊 ADIM 6: Alternatif yaklaşım - Eğer yukarıdaki başarısız olursa
            if not sl_success or not tp_success:
                print("🔄 Alternatif yaklaşım deneniyor...")
                
                # Alternatif SL yaklaşımı
                if not sl_success:
                    try:
                        print("🔄 Alternatif SL yaklaşımı...")
                        await self._rate_limit_delay()
                        alt_sl_order = await self.client.futures_create_order(
                            symbol=symbol,
                            side=opposite_side,
                            type='STOP',
                            quantity=quantity,
                            price=formatted_sl_price,
                            stopPrice=formatted_sl_price,
                            timeInForce='GTC',
                            reduceOnly=True
                        )
                        
                        if alt_sl_order and 'orderId' in alt_sl_order:
                            print(f"✅ Alternatif SL başarılı: {formatted_sl_price}")
                            sl_success = True
                            
                    except BinanceAPIException as alt_sl_error:
                        print(f"❌ Alternatif SL de başarısız: {alt_sl_error}")
                
                # Alternatif TP yaklaşımı
                if not tp_success:
                    try:
                        print("🔄 Alternatif TP yaklaşımı...")
                        await self._rate_limit_delay()
                        alt_tp_order = await self.client.futures_create_order(
                            symbol=symbol,
                            side=opposite_side,
                            type='LIMIT',
                            quantity=quantity,
                            price=formatted_tp_price,
                            timeInForce='GTC',
                            reduceOnly=True
                        )
                        
                        if alt_tp_order and 'orderId' in alt_tp_order:
                            print(f"✅ Alternatif TP (Limit) başarılı: {formatted_tp_price}")
                            tp_success = True
                            
                    except BinanceAPIException as alt_tp_error:
                        print(f"❌ Alternatif TP de başarısız: {alt_tp_error}")
            
            # 📊 ADIM 7: Sonuç raporu ve güvenlik kontrolü
            if not sl_success and not tp_success:
                print("⚠️ UYARI: Ne SL ne de TP kurulabildi! Manuel kontrol gerekebilir.")
                print("🚨 Korumasız pozisyon tespit edildi!")
            elif not sl_success:
                print("⚠️ UYARI: Sadece TP kuruldu, SL kurulamadı!")
            elif not tp_success:
                print("⚠️ UYARI: Sadece SL kuruldu, TP kurulamadı!")
            else:
                print("✅ Pozisyon tam korumalı: Hem SL hem TP kuruldu.")
            
            return main_order
            
        except BinanceAPIException as e:
            print(f"❌ KRITIK HATA: {symbol} ana pozisyon emri oluşturulamadı: {e}")
            # Ana emir başarısız olursa mutlaka temizlik yap
            print("🧹 Hata sonrası acil temizlik yapılıyor...")
            await self.cancel_all_orders_safe(symbol)
            return None
        except Exception as e:
            print(f"❌ {symbol} BEKLENMEYEN HATA: {e}")
            # Genel hata durumunda da temizlik yap
            print("🧹 Beklenmeyen hata sonrası temizlik yapılıyor...")
            await self.cancel_all_orders_safe(symbol)
            return None

    async def close_position(self, symbol: str, position_amt: float, side_to_close: str):
        """DÜZELTME: Pozisyon kapatır - YETİM EMİR TEMİZLİĞİ İLE"""
        try:
            # 🧹 ADIM 1: Pozisyon kapatmadan önce açık emirleri temizle
            if self._debug_enabled:
                print(f"🧹 {symbol} pozisyon kapatma öncesi yetim emir temizliği...")
            await self.cancel_all_orders_safe(symbol)
            await asyncio.sleep(0.2)
            
            # Test modu kontrolü
            if hasattr(settings, 'TEST_MODE') and settings.TEST_MODE:
                print(f"🧪 TEST MODU: {symbol} pozisyon kapatma simüle edildi")
                return {"orderId": "TEST_CLOSE_" + str(int(time.time())), "status": "FILLED"}
            
            # 📉 ADIM 2: Pozisyonu kapat
            print(f"📉 {symbol} pozisyonu kapatılıyor: {abs(position_amt)} miktar")
            await self._rate_limit_delay()
            response = await self.client.futures_create_order(
                symbol=symbol,
                side=side_to_close,
                type='MARKET',
                quantity=abs(position_amt),
                reduceOnly=True
            )
            
            if response and 'orderId' in response:
                print(f"✅ POZİSYON KAPATILDI: {symbol} (ID: {response['orderId']})")
            else:
                print(f"⚠️ {symbol} pozisyon kapatıldı ama ID alınamadı")
            
            # 🧹 ADIM 3: Kapanış sonrası ekstra temizlik (ihtiyaten)
            await asyncio.sleep(0.5)
            await self.cancel_all_orders_safe(symbol)
            
            # 💾 ADIM 4: Cache temizle
            if symbol in self._cached_positions:
                del self._cached_positions[symbol]
            if symbol in self._last_position_check:
                del self._last_position_check[symbol]
            
            return response
            
        except BinanceAPIException as e:
            print(f"❌ {symbol} pozisyon kapatma hatası: {e}")
            # Hata durumunda yine de temizlik yap
            print("🧹 Hata sonrası acil yetim emir temizliği...")
            await self.cancel_all_orders_safe(symbol)
            return None
        except Exception as e:
            print(f"❌ {symbol} pozisyon kapatma genel hatası: {e}")
            await self.cancel_all_orders_safe(symbol)
            return None

    async def get_last_trade_pnl(self, symbol: str) -> float:
        """DÜZELTME: Son işlem PnL'ini al - gelişmiş hata yakalama"""
        try:
            await self._rate_limit_delay()
            trades = await self.client.futures_account_trades(symbol=symbol, limit=5)
            if trades:
                last_order_id = trades[-1]['orderId']
                pnl = 0.0
                for trade in reversed(trades):
                    if trade['orderId'] == last_order_id:
                        pnl += float(trade['realizedPnl'])
                    else:
                        break
                        
                if self._debug_enabled:
                    print(f"📊 {symbol} son işlem PnL: {pnl}")
                return pnl
            return 0.0
            
        except BinanceAPIException as e:
            if "-1003" in str(e):
                print(f"⚠️ Rate limit - {symbol} PNL sorgusu atlanıyor")
                return 0.0
            else:
                print(f"❌ Hata: {symbol} son işlem PNL'i alınamadı: {e}")
                return 0.0
        except Exception as e:
            print(f"❌ {symbol} PNL sorgusu genel hatası: {e}")
            return 0.0

    async def get_account_balance(self, use_cache: bool = True):
        """DÜZELTME: Hesap bakiyesini getirir - cache desteği ile"""
        try:
            current_time = time.time()
            
            # Cache kontrolü (10 saniye cache)
            if use_cache and current_time - self._last_balance_check < 10:
                if self._debug_enabled:
                    print(f"💾 Bakiye cache'den alındı: {self._cached_balance}")
                return self._cached_balance
            
            await self._rate_limit_delay()
            account = await self.client.futures_account()
            
            if not account or 'assets' not in account:
                print("❌ Hesap bilgileri alınamadı")
                return self._cached_balance
                
            total_balance = 0.0
            for asset in account['assets']:
                if asset['asset'] == 'USDT':
                    total_balance = float(asset['walletBalance'])
                    break
            
            # Cache güncelle
            self._last_balance_check = current_time
            self._cached_balance = total_balance
            
            if self._debug_enabled:
                print(f"💰 Güncel bakiye: {total_balance} USDT")
            
            return total_balance
            
        except BinanceAPIException as e:
            if "-1003" in str(e):
                # Rate limit durumunda cache'den döndür
                print(f"⚠️ Rate limit - bakiye cache'den döndürülüyor: {self._cached_balance}")
                return self._cached_balance
            else:
                print(f"❌ Hata: Hesap bakiyesi alınamadı: {e}")
                return self._cached_balance
        except Exception as e:
            print(f"❌ Bakiye sorgusu genel hatası: {e}")
            return self._cached_balance

    async def get_position_pnl(self, symbol: str, use_cache: bool = True):
        """DÜZELTME: Açık pozisyonun anlık PnL'ini getirir - cache desteği ile"""
        try:
            current_time = time.time()
            cache_key = f"{symbol}_pnl"
            
            # Cache kontrolü (3 saniye cache)
            if use_cache and cache_key in self._last_position_check:
                if current_time - self._last_position_check[cache_key] < 3:
                    cached_pnl = self._cached_positions.get(cache_key, 0.0)
                    if self._debug_enabled:
                        print(f"💾 {symbol} PnL cache'den alındı: {cached_pnl}")
                    return cached_pnl
            
            await self._rate_limit_delay()
            positions = await self.client.futures_position_information(symbol=symbol)
            
            if not positions:
                print(f"⚠️ {symbol} için pozisyon bilgisi alınamadı")
                return 0.0
                
            pnl = 0.0
            for position in positions:
                if float(position['positionAmt']) != 0:
                    pnl = float(position['unRealizedProfit'])
                    break
            
            # Cache güncelle
            self._last_position_check[cache_key] = current_time
            self._cached_positions[cache_key] = pnl
            
            if self._debug_enabled:
                print(f"📊 {symbol} anlık PnL: {pnl}")
            
            return pnl
            
        except BinanceAPIException as e:
            if "-1003" in str(e):
                # Rate limit durumunda cache'den döndür
                cached_pnl = self._cached_positions.get(f"{symbol}_pnl", 0.0)
                print(f"⚠️ Rate limit - {symbol} PnL cache'den döndürülüyor: {cached_pnl}")
                return cached_pnl
            else:
                print(f"❌ Hata: {symbol} pozisyon PnL'i alınamadı: {e}")
                return 0.0
        except Exception as e:
            print(f"❌ {symbol} PnL sorgusu genel hatası: {e}")
            return 0.0

    async def force_cleanup_orders(self, symbol: str):
        """DÜZELTME: ACIL DURUM: Tüm açık emirleri zorla temizler"""
        try:
            print(f"🚨 {symbol} için ZORLA YETİM EMİR TEMİZLİĞİ başlatılıyor...")
            max_attempts = 3
            
            for attempt in range(max_attempts):
                print(f"🧹 Temizlik denemesi {attempt + 1}/{max_attempts}")
                
                # Açık emirleri kontrol et
                await self._rate_limit_delay()
                open_orders = await self.client.futures_get_open_orders(symbol=symbol)
                
                if not open_orders:
                    print(f"✅ {symbol} için yetim emir kalmadı.")
                    return True
                
                print(f"🎯 {len(open_orders)} adet yetim emir tespit edildi.")
                
                # Tek tek iptal etmeyi dene
                for order in open_orders:
                    try:
                        await self._rate_limit_delay()
                        await self.client.futures_cancel_order(
                            symbol=symbol, 
                            orderId=order['orderId']
                        )
                        if self._debug_enabled:
                            print(f"✅ Emir iptal edildi: {order['orderId']}")
                    except Exception as order_error:
                        print(f"⚠️ Emir iptal hatası: {order_error}")
                
                # Toplu iptal dene
                try:
                    await self._rate_limit_delay()
                    await self.client.futures_cancel_all_open_orders(symbol=symbol)
                    print("🧹 Toplu iptal komutu gönderildi")
                except Exception as batch_error:
                    print(f"⚠️ Toplu iptal hatası: {batch_error}")
                
                await asyncio.sleep(1)  # Sonraki deneme için bekle
            
            print(f"⚠️ {max_attempts} deneme sonrası bazı yetim emirler kalabilir.")
            return False
            
        except Exception as e:
            print(f"❌ Zorla temizlik hatası: {e}")
            return False

    async def close(self):
        """Bağlantıyı kapat"""
        if self.client:
            try:
                await self.client.close_connection()
                self.client = None
                print("✅ Binance AsyncClient bağlantısı kapatıldı.")
            except Exception as e:
                print(f"⚠️ Bağlantı kapatılırken hata: {e}")

binance_client = BinanceClient()
