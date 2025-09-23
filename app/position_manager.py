# app/position_manager.py - ENHANCED KORUMA SİSTEMİ

import asyncio
import time
from typing import List, Dict, Optional
from .binance_client import binance_client
from .config import settings

class EnhancedPositionManager:
    """
    🛡️ ENHANCED Pozisyon Yöneticisi
    - Açık pozisyonları sürekli tarar
    - TP/SL eksik olanlara otomatik ekler
    - TP/SL'lerin silinmesini engeller
    - Daha sık kontrol ile güvenlik arttırıldı
    """
    
    def __init__(self):
        self.is_running = False
        self.scan_interval = 15  # 15 saniyede bir tara (daha sık!)
        self.processed_positions = set()  # İşlenmiş pozisyonları takip et
        self.last_scan_time = 0
        self.protection_failures = {}  # Symbol -> failure count
        self.max_protection_failures = 3  # Maksimum başarısızlık sayısı
        
        # 🛡️ Enhanced koruma özellikleri
        self.force_rescan_interval = 60  # 60 saniyede bir zorla rescan
        self.last_force_scan = 0
        self.tp_sl_validation_enabled = True
        self.aggressive_protection_mode = True  # Agresif koruma modu
        
        print("🛡️ ENHANCED Pozisyon Yöneticisi başlatıldı")
        print(f"⚡ Tarama aralığı: {self.scan_interval} saniye (çok sık)")
        print(f"🔄 Zorla rescan: {self.force_rescan_interval} saniye")
        print(f"💪 Agresif koruma: {'Aktif' if self.aggressive_protection_mode else 'Pasif'}")
        
    async def start_monitoring(self):
        """Enhanced otomatik TP/SL monitoring başlat"""
        if self.is_running:
            print("⚠️ Enhanced pozisyon monitoring zaten çalışıyor")
            return
            
        self.is_running = True
        print("🔍 ENHANCED pozisyon tarayıcısı başlatıldı...")
        print(f"📋 Tarama aralığı: {self.scan_interval} saniye")
        print("🛡️ TP/SL koruma sistemi aktif!")
        
        while self.is_running:
            try:
                await self._enhanced_scan_and_protect()
                await asyncio.sleep(self.scan_interval)
            except Exception as e:
                print(f"❌ Enhanced monitoring hatası: {e}")
                await asyncio.sleep(3)  # Hata durumunda daha kısa bekle
                
    async def stop_monitoring(self):
        """Enhanced monitoring'i durdur"""
        self.is_running = False
        print("🛑 Enhanced pozisyon monitoring durduruldu")
        
    async def _enhanced_scan_and_protect(self):
        """🛡️ Enhanced pozisyon tarama ve koruma sistemi"""
        try:
            current_time = time.time()
            
            # Rate limit koruması (daha esnek)
            if current_time - self.last_scan_time < 12:
                return
            
            # Zorla rescan kontrolü
            force_scan = (current_time - self.last_force_scan) > self.force_rescan_interval
            if force_scan:
                print("🔄 Enhanced zorla rescan başlatılıyor...")
                self.processed_positions.clear()  # Cache'i temizle
                self.protection_failures.clear()  # Failure count'u sıfırla
                self.last_force_scan = current_time
                
            print("🔍 Enhanced açık pozisyonlar taranıyor...")
            
            # Tüm açık pozisyonları al
            await binance_client._rate_limit_delay()
            all_positions = await binance_client.client.futures_position_information()
            
            # Sadece açık pozisyonları filtrele
            open_positions = [p for p in all_positions if float(p['positionAmt']) != 0]
            
            if not open_positions:
                print("✅ Açık pozisyon bulunamadı")
                self.last_scan_time = current_time
                return
                
            print(f"📊 {len(open_positions)} açık pozisyon tespit edildi - Enhanced koruma başlatılıyor")
            
            # Her pozisyon için enhanced TP/SL kontrolü
            for position in open_positions:
                await self._enhanced_check_and_protect(position, force_scan)
                await asyncio.sleep(0.3)  # Pozisyonlar arası kısa bekle
                
            self.last_scan_time = current_time
            print(f"✅ Enhanced tarama tamamlandı - {len(open_positions)} pozisyon kontrol edildi")
            
        except Exception as e:
            print(f"❌ Enhanced pozisyon tarama hatası: {e}")
            
    async def _enhanced_check_and_protect(self, position: dict, force_scan: bool = False):
        """🛡️ Enhanced tekil pozisyon kontrolü ve koruması"""
        try:
            symbol = position['symbol']
            position_amt = float(position['positionAmt'])
            entry_price = float(position['entryPrice'])
            
            if position_amt == 0:
                return
                
            # Pozisyon ID'si oluştur (tekrar işlemeyi önlemek için)
            position_id = f"{symbol}_{abs(position_amt)}_{entry_price}"
            
            # Bu pozisyon daha önce işlendi mi? (force_scan hariç)
            if not force_scan and position_id in self.processed_positions:
                # Agresif modda bile bazı pozisyonları ara sıra kontrol et
                if self.aggressive_protection_mode and time.time() % 4 == 0:
                    pass  # %25 şansla kontrol et
                else:
                    return
                
            print(f"🎯 {symbol} Enhanced pozisyon kontrol ediliyor...")
            print(f"   Miktar: {position_amt}")
            print(f"   Giriş Fiyatı: {entry_price}")
            
            # Bu sembol için açık emirleri kontrol et
            await binance_client._rate_limit_delay()
            open_orders = await binance_client.client.futures_get_open_orders(symbol=symbol)
            
            # Enhanced TP/SL analizi
            tp_sl_analysis = self._analyze_tp_sl_orders(open_orders, position_amt)
            
            has_sl = tp_sl_analysis['has_sl']
            has_tp = tp_sl_analysis['has_tp']
            sl_count = tp_sl_analysis['sl_count'] 
            tp_count = tp_sl_analysis['tp_count']
            
            print(f"📊 {symbol} TP/SL Analizi:")
            print(f"   SL emirleri: {sl_count} ({'✓' if has_sl else '✗'})")
            print(f"   TP emirleri: {tp_count} ({'✓' if has_tp else '✗'})")
            
            if has_sl and has_tp:
                print(f"✅ {symbol} Enhanced koruma mevcut (SL: ✓, TP: ✓)")
                self.processed_positions.add(position_id)
                return
                
            # Eksik koruma tespit edildi!
            protection_needed = []
            if not has_sl:
                protection_needed.append("SL")
            if not has_tp:
                protection_needed.append("TP")
                
            print(f"⚠️ {symbol} EKSİK KORUMA TESPİT EDİLDİ: {', '.join(protection_needed)}")
            print(f"🚨 Enhanced koruma sistemi devreye giriyor!")
            
            # Koruma başarısızlık kontrolü
            if symbol in self.protection_failures:
                failure_count = self.protection_failures[symbol]
                if failure_count >= self.max_protection_failures:
                    print(f"❌ {symbol} çok fazla koruma başarısızlığı ({failure_count}), atlanıyor")
                    return
                    
            # Symbol bilgilerini al (precision için)
            symbol_info = await binance_client.get_symbol_info(symbol)
            if not symbol_info:
                print(f"❌ {symbol} için sembol bilgisi alınamadı")
                return
                
            price_precision = self._get_price_precision(symbol_info)
            
            # 🛡️ Enhanced TP/SL ekleme
            success = await self._add_enhanced_protection(
                symbol, position_amt, entry_price, price_precision, has_sl, has_tp
            )
            
            if success:
                self.processed_positions.add(position_id)
                # Başarı durumunda failure count'u sıfırla
                if symbol in self.protection_failures:
                    del self.protection_failures[symbol]
                print(f"✅ {symbol} Enhanced koruma başarıyla eklendi!")
            else:
                # Başarısızlık sayacını artır
                self.protection_failures[symbol] = self.protection_failures.get(symbol, 0) + 1
                print(f"❌ {symbol} Enhanced koruma eklenemedi (başarısızlık: {self.protection_failures[symbol]})")
                
        except Exception as e:
            print(f"❌ {position.get('symbol', 'UNKNOWN')} Enhanced pozisyon kontrolü hatası: {e}")
            
    def _analyze_tp_sl_orders(self, open_orders: list, position_amt: float) -> dict:
        """🔍 Açık emirleri analiz et ve TP/SL durumunu belirle"""
        try:
            is_long = position_amt > 0
            required_side = 'SELL' if is_long else 'BUY'
            
            sl_orders = []
            tp_orders = []
            
            for order in open_orders:
                order_side = order.get('side')
                order_type = order.get('type')
                reduce_only = order.get('reduceOnly', False)
                
                # Sadece reduce_only emirleri ve doğru yön
                if not reduce_only or order_side != required_side:
                    continue
                    
                # SL emirleri
                if order_type in ['STOP_MARKET', 'STOP']:
                    sl_orders.append(order)
                    
                # TP emirleri  
                elif order_type in ['TAKE_PROFIT_MARKET', 'TAKE_PROFIT', 'LIMIT']:
                    tp_orders.append(order)
            
            return {
                'has_sl': len(sl_orders) > 0,
                'has_tp': len(tp_orders) > 0,
                'sl_count': len(sl_orders),
                'tp_count': len(tp_orders),
                'sl_orders': sl_orders,
                'tp_orders': tp_orders
            }
            
        except Exception as e:
            print(f"❌ TP/SL analiz hatası: {e}")
            return {
                'has_sl': False,
                'has_tp': False, 
                'sl_count': 0,
                'tp_count': 0,
                'sl_orders': [],
                'tp_orders': []
            }
            
    async def _add_enhanced_protection(self, symbol: str, position_amt: float, 
                                     entry_price: float, price_precision: int, 
                                     has_sl: bool, has_tp: bool) -> bool:
        """🛡️ Enhanced eksik TP/SL koruması ekleme"""
        try:
            print(f"🛡️ {symbol} için Enhanced koruma ekleniyor...")
            
            # Pozisyon yönünü belirle
            is_long = position_amt > 0
            opposite_side = 'SELL' if is_long else 'BUY'
            quantity = abs(position_amt)
            
            # Enhanced fiyat hesaplama - mevcut pozisyon tipine göre
            protection_type = self._determine_protection_type(symbol)
            
            if protection_type == 'partial_exit':
                # Kademeli satış koruması
                success = await self._add_partial_exit_protection(symbol, is_long, quantity, entry_price, 
                                                               price_precision, opposite_side, has_sl, has_tp)
            else:
                # Normal TP/SL koruması  
                success = await self._add_normal_protection(symbol, is_long, quantity, entry_price,
                                                          price_precision, opposite_side, has_sl, has_tp)
            
            return success
            
        except Exception as e:
            print(f"❌ {symbol} Enhanced koruma ekleme genel hatası: {e}")
            return False
            
    def _determine_protection_type(self, symbol: str) -> str:
        """Pozisyon koruma tipini belirle"""
        # Binance client'taki partial exit tracking'i kontrol et
        if hasattr(binance_client, '_partial_exit_positions'):
            if symbol in binance_client._partial_exit_positions:
                return 'partial_exit'
                
        # Veya protected orders'dan kontrol et
        if hasattr(binance_client, '_protected_orders'):
            if symbol in binance_client._protected_orders:
                position_type = binance_client._protected_orders[symbol].get('position_type', 'normal')
                return position_type
                
        return 'normal'
        
    async def _add_normal_protection(self, symbol: str, is_long: bool, quantity: float, 
                                   entry_price: float, price_precision: int, opposite_side: str,
                                   has_sl: bool, has_tp: bool) -> bool:
        """Normal TP/SL koruması ekleme"""
        try:
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
            
            # Stop Loss ekle (eksikse)
            if not has_sl:
                print(f"🛑 {symbol} Normal Stop Loss ekleniyor: {formatted_sl_price}")
                sl_success = await binance_client._create_protected_stop_loss(
                    symbol, opposite_side, quantity, formatted_sl_price
                )
                if sl_success:
                    success_count += 1
                    
            # Take Profit ekle (eksikse)
            if not has_tp:
                print(f"🎯 {symbol} Normal Take Profit ekleniyor: {formatted_tp_price}")
                tp_success = await binance_client._create_protected_take_profit_market(
                    symbol, opposite_side, quantity, formatted_tp_price
                )
                
                if not tp_success:
                    # Alternatif: LIMIT emri dene
                    print(f"🔄 {symbol} Alternatif TP (LIMIT) deneniyor...")
                    tp_success = await binance_client._create_protected_take_profit_limit(
                        symbol, opposite_side, quantity, formatted_tp_price, "TP"
                    )
                    
                if tp_success:
                    success_count += 1
            
            # Başarı değerlendirmesi
            expected_orders = (0 if has_sl else 1) + (0 if has_tp else 1)
            success = success_count >= expected_orders
            
            if success:
                print(f"✅ {symbol} Normal koruma başarılı ({success_count}/{expected_orders})")
            else:
                print(f"⚠️ {symbol} Normal koruma eksik ({success_count}/{expected_orders})")
                
            return success
            
        except Exception as e:
            print(f"❌ {symbol} Normal koruma hatası: {e}")
            return False
            
    async def _add_partial_exit_protection(self, symbol: str, is_long: bool, quantity: float,
                                         entry_price: float, price_precision: int, opposite_side: str,
                                         has_sl: bool, has_tp: bool) -> bool:
        """Kademeli satış koruması ekleme"""
        try:
            print(f"🎯 {symbol} Kademeli satış koruması ekleniyor...")
            
            # Kademeli satış fiyatlarını hesapla
            if is_long:
                sl_price = entry_price * (1 - settings.STOP_LOSS_PERCENT)
                tp1_price = entry_price * (1 + settings.TP1_PERCENT)
                tp2_price = entry_price * (1 + settings.TP2_PERCENT)
            else:
                sl_price = entry_price * (1 + settings.STOP_LOSS_PERCENT)
                tp1_price = entry_price * (1 - settings.TP1_PERCENT)
                tp2_price = entry_price * (1 - settings.TP2_PERCENT)
                
            formatted_sl_price = f"{sl_price:.{price_precision}f}"
            formatted_tp1_price = f"{tp1_price:.{price_precision}f}"
            formatted_tp2_price = f"{tp2_price:.{price_precision}f}"
            
            # Kademeli miktarları hesapla
            tp1_quantity = quantity * settings.TP1_EXIT_RATIO
            tp2_quantity = quantity * settings.TP2_EXIT_RATIO - tp1_quantity
            
            success_count = 0
            
            # Stop Loss ekle (eksikse)
            if not has_sl:
                print(f"🛑 {symbol} Kademeli SL ekleniyor: {formatted_sl_price}")
                sl_success = await binance_client._create_protected_stop_loss(
                    symbol, opposite_side, quantity, formatted_sl_price
                )
                if sl_success:
                    success_count += 1
                    
            # TP1 ve TP2 durumunu kontrol et (daha sofistike)
            if not has_tp:
                print(f"🎯 {symbol} TP1 ekleniyor: {formatted_tp1_price} ({tp1_quantity} miktar)")
                tp1_success = await binance_client._create_protected_take_profit_limit(
                    symbol, opposite_side, tp1_quantity, formatted_tp1_price, "TP1"
                )
                
                print(f"🎯 {symbol} TP2 ekleniyor: {formatted_tp2_price} ({tp2_quantity} miktar)")
                tp2_success = await binance_client._create_protected_take_profit_limit(
                    symbol, opposite_side, tp2_quantity, formatted_tp2_price, "TP2"
                )
                
                if tp1_success or tp2_success:
                    success_count += 1
            
            # Başarı değerlendirmesi
            expected_orders = (0 if has_sl else 1) + (0 if has_tp else 1)
            success = success_count >= expected_orders
            
            if success:
                print(f"✅ {symbol} Kademeli koruma başarılı ({success_count}/{expected_orders})")
            else:
                print(f"⚠️ {symbol} Kademeli koruma eksik ({success_count}/{expected_orders})")
                
            return success
            
        except Exception as e:
            print(f"❌ {symbol} Kademeli koruma hatası: {e}")
            return False
            
    def _get_price_precision(self, symbol_info: dict) -> int:
        """Symbol için fiyat precision'ını al"""
        try:
            for f in symbol_info['filters']:
                if f['filterType'] == 'PRICE_FILTER':
                    tick_size = f['tickSize']
                    if '.' in tick_size:
                        return len(tick_size.split('.')[1].rstrip('0'))
            return 2  # Varsayılan
        except:
            return 2  # Hata durumunda varsayılan
            
    async def manual_scan_symbol(self, symbol: str) -> bool:
        """Belirli bir symbol için manuel Enhanced tarama"""
        try:
            print(f"🔍 {symbol} için Enhanced manuel pozisyon taraması...")
            
            # Bu symbol için pozisyonları al
            await binance_client._rate_limit_delay()
            positions = await binance_client.client.futures_position_information(symbol=symbol)
            
            open_position = None
            for pos in positions:
                if float(pos['positionAmt']) != 0:
                    open_position = pos
                    break
                    
            if not open_position:
                print(f"✅ {symbol} için açık pozisyon bulunamadı")
                return True
                
            # Bu pozisyonu Enhanced kontrol et ve koru
            await self._enhanced_check_and_protect(open_position, force_scan=True)
            return True
            
        except Exception as e:
            print(f"❌ {symbol} Enhanced manuel tarama hatası: {e}")
            return False
            
    def get_status(self) -> dict:
        """Enhanced monitoring durumunu döndür"""
        return {
            "is_running": self.is_running,
            "scan_interval": self.scan_interval,
            "processed_positions_count": len(self.processed_positions),
            "last_scan_ago_seconds": int(time.time() - self.last_scan_time) if self.last_scan_time > 0 else None,
            
            # Enhanced özellikler
            "protection_failures": dict(self.protection_failures),
            "max_protection_failures": self.max_protection_failures,
            "force_rescan_interval": self.force_rescan_interval,
            "last_force_scan_ago": int(time.time() - self.last_force_scan) if self.last_force_scan > 0 else None,
            "aggressive_protection_mode": self.aggressive_protection_mode,
            "tp_sl_validation_enabled": self.tp_sl_validation_enabled,
            
            "enhanced_features": {
                "frequent_scanning": True,
                "protection_failure_tracking": True,
                "force_rescan": True,
                "tp_sl_validation": self.tp_sl_validation_enabled,
                "partial_exit_support": True
            }
        }

# Global enhanced instance
position_manager = EnhancedPositionManager()
