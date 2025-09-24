import asyncio
from binance import AsyncClient
from binance.exceptions import BinanceAPIException
from .config import settings
import time
from typing import Optional, Dict, Any

class SimpleBinanceClient:
    def __init__(self):
        self.api_key = settings.API_KEY
        self.api_secret = settings.API_SECRET
        self.is_testnet = settings.ENVIRONMENT == "TEST"
        self.client: AsyncClient | None = None
        self.exchange_info = None
        self._last_balance_check = 0
        self._cached_balance = 0.0
        self._rate_limit_delay_time = 0.2
        
        print(f"🎯 Basit Binance İstemcisi başlatılıyor. Ortam: {settings.ENVIRONMENT}")
        
    async def _rate_limit_delay(self):
        """Rate limit koruması için bekleme"""
        await asyncio.sleep(self._rate_limit_delay_time)
        
    async def initialize(self):
        """Bağlantıyı başlat"""
        if self.client is None:
            try:
                self.client = await AsyncClient.create(self.api_key, self.api_secret, testnet=self.is_testnet)
                await self._rate_limit_delay()
                
                # Exchange info al
                self.exchange_info = await self.client.get_exchange_info()
                
                if not self.exchange_info or 'symbols' not in self.exchange_info:
                    raise Exception("Exchange info alınamadı")
                    
                print("✅ Basit Binance AsyncClient başarıyla başlatıldı.")
                
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

    async def create_simple_position(self, symbol: str, side: str, quantity: float, 
                                   entry_price: float, price_precision: int) -> Optional[Dict]:
        """
        🎯 Basit pozisyon oluştur (sadece TP/SL ile)
        """
        def format_price(price):
            return f"{price:.{price_precision}f}"
            
        try:
            print(f"🎯 {symbol} basit pozisyonu oluşturuluyor:")
            print(f"   Yön: {side}, Miktar: {quantity}, Fiyat: {entry_price}")
            
            # Test modu kontrolü
            if settings.TEST_MODE:
                print(f"🧪 TEST: {symbol} pozisyon simüle edildi")
                return {"orderId": "TEST_" + str(int(time.time())), "status": "FILLED"}
            
            # Açık emirleri temizle
            await self.cancel_all_orders_safe(symbol)
            await asyncio.sleep(0.3)
            
            # Ana pozisyonu aç
            print(f"📈 {symbol} ana pozisyon açılıyor...")
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
                
            print(f"✅ Ana pozisyon başarılı: {symbol} {side} {quantity}")
            await asyncio.sleep(1.0)
            
            # TP/SL fiyatlarını hesapla
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
            
            print(f"💡 TP/SL planı:")
            print(f"   SL: {formatted_sl_price}")
            print(f"   TP: {formatted_tp_price}")
            
            # Stop Loss ekle
            sl_order = await self._create_stop_loss(symbol, opposite_side, quantity, formatted_sl_price)
            
            # Take Profit ekle
            tp_order = await self._create_take_profit(symbol, opposite_side, quantity, formatted_tp_price)
            
            # Sonuç raporu
            success_count = sum([bool(sl_order), bool(tp_order)])
            if success_count >= 1:
                print(f"✅ {symbol} pozisyon başarılı! ({success_count}/2 emir)")
            else:
                print(f"⚠️ {symbol} TP/SL eklenemedi")
                
            return main_order
            
        except BinanceAPIException as e:
            print(f"❌ {symbol} pozisyon hatası: {e}")
            await self.cancel_all_orders_safe(symbol)
            return None
        except Exception as e:
            print(f"❌ {symbol} beklenmeyen hata: {e}")
            await self.cancel_all_orders_safe(symbol)
            return None

    async def _create_stop_loss(self, symbol: str, side: str, quantity: float, price: str) -> Optional[Dict]:
        """Stop Loss emri oluştur"""
        try:
            print(f"🛑 {symbol} Stop Loss oluşturuluyor: {price}")
            await self._rate_limit_delay()
            
            sl_order = await self.client.futures_create_order(
                symbol=symbol,
                side=side,
                type='STOP_MARKET',
                quantity=quantity,
                stopPrice=price,
                timeInForce='GTE_GTC',
                reduceOnly=True
            )
            
            if sl_order and 'orderId' in sl_order:
                print(f"✅ Stop Loss başarılı: {price}")
                return sl_order
            return None
            
        except Exception as e:
            print(f"❌ Stop Loss hatası: {e}")
            return None

    async def _create_take_profit(self, symbol: str, side: str, quantity: float, price: str) -> Optional[Dict]:
        """Take Profit emri oluştur"""
        try:
            print(f"🎯 {symbol} Take Profit oluşturuluyor: {price}")
            await self._rate_limit_delay()
            
            tp_order = await self.client.futures_create_order(
                symbol=symbol,
                side=side,
                type='TAKE_PROFIT_MARKET',
                quantity=quantity,
                stopPrice=price,
                timeInForce='GTE_GTC',
                reduceOnly=True
            )
            
            if tp_order and 'orderId' in tp_order:
                print(f"✅ Take Profit başarılı: {price}")
                return tp_order
            return None
            
        except Exception as e:
            print(f"❌ Take Profit hatası: {e}")
            return None

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
            print(f"❌ {symbol} sembol bilgisi alınırken hata: {e}")
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
        """Güvenli emirlerin iptali"""
        try:
            await self._rate_limit_delay()
            await self.client.futures_cancel_all_open_orders(symbol=symbol)
            print(f"🗑️ {symbol} tüm açık emirler iptal edildi")
            return True
                
        except Exception as e:
            print(f"❌ {symbol} emir iptali hatası: {e}")
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
            except BinanceAPIException as margin_error:
                if "No need to change margin type" in str(margin_error):
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

    async def close(self):
        """Bağlantıyı kapat"""
        if self.client:
            try:
                await self.client.close_connection()
                self.client = None
                print("✅ Basit Binance AsyncClient bağlantısı kapatıldı.")
            except Exception as e:
                print(f"⚠️ Bağlantı kapatılırken hata: {e}")

# Global simple instance
binance_client = SimpleBinanceClient()
