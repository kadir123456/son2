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
from typing import Dict, Optional

class CoinTracker:
    """Her coin için bağımsız pozisyon ve strateji takibi"""
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.klines: list = []
        self.position_side: Optional[str] = None  # "LONG", "SHORT" veya None
        self.in_position: bool = False
        self.last_signal: str = "N/A"
        self.quantity_precision: int = 0
        self.price_precision: int = 0
        self.websocket_task: Optional[asyncio.Task] = None

class BotCore:
    def __init__(self):
        self.status = {
            "is_running": False,
            "total_balance": settings.INITIAL_ORDER_SIZE_USDT,
            "active_coins": {},  # Her coin için detaylı durum
            "total_positions": 0,
            "status_message": "Bot başlatılmadı."
        }
        self.coin_trackers: Dict[str, CoinTracker] = {}
        self._stop_requested: bool = False

    def _get_precision_from_filter(self, symbol_info, filter_type, key):
        """Binance sembol bilgilerinden miktar/fiyat hassasiyetini alır."""
        for f in symbol_info['filters']:
            if f['filterType'] == filter_type:
                size_str = f[key]
                if '.' in size_str:
                    return len(size_str.split('.')[1].rstrip('0'))
                return 0
        return 0

    async def add_coin(self, symbol: str, order_size_usdt: float) -> bool:
        """Yeni bir coin ekler ve işlem başlatır"""
        if not self.status["is_running"]:
            await self._initialize_bot()
        
        symbol = symbol.upper()
        
        if symbol in self.coin_trackers:
            print(f"⚠️ {symbol} zaten izleniyor.")
            return False

        # Sembol bilgilerini kontrol et
        symbol_info = await binance_client.get_symbol_info(symbol)
        if not symbol_info:
            print(f"❌ {symbol} için borsa bilgileri alınamadı.")
            return False

        # Yeni coin tracker oluştur
        tracker = CoinTracker(symbol)
        tracker.quantity_precision = self._get_precision_from_filter(symbol_info, 'LOT_SIZE', 'stepSize')
        tracker.price_precision = self._get_precision_from_filter(symbol_info, 'PRICE_FILTER', 'tickSize')
        
        print(f"📊 {symbol} - Miktar Hassasiyeti: {tracker.quantity_precision}, Fiyat Hassasiyeti: {tracker.price_precision}")
        
        # Kaldıracı ayarla
        if not await binance_client.set_leverage(symbol, settings.LEVERAGE):
            print(f"❌ {symbol} için kaldıraç ayarlanamadı.")
            return False

        # Geçmiş mum verilerini çek
        tracker.klines = await binance_client.get_historical_klines(symbol, settings.TIMEFRAME, limit=50)
        if not tracker.klines:
            print(f"❌ {symbol} için geçmiş veri alınamadı.")
            return False

        # Coin tracker'ı kaydet
        self.coin_trackers[symbol] = tracker
        
        # Durum güncelle
        self.status["active_coins"][symbol] = {
            "order_size_usdt": order_size_usdt,
            "position_side": None,
            "in_position": False,
            "last_signal": "N/A",
            "pnl": 0.0
        }

        # WebSocket başlat
        tracker.websocket_task = asyncio.create_task(self._run_websocket_for_coin(symbol))
        
        print(f"✅ {symbol} başarıyla eklendi ve izleniyor. İşlem boyutu: {order_size_usdt} USDT")
        self._update_status_message()
        return True

    async def remove_coin(self, symbol: str) -> bool:
        """Coin'i izlemekten çıkarır ve pozisyon varsa kapatır"""
        symbol = symbol.upper()
        
        if symbol not in self.coin_trackers:
            print(f"⚠️ {symbol} zaten izlenmiyor.")
            return False

        tracker = self.coin_trackers[symbol]
        
        # Önce açık pozisyonu kapat
        if tracker.in_position:
            await self._close_position_for_coin(symbol)
            await asyncio.sleep(1)  # Pozisyon kapanması için bekleme

        # WebSocket görevini iptal et
        if tracker.websocket_task:
            tracker.websocket_task.cancel()
            try:
                await tracker.websocket_task
            except asyncio.CancelledError:
                pass

        # Tracker'ı kaldır
        del self.coin_trackers[symbol]
        if symbol in self.status["active_coins"]:
            del self.status["active_coins"][symbol]

        print(f"🗑️ {symbol} izlemeden çıkarıldı.")
        self._update_status_message()
        return True

    async def _initialize_bot(self):
        """Bot'un temel bileşenlerini başlatır"""
        if not self.status["is_running"]:
            await binance_client.initialize()
            self.status["is_running"] = True
            print("🤖 Bot core başlatıldı.")

    async def start_monitoring(self):
        """Genel bot durumunu başlatır"""
        if self.status["is_running"]:
            print("⚠️ Bot zaten çalışıyor.")
            return

        self._stop_requested = False
        await self._initialize_bot()
        self._update_status_message()

    async def stop_all(self):
        """Tüm coin'leri durdurur ve botu kapatır"""
        self._stop_requested = True
        
        # Tüm coin'ler için pozisyonları kapat ve websocket'leri iptal et
        for symbol in list(self.coin_trackers.keys()):
            await self.remove_coin(symbol)

        # Bot durumunu sıfırla
        self.status.update({
            "is_running": False,
            "active_coins": {},
            "total_positions": 0,
            "status_message": "Bot durduruldu."
        })
        
        print("🛑 Bot durduruldu ve tüm pozisyonlar kapatıldı.")
        await binance_client.close()

    async def _run_websocket_for_coin(self, symbol: str):
        """Belirli bir coin için WebSocket bağlantısını yönetir"""
        ws_url = f"{settings.WEBSOCKET_URL}/ws/{symbol.lower()}@kline_{settings.TIMEFRAME}"
        tracker = self.coin_trackers.get(symbol)
        
        if not tracker:
            return

        while not self._stop_requested and symbol in self.coin_trackers:
            try:
                async with websockets.connect(ws_url, ping_interval=30, ping_timeout=15) as ws:
                    print(f"🔗 {symbol} WebSocket bağlantısı kuruldu")
                    while not self._stop_requested and symbol in self.coin_trackers:
                        try:
                            message = await asyncio.wait_for(ws.recv(), timeout=60.0)
                            await self._handle_websocket_message_for_coin(symbol, message)
                        except (asyncio.TimeoutError, websockets.exceptions.ConnectionClosed):
                            print(f"⚠️ {symbol} WebSocket bağlantı sorunu. Yeniden bağlanılıyor...")
                            break
                        except asyncio.CancelledError:
                            print(f"🛑 {symbol} WebSocket görevi iptal edildi.")
                            return
            except Exception as e:
                if symbol in self.coin_trackers:  # Sadece hala izlenen coin'ler için hata mesajı
                    print(f"❌ {symbol} WebSocket hatası: {e}")
                    await asyncio.sleep(5)

    async def _handle_websocket_message_for_coin(self, symbol: str, message: str):
        """Belirli bir coin için WebSocket mesajını işler"""
        if symbol not in self.coin_trackers:
            return

        tracker = self.coin_trackers[symbol]
        data = json.loads(message)
        
        # Mum kapanma kontrolü
        if not data.get('k', {}).get('x', False) or data['k']['s'].upper() != symbol:
            return

        print(f"📊 {symbol} yeni mum kapandı - Kapanış: {data['k']['c']}")
        
        # Klines güncelle
        tracker.klines.pop(0)
        tracker.klines.append([data['k'][key] for key in ['t','o','h','l','c','v','T','q','n','V','Q']] + ['0'])
        
        # Pozisyon durumunu kontrol et
        open_positions = await binance_client.get_open_positions(symbol)
        was_in_position = tracker.in_position
        
        tracker.in_position = bool(open_positions)
        
        if open_positions:
            position_amt = float(open_positions[0]['positionAmt'])
            tracker.position_side = "LONG" if position_amt > 0 else "SHORT"
        else:
            # Pozisyon kapandıysa PNL hesapla
            if was_in_position and tracker.position_side:
                await self._handle_position_closed(symbol)
            tracker.position_side = None

        # Strateji analizi
        signal = trading_strategy.analyze_klines(tracker.klines)
        tracker.last_signal = signal
        
        print(f"📈 {symbol} sinyal analizi: {signal}")

        # İşlem mantığı
        await self._process_signal_for_coin(symbol, signal)
        
        # Durumu güncelle
        self._update_coin_status(symbol)

    async def _process_signal_for_coin(self, symbol: str, signal: str):
        """Geliştirilmiş sinyal işleme mantığı"""
        tracker = self.coin_trackers[symbol]
        order_size = self.status["active_coins"][symbol]["order_size_usdt"]

        # Eğer pozisyon yoksa ve sinyal varsa aç
        if not tracker.in_position and signal != "HOLD":
            await self._open_position_for_coin(symbol, signal, order_size)
        
        # Eğer pozisyon varsa ve sinyal farklıysa - akıllı pozisyon değiştirme
        elif tracker.in_position and signal != "HOLD" and signal != tracker.position_side:
            # Strateji güvenilirliğini kontrol et
            if trading_strategy.should_reverse_position(symbol, tracker.position_side, signal):
                print(f"🔄 {symbol} pozisyon değişimi: {tracker.position_side} → {signal}")
                await self._close_position_for_coin(symbol)
                await asyncio.sleep(1.0)  # Pozisyon kapanması için daha uzun bekleme
                await self._open_position_for_coin(symbol, signal, order_size)
            else:
                print(f"⚠️ {symbol} pozisyon değişimi güvenilirlik kontrolünden geçemedi")
        
        # Eğer HOLD sinyali gelirse ve pozisyon açıksa, pozisyonu kapat (opsiyonel)
        elif tracker.in_position and signal == "HOLD":
            # Bu özellik isteğe bağlı - config'den kontrol edilebilir
            if hasattr(settings, 'CLOSE_ON_HOLD_SIGNAL') and settings.CLOSE_ON_HOLD_SIGNAL:
                print(f"⏸️ {symbol} HOLD sinyali nedeniyle pozisyon kapatılıyor")
                await self._close_position_for_coin(symbol)

    async def _open_position_for_coin(self, symbol: str, signal: str, order_size_usdt: float):
        """Belirli coin için pozisyon açar"""
        tracker = self.coin_trackers[symbol]
        side = "BUY" if signal == "LONG" else "SELL"
        price = await binance_client.get_market_price(symbol)
        
        if not price:
            print(f"❌ {symbol} için piyasa fiyatı alınamadı.")
            return

        quantity = self._format_quantity(
            (order_size_usdt / price) * settings.LEVERAGE, 
            tracker.quantity_precision
        )
        
        if quantity <= 0:
            print(f"❌ {symbol} için hesaplanan miktar çok düşük.")
            return

        order = await binance_client.create_market_order_with_sl_tp(
            symbol, side, quantity, price, tracker.price_precision
        )
        
        if order:
            tracker.position_side = signal
            tracker.in_position = True
            print(f"✅ {symbol} {signal} pozisyonu açıldı: {price} USDT")
            
            firebase_manager.log_trade({
                "symbol": symbol,
                "entry_price": price,
                "side": signal,
                "quantity": quantity,
                "order_size_usdt": order_size_usdt,
                "status": "OPEN",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

    async def _close_position_for_coin(self, symbol: str):
        """Belirli coin için pozisyonu kapatır"""
        tracker = self.coin_trackers[symbol]
        
        if not tracker.in_position:
            return

        open_positions = await binance_client.get_open_positions(symbol)
        if not open_positions:
            return

        position_amt = float(open_positions[0]['positionAmt'])
        side_to_close = 'SELL' if position_amt > 0 else 'BUY'
        
        response = await binance_client.close_position(symbol, position_amt, side_to_close)
        
        if response:
            print(f"🔴 {symbol} pozisyonu kapatıldı.")
            tracker.in_position = False
            tracker.position_side = None

    async def _handle_position_closed(self, symbol: str):
        """Pozisyon kapandığında PNL hesaplar ve kaydeder"""
        pnl = await binance_client.get_last_trade_pnl(symbol)
        log_status = "CLOSED_BY_TP" if pnl > 0 else ("CLOSED_BY_SL" if pnl < 0 else "CLOSED_MANUALLY")
        
        # Toplam bakiyeyi güncelle
        self.status["total_balance"] += pnl
        self.status["active_coins"][symbol]["pnl"] += pnl
        
        print(f"💰 {symbol} PNL: {pnl:.2f} USDT. Toplam bakiye: {self.status['total_balance']:.2f} USDT")
        
        firebase_manager.log_trade({
            "symbol": symbol,
            "pnl": pnl,
            "status": log_status,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

    def _format_quantity(self, quantity: float, precision: int):
        """Miktarı hassasiyete göre formatlar"""
        if precision == 0:
            return math.floor(quantity)
        factor = 10 ** precision
        return math.floor(quantity * factor) / factor

    def _update_coin_status(self, symbol: str):
        """Coin durumunu günceller"""
        if symbol not in self.coin_trackers:
            return
            
        tracker = self.coin_trackers[symbol]
        self.status["active_coins"][symbol].update({
            "position_side": tracker.position_side,
            "in_position": tracker.in_position,
            "last_signal": tracker.last_signal
        })
        
        # Toplam pozisyon sayısını güncelle
        self.status["total_positions"] = sum(
            1 for coin_status in self.status["active_coins"].values() 
            if coin_status["in_position"]
        )
        
        self._update_status_message()

    def _update_status_message(self):
        """Durum mesajını günceller"""
        active_count = len(self.status["active_coins"])
        position_count = self.status["total_positions"]
        
        if not self.status["is_running"]:
            self.status["status_message"] = "Bot durduruldu."
        elif active_count == 0:
            self.status["status_message"] = "Bot çalışıyor, coin bekleniyor."
        else:
            self.status["status_message"] = f"{active_count} coin izleniyor, {position_count} pozisyon açık."

    def get_detailed_status(self):
        """Detaylı durum bilgisi döndürür"""
        return {
            **self.status,
            "coin_details": {
                symbol: {
                    **coin_status,
                    "last_signal": self.coin_trackers[symbol].last_signal if symbol in self.coin_trackers else "N/A"
                }
                for symbol, coin_status in self.status["active_coins"].items()
            }
        }

bot_core = BotCore()
