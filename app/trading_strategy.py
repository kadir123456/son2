# app/trading_strategy.py - BOLLİNGER BANDS STRATEJİSİ

import pandas as pd
import numpy as np
from typing import Dict, Optional
from .config import settings

class PureEMAStrategy:  # İsim aynı kaldı - uyumluluk için
    """
    📊 Bollinger Bands Al-Sat Stratejisi
    
    Her dakika:
    1. Bollinger Bantlarını hesapla
    2. 1 LONG pozisyon aç (alt bantta alış)
    3. 1 SHORT pozisyon aç (üst bantta satış)
    4. Dinamik TP/SL (bant genişliğine göre)
    """
    
    def __init__(self):
        self.bb_period = settings.BB_PERIOD
        self.bb_std = settings.BB_STD_DEV
        self.analysis_count = 0
        self.successful_signals = 0
        
        print(f"📊 Bollinger Bands Stratejisi başlatıldı")
        print(f"   Period: {self.bb_period}")
        print(f"   Std Dev: {self.bb_std}")
        print(f"   Timeframe: {settings.TIMEFRAME}")
    
    def analyze_klines(self, klines: list, symbol: str = "UNKNOWN") -> str:
        """
        📊 Bollinger Bands analizi - Geriye uyumluluk için
        
        Returns: "LONG" | "SHORT" | "HOLD"
        """
        analysis = self.analyze_and_calculate_levels(klines, symbol)
        if analysis and analysis.get('should_trade'):
            return "LONG"  # Her zaman pozisyon açmaya hazır
        return "HOLD"
    
    def analyze_and_calculate_levels(self, klines: list, symbol: str = "UNKNOWN") -> Optional[Dict]:
        """
        📊 Bollinger Bands hesaplama ve giriş seviyelerini belirleme
        
        Returns:
        {
            "long_entry": float,
            "short_entry": float,
            "long_tp": float,
            "long_sl": float,
            "short_tp": float,
            "short_sl": float,
            "bb_upper": float,
            "bb_middle": float,
            "bb_lower": float,
            "bb_width_percent": float,
            "should_trade": bool
        }
        """
        self.analysis_count += 1
        
        # Minimum veri kontrolü
        min_required = self.bb_period + 5
        if not klines or len(klines) < min_required:
            if settings.DEBUG_MODE:
                print(f"❌ {symbol}: Yetersiz veri ({len(klines) if klines else 0}/{min_required})")
            return None

        try:
            # DataFrame hazırla
            df = self._prepare_dataframe(klines)
            
            if df is None or len(df) < min_required:
                return None
            
            # Bollinger Bands hesapla
            df['bb_middle'] = df['close'].rolling(window=self.bb_period).mean()
            df['bb_std'] = df['close'].rolling(window=self.bb_period).std()
            df['bb_upper'] = df['bb_middle'] + (self.bb_std * df['bb_std'])
            df['bb_lower'] = df['bb_middle'] - (self.bb_std * df['bb_std'])
            
            # NaN temizle
            df = df.dropna().copy()
            
            if len(df) < 1:
                return None
            
            # Son değerler
            last_row = df.iloc[-1]
            current_price = float(last_row['close'])
            bb_upper = float(last_row['bb_upper'])
            bb_middle = float(last_row['bb_middle'])
            bb_lower = float(last_row['bb_lower'])
            bb_width = bb_upper - bb_lower
            bb_width_percent = (bb_width / current_price) * 100
            
            if settings.DEBUG_MODE:
                print(f"\n📊 {symbol} Bollinger Bands:")
                print(f"   Üst Bant: {bb_upper:.4f}")
                print(f"   Orta: {bb_middle:.4f}")
                print(f"   Alt Bant: {bb_lower:.4f}")
                print(f"   Genişlik: %{bb_width_percent:.3f}")
                print(f"   Güncel Fiyat: {current_price:.4f}")
            
            # Giriş seviyeleri
            # LONG: Alt banda yakın (alt bant + %10 yukarı)
            long_entry = bb_lower + (bb_width * 0.1)
            
            # SHORT: Üst banda yakın (üst bant - %10 aşağı)
            short_entry = bb_upper - (bb_width * 0.1)
            
            # Dinamik TP/SL hesaplama
            tp_distance = bb_width * settings.TP_MULTIPLIER
            sl_distance = bb_width * settings.SL_MULTIPLIER
            
            # TP/SL yüzdeleri
            long_tp_percent = (tp_distance / long_entry)
            long_sl_percent = (sl_distance / long_entry)
            short_tp_percent = (tp_distance / short_entry)
            short_sl_percent = (sl_distance / short_entry)
            
            # Min/Max sınırları uygula
            long_tp_percent = max(settings.MIN_TP_PERCENT, min(settings.MAX_TP_PERCENT, long_tp_percent))
            long_sl_percent = max(settings.MIN_SL_PERCENT, min(settings.MAX_SL_PERCENT, long_sl_percent))
            short_tp_percent = max(settings.MIN_TP_PERCENT, min(settings.MAX_TP_PERCENT, short_tp_percent))
            short_sl_percent = max(settings.MIN_SL_PERCENT, min(settings.MAX_SL_PERCENT, short_sl_percent))
            
            # LONG pozisyon seviyeleri
            long_tp = long_entry * (1 + long_tp_percent)
            long_sl = long_entry * (1 - long_sl_percent)
            
            # SHORT pozisyon seviyeleri
            short_tp = short_entry * (1 - short_tp_percent)
            short_sl = short_entry * (1 + short_sl_percent)
            
            if settings.DEBUG_MODE:
                print(f"\n🎯 {symbol} Pozisyon Seviyeleri:")
                print(f"   LONG Entry: {long_entry:.4f} | TP: {long_tp:.4f} (+%{long_tp_percent*100:.2f}) | SL: {long_sl:.4f} (-%{long_sl_percent*100:.2f})")
                print(f"   SHORT Entry: {short_entry:.4f} | TP: {short_tp:.4f} (-%{short_tp_percent*100:.2f}) | SL: {short_sl:.4f} (+%{short_sl_percent*100:.2f})")
            
            # Trade yapmak için minimum genişlik kontrolü
            should_trade = bb_width_percent > 0.1  # Minimum %0.1 genişlik
            
            if not should_trade:
                print(f"⚠️ {symbol}: Bollinger bantları çok dar, trade yapılmıyor")
            else:
                self.successful_signals += 1
            
            return {
                "long_entry": long_entry,
                "short_entry": short_entry,
                "long_tp": long_tp,
                "long_sl": long_sl,
                "long_tp_percent": long_tp_percent,
                "long_sl_percent": long_sl_percent,
                "short_tp": short_tp,
                "short_sl": short_sl,
                "short_tp_percent": short_tp_percent,
                "short_sl_percent": short_sl_percent,
                "bb_upper": bb_upper,
                "bb_middle": bb_middle,
                "bb_lower": bb_lower,
                "bb_width_percent": bb_width_percent,
                "current_price": current_price,
                "should_trade": should_trade
            }
            
        except Exception as e:
            print(f"❌ {symbol} Bollinger analiz hatası: {e}")
            return None
    
    def _prepare_dataframe(self, klines: list) -> Optional[pd.DataFrame]:
        """Kline verilerini DataFrame'e çevir"""
        try:
            klines_data = []
            for kline in klines:
                close_price = float(kline[4])
                if close_price > 0 and not (np.isnan(close_price) or np.isinf(close_price)):
                    klines_data.append({'close': close_price})
                    
            if not klines_data or len(klines_data) < 10:
                return None
                
            df = pd.DataFrame(klines_data)
            df = df[df['close'] > 0].copy()
            df = df.dropna().copy()
            
            return df if len(df) >= 10 else None
            
        except Exception as e:
            print(f"❌ DataFrame hatası: {e}")
            return None
    
    def get_debug_info(self, klines: list, symbol: str) -> dict:
        """Debug bilgisi"""
        try:
            analysis = self.analyze_and_calculate_levels(klines, symbol)
            if not analysis:
                return {"error": "Analiz yapılamadı"}
            
            return {
                "symbol": symbol,
                "strategy": "bollinger_bands",
                "current_price": analysis['current_price'],
                "bb_upper": analysis['bb_upper'],
                "bb_middle": analysis['bb_middle'],
                "bb_lower": analysis['bb_lower'],
                "bb_width_percent": analysis['bb_width_percent'],
                "long_entry": analysis['long_entry'],
                "short_entry": analysis['short_entry'],
                "should_trade": analysis['should_trade'],
                "total_analysis": self.analysis_count,
                "successful_signals": self.successful_signals
            }
        except Exception as e:
            return {"error": f"Debug hatası: {str(e)}"}
    
    def get_debug_info_optimized(self, klines: list, symbol: str) -> dict:
        """Geriye uyumluluk"""
        return self.get_debug_info(klines, symbol)
    
    def get_strategy_status_optimized(self, symbol: str) -> dict:
        """Strateji durumu"""
        return {
            "strategy_name": "Bollinger Bands Al-Sat",
            "version": "1.0",
            "bb_period": self.bb_period,
            "bb_std_dev": self.bb_std,
            "timeframe": settings.TIMEFRAME,
            "position_size": f"{settings.POSITION_SIZE_USDT} USDT",
            "leverage": f"{settings.LEVERAGE}x",
            "total_analysis": self.analysis_count,
            "successful_signals": self.successful_signals
        }
    
    def get_strategy_info(self) -> Dict:
        """Strateji bilgisi"""
        return self.get_strategy_status_optimized("GLOBAL")

# Global instance
trading_strategy = PureEMAStrategy()
