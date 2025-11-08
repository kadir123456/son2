# app/binance_client.py - TP/SL FIX
import asyncio
from binance import AsyncClient
from binance.exceptions import BinanceAPIException
import time
from typing import Optional, Dict, Any
import math

class FixedBinanceClient:
    def __init__(self, settings):
        self.api_key = settings.API_KEY
        self.api_secret = settings.API_SECRET
        self.is_testnet = settings.ENVIRONMENT == "TEST"
        self.client: AsyncClient | None = None
        self.exchange_info = None
        self._last_balance_check = 0
        self._cached_balance = 0.0
        self._rate_limit_delay_time = 0.2
        
        print(f"🎯 Fixed Binance Client başlatılıyor. Ortam: {settings.ENVIRONMENT}")
        
    async def _rate_limit_delay(self):
        """Rate limit koruması"""
        await asyncio.sleep(self._rate_limit_delay_time)
        
    async def initialize(self):
        """Bağlantıyı başlat"""
        if self.client is None:
            try:
                self.client = await AsyncClient.create(
                    self.api_key, self.api_secret, testnet=self.is_testnet
                )
                await self._rate_limit_delay()
                
                self.exchange_info = await self.client.get_exchange_info()
                
                if not self.exchange_info or 'symbols' not in self.exchange_info:
                    raise Exception("Exchange info alınamadı")
                    
                print("✅ Binance AsyncClient başarıyla başlatıldı.")
                await self._test_connection()
                
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

    async def create_position_with_tpsl(
        self, 
        symbol: str, 
        side: str, 
        quantity: float,
        entry_price: float, 
        price_precision: int,
        tp_percent: float,
        sl_percent: float
    ) -> Optional[Dict]:
        """
        🎯 POZİSYON AÇ + TP/SL EKLE (DÜZELTİLMİŞ)
        
        DEĞİŞİKLİKLER:
        1. Ana pozisyon açıldıktan sonra doğrulama
        2. TP/SL için daha fazla bekleme
        3. GTC yerine GTE_GTC kullanımı
        4. Hata durumunda pozisyon kapatma
        """
        def format_price(price):
            return f"{price:.{price_precision}f}"
            
        try:
            print(f"\n{'='*60}")
            print(f"🎯 {symbol} POZİSYON AÇILIYOR")
            print(f"{'='*60}")
            print(f"   Yön: {side}")
            print(f"   Miktar: {quantity}")
            print(f"   Entry: {entry_price}")
            print(f"   TP: %{tp_percent*100:.2f} | SL: %{sl_percent*100:.2f}")
            
            # TEST MODU
            if hasattr(self, 'TEST_MODE') and self.TEST_MODE:
                print(f"🧪 TEST: {symbol} pozisyon simüle edildi")
                return {"orderId": "TEST_" + str(int(time.time())), "status": "FILLED"}
            
            # 1. Açık emirleri temizle
            await self.cancel_all_orders_safe(symbol)
            await asyncio.sleep(0.5)
            
            # 2. Ana pozisyon aç
            print(f"\n📈 Ana pozisyon açılıyor...")
            await self._rate_limit_delay()
            
            main_order = await self.client.futures_create_order(
                symbol=symbol,
                side=side,
                type='MARKET',
                quantity=quantity
            )
            
            if not main_order or 'orderId' not in main_order:
                print(f"❌ Ana emir oluşturulamadı")
                return None
                
            print(f"✅ Ana pozisyon AÇILDI: Order ID {main_order['orderId']}")
            
            # 3. POZİSYON DOĞRULAMASI (ÖNEMLİ!)
            print(f"\n🔍 Pozisyon doğrulanıyor...")
            await asyncio.sleep(2.0)  # Pozisyonun açılması için bekle
            
            position = await self._verify_position(symbol, side)
            if not position:
                print(f"⚠️ Pozisyon doğrulanamadı, TP/SL eklenemiyor")
                return main_order
            
            print(f"✅ Pozisyon doğrulandı: {abs(float(position['positionAmt']))} {symbol}")
            
            # 4. TP/SL Hesapla
            opposite_side = 'SELL' if side == 'BUY' else 'BUY'
            
            if side == 'BUY':  # Long
                tp_price = entry_price * (1 + tp_percent)
                sl_price = entry_price * (1 - sl_percent)
            else:  # Short
                tp_price = entry_price * (1 - tp_percent)
                sl_price = entry_price * (1 + sl_percent)
            
            formatted_tp = format_price(tp_price)
            formatted_sl = format_price(sl_price)
            
            print(f"\n💹 TP/SL SEVİYELERİ:")
            print(f"   Take Profit: {formatted_tp}")
            print(f"   Stop Loss: {formatted_sl}")
            
            # 5. STOP LOSS Ekle
            await asyncio.sleep(0.5)
            sl_success = await self._create_stop_loss_fixed(
                symbol, opposite_side, quantity, formatted_sl
            )
            
            # 6. TAKE PROFIT Ekle
            await asyncio.sleep(0.5)
            tp_success = await self._create_take_profit_fixed(
                symbol, opposite_side, quantity, formatted_tp
            )
            
            # 7. Sonuç raporu
            success_count = sum([sl_success, tp_success])
            
            print(f"\n{'='*60}")
            if success_count == 2:
                print(f"✅ {symbol} POZİSYON TAM KORUMALI (TP + SL)")
            elif success_count == 1:
                print(f"⚠️ {symbol} KISMÎ KORUMA ({success_count}/2)")
            else:
                print(f"❌ {symbol} KORUMASIZ POZİSYON!")
                # Korumasız pozisyonu kapat
                await self._emergency_close_position(symbol, opposite_side, quantity)
            print(f"{'='*60}\n")
            
            return main_order
            
        except BinanceAPIException as e:
            print(f"❌ {symbol} Binance API hatası: {e}")
            await self.cancel_all_orders_safe(symbol)
            return None
        except Exception as e:
            print(f"❌ {symbol} Beklenmeyen hata: {e}")
            await self.cancel_all_orders_safe(symbol)
            return None

    async def _verify_position(self, symbol: str, expected_side: str) -> Optional[Dict]:
        """Pozisyonun açıldığını doğrula"""
        try:
            await self._rate_limit_delay()
            positions = await self.client.futures_position_information(symbol=symbol)
            
            for pos in positions:
                position_amt = float(pos['positionAmt'])
                if position_amt == 0:
                    continue
                
                actual_side = 'BUY' if position_amt > 0 else 'SELL'
                if actual_side == expected_side:
                    return pos
            
            return None
            
        except Exception as e:
            print(f"❌ Pozisyon doğrulama hatası: {e}")
            return None

    async def _create_stop_loss_fixed(
        self, symbol: str, side: str, quantity: float, price: str
    ) -> bool:
        """STOP LOSS (DÜZELTİLMİŞ)"""
        try:
            print(f"🛑 Stop Loss oluşturuluyor: {price}")
            await self._rate_limit_delay()
            
            sl_order = await self.client.futures_create_order(
                symbol=symbol,
                side=side,
                type='STOP_MARKET',
                quantity=quantity,
                stopPrice=price,
                timeInForce='GTE_GTC',  # Good Till Expire - Good Till Cancel
                reduceOnly=True,
                closePosition=False
            )
            
            if sl_order and 'orderId' in sl_order:
                print(f"✅ Stop Loss BAŞARILI: {price} (Order ID: {sl_order['orderId']})")
                return True
            
            return False
            
        except BinanceAPIException as e:
            print(f"❌ Stop Loss API hatası: {e.code} - {e.message}")
            return False
        except Exception as e:
            print(f"❌ Stop Loss genel hatası: {e}")
            return False

    async def _create_take_profit_fixed(
        self, symbol: str, side: str, quantity: float, price: str
    ) -> bool:
        """TAKE PROFIT (DÜZELTİLMİŞ)"""
        try:
            print(f"🎯 Take Profit oluşturuluyor: {price}")
            await self._rate_limit_delay()
            
            tp_order = await self.client.futures_create_order(
                symbol=symbol,
                side=side,
                type='TAKE_PROFIT_MARKET',
                quantity=quantity,
                stopPrice=price,
                timeInForce='GTE_GTC',
                reduceOnly=True,
                closePosition=False
            )
            
            if tp_order and 'orderId' in tp_order:
                print(f"✅ Take Profit BAŞARILI: {price} (Order ID: {tp_order['orderId']})")
                return True
            
            return False
            
        except BinanceAPIException as e:
            print(f"❌ Take Profit API hatası: {e.code} - {e.message}")
            return False
        except Exception as e:
            print(f"❌ Take Profit genel hatası: {e}")
            return False

    async def _emergency_close_position(
        self, symbol: str, side: str, quantity: float
    ):
        """Acil pozisyon kapatma (korumasız pozisyonlar için)"""
        try:
            print(f"🚨 {symbol} ACİL KAPATILIYOR (korumasız pozisyon)")
            await self._rate_limit_delay()
            
            close_order = await self.client.futures_create_order(
                symbol=symbol,
                side=side,
                type='MARKET',
                quantity=quantity,
                reduceOnly=True
            )
            
            if close_order:
                print(f"✅ {symbol} pozisyon kapatıldı")
            
        except Exception as e:
            print(f"❌ Acil kapatma hatası: {e}")

    async def get_symbol_info(self, symbol: str):
        """Symbol bilgilerini al"""
        try:
            if not self.exchange_info:
                await self._rate_limit_delay()
                self.exchange_info = await self.client.get_exchange_info()
                
            if not self.exchange_info or 'symbols' not in self.exchange_info:
                return None
                
            for s in self.exchange_info['symbols']:
                if s['symbol'] == symbol:
                    return s
                    
            return None
            
        except Exception as e:
            print(f"❌ {symbol} sembol bilgisi hatası: {e}")
            return None
        
    async def get_open_positions(self, symbol: str):
        """Açık pozisyonları getir"""
        try:
            await self._rate_limit_delay()
            positions = await self.client.futures_position_information(symbol=symbol)
            
            if not positions:
                return []
                
            open_positions = [p for p in positions if float(p['positionAmt']) != 0]
            return open_positions
            
        except Exception as e:
            print(f"❌ {symbol} pozisyon sorgusu hatası: {e}")
            return []

    async def cancel_all_orders_safe(self, symbol: str):
        """Güvenli emir iptali"""
        try:
            await self._rate_limit_delay()
            result = await self.client.futures_cancel_all_open_orders(symbol=symbol)
            if result:
                print(f"🗑️ {symbol} açık emirler iptal edildi")
            return True
                
        except Exception as e:
            # Zaten açık emir yoksa hata almayı görmezden gel
            if "-2011" not in str(e):
                print(f"⚠️ {symbol} emir iptali: {e}")
            return False

    async def get_market_price(self, symbol: str):
        """Market fiyatını al"""
        try:
            await self._rate_limit_delay()
            ticker = await self.client.futures_symbol_ticker(symbol=symbol)
            
            if not ticker or 'price' not in ticker:
                return None
                
            return float(ticker['price'])
            
        except Exception as e:
            print(f"❌ {symbol} fiyat sorgusu hatası: {e}")
            return None

    async def get_historical_klines(self, symbol: str, interval: str, limit: int = 100):
        """Geçmiş veri al"""
        try:
            await self._rate_limit_delay()
            klines = await self.client.get_historical_klines(symbol, interval, limit=limit)
            return klines if klines else []
            
        except Exception as e:
            print(f"❌ {symbol} geçmiş veri hatası: {e}")
            return []

    async def set_leverage(self, symbol: str, leverage: int):
        """Kaldıraç ayarla"""
        try:
            # Açık pozisyon kontrolü
            open_positions = await self.get_open_positions(symbol)
            if open_positions:
                print(f"⚠️ {symbol} için açık pozisyon mevcut. Kaldıraç değiştirilemez.")
                return False
            
            # Margin tipini cross olarak ayarla
            try:
                await self._rate_limit_delay()
                await self.client.futures_change_margin_type(symbol=symbol, marginType='CROSSED')
            except BinanceAPIException as e:
                if "No need to change margin type" in str(e):
                    pass  # Zaten cross modunda
            
            # Kaldıracı ayarla
            await self._rate_limit_delay()
            result = await self.client.futures_change_leverage(symbol=symbol, leverage=leverage)
            
            if result:
                print(f"✅ {symbol} kaldıracı {leverage}x")
                return True
            return False
                
        except Exception as e:
            print(f"❌ {symbol} kaldıraç ayarlama hatası: {e}")
            return False

    async def get_account_balance(self):
        """Hesap bakiyesini getir"""
        try:
            current_time = time.time()
            
            # Cache kontrolü
            if current_time - self._last_balance_check < 30:
                return self._cached_balance
            
            await self._rate_limit_delay()
            account = await self.client.futures_account()
            
            if not account or 'assets' not in account:
                return self._cached_balance
                
            total_balance = 0.0
            for asset in account['assets']:
                if asset['asset'] == 'USDT':
                    total_balance = float(asset['walletBalance'])
                    break
            
            self._last_balance_check = current_time
            self._cached_balance = total_balance
            
            return total_balance
            
        except Exception as e:
            print(f"❌ Bakiye sorgusu hatası: {e}")
            return self._cached_balance

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

    async def close(self):
        """Bağlantıyı kapat"""
        if self.client:
            try:
                await self.client.close_connection()
                self.client = None
                print("✅ Binance AsyncClient bağlantısı kapatıldı.")
            except Exception as e:
                print(f"⚠️ Bağlantı kapatılırken hata: {e}")


# ÖNEMLİ: main.py'nin import edebilmesi için client instance'ı oluştur
# Bu satır main.py'deki "from .binance_client import binance_client" import'unu çözer
binance_client = None  # İlk başta None, settings yüklendikten sonra doldurulacak


def create_binance_client(settings):
    """Binance client instance'ı oluştur"""
    global binance_client
    binance_client = FixedBinanceClient(settings)
    return binance_client
