# bot_core.py

import asyncio
import json
import websockets
from .config import settings
from .binance_client import binance_client
from .trading_strategy import trading_strategy
from .firebase_manager import firebase_manager
from datetime import datetime, timezone
import math

class BotCore:
    def __init__(self):
        self.status = {
            "is_running": False,
            "symbol": None,
            "position_side": None, # "LONG", "SHORT" veya None
            "status_message": "Bot başlatılmadı.",
            "current_balance": settings.INITIAL_ORDER_SIZE_USDT, # Başlangıç bakiyesi
            "current_symbol_index": 0, # İşlem yapılacak coin listesi için index
            "last_signal": "N/A", # Son gelen sinyal
            "in_position": False # Pozisyonda olup olmadığını gösterir
        }
        self.klines: list = []
        self._stop_requested: bool = False
        self.quantity_precision: int = 0
        self.price_precision: int = 0
        self.current_websocket_task: asyncio.Task | None = None # Aktif WebSocket görevini tutar

    def _get_precision_from_filter(self, symbol_info, filter_type, key):
        """Binance sembol bilgilerinden miktar/fiyat hassasiyetini alır."""
        for f in symbol_info['filters']:
            if f['filterType'] == filter_type:
                size_str = f[key]
                if '.' in size_str:
                    return len(size_str.split('.')[1].rstrip('0'))
                return 0
        return 0

    async def start(self, initial_symbol: str = None):
        """Botu başlatır ve işlem döngüsünü tetikler."""
        if self.status["is_running"]:
            print("Bot zaten çalışıyor.")
            self.status["status_message"] = "Bot zaten çalışıyor."
            return

        self._stop_requested = False
        self.status["is_running"] = True
        self.status["status_message"] = "Bot başlatılıyor..."
        print(self.status["status_message"])

        await binance_client.initialize()
        
        # Eğer manuel sembol verilmediyse, listeden ilkini al
        if initial_symbol:
            # Eğer verilen sembol listede yoksa ekleyelim ve sadece onu izleyelim
            if initial_symbol.upper() not in settings.SYMBOLS_TO_TRADE:
                settings.SYMBOLS_TO_TRADE = [initial_symbol.upper()]
                self.status["current_symbol_index"] = 0
                print(f"UYARI: {initial_symbol} SYMBOLS_TO_TRADE listesinde yoktu, sadece bu sembol izlenecek.")
            else:
                self.status["current_symbol_index"] = settings.SYMBOLS_TO_TRADE.index(initial_symbol.upper())

            self.status["symbol"] = initial_symbol.upper()
        else:
            if not settings.SYMBOLS_TO_TRADE:
                self.status["status_message"] = "İşlem yapılacak coin listesi boş. Bot durduruluyor."
                await self.stop()
                return
            self.status["symbol"] = settings.SYMBOLS_TO_TRADE[self.status["current_symbol_index"]]

        await self._start_trading_for_symbol(self.status["symbol"])

    async def _start_trading_for_symbol(self, symbol: str):
        """Belirli bir sembol için işlem döngüsünü başlatır."""
        if not self.status["is_running"] or self._stop_requested:
            print(f"Bot durdurulduğu için {symbol} işlemi başlatılmıyor.")
            return

        self.status.update({"symbol": symbol, "position_side": None, "in_position": False, "status_message": f"{symbol} için başlatılıyor..."})
        print(f"--> {symbol} üzerinde işlem başlıyor.")

        symbol_info = await binance_client.get_symbol_info(symbol)
        if not symbol_info:
            self.status["status_message"] = f"{symbol} için borsa bilgileri alınamadı. Sonraki coine geçiliyor..."
            print(self.status["status_message"])
            await self._try_next_symbol()
            return
        
        # Hassasiyetleri al
        self.quantity_precision = self._get_precision_from_filter(symbol_info, 'LOT_SIZE', 'stepSize')
        self.price_precision = self._get_precision_from_filter(symbol_info, 'PRICE_FILTER', 'tickSize')
        print(f"{symbol} için Miktar Hassasiyeti: {self.quantity_precision}, Fiyat Hassasiyeti: {self.price_precision}")
        
        # Kaldıracı ayarla
        if not await binance_client.set_leverage(symbol, settings.LEVERAGE):
            self.status["status_message"] = "Kaldıraç ayarlanamadı. Sonraki coine geçiliyor..."
            print(self.status["status_message"])
            await self._try_next_symbol()
            return

        # Geçmiş mum verilerini çek
        self.klines = await binance_client.get_historical_klines(symbol, settings.TIMEFRAME, limit=50)
        if not self.klines:
            self.status["status_message"] = "Geçmiş veri alınamadı. Sonraki coine geçiliyor..."
            print(self.status["status_message"])
            await self._try_next_symbol()
            return

        self.status["status_message"] = f"{symbol} ({settings.TIMEFRAME}) için sinyal bekleniyor..."
        print(self.status["status_message"])

        # Mevcut WebSocket görevini iptal et ve yenisini başlat
        if self.current_websocket_task:
            self.current_websocket_task.cancel()
            try:
                await self.current_websocket_task # Önceki görevin sonlanmasını bekle
            except asyncio.CancelledError:
                pass # İptal edildiği için hata vermemeli

        # Yeni WebSocket görevini oluştur ve başlat
        self.current_websocket_task = asyncio.create_task(self._run_websocket(symbol))


    async def _run_websocket(self, symbol: str):
        """Belirli bir sembol için WebSocket bağlantısını yönetir."""
        ws_url = f"{settings.WEBSOCKET_URL}/ws/{symbol.lower()}@kline_{settings.TIMEFRAME}"
        while not self._stop_requested and self.status["is_running"] and self.status["symbol"] == symbol:
            try:
                async with websockets.connect(ws_url, ping_interval=30, ping_timeout=15) as ws:
                    print(f"WebSocket bağlantısı kuruldu: {ws_url}")
                    while not self._stop_requested and self.status["is_running"] and self.status["symbol"] == symbol:
                        try:
                            message = await asyncio.wait_for(ws.recv(), timeout=60.0)
                            await self._handle_websocket_message(message)
                        except (asyncio.TimeoutError, websockets.exceptions.ConnectionClosed):
                            print(f"{symbol} piyasa veri akışı bağlantı sorunu. Yeniden bağlanılıyor...")
                            break # Inner while döngüsünden çıkıp dıştaki while döngüsüne düşer
                        except asyncio.CancelledError:
                            print(f"WebSocket görevi {symbol} için iptal edildi.")
                            return # Görev iptal edilirse tamamen çık
            except Exception as e:
                print(f"WebSocket bağlantı hatası ({symbol}): {e}. Yeniden deneniyor...")
                self.status["status_message"] = f"WebSocket bağlantı hatası ({symbol})."
                await asyncio.sleep(5) # Hata durumunda kısa bekleme ve yeniden deneme
        
        # WebSocket döngüsü bittiğinde (bot durdurulduğunda veya sembol değiştiğinde)
        if not self._stop_requested and self.status["is_running"]:
            print(f"WebSocket {symbol} için kapandı veya sembol değişti. Yeni bir sembole geçiliyor...")
            await self._try_next_symbol() # Sembol değiştiyse veya bağlantı koptuysa sonraki coine geç

    async def _try_next_symbol(self):
        """Sıradaki işlem yapılacak coine geçer."""
        if not self.status["is_running"] or self._stop_requested:
            return # Bot durdurulmuşsa veya durdurma isteği varsa çık

        if not settings.SYMBOLS_TO_TRADE:
            self.status["status_message"] = "İşlem yapılacak coin listesi boş. Bot durduruluyor."
            await self.stop()
            return

        current_index = self.status["current_symbol_index"]
        next_index = (current_index + 1) % len(settings.SYMBOLS_TO_TRADE)
        self.status["current_symbol_index"] = next_index
        next_symbol = settings.SYMBOLS_TO_TRADE[next_index]

        if next_symbol == self.status["symbol"] and len(settings.SYMBOLS_TO_TRADE) > 1:
            print(f"Tüm coinler denendi, başa dönülüyor ({next_symbol}).")
        elif len(settings.SYMBOLS_TO_TRADE) == 1:
            print(f"Tek coin mevcut ({next_symbol}), tekrar deneniyor.")

        print(f"Sonraki sembole geçiliyor: {next_symbol}")
        await asyncio.sleep(3) # Coin geçişleri arasında biraz bekleme
        await self._start_trading_for_symbol(next_symbol) # Yeni sembol ile başlat

    async def stop(self):
        """Botu durdurur ve tüm işlemleri temizler."""
        self._stop_requested = True
        if self.current_websocket_task:
            self.current_websocket_task.cancel() # Aktif WebSocket görevini iptal et
            try:
                await self.current_websocket_task # Görevin tamamlanmasını bekle
            except asyncio.CancelledError:
                pass # Görev iptal edildiğinde beklenen hata

        if self.status["is_running"]:
            self.status.update({
                "is_running": False, 
                "symbol": None, 
                "position_side": None, 
                "in_position": False,
                "status_message": "Bot durduruldu.",
                "last_signal": "N/A"
            })
            print(self.status["status_message"])
            await binance_client.close() # Binance bağlantısını kapat

    async def _handle_websocket_message(self, message: str):
        """WebSocket'ten gelen mum verilerini işler ve stratejiyi uygular."""
        data = json.loads(message)
        
        # Eğer mum kapanmadıysa veya bizim sembolümüze ait değilse işlem yapma
        if not data.get('k', {}).get('x', False) or data['k']['s'].upper() != self.status["symbol"]:
            return
            
        current_symbol = self.status["symbol"]
        
        print(f"Yeni mum kapandı: {current_symbol} ({settings.TIMEFRAME}) - Kapanış: {data['k']['c']}")
        
        # Klines listesini güncelle (en eski mumu çıkar, yeni mumu ekle)
        # Deep copy yerine, sadece gerekli kısımları alarak performans artırımı
        self.klines.pop(0)
        self.klines.append([data['k'][key] for key in ['t','o','h','l','c','v','T','q','n','V','Q']] + ['0'])
        
        # Mevcut açık pozisyonları kontrol et
        open_positions = await binance_client.get_open_positions(current_symbol)
        
        # Pozisyon durumu güncellemesi
        self.status["in_position"] = bool(open_positions)
        if open_positions:
            position_amt = float(open_positions[0]['positionAmt'])
            self.status["position_side"] = "LONG" if position_amt > 0 else "SHORT"
        else:
            # Eğer open_positions boşsa ve daha önce bir pozisyon vardıysa (position_side None değilse),
            # bu pozisyonun SL/TP veya manuel olarak kapandığı anlamına gelir.
            if self.status["position_side"] is not None:
                print(f"--> Pozisyon SL/TP veya başka bir nedenle kapandı. PNL hesaplanıyor...")
                pnl = await binance_client.get_last_trade_pnl(current_symbol)
                log_status = "CLOSED_BY_TP" if pnl > 0 else ("CLOSED_BY_SL" if pnl < 0 else "CLOSED_MANUALLY")
                
                firebase_manager.log_trade({
                    "symbol": current_symbol, 
                    "pnl": pnl, 
                    "status": log_status, 
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
                
                # Katlamalı sistem: Kârı (veya zararı) ana bakiyeye ekle
                self.status["current_balance"] += pnl
                # Minimum işlem boyutunun altına düşmemek için bir kontrol eklenebilir.
                # Örneğin: max(settings.INITIAL_ORDER_SIZE_USDT, self.status["current_balance"])
                settings.ORDER_SIZE_USDT = self.status["current_balance"] 
                
                print(f"Güncel bakiye: {self.status['current_balance']:.2f} USDT. Sonraki işlem boyutu: {settings.ORDER_SIZE_USDT:.2f} USDT.")
                
                self.status["position_side"] = None
                self.status["in_position"] = False
                
                # Pozisyon kapandıktan sonra bir sonraki uygun coine geç
                await self._try_next_symbol()
                return # Pozisyon kapandığı için bu döngüde yeni sinyal analizine devam etme

        # Yeni sinyali al
        signal = trading_strategy.analyze_klines(self.klines)
        self.status["last_signal"] = signal
        print(f"Strateji analizi sonucu: {signal}")

        # Ek onay kontrolü (Yeni Eklendi)
        if settings.USE_ADDITIONAL_CONFIRMATION and signal != "HOLD":
            print(f"Ek onay kontrolü yapılıyor ({settings.CONFIRMATION_TIMEFRAME})...")
            # Daha büyük zaman dilimi verisini çek
            confirmation_klines = await binance_client.get_historical_klines(current_symbol, settings.CONFIRMATION_TIMEFRAME, limit=50)
            if not confirmation_klines:
                print(f"Ek onay için geçmiş veri alınamadı. Sinyal yoksayılıyor.")
                return # Ek onay alınamazsa sinyali yoksay

            confirmation_signal = trading_strategy.analyze_klines(confirmation_klines)
            print(f"Ek onay sinyali ({settings.CONFIRMATION_TIMEFRAME}): {confirmation_signal}")
            
            if signal != confirmation_signal:
                print(f"Sinyaller uyuşmuyor ({signal} vs {confirmation_signal}). İşlem açılmıyor.")
                return # Sinyaller uyuşmuyorsa işlem açma

        # Eğer şu an pozisyonda değilsek ve yeni bir sinyal varsa, pozisyon aç
        if not self.status["in_position"] and signal != "HOLD":
            print(f"--> Yeni {signal} pozisyonu açılıyor...")
            side = "BUY" if signal == "LONG" else "SELL"
            price = await binance_client.get_market_price(current_symbol)
            
            if not price:
                print("Yeni pozisyon için piyasa fiyatı alınamadı.")
                self.status["status_message"] = "Piyasa fiyatı alınamadı, pozisyon açılamadı."
                return

            # Dinamik işlem boyutu hesaplaması
            # ORDER_SIZE_USDT şu anki güncel bakiyemizle aynı olacak
            quantity = self._format_quantity((settings.ORDER_SIZE_USDT / price) * settings.LEVERAGE)
            
            if quantity <= 0:
                print("Hesaplanan miktar çok düşük. İşlem açılamadı.")
                self.status["status_message"] = "Hesaplanan miktar çok düşük, pozisyon açılamadı."
                return

            order = await binance_client.create_market_order_with_sl_tp(current_symbol, side, quantity, price, self.price_precision)
            
            if order:
                self.status["position_side"] = signal
                self.status["in_position"] = True
                self.status["status_message"] = f"Yeni {signal} pozisyonu {price} fiyattan açıldı."
                firebase_manager.log_trade({
                    "symbol": current_symbol, 
                    "entry_price": price, 
                    "side": signal, 
                    "quantity": quantity, 
                    "status": "OPEN", 
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
            else:
                self.status["position_side"] = None
                self.status["in_position"] = False
                self.status["status_message"] = "Yeni pozisyon açılamadı."
            print(self.status["status_message"])

    def _format_quantity(self, quantity: float):
        """Miktarı, sembolün hassasiyetine göre formatlar."""
        if self.quantity_precision == 0:
            return math.floor(quantity)
        factor = 10 ** self.quantity_precision
        return math.floor(quantity * factor) / factor

bot_core = BotCore()