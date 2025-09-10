# app/position_manager.py - YENİ DOSYA OLUŞTURUN

import asyncio
import time
from typing import List, Dict, Optional
from .binance_client import binance_client
from .config import settings

class PositionManager:
    """
    Açık pozisyonları tarar ve TP/SL eksik olanlara otomatik ekler
    Manuel işlemler ve çoklu coin desteği ile
    """
    
    def __init__(self):
        self.is_running = False
        self.scan_interval = 30  # 30 saniyede bir tara
        self.processed_positions = set()  # İşlenmiş pozisyonları takip et
        self.last_scan_time = 0
        print("🛡️ Pozisyon Yöneticisi başlatıldı - Otomatik TP/SL Koruması")
        
    async def start_monitoring(self):
        """Otomatik TP/SL monitoring başlat"""
        if self.is_running:
            print("⚠️ Pozisyon monitoring zaten çalışıyor")
            return
            
        self.is_running = True
        print("🔍 Açık pozisyon tarayıcısı başlatıldı...")
        print(f"📋 Tarama aralığı: {self.scan_interval} saniye")
        
        while self.is_running:
            try:
                await self._scan_and_protect_positions()
                await asyncio.sleep(self.scan_interval)
            except Exception as e:
                print(f"❌ Monitoring hatası: {e}")
                await asyncio.sleep(5)  # Hata durumunda kısa bekle
                
    async def stop_monitoring(self):
        """Monitoring'i durdur"""
        self.is_running = False
        print("🛑 Pozisyon monitoring durduruldu")
        
    async def _scan_and_protect_positions(self):
        """Tüm açık pozisyonları tara ve TP/SL eksik olanları koru"""
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
                await self._check_and_add_protection(position)
                await asyncio.sleep(0.5)  # Pozisyonlar arası kısa bekle
                
            self.last_scan_time = current_time
            
        except Exception as e:
            print(f"❌ Pozisyon tarama hatası: {e}")
            
    async def _check_and_add_protection(self, position: dict):
        """Tekil pozisyon için TP/SL kontrolü ve ekleme"""
        try:
            symbol = position['symbol']
            position_amt = float(position['positionAmt'])
            entry_price = float(position['entryPrice'])
            
            if position_amt == 0:
                return
                
            # Pozisyon ID'si oluştur (tekrar işlemeyi önlemek için)
            position_id = f"{symbol}_{abs(position_amt)}_{entry_price}"
            
            # Bu pozisyon daha önce işlendi mi?
            if position_id in self.processed_positions:
                return
                
            print(f"🎯 {symbol} pozisyonu kontrol ediliyor...")
            print(f"   Miktar: {position_amt}")
            print(f"   Giriş Fiyatı: {entry_price}")
            
            # Bu sembol için açık emirleri kontrol et
            await binance_client._rate_limit_delay()
            open_orders = await binance_client.client.futures_get_open_orders(symbol=symbol)
            
            # TP/SL emirleri var mı kontrol et
            has_sl = any(order['type'] in ['STOP_MARKET', 'STOP'] for order in open_orders)
            has_tp = any(order['type'] in ['TAKE_PROFIT_MARKET', 'TAKE_PROFIT', 'LIMIT'] 
                        and order.get('reduceOnly') for order in open_orders)
            
            if has_sl and has_tp:
                print(f"✅ {symbol} zaten korumalı (SL: ✓, TP: ✓)")
                self.processed_positions.add(position_id)
                return
                
            # Eksik koruma varsa ekle
            protection_needed = []
            if not has_sl:
                protection_needed.append("SL")
            if not has_tp:
                protection_needed.append("TP")
                
            print(f"⚠️ {symbol} eksik koruma: {', '.join(protection_needed)}")
            
            # Symbol bilgilerini al (precision için)
            symbol_info = await binance_client.get_symbol_info(symbol)
            if not symbol_info:
                print(f"❌ {symbol} için sembol bilgisi alınamadı")
                return
                
            price_precision = self._get_price_precision(symbol_info)
            
            # TP/SL ekle
            success = await self._add_missing_protection(
                symbol, position_amt, entry_price, price_precision, has_sl, has_tp
            )
            
            if success:
                self.processed_positions.add(position_id)
                print(f"✅ {symbol} pozisyonu başarıyla korundu")
            else:
                print(f"❌ {symbol} pozisyonu korunamadı")
                
        except Exception as e:
            print(f"❌ {position.get('symbol', 'UNKNOWN')} pozisyon kontrolü hatası: {e}")
            
    async def _add_missing_protection(self, symbol: str, position_amt: float, 
                                    entry_price: float, price_precision: int, 
                                    has_sl: bool, has_tp: bool) -> bool:
        """Eksik TP/SL emirlerini ekle"""
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
                try:
                    print(f"🛑 {symbol} Stop Loss ekleniyor: {formatted_sl_price}")
                    await binance_client._rate_limit_delay()
                    
                    sl_order = await binance_client.client.futures_create_order(
                        symbol=symbol,
                        side=opposite_side,
                        type='STOP_MARKET',
                        quantity=quantity,
                        stopPrice=formatted_sl_price,
                        timeInForce='GTE_GTC',
                        reduceOnly=True
                    )
                    print(f"✅ {symbol} Stop Loss başarılı: {formatted_sl_price}")
                    success_count += 1
                    
                except Exception as sl_error:
                    print(f"❌ {symbol} Stop Loss hatası: {sl_error}")
                    
            # Take Profit ekle (eksikse)
            if not has_tp:
                try:
                    print(f"🎯 {symbol} Take Profit ekleniyor: {formatted_tp_price}")
                    await binance_client._rate_limit_delay()
                    
                    tp_order = await binance_client.client.futures_create_order(
                        symbol=symbol,
                        side=opposite_side,
                        type='TAKE_PROFIT_MARKET',
                        quantity=quantity,
                        stopPrice=formatted_tp_price,
                        timeInForce='GTE_GTC',
                        reduceOnly=True
                    )
                    print(f"✅ {symbol} Take Profit başarılı: {formatted_tp_price}")
                    success_count += 1
                    
                except Exception as tp_error:
                    print(f"❌ {symbol} Take Profit hatası: {tp_error}")
                    
                    # Alternatif: LIMIT emri dene
                    try:
                        print(f"🔄 {symbol} alternatif TP (LIMIT) deneniyor...")
                        await binance_client._rate_limit_delay()
                        
                        alt_tp_order = await binance_client.client.futures_create_order(
                            symbol=symbol,
                            side=opposite_side,
                            type='LIMIT',
                            quantity=quantity,
                            price=formatted_tp_price,
                            timeInForce='GTC',
                            reduceOnly=True
                        )
                        print(f"✅ {symbol} Alternatif TP başarılı: {formatted_tp_price}")
                        success_count += 1
                        
                    except Exception as alt_tp_error:
                        print(f"❌ {symbol} Alternatif TP de başarısız: {alt_tp_error}")
            
            # Başarı değerlendirmesi
            expected_orders = (0 if has_sl else 1) + (0 if has_tp else 1)
            return success_count >= expected_orders
            
        except Exception as e:
            print(f"❌ {symbol} koruma ekleme genel hatası: {e}")
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
            await self._check_and_add_protection(open_position)
            return True
            
        except Exception as e:
            print(f"❌ {symbol} manuel tarama hatası: {e}")
            return False
            
    def get_status(self) -> dict:
        """Monitoring durumunu döndür"""
        return {
            "is_running": self.is_running,
            "scan_interval": self.scan_interval,
            "processed_positions_count": len(self.processed_positions),
            "last_scan_ago_seconds": int(time.time() - self.last_scan_time) if self.last_scan_time > 0 else None
        }

# Global instance
position_manager = PositionManager()
