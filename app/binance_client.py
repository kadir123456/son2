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
        self._rate_limit_delay_time = 0.1  # Minimum delay between requests (RENAMED)
        print(f"Binance İstemcisi başlatılıyor. Ortam: {settings.ENVIRONMENT}")
        
    async def _rate_limit_delay(self):
        """Rate limit koruması için bekleme"""
        await asyncio.sleep(self._rate_limit_delay_time)  # Use the renamed variable
        
    async def initialize(self):
        if self.client is None:
            self.client = await AsyncClient.create(self.api_key, self.api_secret, testnet=self.is_testnet)
            await self._rate_limit_delay()
            self.exchange_info = await self.client.get_exchange_info()
            print("Binance AsyncClient başarıyla başlatıldı.")
        return self.client
        
    async def get_symbol_info(self, symbol: str):
        if not self.exchange_info:
            return None
        for s in self.exchange_info['symbols']:
            if s['symbol'] == symbol:
                return s
        return None
        
    async def get_open_positions(self, symbol: str, use_cache: bool = True):
        """Açık pozisyonları getirir - cache desteği ile"""
        try:
            current_time = time.time()
            cache_key = symbol
            
            # Cache kontrolü (5 saniye cache)
            if use_cache and cache_key in self._last_position_check:
                if current_time - self._last_position_check[cache_key] < 5:
                    return self._cached_positions.get(cache_key, [])
            
            await self._rate_limit_delay()
            positions = await self.client.futures_position_information(symbol=symbol)
            open_positions = [p for p in positions if float(p['positionAmt']) != 0]
            
            # Cache güncelle
            self._last_position_check[cache_key] = current_time
            self._cached_positions[cache_key] = open_positions
            
            return open_positions
            
        except BinanceAPIException as e:
            if "-1003" in str(e):  # Rate limit hatası
                print(f"Rate limit - pozisyon kontrolü atlanıyor")
                # Cache'den döndür
                return self._cached_positions.get(symbol, [])
            print(f"Hata: Pozisyon bilgileri alınamadı: {e}")
            return []

    async def cancel_all_orders_safe(self, symbol: str):
        """Tüm açık emirleri güvenli şekilde iptal eder"""
        try:
            await self._rate_limit_delay()
            open_orders = await self.client.futures_get_open_orders(symbol=symbol)
            if open_orders:
                print(f"{len(open_orders)} adet açık emir iptal ediliyor...")
                await self._rate_limit_delay()
                await self.client.futures_cancel_all_open_orders(symbol=symbol)
                await asyncio.sleep(0.5)
                print("Tüm açık emirler iptal edildi.")
            return True
        except BinanceAPIException as e:
            if "-1003" in str(e):
                print("Rate limit - emir iptali atlanıyor")
                return False
            print(f"Emirler iptal edilirken hata: {e}")
            return False

    async def create_market_order_with_sl_tp(self, symbol: str, side: str, quantity: float, entry_price: float, price_precision: int):
        """Piyasa emri ile birlikte hem Stop Loss hem de Take Profit emri oluşturur"""
        def format_price(price):
            return f"{price:.{price_precision}f}"
            
        try:
            # Ana piyasa emrini oluştur
            await self._rate_limit_delay()
            main_order = await self.client.futures_create_order(
                symbol=symbol,
                side=side,
                type='MARKET',
                quantity=quantity
            )
            print(f"Başarılı: {symbol} {side} {quantity} PİYASA EMRİ oluşturuldu.")
            
            # Kısa bekleme
            await asyncio.sleep(0.8)
            
            # Stop Loss ve Take Profit fiyatlarını hesapla
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
            
            # Stop Loss emrini oluştur
            try:
                await self._rate_limit_delay()
                sl_order = await self.client.futures_create_order(
                    symbol=symbol,
                    side=opposite_side,
                    type='STOP_MARKET',
                    stopPrice=formatted_sl_price,
                    closePosition=True
                )
                print(f"Başarılı: {symbol} için STOP LOSS emri {formatted_sl_price} seviyesine kuruldu.")
            except BinanceAPIException as e:
                print(f"Hata: Stop Loss emri oluşturulamadı: {e}")
            
            # Take Profit emrini oluştur
            try:
                await self._rate_limit_delay()
                tp_order = await self.client.futures_create_order(
                    symbol=symbol,
                    side=opposite_side,
                    type='TAKE_PROFIT_MARKET',
                    stopPrice=formatted_tp_price,
                    closePosition=True
                )
                print(f"Başarılı: {symbol} için TAKE PROFIT emri {formatted_tp_price} seviyesine kuruldu.")
            except BinanceAPIException as e:
                print(f"Hata: Take Profit emri oluşturulamadı: {e}")
            
            return main_order
            
        except BinanceAPIException as e:
            print(f"Hata: SL/TP ile emir oluşturulurken sorun oluştu: {e}")
            return None

    async def close_position(self, symbol: str, position_amt: float, side_to_close: str):
        try:
            # Pozisyonu kapat
            await self._rate_limit_delay()
            response = await self.client.futures_create_order(
                symbol=symbol,
                side=side_to_close,
                type='MARKET',
                quantity=abs(position_amt),
                reduceOnly=True
            )
            print(f"--> POZİSYON KAPATILDI: {symbol}")
            
            # Kapanış sonrası cache temizle
            if symbol in self._cached_positions:
                del self._cached_positions[symbol]
            if symbol in self._last_position_check:
                del self._last_position_check[symbol]
            
            return response
        except BinanceAPIException as e:
            print(f"Hata: Pozisyon kapatılırken sorun oluştu: {e}")
            return None

    async def get_last_trade_pnl(self, symbol: str) -> float:
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
                return pnl
            return 0.0
        except BinanceAPIException as e:
            if "-1003" in str(e):
                print("Rate limit - PNL sorgusu atlanıyor")
                return 0.0
            print(f"Hata: Son işlem PNL'i alınamadı: {e}")
            return 0.0

    async def close(self):
        if self.client:
            await self.client.close_connection()
            self.client = None
            print("Binance AsyncClient bağlantısı kapatıldı.")

    async def get_historical_klines(self, symbol: str, interval: str, limit: int = 100):
        try:
            print(f"{symbol} için {limit} adet geçmiş mum verisi çekiliyor...")
            await self._rate_limit_delay()
            return await self.client.get_historical_klines(symbol, interval, limit=limit)
        except BinanceAPIException as e:
            print(f"Hata: Geçmiş mum verileri çekilemedi: {e}")
            return []

    async def set_leverage(self, symbol: str, leverage: int):
        """Kaldıraç ayarlama - açık pozisyon kontrolü ile"""
        try:
            # Önce açık pozisyon kontrolü yap
            open_positions = await self.get_open_positions(symbol, use_cache=False)
            if open_positions:
                print(f"Uyarı: {symbol} için açık pozisyon mevcut. Kaldıraç değiştirilemez.")
                return False
            
            # Margin tipini cross olarak ayarla
            try:
                await self._rate_limit_delay()
                await self.client.futures_change_margin_type(symbol=symbol, marginType='CROSSED')
                print(f"{symbol} margin tipi CROSSED olarak ayarlandı.")
            except BinanceAPIException as margin_error:
                if "No need to change margin type" in str(margin_error) or "-4046" in str(margin_error):
                    print(f"{symbol} zaten CROSSED margin modunda.")
                else:
                    print(f"Margin tipi değiştirilemedi: {margin_error}")
            
            # Kaldıracı ayarla
            await self._rate_limit_delay()
            await self.client.futures_change_leverage(symbol=symbol, leverage=leverage)
            print(f"Başarılı: {symbol} kaldıracı {leverage}x olarak ayarlandı.")
            return True
            
        except BinanceAPIException as e:
            if "-1003" in str(e):
                print("Rate limit - kaldıraç ayarı atlanıyor")
                return False
            print(f"Hata: Kaldıraç ayarlanamadı: {e}")
            return False

    async def get_market_price(self, symbol: str):
        try:
            await self._rate_limit_delay()
            ticker = await self.client.futures_symbol_ticker(symbol=symbol)
            return float(ticker['price'])
        except BinanceAPIException as e:
            if "-1003" in str(e):
                print("Rate limit - fiyat sorgusu atlanıyor")
                return None
            print(f"Hata: {symbol} fiyatı alınamadı: {e}")
            return None

    async def get_account_balance(self, use_cache: bool = True):
        """Hesap bakiyesini getirir - cache desteği ile"""
        try:
            current_time = time.time()
            
            # Cache kontrolü (10 saniye cache)
            if use_cache and current_time - self._last_balance_check < 10:
                return self._cached_balance
            
            await self._rate_limit_delay()
            account = await self.client.futures_account()
            total_balance = 0.0
            for asset in account['assets']:
                if asset['asset'] == 'USDT':
                    total_balance = float(asset['walletBalance'])
                    break
            
            # Cache güncelle
            self._last_balance_check = current_time
            self._cached_balance = total_balance
            
            return total_balance
            
        except BinanceAPIException as e:
            if "-1003" in str(e):
                # Rate limit durumunda cache'den döndür
                return self._cached_balance
            print(f"Hata: Hesap bakiyesi alınamadı: {e}")
            return self._cached_balance

    async def get_position_pnl(self, symbol: str, use_cache: bool = True):
        """Açık pozisyonun anlık PnL'ini getirir - cache desteği ile"""
        try:
            current_time = time.time()
            cache_key = f"{symbol}_pnl"
            
            # Cache kontrolü (3 saniye cache)
            if use_cache and cache_key in self._last_position_check:
                if current_time - self._last_position_check[cache_key] < 3:
                    return self._cached_positions.get(cache_key, 0.0)
            
            await self._rate_limit_delay()
            positions = await self.client.futures_position_information(symbol=symbol)
            pnl = 0.0
            for position in positions:
                if float(position['positionAmt']) != 0:
                    pnl = float(position['unRealizedProfit'])
                    break
            
            # Cache güncelle
            self._last_position_check[cache_key] = current_time
            self._cached_positions[cache_key] = pnl
            
            return pnl
            
        except BinanceAPIException as e:
            if "-1003" in str(e):
                # Rate limit durumunda cache'den döndür
                return self._cached_positions.get(f"{symbol}_pnl", 0.0)
            print(f"Hata: Pozisyon PnL'i alınamadı: {e}")
            return 0.0

binance_client = BinanceClient()
