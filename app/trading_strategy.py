import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from .config import settings

class TradingStrategy:
    """
    🔧 DEBUG VERSİYONU - Basitleştirilmiş Sinyal Üretimi
    
    Temel Sinyal: EMA(9,21) kesişimi
    Filtrelerin çoğu debug için devre dışı bırakılmış
    """
    
    def __init__(self, short_ema_period: int = 9, long_ema_period: int = 21):
        self.short_ema_period = short_ema_period
        self.long_ema_period = long_ema_period
        self.last_signal_time = {}
        self.consecutive_losses = {}
        self.daily_positions = {}
        self.daily_loss = {}
        self.daily_reset_time = {}
        self.debug_mode = True  # DEBUG MOD AÇIK
        
        print(f"🔧 DEBUG Trading Strategy başlatıldı: EMA({self.short_ema_period}, {self.long_ema_period})")
        print(f"⚠️  DEBUG MODU AKTİF - Çoğu filtre devre dışı!")

    def analyze_klines(self, klines: list, symbol: str = "UNKNOWN") -> str:
        """
        🔧 DEBUG ANALİZ FONKSİYONU - Basitleştirilmiş
        """
        print(f"\n🔍 DEBUG ANALIZ BAŞLIYOR: {symbol}")
        print(f"   📊 Mevcut mum sayısı: {len(klines)}")
        
        # Minimum veri kontrolü - çok düşük tutuldu
        if len(klines) < 30:
            print(f"❌ DEBUG: {symbol} yetersiz veri: {len(klines)}/30")
            return "HOLD"

        try:
            # DataFrame oluştur
            df = self._prepare_dataframe(klines)
            print(f"✅ DEBUG: {symbol} DataFrame oluşturuldu ({len(df)} satır)")
            
            # Temel EMA'ları hesapla
            df['short_ema'] = df['close'].ewm(span=self.short_ema_period, adjust=False).mean()
            df['long_ema'] = df['close'].ewm(span=self.long_ema_period, adjust=False).mean()
            
            # Son değerleri kontrol et
            if len(df) < 3:
                print(f"❌ DEBUG: {symbol} EMA hesaplaması için yetersiz veri")
                return "HOLD"
                
            last_row = df.iloc[-1]
            prev_row = df.iloc[-2]
            
            short_current = last_row['short_ema']
            long_current = last_row['long_ema']
            short_prev = prev_row['short_ema']
            long_prev = prev_row['long_ema']
            
            print(f"📈 DEBUG: {symbol} EMA Değerleri:")
            print(f"   Short EMA: {short_current:.8f} (önceki: {short_prev:.8f})")
            print(f"   Long EMA:  {long_current:.8f} (önceki: {long_prev:.8f})")
            print(f"   Fark:      {abs(short_current - long_current):.8f}")
            
            # Temel EMA kesişim sinyali - HİÇ FİLTRE YOK
            base_signal = self._get_debug_ema_signal(df)
            print(f"🎯 DEBUG: {symbol} Ham EMA sinyali: {base_signal}")
            
            if base_signal == "HOLD":
                print(f"⚪ DEBUG: {symbol} EMA kesişimi yok")
                return "HOLD"
            
            # DEBUG MODUNDA FİLTRELERİN ÇOĞUNU BY-PASS ET
            if self.debug_mode:
                # Sadece çok temel kontrolleri yap
                if not self._basic_debug_checks(symbol):
                    print(f"🚫 DEBUG: {symbol} temel kontrolleri geçemedi")
                    return "HOLD"
                    
                print(f"✅ DEBUG: {symbol} temel kontrolleri geçti")
            else:
                # Normal mod - tüm filtreleri uygula (eski kod)
                if not self._pass_all_enhanced_filters(df, base_signal, symbol):
                    return "HOLD"
            
            # Sinyal onaylandı
            self._update_signal_success(symbol)
            
            print(f"🎯 DEBUG: {symbol} için KALİTELİ SİNYAL ÜRETİLDİ: {base_signal}")
            print(f"=" * 50)
            return base_signal
            
        except Exception as e:
            print(f"❌ DEBUG: {symbol} analiz hatası: {e}")
            import traceback
            print(f"📋 DEBUG Traceback:\n{traceback.format_exc()}")
            return "HOLD"

    def _get_debug_ema_signal(self, df: pd.DataFrame) -> str:
        """DEBUG: Basit EMA kesişim kontrolü - hiç eğim kontrolü yok"""
        if len(df) < 2:
            return "HOLD"
            
        last_row = df.iloc[-1]
        prev_row = df.iloc[-2]
        
        short_current = last_row['short_ema']
        long_current = last_row['long_ema']
        short_prev = prev_row['short_ema']
        long_prev = prev_row['long_ema']
        
        print(f"🔍 DEBUG EMA Kesişim Kontrolü:")
        print(f"   Önceki: Short({short_prev:.8f}) vs Long({long_prev:.8f}) = {short_prev - long_prev:.8f}")
        print(f"   Şimdiki: Short({short_current:.8f}) vs Long({long_current:.8f}) = {short_current - long_current:.8f}")
        
        # LONG: Short EMA, Long EMA'yı aşağıdan yukarı kesti
        if short_prev <= long_prev and short_current > long_current:
            print(f"🟢 DEBUG: LONG kesişimi tespit edildi!")
            return "LONG"
        
        # SHORT: Short EMA, Long EMA'yı yukarıdan aşağı kesti
        elif short_prev >= long_prev and short_current < long_current:
            print(f"🔴 DEBUG: SHORT kesişimi tespit edildi!")
            return "SHORT"
        
        return "HOLD"

    def _basic_debug_checks(self, symbol: str) -> bool:
        """DEBUG: Sadece çok temel kontroller"""
        
        # 1. Günlük limit kontrolü - çok yüksek limite çık
        if symbol not in self.daily_positions:
            self.daily_positions[symbol] = 0
            
        if self.daily_positions[symbol] >= 50:  # Çok yüksek limit
            print(f"🚫 DEBUG: {symbol} günlük limit (50) aşıldı: {self.daily_positions[symbol]}")
            return False
        
        # 2. Soğuma kontrolü - çok kısa süre
        if symbol in self.last_signal_time:
            time_since = datetime.now() - self.last_signal_time[symbol]
            cooldown = timedelta(minutes=2)  # Sadece 2 dakika
            
            if time_since < cooldown:
                remaining = cooldown - time_since
                print(f"🚫 DEBUG: {symbol} soğuma süresi: {remaining.seconds} saniye kaldı")
                return False
        
        print(f"✅ DEBUG: {symbol} temel kontrolleri başarılı")
        return True

    def _prepare_dataframe(self, klines: list) -> pd.DataFrame:
        """DataFrame hazırla"""
        df = pd.DataFrame(klines, columns=[
            'open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time',
            'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume',
            'taker_buy_quote_asset_volume', 'ignore'
        ])
        
        # Sayısal dönüşümler
        numeric_columns = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        return df

    def _update_signal_success(self, symbol: str):
        """Başarılı sinyal sonrası güncelleme"""
        self.last_signal_time[symbol] = datetime.now()
        
        if symbol not in self.daily_positions:
            self.daily_positions[symbol] = 0
        self.daily_positions[symbol] += 1
        
        print(f"📊 DEBUG: {symbol} günlük pozisyon sayısı: {self.daily_positions[symbol]}")

    def update_trade_result(self, symbol: str, pnl: float):
        """Trade sonucunu güncelle"""
        print(f"📈 DEBUG: {symbol} işlem sonucu: {pnl:.4f}")
        
        if pnl < 0:
            if symbol not in self.consecutive_losses:
                self.consecutive_losses[symbol] = 0
            self.consecutive_losses[symbol] += 1
            
            if symbol not in self.daily_loss:
                self.daily_loss[symbol] = 0.0
            self.daily_loss[symbol] += abs(pnl)
            
            print(f"📉 DEBUG: {symbol} ardışık kayıp: {self.consecutive_losses[symbol]}")
        else:
            self.consecutive_losses[symbol] = 0
            print(f"📈 DEBUG: {symbol} kazanç - ardışık kayıp sıfırlandı")

    def get_filter_status(self, symbol: str) -> dict:
        """DEBUG: Basitleştirilmiş durum"""
        return {
            "debug_mode": self.debug_mode,
            "timeframe": settings.TIMEFRAME,
            "daily_positions": self.daily_positions.get(symbol, 0),
            "consecutive_losses": self.consecutive_losses.get(symbol, 0),
            "last_signal_time": self.last_signal_time.get(symbol),
            "filters_bypassed": True
        }

    # Eski metodları koru (geriye uyumluluk için)
    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Geriye uyumluluk - şu an kullanılmıyor"""
        return df
        
    def _pass_all_enhanced_filters(self, df, signal, symbol):
        """Geriye uyumluluk - debug modda by-pass edilir"""
        if self.debug_mode:
            return True
        return False

# Global instance
trading_strategy = TradingStrategy(short_ema_period=9, long_ema_period=21)
