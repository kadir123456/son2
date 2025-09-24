# app/position_manager.py - Basit Pozisyon Yöneticisi

import asyncio
import time
from typing import List, Dict, Optional
from .binance_client import binance_client
from .config import settings

class SimplePositionManager:
    """
    🛡️ Basit Pozisyon Yöneticisi
    - Açık pozisyonları kontrol eder
    - Eksik TP/SL ekler
    - Sadece temel koruma
    """
    
    def __init__(self):
        self.is_running = False
        self.scan_interval = 30  # 30 saniyede bir tara
        self.last_scan_time = 0
        
        print("🛡️ Basit Pozisyon Yöneticisi başlatıldı")
        print(f"⚡ Tarama aralığı: {self.scan_interval} saniye")
        
    async def start_monitoring(self):
        """Otomatik TP/SL monitoring başlat"""
        if self.is_running:
            print("⚠️ Pozisyon monitoring zaten çalışıyor")
            return
            
        self.is_running = True
        print("🔍 Pozisyon tarayıcısı başlatıldı...")
        
        while self.is_running:
            try:
                await self._scan_and_protect()
                await asyncio.sleep(self.scan_interval)
            except Exception as e:
                print(f"❌ Monitoring hatası: {e}")
                await asyncio.sleep(5)
                
    async def stop_monitoring(self):
        """Monitoring'i durdur"""
        self.is_running = False
        print("🛑 Pozisyon monitoring durduruldu")
        
    async def _scan_and_protect(self):
        """Pozisyon tarama ve koruma"""
        try:
            current_time = time.time()
            
            # Rate limit koruması
            if current_time - self.last_scan_time < 25:
                return
            
            print("🔍 Açık pozisyonlar taranıyor...")
            
            # Tüm açık pozisyonları al
            await binance_client._rate_limit_delay()
            all_positions = await binance_client.client.futures_position_information()
            
            # Sadece açık pozisyonları filtrele
            open_positions = [p for p in all_positions if float(p['positionAmt']) != 0]
            
            if not open_positions:
                print("✅ Açık pozisyon bulunamadı")
                self.last_scan_time = current_time
                return
                
            print(f"📊 {len(open_positions)} açık pozisyon tespit edildi")
            
            # Her pozisyon için TP/SL kontrolü
            for position in open_positions:
                await self._check_and_protect(position)
                await asyncio.sleep(0.5)
                
            self.last_scan_time = current_time
            print(f"✅ Tarama tamamlandı - {len(open_positions)} pozisyon kontrol edildi")
            
        except Exception as e:
            print(f"❌ Pozisyon tarama hatası: {e}")
            
    async def _check_and_protect(self, position: dict):
        """Tekil pozisyon kontrolü ve koruması"""
        try:
            symbol = position['symbol']
            position_amt = float(position['positionAmt'])
            entry_price = float(position['entryPrice'])
            
            if position_amt == 0:
                return
                
            print(f"🎯 {symbol} pozisyon kontrol ediliyor...")
            print(f"   Miktar: {position_amt}")
            print(f"   Giriş Fiyatı: {entry_price}")
            
            # Bu sembol için açık emirleri kontrol et
            await binance_client._rate_limit_delay()
            open_orders = await binance_client.client.futures_get_open_orders(symbol=symbol)
            
            # TP/SL analizi
            has_sl, has_tp = self._analyze_orders(open_orders, position_amt)
            
            print(f"📊 {symbol} TP/SL Durumu:")
            print(f"   SL: {'✓' if has_sl else '✗'}")
            print(f"   TP: {'✓' if has_tp else '✗'}")
            
            if has_sl and has_tp:
                print(f"✅ {symbol} koruma mevcut")
                return
                
            # Eksik koruma tespit edildi!
            protection_needed = []
            if not has_sl:
                protection_needed.append("SL")
            if not has_tp:
                protection_needed.append("TP")
                
            print(f"⚠️ {symbol} EKSİK KORUMA: {', '.join(protection_needed)}")
            
            # Symbol bilgilerini al
            symbol_info = await binance_client.get_symbol_info(symbol)
            if not symbol_info:
                print(f"❌ {symbol} için sembol bilgisi alınamadı")
                return
                
            price_precision = self._get_price_precision(symbol_info)
            
            # Eksik TP/SL ekleme
            success = await self._add_missing_protection(
                symbol, position_amt, entry_price, price_precision, has_sl, has_tp
            )
            
            if success:
                print(f"✅ {symbol} koruma başarıyla eklendi!")
            else:
                print(f"❌ {symbol} koruma eklenemedi")
                
        except Exception as e:
            print(f"❌ {position.get('symbol', 'UNKNOWN')} pozisyon kontrolü hatası: {e}")
            
    def _analyze_orders(self, open_orders: list, position_amt: float) -> tuple:
        """Açık emirleri analiz et"""
        try:
            is_long = position_amt > 0
            required_side = 'SELL' if is_long else 'BUY'
            
            has_sl = False
            has_tp = False
            
            for order in open_orders:
                order_side = order.get('side')
                order_type = order.get('type')
                reduce_only = order.get('reduceOnly', False)
                
                # Sadece reduce_only emirleri ve doğru yön
                if not reduce_only or order_side != required_side:
                    continue
                    
                # SL emirleri
                if order_type in ['STOP_MARKET', 'STOP']:
                    has_sl = True
                    
                # TP emirleri  
                elif order_type in ['TAKE_PROFIT_MARKET', 'TAKE_PROFIT', 'LIMIT']:
                    has_tp = True
            
            return has_sl, has_tp
            
        except Exception as e:
            print(f"❌ Emir analiz hatası: {e}")
            return False, False
            
    async def _add_missing_protection(self, symbol: str, position_amt: float, 
                                    entry_price: float, price_precision: int, 
                                    has_sl: bool, has_tp: bool) -> bool:
        """Eksik TP/SL ekleme"""
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
            
            # Stop Loss ekle (eksikse)
            if not has_sl:
                print(f"🛑 {symbol} Stop Loss ekleniyor: {formatted_sl_price}")
                sl_success = await binance_client._create_stop_loss(
                    symbol, opposite_side, quantity, formatted_sl_price
                )
                if sl_success:
                    success_count += 1
                    
            # Take Profit ekle (eksikse)
            if not has_tp:
                print(f"🎯 {symbol} Take Profit ekleniyor: {formatted_tp_price}")
                tp_success = await binance_client._create_take_profit(
                    symbol, opposite_side, quantity, formatted_tp_price
                )
                if tp_success:
                    success_count += 1
            
            # Başarı değerlendirmesi
            expected_orders = (0 if has_sl else 1) + (0 if has_tp else 1)
            return success_count >= expected_orders
            
        except Exception as e:
            print(f"❌ {symbol} koruma ekleme hatası: {e}")
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
        """Belirli bir symbol için manuel tarama"""
        try:
            print(f"🔍 {symbol} için manuel pozisyon taraması...")
            
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
                
            # Bu pozisyonu kontrol et ve koru
            await self._check_and_protect(open_position)
            return True
            
        except Exception as e:
            print(f"❌ {symbol} manuel tarama hatası: {e}")
            return False
            
    def get_status(self) -> dict:
        """Monitoring durumunu döndür"""
        return {
            "is_running": self.is_running,
            "scan_interval": self.scan_interval,
            "last_scan_ago_seconds": int(time.time() - self.last_scan_time) if self.last_scan_time > 0 else None,
            "features": {
                "simple_tp_sl_protection": True,
                "basic_position_monitoring": True
            }
        }

# Global simple instance
position_manager = SimplePositionManager()
