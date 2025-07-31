# binance_client.py

import asyncio
from binance import AsyncClient
from binance.exceptions import BinanceAPIException
from .config import settings

class BinanceClient:
    def __init__(self):
        self.api_key = settings.API_KEY
        self.api_secret = settings.API_SECRET
        self.is_testnet = settings.ENVIRONMENT == "TEST"
        self.client: AsyncClient | None = None
        self.exchange_info = None
        print(f"Binance İstemcisi başlatılıyor. Ortam: {settings.ENVIRONMENT}")

    async def initialize(self):
        """Binance AsyncClient'ı başlatır ve borsa bilgilerini çeker."""
        if self.client is None:
            self.client = await AsyncClient.create(self.api_key, self.api_secret, testnet=self.is_testnet)
            self.exchange_info = await self.client.get_exchange_info()
            print("Binance AsyncClient başarıyla başlatıldı.")
        return self.client

    async def get_symbol_info(self, symbol: str):
        """Belirli bir sembolün borsa bilgilerini (hassasiyetler vb.) döndürür."""
        if not self.exchange_info:
            return None
        for s in self.exchange_info['symbols']:
            if s['symbol'] == symbol:
                return s
        return None

    async def get_open_positions(self, symbol: str):
        """Belirli bir sembol için açık pozisyonları döndürür."""
        try:
            positions = await self.client.futures_position_information(symbol=symbol)
            return [p for p in positions if float(p['positionAmt']) != 0]
        except BinanceAPIException as e:
            print(f"Hata: Pozisyon bilgileri alınamadı: {e}")
            return []
        
    async def create_market_order_with_sl_tp(self, symbol: str, side: str, quantity: float, entry_price: float, price_precision: int):
        """
        Piyasa emri oluşturur ve otomatik olarak Stop Loss (SL) ve Take Profit (TP) emirleri kurar.
        """
        def format_price(price):
            return f"{price:.{price_precision}f}"

        try:
            # 1. Ana PİYASA emri
            main_order = await self.client.futures_create_order(
                symbol=symbol,
                side=side,
                type='MARKET',
                quantity=quantity
            )
            print(f"Başarılı: {symbol} {side} {quantity:.{price_precision}f} PİYASA EMRİ oluşturuldu.")
            await asyncio.sleep(0.5) # Emirin oluşması için küçük bekleme

            # 2. STOP LOSS emri
            sl_price = entry_price * (1 - settings.STOP_LOSS_PERCENT) if side == 'BUY' else entry_price * (1 + settings.STOP_LOSS_PERCENT)
            formatted_sl_price = format_price(sl_price)
            
            await self.client.futures_create_order(
                symbol=symbol,
                side='SELL' if side == 'BUY' else 'BUY', # Karşıt yön
                type='STOP_MARKET',
                stopPrice=formatted_sl_price, # Tetikleme fiyatı
                closePosition=True, # Pozisyonu tamamen kapat
                timeInForce='GTC' # Good Till Cancel - Açık kalacak
            )
            print(f"Başarılı: {symbol} için STOP LOSS emri {formatted_sl_price} seviyesine kuruldu.")

            # 3. TAKE PROFIT emri (Yeni eklendi)
            tp_price = entry_price * (1 + settings.TAKE_PROFIT_PERCENT) if side == 'BUY' else entry_price * (1 - settings.TAKE_PROFIT_PERCENT)
            formatted_tp_price = format_price(tp_price)
            
            await self.client.futures_create_order(
                symbol=symbol,
                side='SELL' if side == 'BUY' else 'BUY', # Karşıt yön
                type='TAKE_PROFIT_MARKET', # TP tipi
                stopPrice=formatted_tp_price, # TP tetikleme fiyatı
                closePosition=True,
                timeInForce='GTC'
            )
            print(f"Başarılı: {symbol} için TAKE PROFIT emri {formatted_tp_price} seviyesine kuruldu.")

            return main_order
        except BinanceAPIException as e:
            print(f"Hata: SL/TP ile emir oluşturulurken sorun oluştu: {e}")
            # Hata durumunda açık kalan tüm emirleri iptal et
            print(f"{symbol} için açık tüm emirler iptal ediliyor...")
            await self.client.futures_cancel_all_open_orders(symbol=symbol)
            return None

    async def close_position(self, symbol: str, position_amt: float, side_to_close: str):
        """Açık pozisyonu piyasa emri ile kapatır ve tüm açık emirleri iptal eder."""
        try:
            # Önce tüm açık emirleri (SL/TP) iptal et
            await self.client.futures_cancel_all_open_orders(symbol=symbol)
            await asyncio.sleep(0.1) # İptallerin işlenmesi için kısa bekleme

            response = await self.client.futures_create_order(
                symbol=symbol,
                side=side_to_close,
                type='MARKET',
                quantity=abs(position_amt),
                reduceOnly=True # Sadece pozisyon azaltma/kapatma amaçlı
            )
            print(f"--> POZİSYON KAPATILDI: {symbol}")
            return response
        except BinanceAPIException as e:
            print(f"Hata: Pozisyon kapatılırken sorun oluştu: {e}")
            return None

    async def get_last_trade_pnl(self, symbol: str) -> float:
        """Son kapanan işlemden elde edilen gerçekleşmiş PNL'yi döndürür."""
        try:
            # Son gerçekleşen işlemleri çek
            # 'incomeType': 'REALIZED_PNL' olanları kontrol ederek daha kesin olunabilir
            trades = await self.client.futures_account_trades(symbol=symbol, limit=20) # Limiti artırdık
            pnl = 0.0
            
            # Son kapanan pozisyonun PNL'ini bulmaya çalış
            # Position_amount'ın 0 olduğu durumlara bakmak daha güvenilir olabilir.
            # Binance'in PNL kayıtları bazen karmaşık olabilir, bu yüzden en son tüm trades'lerin realizedPnl'ine bakıyoruz.
            
            # Daha doğru bir PNL hesabı için pozisyon geçmişi kullanılabilir,
            # ancak bu bot sadece son kapanan işlemi takip ediyor.
            
            # Basit bir yaklaşımla, son birkaç işlemin gerçekleşmiş PNL'ine bakıyoruz.
            if trades:
                # Genellikle son işlem veya son birkaç işlem kapanan pozisyona aittir.
                # Daha güvenli bir yaklaşım, 'closedPosition' alanını kontrol etmek veya
                # sadece 'REALIZED_PNL' tipi income kayıtlarını kontrol etmektir.
                # Ancak 'futures_account_trades' içinde 'REALIZED_PNL' tipi doğrudan gelmez.
                # Bu nedenle, son birkaç trade'in PNL'ini toplamak daha güvenli.
                for trade in reversed(trades):
                    if float(trade['realizedPnl']) != 0:
                        pnl += float(trade['realizedPnl'])
                        # İlk nonzero PNL'i bulduğumuzda genellikle o son işlemdir
                        # Ancak birden fazla kısmi kapanış olabileceği için, son birkaç trade'e bakmak iyi.
                        # Burada basitleştirilmiş bir yaklaşım izleniyor: tüm son pnl'leri topla.
                        # Eğer kesinlikle son bir işlemin PNL'i isteniyorsa, orderId takibi daha iyi olur.
                        # Şimdilik, kapanan bir pozisyonda, tüm ilgili PNL'leri toplayalım:
                        # Bu kısım biraz Binance API'sının davranışına bağlıdır.
                        # Basitçe son trade'in PNL'ini döndürelim:
                        return float(trades[-1]['realizedPnl']) # Sadece son trade'in PNL'ini alıyoruz.
            return 0.0
        except BinanceAPIException as e:
            print(f"Hata: Son işlem PNL'i alınamadı: {e}")
            return 0.0

    async def close(self):
        """Binance AsyncClient bağlantısını kapatır."""
        if self.client:
            await self.client.close_connection()
            self.client = None
            print("Binance AsyncClient bağlantısı kapatıldı.")

    async def get_historical_klines(self, symbol: str, interval: str, limit: int = 100):
        """Geçmiş mum verilerini çeker."""
        try:
            print(f"{symbol} için {limit} adet geçmiş {interval} mum verisi çekiliyor...")
            return await self.client.get_historical_klines(symbol, interval, limit=limit)
        except BinanceAPIException as e:
            print(f"Hata: Geçmiş mum verileri çekilemedi ({symbol}, {interval}): {e}")
            return []

    async def set_leverage(self, symbol: str, leverage: int):
        """Belirli bir sembol için kaldıracı ayarlar."""
        try:
            await self.client.futures_change_leverage(symbol=symbol, leverage=leverage)
            print(f"Başarılı: {symbol} kaldıracı {leverage}x olarak ayarlandı.")
            return True
        except BinanceAPIException as e:
            print(f"Hata: Kaldıraç ayarlanamadı ({symbol}): {e}")
            return False

    async def get_market_price(self, symbol: str):
        """Belirli bir sembolün anlık piyasa fiyatını döndürür."""
        try:
            ticker = await self.client.futures_symbol_ticker(symbol=symbol)
            return float(ticker['price'])
        except BinanceAPIException as e:
            print(f"Hata: {symbol} fiyatı alınamadı: {e}")
            return None

binance_client = BinanceClient()