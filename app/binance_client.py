import asyncio
from binance import AsyncClient
from binance.exceptions import BinanceAPIException
from .config import settings
import time
from typing import Optional, Dict, Any, Tuple

class EnhancedBinanceClient:
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
        self._rate_limit_delay_time = 0.1
        self._debug_enabled = settings.DEBUG_MODE if hasattr(settings, 'DEBUG_MODE') else True
        
        # 🎯 Kademeli satış tracking
        self._partial_exit_positions = {}  # Symbol -> {tp1_executed, tp2_executed, original_qty}
        self._sl_tightening_positions = {}  # Symbol -> {tightened, original_sl}
        
        # 🛡️ TP/SL KORUMA SİSTEMİ
        self._protected_orders = {}  # Symbol -> {sl_order_id, tp_order_id, tp1_order_id, tp2_order_id}
        self._last_tp_sl_check = {}  # Symbol -> last_check_time
        self._tp_sl_protection_interval = 30  # 30 saniyede bir kontrol
        
        print(f"🎯 ENHANCED Binance İstemcisi başlatılıyor. Ortam: {settings.ENVIRONMENT}")
        print(f"✅ Kademeli satış: {'Aktif' if settings.ENABLE_PARTIAL_EXITS else 'Deaktif'}")
        print(f"✅ SL Tightening: {'Aktif' if settings.ENABLE_SL_TIGHTENING else 'Deaktif'}")
        print(f"🛡️ TP/SL Koruma Sistemi: Aktif")
        
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
                    
                print("✅ Enhanced Binance AsyncClient başarıyla başlatıldı.")
                print(f"📊 {len(self.exchange_info['symbols'])} sembol bilgisi yüklendi")
                
                # Test connection
                await self._test_connection()
                
                # TP/SL koruma task'ını başlat
                asyncio.create_task(self._tp_sl_protection_loop())
                
            except BinanceAPIException as e:
                print(f"❌ Binance API Hatası: {e}")
                raise e
            except Exception as e:
                print(f"❌ Binance bağlantı hatası: {e}")
                raise e
                
        return self.client

    async def _tp_sl_protection_loop(self):
        """🛡️ TP/SL koruma döngüsü - emirlerin silinmesini engeller"""
        print("🛡️ TP/SL koruma sistemi başlatıldı")
        
        while True:
            try:
                await self._check_and_restore_tp_sl()
                await asyncio.sleep(self._tp_sl_protection_interval)
            except Exception as e:
                print(f"❌ TP/SL koruma döngüsü hatası: {e}")
                await asyncio.sleep(5)

    async def _check_and_restore_tp_sl(self):
        """Tüm açık pozisyonların TP/SL'lerini kontrol et ve restore et"""
        try:
            if not self.client:
                return
                
            # Tüm açık pozisyonları al
            await self._rate_limit_delay()
            all_positions = await self.client.futures_position_information()
            open_positions = [p for p in all_positions if float(p['positionAmt']) != 0]
            
            for position in open_positions:
                symbol = position['symbol']
                await self._ensure_tp_sl_exists(symbol, position)
                await asyncio.sleep(0.5)  # Rate limiting
                
        except Exception as e:
            print(f"❌ TP/SL kontrol hatası: {e}")

    async def _ensure_tp_sl_exists(self, symbol: str, position: dict):
        """Belirli bir pozisyon için TP/SL'nin var olduğundan emin ol"""
        try:
            position_amt = float(position['positionAmt'])
            if position_amt == 0:
                return
                
            # Açık emirleri kontrol et
            await self._rate_limit_delay()
            open_orders = await self.client.futures_get_open_orders(symbol=symbol)
            
            # TP/SL emirlerini analiz et
            has_sl = any(order['type'] in ['STOP_MARKET', 'STOP'] for order in open_orders)
            has_tp = any(order['type'] in ['TAKE_PROFIT_MARKET', 'TAKE_PROFIT', 'LIMIT'] 
                        and order.get('reduceOnly') for order in open_orders)
            
            # Eksik TP/SL varsa ekle
            if not has_sl or not has_tp:
                print(f"⚠️ {symbol} eksik koruma tespit edildi! SL: {has_sl}, TP: {has_tp}")
                await self._restore_missing_tp_sl(symbol, position, has_sl, has_tp)
                
        except Exception as e:
            print(f"❌ {symbol} TP/SL kontrol hatası: {e}")

    async def _restore_missing_tp_sl(self, symbol: str, position: dict, has_sl: bool, has_tp: bool):
        """Eksik TP/SL'leri yeniden ekle"""
        try:
            position_amt = float(position['positionAmt'])
            entry_price = float(position['entryPrice'])
            
            # Symbol bilgilerini al
            symbol_info = await self.get_symbol_info(symbol)
            if not symbol_info:
                print(f"❌ {symbol} sembol bilgisi alınamadı")
                return
                
            price_precision = self._get_precision_from_filter(symbol_info, 'PRICE_FILTER', 'tickSize')
            
            # TP/SL ekle
            success = await self._add_missing_protection(
                symbol, position_amt, entry_price, price_precision, has_sl, has_tp
            )
            
            if success:
                print(f"✅ {symbol} TP/SL koruma restore edildi")
            else:
                print(f"❌ {symbol} TP/SL restore başarısız")
                
        except Exception as e:
            print(f"❌ {symbol} TP/SL restore hatası: {e}")

    def _should_use_partial_exits(self, timeframe: str) -> bool:
        """Kademeli satış kullanılmalı mı kontrol et"""
        if not settings.ENABLE_PARTIAL_EXITS:
            return False
            
        return timeframe in settings.TIMEFRAMES_FOR_PARTIAL

    async def create_market_order_with_smart_exits(self, symbol: str, side: str, quantity: float, 
                                                  entry_price: float, price_precision: int, 
                                                  timeframe: str) -> Optional[Dict]:
        """
        🎯 ENHANCED: Akıllı çıkış sistemi - TP/SL koruma ile
        """
        if self._should_use_partial_exits(timeframe):
            print(f"🎯 {symbol}: Kademeli satış sistemi kullanılıyor (timeframe: {timeframe})")
            return await self._create_partial_exit_position(symbol, side, quantity, entry_price, price_precision)
        else:
            print(f"🎯 {symbol}: Normal TP/SL sistemi kullanılıyor (timeframe: {timeframe})")
            return await self._create_normal_position(symbol, side, quantity, entry_price, price_precision)

    async def _create_partial_exit_position(self, symbol: str, side: str, quantity: float, 
                                          entry_price: float, price_precision: int) -> Optional[Dict]:
        """
        🎯 Kademeli satış pozisyonu oluştur - KORUMALI SÜRÜM
        """
        def format_price(price):
            return f"{price:.{price_precision}f}"
            
        try:
            print(f"🎯 {symbol} KADEMELI SATIŞ pozisyonu oluşturuluyor:")
            print(f"   Yön: {side}, Miktar: {quantity}, Fiyat: {entry_price}")
            
            # Test modu kontrolü
            if hasattr(settings, 'TEST_MODE') and settings.TEST_MODE:
                print(f"🧪 TEST: {symbol} kademeli satış simüle edildi")
                return {"orderId": "TEST_PARTIAL_" + str(int(time.time())), "status": "FILLED"}
            
            # 🛡️ SADECE YETİM EMİRLERİ TEMİZLE (TP/SL değil)
            await self._safe_cancel_orphan_orders(symbol)
            await asyncio.sleep(0.3)
            
            # 📈 Ana pozisyonu aç
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
            
            # 🎯 Kademeli satış fiyatlarını hesapla
            if side == 'BUY':  # Long pozisyon
                sl_price = entry_price * (1 - settings.STOP_LOSS_PERCENT)
                tp1_price = entry_price * (1 + settings.TP1_PERCENT)
                tp2_price = entry_price * (1 + settings.TP2_PERCENT)
                opposite_side = 'SELL'
            else:  # Short pozisyon
                sl_price = entry_price * (1 + settings.STOP_LOSS_PERCENT)
                tp1_price = entry_price * (1 - settings.TP1_PERCENT)
                tp2_price = entry_price * (1 - settings.TP2_PERCENT)
                opposite_side = 'BUY'
            
            formatted_sl_price = format_price(sl_price)
            formatted_tp1_price = format_price(tp1_price)
            formatted_tp2_price = format_price(tp2_price)
            
            # Kademeli satış miktarlarını hesapla
            tp1_quantity = quantity * settings.TP1_EXIT_RATIO
            tp2_quantity = quantity * settings.TP2_EXIT_RATIO - tp1_quantity  # Kalan miktar
            
            print(f"💡 Kademeli satış planı:")
            print(f"   SL: {formatted_sl_price} (tüm pozisyon)")
            print(f"   TP1: {formatted_tp1_price} ({tp1_quantity} miktar - %{settings.TP1_EXIT_RATIO*100:.0f})")
            print(f"   TP2: {formatted_tp2_price} ({tp2_quantity} miktar - kalan)")
            
            # 🛡️ KORUMALI TP/SL oluştur
            sl_order = await self._create_protected_stop_loss(symbol, opposite_side, quantity, formatted_sl_price)
            tp1_order = await self._create_protected_take_profit_limit(symbol, opposite_side, tp1_quantity, 
                                                                     formatted_tp1_price, "TP1")
            tp2_order = await self._create_protected_take_profit_limit(symbol, opposite_side, tp2_quantity, 
                                                                     formatted_tp2_price, "TP2")
            
            # Koruma bilgilerini kaydet
            if sl_order or tp1_order or tp2_order:
                self._protected_orders[symbol] = {
                    'sl_order_id': sl_order.get('orderId') if sl_order else None,
                    'tp1_order_id': tp1_order.get('orderId') if tp1_order else None,
                    'tp2_order_id': tp2_order.get('orderId') if tp2_order else None,
                    'created_at': time.time(),
                    'entry_price': entry_price,
                    'position_type': 'partial_exit'
                }
            
            # Tracking bilgilerini kaydet
            self._partial_exit_positions[symbol] = {
                'tp1_executed': False,
                'tp2_executed': False,
                'original_qty': quantity,
                'tp1_qty': tp1_quantity,
                'tp2_qty': tp2_quantity,
                'entry_price': entry_price,
                'side': side
            }
            
            # Sonuç raporu
            success_count = sum([bool(sl_order), bool(tp1_order), bool(tp2_order)])
            if success_count >= 2:
                print(f"✅ {symbol} kademeli satış pozisyonu başarılı! ({success_count}/3 emir)")
            else:
                print(f"⚠️ {symbol} kademeli satış eksik emirler var ({success_count}/3)")
                
            return main_order
            
        except BinanceAPIException as e:
            print(f"❌ {symbol} kademeli satış hatası: {e}")
            await self._safe_cancel_orphan_orders(symbol)
            return None
        except Exception as e:
            print(f"❌ {symbol} beklenmeyen hata: {e}")
            await self._safe_cancel_orphan_orders(symbol)
            return None

    async def _create_normal_position(self, symbol: str, side: str, quantity: float, 
                                    entry_price: float, price_precision: int) -> Optional[Dict]:
        """
        Normal TP/SL pozisyonu oluştur - KORUMALI SÜRÜM
        """
        def format_price(price):
            return f"{price:.{price_precision}f}"
            
        try:
            print(f"🎯 {symbol} NORMAL TP/SL pozisyonu oluşturuluyor")
            
            # Test modu kontrolü
            if hasattr(settings, 'TEST_MODE') and settings.TEST_MODE:
                print(f"🧪 TEST: {symbol} normal pozisyon simüle edildi")
                return {"orderId": "TEST_NORMAL_" + str(int(time.time())), "status": "FILLED"}
            
            # 🛡️ SADECE YETİM EMİRLERİ TEMİZLE
            await self._safe_cancel_orphan_orders(symbol)
            await asyncio.sleep(0.3)
            
            # 📈 Ana pozisyonu aç
            await self._rate_limit_delay()
            main_order = await self.client.futures_create_order(
                symbol=symbol,
                side=side,
                type='MARKET',
                quantity=quantity
            )
            
            if not main_order or 'orderId' not in main_order:
                return None
                
            print(f"✅ Ana pozisyon başarılı: {symbol} {side} {quantity}")
            await asyncio.sleep(1.0)
            
            # Fiyatları hesapla
            if side == 'BUY':
                sl_price = entry_price * (1 - settings.STOP_LOSS_PERCENT)
                tp_price = entry_price * (1 + settings.TAKE_PROFIT_PERCENT)
                opposite_side = 'SELL'
            else:
                sl_price = entry_price * (1 + settings.STOP_LOSS_PERCENT)
                tp_price = entry_price * (1 - settings.TAKE_PROFIT_PERCENT)
                opposite_side = 'BUY'
            
            formatted_sl_price = format_price(sl_price)
            formatted_tp_price = format_price(tp_price)
            
            # 🛡️ KORUMALI SL ve TP oluştur
            sl_order = await self._create_protected_stop_loss(symbol, opposite_side, quantity, formatted_sl_price)
            tp_order = await self._create_protected_take_profit_market(symbol, opposite_side, quantity, formatted_tp_price)
            
            # Koruma bilgilerini kaydet
            if sl_order or tp_order:
                self._protected_orders[symbol] = {
                    'sl_order_id': sl_order.get('orderId') if sl_order else None,
                    'tp_order_id': tp_order.get('orderId') if tp_order else None,
                    'created_at': time.time(),
                    'entry_price': entry_price,
                    'position_type': 'normal'
                }
            
            if sl_order and tp_order:
                print(f"✅ {symbol} tam korumalı pozisyon!")
            else:
                print(f"⚠️ {symbol} eksik koruma: SL={bool(sl_order)}, TP={bool(tp_order)}")
                
            return main_order
            
        except Exception as e:
            print(f"❌ {symbol} normal pozisyon hatası: {e}")
            await self._safe_cancel_orphan_orders(symbol)
            return None

    async def _safe_cancel_orphan_orders(self, symbol: str):
        """🛡️ SADECE YETİM EMİRLERİ İPTAL ET (TP/SL korunur)"""
        try:
            await self._rate_limit_delay()
            open_orders = await self.client.futures_get_open_orders(symbol=symbol)
            
            # Korunacak emir ID'lerini al
            protected_ids = set()
            if symbol in self._protected_orders:
                protected_info = self._protected_orders[symbol]
                for order_id in [protected_info.get('sl_order_id'), 
                               protected_info.get('tp_order_id'),
                               protected_info.get('tp1_order_id'),
                               protected_info.get('tp2_order_id')]:
                    if order_id:
                        protected_ids.add(str(order_id))
            
            # Sadece korumasız emirleri iptal et
            orphan_orders = []
            for order in open_orders:
                order_id = str(order['orderId'])
                order_type = order['type']
                
                # TP/SL emirlerini koruma kontrolü
                is_tp_sl = order_type in ['STOP_MARKET', 'TAKE_PROFIT_MARKET', 'TAKE_PROFIT', 'LIMIT'] and order.get('reduceOnly')
                is_protected = order_id in protected_ids
                
                if not (is_tp_sl and is_protected):
                    orphan_orders.append(order)
            
            # Yetim emirleri iptal et
            for order in orphan_orders:
                try:
                    await self._rate_limit_delay()
                    await self.client.futures_cancel_order(symbol=symbol, orderId=order['orderId'])
                    print(f"🗑️ {symbol} yetim emir iptal edildi: {order['orderId']} ({order['type']})")
                except Exception as cancel_error:
                    print(f"⚠️ {symbol} emir iptal hatası: {cancel_error}")
                    
            if len(orphan_orders) > 0:
                print(f"✅ {symbol} {len(orphan_orders)} yetim emir temizlendi, TP/SL korundu")
            
        except Exception as e:
            print(f"❌ {symbol} güvenli emir iptali hatası: {e}")

    async def _create_protected_stop_loss(self, symbol: str, side: str, quantity: float, price: str) -> Optional[Dict]:
        """🛡️ Korumalı Stop Loss emri oluştur"""
        try:
            print(f"🛑 {symbol} Korumalı Stop Loss oluşturuluyor: {price}")
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
                print(f"✅ Korumalı Stop Loss başarılı: {price}")
                return sl_order
            return None
            
        except Exception as e:
            print(f"❌ Korumalı Stop Loss hatası: {e}")
            return None

    async def _create_protected_take_profit_market(self, symbol: str, side: str, quantity: float, price: str) -> Optional[Dict]:
        """🛡️ Korumalı Market Take Profit emri oluştur"""
        try:
            print(f"🎯 {symbol} Korumalı Take Profit oluşturuluyor: {price}")
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
                print(f"✅ Korumalı Take Profit başarılı: {price}")
                return tp_order
            return None
            
        except Exception as e:
            print(f"❌ Korumalı Take Profit hatası: {e}")
            return None

    async def _create_protected_take_profit_limit(self, symbol: str, side: str, quantity: float, 
                                                price: str, label: str = "TP") -> Optional[Dict]:
        """🛡️ Korumalı Limit Take Profit emri oluştur"""
        try:
            print(f"🎯 {symbol} Korumalı {label} Limit emri oluşturuluyor: {price} ({quantity} miktar)")
            await self._rate_limit_delay()
            
            tp_order = await self.client.futures_create_order(
                symbol=symbol,
                side=side,
                type='LIMIT',
                quantity=quantity,
                price=price,
                timeInForce='GTC',
                reduceOnly=True
            )
            
            if tp_order and 'orderId' in tp_order:
                print(f"✅ Korumalı {label} Limit emri başarılı: {price}")
                return tp_order
            return None
            
        except Exception as e:
            print(f"❌ Korumalı {label} Limit emri hatası: {e}")
            return None

    async def check_and_tighten_stop_loss(self, symbol: str) -> bool:
        """
        🛡️ ENHANCED: Stop-Loss Tightening - Mevcut TP'leri koruyarak
        """
        if not settings.ENABLE_SL_TIGHTENING:
            return False
            
        try:
            # Pozisyonu kontrol et
            positions = await self.get_open_positions(symbol, use_cache=False)
            if not positions:
                return False
                
            position = positions[0]
            position_amt = float(position['positionAmt'])
            if position_amt == 0:
                return False
                
            entry_price = float(position['entryPrice'])
            unrealized_pnl_ratio = float(position['unRealizedProfit']) / (abs(position_amt) * entry_price)
            
            # Kar threshold kontrolü
            if abs(unrealized_pnl_ratio) < settings.SL_TIGHTEN_PROFIT_THRESHOLD:
                return False  # Henüz yeterli kar yok
                
            # Daha önce sıkılaştırıldı mı?
            if symbol in self._sl_tightening_positions:
                if self._sl_tightening_positions[symbol]['tightened']:
                    return False  # Zaten sıkılaştırıldı
                    
            print(f"💰 {symbol}: Kar durumu tespit edildi (%{unrealized_pnl_ratio*100:.2f})")
            print(f"🎯 Stop-Loss sıkılaştırılıyor...")
            
            # 🛡️ SADECE SL EMİRLERİNİ İPTAL ET (TP'leri koru)
            await self._cancel_only_sl_orders(symbol)
            await asyncio.sleep(0.5)
            
            # Yeni sıkı SL hesapla
            is_long = position_amt > 0
            if is_long:
                new_sl_price = entry_price * (1 - settings.STOP_LOSS_PERCENT * settings.SL_TIGHTEN_RATIO)
                opposite_side = 'SELL'
            else:
                new_sl_price = entry_price * (1 + settings.STOP_LOSS_PERCENT * settings.SL_TIGHTEN_RATIO)
                opposite_side = 'BUY'
                
            # Symbol bilgilerini al
            symbol_info = await self.get_symbol_info(symbol)
            if symbol_info:
                price_precision = self._get_precision_from_filter(symbol_info, 'PRICE_FILTER', 'tickSize')
                formatted_sl_price = f"{new_sl_price:.{price_precision}f}"
                
                # Yeni sıkı SL oluştur
                sl_order = await self._create_protected_stop_loss(symbol, opposite_side, abs(position_amt), formatted_sl_price)
                
                if sl_order:
                    print(f"✅ {symbol} Stop-Loss sıkılaştırıldı: {formatted_sl_price}")
                    
                    # Koruma bilgisini güncelle
                    if symbol in self._protected_orders:
                        self._protected_orders[symbol]['sl_order_id'] = sl_order.get('orderId')
                    
                    # Tracking bilgisini güncelle
                    self._sl_tightening_positions[symbol] = {
                        'tightened': True,
                        'original_sl': entry_price * (1 - settings.STOP_LOSS_PERCENT if is_long else 1 + settings.STOP_LOSS_PERCENT),
                        'tightened_sl': new_sl_price
                    }
                    return True
                    
            return False
            
        except Exception as e:
            print(f"❌ {symbol} SL tightening hatası: {e}")
            return False

    async def _cancel_only_sl_orders(self, symbol: str):
        """🛡️ SADECE SL EMİRLERİNİ İPTAL ET (TP'leri koru)"""
        try:
            await self._rate_limit_delay()
            open_orders = await self.client.futures_get_open_orders(symbol=symbol)
            
            # Sadece SL emirlerini bul ve iptal et
            for order in open_orders:
                if order['type'] in ['STOP_MARKET', 'STOP'] and order.get('reduceOnly'):
                    try:
                        await self._rate_limit_delay()
                        await self.client.futures_cancel_order(symbol=symbol, orderId=order['orderId'])
                        print(f"🗑️ {symbol} SL emri iptal edildi: {order['orderId']}")
                    except Exception as cancel_error:
                        print(f"⚠️ {symbol} SL emir iptal hatası: {cancel_error}")
                        
        except Exception as e:
            print(f"❌ {symbol} SL emir iptali hatası: {e}")

    # Diğer metodları aynı bırak...
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

    def _get_precision_from_filter(self, symbol_info, filter_type, key):
        """Symbol precision'ını al"""
        for f in symbol_info['filters']:
            if f['filterType'] == filter_type:
                size_str = f[key]
                if '.' in size_str:
                    return len(size_str.split('.')[1].rstrip('0'))
                return 0
        return 0

    # Mevcut metodları koruyalım - aynı işlevsellik
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
        
    async def get_open_positions(self, symbol: str, use_cache: bool = True):
        """Açık pozisyonları getir"""
        try:
            current_time = time.time()
            cache_key = symbol
            
            # Cache kontrolü
            if use_cache and cache_key in self._last_position_check:
                if current_time - self._last_position_check[cache_key] < 5:
                    return self._cached_positions.get(cache_key, [])
            
            await self._rate_limit_delay()
            positions = await self.client.futures_position_information(symbol=symbol)
            
            if not positions:
                return []
                
            open_positions = [p for p in positions if float(p['positionAmt']) != 0]
            
            # Cache güncelle
            self._last_position_check[cache_key] = current_time
            self._cached_positions[cache_key] = open_positions
            
            return open_positions
            
        except Exception as e:
            print(f"❌ {symbol} pozisyon sorgusu hatası: {e}")
            return []

    async def cancel_all_orders_safe(self, symbol: str):
        """🛡️ GÜVENLİ emirlerin iptalı - TP/SL korumalı"""
        try:
            # Bu metod artık koruma sistemi kullanacak
            await self._safe_cancel_orphan_orders(symbol)
            return True
                
        except Exception as e:
            print(f"❌ {symbol} güvenli emir iptali hatası: {e}")
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
            open_positions = await self.get_open_positions(symbol, use_cache=False)
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

    async def get_account_balance(self, use_cache: bool = True):
        """Hesap bakiyesini getir"""
        try:
            current_time = time.time()
            
            if use_cache and current_time - self._last_balance_check < 10:
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
                print("✅ Enhanced Binance AsyncClient bağlantısı kapatıldı.")
            except Exception as e:
                print(f"⚠️ Bağlantı kapatılırken hata: {e}")

    def get_client_status(self) -> dict:
        """Client durumunu döndür"""
        return {
            "client_version": "enhanced_v4.1_protected",
            "features": {
                "partial_exits": settings.ENABLE_PARTIAL_EXITS,
                "sl_tightening": settings.ENABLE_SL_TIGHTENING,
                "timeframe_based_logic": True,
                "tp_sl_protection": True  # YENİ!
            },
            "partial_exit_positions": len(self._partial_exit_positions),
            "sl_tightening_positions": len(self._sl_tightening_positions),
            "protected_orders": len(self._protected_orders),  # YENİ!
            "cache_status": {
                "cached_positions": len(self._cached_positions),
                "last_balance_check": self._last_balance_check,
                "cached_balance": self._cached_balance
            },
            "protection_system": {
                "active": True,
                "check_interval": self._tp_sl_protection_interval,
                "protected_symbols": list(self._protected_orders.keys())
            }
        }

    async def _add_missing_protection(self, symbol: str, position_amt: float, entry_price: float, 
                                    price_precision: int, has_sl: bool, has_tp: bool) -> bool:
        """Position Manager için eksik TP/SL ekleme"""
        try:
            print(f"🛡️ {symbol} için eksik koruma ekleniyor...")
            
            # Pozisyon yönünü belirle
            is_long = position_amt > 0
            opposite_side = 'SELL' if is_long else 'BUY'
            quantity = abs(position_amt)
            
            # Fiyatları hesapla
            if is_long:
                sl_price = entry_price * (1 - settings.STOP_LOSS_PERCENT)
                tp_price = entry_price * (1 + settings.TAKE_PROFIT_PERCENT)
            else:
                sl_price = entry_price * (1 + settings.STOP_LOSS_PERCENT)
                tp_price = entry_price * (1 - settings.TAKE_PROFIT_PERCENT)
                
            formatted_sl_price = f"{sl_price:.{price_precision}f}"
            formatted_tp_price = f"{tp_price:.{price_precision}f}"
            
            success_count = 0
            sl_order = None
            tp_order = None
            
            # Stop Loss ekle (eksikse)
            if not has_sl:
                sl_order = await self._create_protected_stop_loss(symbol, opposite_side, quantity, formatted_sl_price)
                if sl_order:
                    success_count += 1
                    
            # Take Profit ekle (eksikse)
            if not has_tp:
                tp_order = await self._create_protected_take_profit_market(symbol, opposite_side, quantity, formatted_tp_price)
                if not tp_order:
                    # Alternatif: LIMIT emri dene
                    tp_order = await self._create_protected_take_profit_limit(symbol, opposite_side, quantity, formatted_tp_price)
                
                if tp_order:
                    success_count += 1
            
            # Koruma bilgilerini kaydet
            if sl_order or tp_order:
                self._protected_orders[symbol] = {
                    'sl_order_id': sl_order.get('orderId') if sl_order else None,
                    'tp_order_id': tp_order.get('orderId') if tp_order else None,
                    'created_at': time.time(),
                    'entry_price': entry_price,
                    'position_type': 'restored'
                }
            
            # Başarı değerlendirmesi
            expected_orders = (0 if has_sl else 1) + (0 if has_tp else 1)
            return success_count >= expected_orders
            
        except Exception as e:
            print(f"❌ {symbol} koruma ekleme genel hatası: {e}")
            return False

# Global enhanced instance
binance_client = EnhancedBinanceClient()
