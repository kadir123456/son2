# app/position_manager.py - DİNAMİK TP/SL DESTEKLİ VERSİYON

import asyncio
import time
from typing import List, Dict, Optional
from .binance_client import binance_client
from .config import settings

class PositionManager:
    """
    🚀 Gelişmiş Pozisyon Yöneticisi
    
    Açık pozisyonları tarar ve TP/SL eksik olanlara otomatik ekler
    - Dinamik TP/SL: Zaman dilimine göre otomatik hesaplama
    - Manuel işlemler ve çoklu coin desteği
    - Risk yönetimi entegrasyonu
    - Akıllı TP/SL tespit ve ekleme
    """
    
    def __init__(self):
        self.is_running = False
        self.scan_interval = 30  # 30 saniyede bir tara
        self.processed_positions = set()  # İşlenmiş pozisyonları takip et
        self.last_scan_time = 0
        self._position_snapshots = {}  # Pozisyon anlık görüntüleri
        self._failed_attempts = {}  # Başarısız deneme sayıları
        print("🛡️ Gelişmiş Pozisyon Yöneticisi başlatıldı")
        print(f"📊 Dinamik TP/SL Koruması - Zaman Dilimi: {settings.TIMEFRAME}")
        print(f"⚖️  Risk/Reward: 1:{settings.get_risk_reward_ratio():.1f}")
        
    async def start_monitoring(self):
        """Otomatik TP/SL monitoring başlat"""
        if self.is_running:
            print("⚠️ Pozisyon monitoring zaten çalışıyor")
            return
            
        self.is_running = True
        print("🔍 Gelişmiş açık pozisyon tarayıcısı başlatıldı...")
        print(f"📋 Tarama aralığı: {self.scan_interval} saniye")
        print(f"📊 Dinamik TP/SL aktif - Zaman dilimi: {settings.TIMEFRAME}")
        
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
        self.processed_positions.clear()
        self._position_snapshots.clear()
        self._failed_attempts.clear()
        print("🛑 Gelişmiş pozisyon monitoring durduruldu")
        
    async def _scan_and_protect_positions(self):
        """🚀 Tüm açık pozisyonları tara ve dinamik TP/SL eksik olanları koru"""
        try:
            current_time = time.time()
            
            # Rate limit koruması
            if current_time - self.last_scan_time < 25:
                return
                
            print("🔍 Açık pozisyonlar taranıyor (Dinamik TP/SL ile)...")
            
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
            
            # Her pozisyon için dinamik TP/SL kontrolü
            for position in open_positions:
                await self._check_and_add_dynamic_protection(position)
                await asyncio.sleep(0.5)  # Pozisyonlar arası kısa bekle
                
            self.last_scan_time = current_time
            
        except Exception as e:
            print(f"❌ Pozisyon tarama hatası: {e}")
            
    async def _check_and_add_dynamic_protection(self, position: dict):
        """🎯 Tekil pozisyon için dinamik TP/SL kontrolü ve ekleme"""
        try:
            symbol = position['symbol']
            position_amt = float(position['positionAmt'])
            entry_price = float(position['entryPrice'])
            
            if position_amt == 0:
                return
                
            # Pozisyon ID'si oluştur (tekrar işlemeyi önlemek için)
            position_id = f"{symbol}_{abs(position_amt)}_{entry_price}"
            
            # Başarısız deneme sayısını kontrol et
            if symbol in self._failed_attempts and self._failed_attempts[symbol] >= 3:
                print(f"⚠️ {symbol} maksimum başarısız deneme aşıldı, atlanıyor")
                return
                
            # Bu pozisyon daha önce işlendi mi?
            if position_id in self.processed_positions:
                return
                
            print(f"🎯 {symbol} pozisyonu dinamik kontrol ediliyor...")
            print(f"   Miktar: {position_amt}")
            print(f"   Giriş Fiyatı: {entry_price}")
            print(f"   Zaman Dilimi: {settings.TIMEFRAME}")
            
            # Bu sembol için açık emirleri kontrol et
            await binance_client._rate_limit_delay()
            open_orders = await binance_client.client.futures_get_open_orders(symbol=symbol)
            
            # TP/SL emirleri var mı kontrol et
            has_sl = any(order['type'] in ['STOP_MARKET', 'STOP'] for order in open_orders)
            has_tp = any(order['type'] in ['TAKE_PROFIT_MARKET', 'TAKE_PROFIT', 'LIMIT'] 
                        and order.get('reduceOnly') for order in open_orders)
            
            if has_sl and has_tp:
                print(f"✅ {symbol} zaten dinamik korumalı (SL: ✓, TP: ✓)")
                self.processed_positions.add(position_id)
                # Başarılı durumda failed_attempts'i sıfırla
                if symbol in self._failed_attempts:
                    del self._failed_attempts[symbol]
                return
                
            # Eksik koruma varsa ekle
            protection_needed = []
            if not has_sl:
                protection_needed.append("SL")
            if not has_tp:
                protection_needed.append("TP")
                
            print(f"⚠️ {symbol} eksik dinamik koruma: {', '.join(protection_needed)}")
            
            # Symbol bilgilerini al (precision için)
            symbol_info = await binance_client.get_symbol_info(symbol)
            if not symbol_info:
                print(f"❌ {symbol} için sembol bilgisi alınamadı")
                return
                
            price_precision = self._get_price_precision(symbol_info)
            
            # 🚀 Dinamik TP/SL ekle
            success = await self._add_dynamic_missing_protection(
                symbol, position_amt, entry_price, price_precision, has_sl, has_tp
            )
            
            if success:
                self.processed_positions.add(position_id)
                print(f"✅ {symbol} pozisyonu dinamik koruma ile başarıyla korundu")
                # Başarılı durumda failed_attempts'i sıfırla
                if symbol in self._failed_attempts:
                    del self._failed_attempts[symbol]
            else:
                print(f"❌ {symbol} pozisyonu dinamik koruma eklenemedi")
                # Başarısız deneme sayısını artır
                if symbol not in self._failed_attempts:
                    self._failed_attempts[symbol] = 0
                self._failed_attempts[symbol] += 1
                
        except Exception as e:
            print(f"❌ {position.get('symbol', 'UNKNOWN')} pozisyon kontrolü hatası: {e}")
            
    async def _add_dynamic_missing_protection(self, symbol: str, position_amt: float, 
                                            entry_price: float, price_precision: int, 
                                            has_sl: bool, has_tp: bool) -> bool:
        """🚀 Eksik dinamik TP/SL emirlerini ekle - zaman dilimine göre otomatik hesaplama"""
        try:
            print(f"🛡️ {symbol} için dinamik eksik koruma ekleniyor...")
            print(f"📊 Zaman dilimi: {settings.TIMEFRAME}")
            
            # Pozisyon yönünü belirle
            is_long = position_amt > 0
            opposite_side = 'SELL' if is_long else 'BUY'
            quantity = abs(position_amt)
            
            # 🚀 DİNAMİK fiyatları hesapla - mevcut zaman dilimine göre
            current_sl_percent = settings.STOP_LOSS_PERCENT
            current_tp_percent = settings.TAKE_PROFIT_PERCENT
            
            print(f"💡 Dinamik hesaplama:")
            print(f"   SL Oranı: %{current_sl_percent*100:.2f}")
            print(f"   TP Oranı: %{current_tp_percent*100:.2f}")
            print(f"   Risk/Reward: 1:{settings.get_risk_reward_ratio():.1f}")
            
            if is_long:
                sl_price = entry_price * (1 - current_sl_percent)
                tp_price = entry_price * (1 + current_tp_percent)
            else:
                sl_price = entry_price * (1 + current_sl_percent)
                tp_price = entry_price * (1 - current_tp_percent)
                
            formatted_sl_price = f"{sl_price:.{price_precision}f}"
            formatted_tp_price = f"{tp_price:.{price_precision}f}"
            
            print(f"🎯 Hesaplanan dinamik fiyatlar:")
            print(f"   Giriş: {entry_price}")
            print(f"   Dinamik SL: {formatted_sl_price}")
            print(f"   Dinamik TP: {formatted_tp_price}")
            
            success_count = 0
            
            # Stop Loss ekle (eksikse) - DİNAMİK
            if not has_sl:
                sl_success = await self._create_dynamic_stop_loss(
                    symbol, opposite_side, quantity, formatted_sl_price
                )
                if sl_success:
                    success_count += 1
                    
            # Take Profit ekle (eksikse) - DİNAMİK
            if not has_tp:
                tp_success = await self._create_dynamic_take_profit(
                    symbol, opposite_side, quantity, formatted_tp_price
                )
                if tp_success:
                    success_count += 1
            
            # Başarı değerlendirmesi
            expected_orders = (0 if has_sl else 1) + (0 if has_tp else 1)
            is_success = success_count >= expected_orders
            
            if is_success:
                rr_ratio = settings.get_risk_reward_ratio()
                print(f"✅ {symbol} dinamik koruma tamamlandı (RR: 1:{rr_ratio:.1f})")
            
            return is_success
            
        except Exception as e:
            print(f"❌ {symbol} dinamik koruma ekleme genel hatası: {e}")
            return False
    
    async def _create_dynamic_stop_loss(self, symbol: str, opposite_side: str, 
                                      quantity: float, formatted_sl_price: str) -> bool:
        """Dinamik Stop Loss emri oluştur"""
        try:
            print(f"🛑 {symbol} Dinamik Stop Loss ekleniyor: {formatted_sl_price}")
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
            print(f"✅ {symbol} Dinamik Stop Loss başarılı: {formatted_sl_price}")
            return True
            
        except Exception as sl_error:
            print(f"❌ {symbol} Dinamik Stop Loss hatası: {sl_error}")
            
            # Alternatif yaklaşım
            try:
                print(f"🔄 {symbol} Alternatif dinamik SL deneniyor...")
                await binance_client._rate_limit_delay()
                
                alt_sl_order = await binance_client.client.futures_create_order(
                    symbol=symbol,
                    side=opposite_side,
                    type='STOP',
                    quantity=quantity,
                    price=formatted_sl_price,
                    stopPrice=formatted_sl_price,
                    timeInForce='GTC',
                    reduceOnly=True
                )
                print(f"✅ {symbol} Alternatif dinamik SL başarılı: {formatted_sl_price}")
                return True
                
            except Exception as alt_sl_error:
                print(f"❌ {symbol} Alternatif dinamik SL de başarısız: {alt_sl_error}")
                return False
    
    async def _create_dynamic_take_profit(self, symbol: str, opposite_side: str, 
                                        quantity: float, formatted_tp_price: str) -> bool:
        """Dinamik Take Profit emri oluştur"""
        try:
            print(f"🎯 {symbol} Dinamik Take Profit ekleniyor: {formatted_tp_price}")
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
            print(f"✅ {symbol} Dinamik Take Profit başarılı: {formatted_tp_price}")
            return True
            
        except Exception as tp_error:
            print(f"❌ {symbol} Dinamik Take Profit hatası: {tp_error}")
            
            # Alternatif yaklaşım - LIMIT emri
            try:
                print(f"🔄 {symbol} Alternatif dinamik TP (LIMIT) deneniyor...")
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
                print(f"✅ {symbol} Alternatif dinamik TP başarılı: {formatted_tp_price}")
                return True
                
            except Exception as alt_tp_error:
                print(f"❌ {symbol} Alternatif dinamik TP de başarısız: {alt_tp_error}")
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
        """🎯 Belirli bir symbol için manuel dinamik tarama"""
        try:
            print(f"🔍 {symbol} için manuel dinamik pozisyon taraması...")
            print(f"📊 Zaman dilimi: {settings.TIMEFRAME}")
            
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
                
            # Bu pozisyonu dinamik kontrol et ve koru
            await self._check_and_add_dynamic_protection(open_position)
            return True
            
        except Exception as e:
            print(f"❌ {symbol} manuel dinamik tarama hatası: {e}")
            return False
    
    # YENİ: ZAMAN DİLİMİ SPESİFİK METODLAR
    
    async def scan_with_specific_timeframe(self, symbol: str, timeframe: str) -> bool:
        """
        Belirli bir zaman dilimi ayarları ile pozisyon tarama
        Geçici olarak ayarları değiştirir, tarama yapar, geri yükler
        """
        try:
            # Mevcut ayarları kaydet
            original_timeframe = settings.TIMEFRAME
            
            # Geçici olarak zaman dilimini değiştir
            if not settings.set_timeframe(timeframe):
                print(f"❌ Geçersiz zaman dilimi: {timeframe}")
                return False
            
            print(f"🕐 {symbol} için geçici zaman dilimi: {timeframe}")
            print(f"📊 Geçici TP/SL: %{settings.TAKE_PROFIT_PERCENT*100:.2f}/%{settings.STOP_LOSS_PERCENT*100:.2f}")
            
            # Manuel tarama yap
            result = await self.manual_scan_symbol(symbol)
            
            # Orijinal ayarları geri yükle
            settings.set_timeframe(original_timeframe)
            print(f"🔄 Zaman dilimi geri yüklendi: {original_timeframe}")
            
            return result
            
        except Exception as e:
            # Hata durumunda da orijinal ayarları geri yükle
            settings.set_timeframe(settings.TIMEFRAME)
            print(f"❌ {symbol} belirli zaman dilimi tarama hatası: {e}")
            return False
    
    async def bulk_scan_symbols(self, symbols: list, max_concurrent: int = 3) -> Dict[str, bool]:
        """
        Birden fazla symbol'ü paralel olarak tara
        """
        results = {}
        
        # Semaphore ile eşzamanlı işlem sayısını sınırla
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def scan_single_symbol(symbol: str):
            async with semaphore:
                try:
                    result = await self.manual_scan_symbol(symbol)
                    results[symbol] = result
                    return result
                except Exception as e:
                    print(f"❌ {symbol} bulk scan hatası: {e}")
                    results[symbol] = False
                    return False
        
        # Tüm symboller için task oluştur
        tasks = [scan_single_symbol(symbol) for symbol in symbols]
        
        # Paralel çalıştır
        await asyncio.gather(*tasks, return_exceptions=True)
        
        print(f"📊 Bulk scan tamamlandı: {len(symbols)} symbol")
        successful = sum(1 for success in results.values() if success)
        print(f"✅ Başarılı: {successful}/{len(symbols)}")
        
        return results
            
    def get_status(self) -> dict:
        """Gelişmiş monitoring durumunu döndür"""
        return {
            "is_running": self.is_running,
            "scan_interval": self.scan_interval,
            "processed_positions_count": len(self.processed_positions),
            "failed_attempts_count": len(self._failed_attempts),
            "last_scan_ago_seconds": int(time.time() - self.last_scan_time) if self.last_scan_time > 0 else None,
            "current_timeframe": settings.TIMEFRAME,
            "dynamic_tp_sl": {
                "stop_loss_percent": settings.STOP_LOSS_PERCENT * 100,
                "take_profit_percent": settings.TAKE_PROFIT_PERCENT * 100,
                "risk_reward_ratio": settings.get_risk_reward_ratio()
            },
            "position_snapshots_count": len(self._position_snapshots),
            "monitoring_features": {
                "dynamic_tp_sl": True,
                "timeframe_specific_levels": True,
                "bulk_scanning": True,
                "failed_attempt_tracking": True,
                "rate_limit_protection": True
            }
        }
    
    def get_failed_attempts_report(self) -> Dict[str, int]:
        """Başarısız denemeler raporu"""
        return self._failed_attempts.copy()
    
    def reset_failed_attempts(self, symbol: str = None):
        """Başarısız denemeleri sıfırla"""
        if symbol:
            if symbol in self._failed_attempts:
                del self._failed_attempts[symbol]
                print(f"🔄 {symbol} başarısız denemeleri sıfırlandı")
        else:
            self._failed_attempts.clear()
            print("🔄 Tüm başarısız denemeler sıfırlandı")
    
    def reset_processed_positions(self):
        """İşlenmiş pozisyonları sıfırla - yeniden tarama için"""
        self.processed_positions.clear()
        print("🔄 İşlenmiş pozisyonlar sıfırlandı - tüm pozisyonlar yeniden taranacak")
    
    async def get_position_summary(self) -> Dict[str, Any]:
        """Detaylı pozisyon özeti"""
        try:
            await binance_client._rate_limit_delay()
            all_positions = await binance_client.client.futures_position_information()
            open_positions = [p for p in all_positions if float(p['positionAmt']) != 0]
            
            summary = {
                "total_open_positions": len(open_positions),
                "positions": [],
                "total_unrealized_pnl": 0.0,
                "scan_timestamp": time.time(),
                "dynamic_settings": {
                    "timeframe": settings.TIMEFRAME,
                    "sl_percent": settings.STOP_LOSS_PERCENT * 100,
                    "tp_percent": settings.TAKE_PROFIT_PERCENT * 100,
                    "risk_reward": settings.get_risk_reward_ratio()
                }
            }
            
            for pos in open_positions:
                symbol = pos['symbol']
                position_amt = float(pos['positionAmt'])
                entry_price = float(pos['entryPrice'])
                unrealized_pnl = float(pos['unRealizedProfit'])
                
                # TP/SL durumunu kontrol et
                try:
                    await binance_client._rate_limit_delay()
                    open_orders = await binance_client.client.futures_get_open_orders(symbol=symbol)
                    has_sl = any(order['type'] in ['STOP_MARKET', 'STOP'] for order in open_orders)
                    has_tp = any(order['type'] in ['TAKE_PROFIT_MARKET', 'TAKE_PROFIT', 'LIMIT'] 
                                and order.get('reduceOnly') for order in open_orders)
                except:
                    has_sl = False
                    has_tp = False
                
                # Dinamik TP/SL seviyeleri hesapla
                side = 'BUY' if position_amt > 0 else 'SELL'
                dynamic_levels = binance_client.get_dynamic_sl_tp_levels(entry_price, side)
                
                position_info = {
                    "symbol": symbol,
                    "side": "LONG" if position_amt > 0 else "SHORT",
                    "position_amt": position_amt,
                    "entry_price": entry_price,
                    "unrealized_pnl": unrealized_pnl,
                    "has_stop_loss": has_sl,
                    "has_take_profit": has_tp,
                    "protection_status": "FULL" if (has_sl and has_tp) else "PARTIAL" if (has_sl or has_tp) else "NONE",
                    "dynamic_levels": dynamic_levels,
                    "failed_attempts": self._failed_attempts.get(symbol, 0)
                }
                
                summary["positions"].append(position_info)
                summary["total_unrealized_pnl"] += unrealized_pnl
            
            return summary
            
        except Exception as e:
            print(f"❌ Pozisyon özeti hatası: {e}")
            return {
                "error": str(e),
                "total_open_positions": 0,
                "positions": [],
                "total_unrealized_pnl": 0.0
            }

# Global instance
position_manager = PositionManager()
