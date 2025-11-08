# app/fast_scalping_strategy.py - HIZLI SCALPING STRATEJİSİ
# 30 saniye ve 1 dakika - Sürekli kar al-sat

import pandas as pd
import numpy as np
from typing import Dict, Optional
from datetime import datetime

class FastScalpingStrategy:
    """
    ⚡ HIZLI SCALPING STRATEJİSİ
    
    - 30 saniye ve 1 dakikalık mumlar
    - Hızlı giriş-çıkış (TP: %0.3-0.5, SL: %0.2-0.3)
    - Filtre YOK - Sürekli trade
    - Dakikada 1-2 pozisyon hedefi
    """
    
    def __init__(self):
        # Hızlı scalping parametreleri
        self.ema_fast = 5      # Çok hızlı EMA
        self.ema_slow = 13     # Hızlı EMA
        
        # TP/SL - Çok sıkı
        self.tp_percent = 0.004  # %0.4 kar al
        self.sl_percent = 0.002  # %0.2 zarar durdur
        
        # Momentum kontrolü
        self.min_momentum = 0.0005  # Minimum %0.05 hareket
        
        # İstatistikler
        self.analysis_count = 0
        self.signal_count = 0
        
        print("⚡ HIZLI SCALPING STRATEJİSİ AKTIF")
        print(f"   EMA: {self.ema_fast}/{self.ema_slow}")
        print(f"   TP: %{self.tp_percent*100:.2f} | SL: %{self.sl_percent*100:.2f}")
        print("   FİLTRE: YOK - SÜREKLI TRADE!")
    
    def analyze_and_calculate_levels(self, klines: list, symbol: str = "UNKNOWN") -> Optional[Dict]:
        """
        ⚡ Hızlı analiz ve seviye hesaplama
        
        Returns:
        {
            "signal": "LONG" | "SHORT",
            "should_trade": True (her zaman),
            "entry_price": float,
            "tp_price": float,
            "sl_price": float,
            "momentum": float
        }
        """
        self.analysis_count += 1
        
        # Minimum veri kontrolü
        if not klines or len(klines) < 15:
            return None
        
        try:
            # DataFrame hazırla
            df = self._prepare_dataframe(klines)
            if df is None or len(df) < 15:
                return None
            
            # EMA hesapla
            df['ema_fast'] = df['close'].ewm(span=self.ema_fast, adjust=False).mean()
            df['ema_slow'] = df['close'].ewm(span=self.ema_slow, adjust=False).mean()
            
            # NaN temizle
            df = df.dropna().copy()
            if len(df) < 2:
                return None
            
            # Son değerler
            last_row = df.iloc[-1]
            prev_row = df.iloc[-2]
            
            current_price = float(last_row['close'])
            ema_fast_current = float(last_row['ema_fast'])
            ema_slow_current = float(last_row['ema_slow'])
            
            ema_fast_prev = float(prev_row['ema_fast'])
            ema_slow_prev = float(prev_row['ema_slow'])
            
            # Momentum hesapla
            momentum = abs(current_price - float(df['close'].iloc[-5])) / current_price
            
            # Sinyal belirleme - Basit EMA cross
            bullish = ema_fast_current > ema_slow_current
            bearish = ema_fast_current < ema_slow_current
            
            # Cross kontrolü (daha hassas)
            bullish_cross = (ema_fast_prev <= ema_slow_prev) and (ema_fast_current > ema_slow_current)
            bearish_cross = (ema_fast_prev >= ema_slow_prev) and (ema_fast_current < ema_slow_current)
            
            # Sinyal seç
            if bullish_cross or (bullish and momentum > self.min_momentum):
                signal = "LONG"
            elif bearish_cross or (bearish and momentum > self.min_momentum):
                signal = "SHORT"
            else:
                # Momentum varsa yönde pozisyon aç
                signal = "LONG" if bullish else "SHORT"
            
            # TP/SL hesapla
            if signal == "LONG":
                tp_price = current_price * (1 + self.tp_percent)
                sl_price = current_price * (1 - self.sl_percent)
            else:  # SHORT
                tp_price = current_price * (1 - self.tp_percent)
                sl_price = current_price * (1 + self.sl_percent)
            
            self.signal_count += 1
            
            return {
                "signal": signal,
                "should_trade": True,  # HER ZAMAN TRADE YAP!
                "entry_price": current_price,
                "tp_price": tp_price,
                "sl_price": sl_price,
                "tp_percent": self.tp_percent,
                "sl_percent": self.sl_percent,
                "momentum": momentum,
                "ema_fast": ema_fast_current,
                "ema_slow": ema_slow_current,
                "bullish_cross": bullish_cross,
                "bearish_cross": bearish_cross
            }
            
        except Exception as e:
            print(f"❌ {symbol} analiz hatası: {e}")
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
            
            return df if len(df) >= 10 else None
            
        except Exception as e:
            print(f"❌ DataFrame hatası: {e}")
            return None
    
    def get_status(self) -> Dict:
        """Strateji durumu"""
        return {
            "strategy": "fast_scalping",
            "timeframe": "30s/1m",
            "ema_fast": self.ema_fast,
            "ema_slow": self.ema_slow,
            "tp_percent": f"%{self.tp_percent*100:.2f}",
            "sl_percent": f"%{self.sl_percent*100:.2f}",
            "total_analysis": self.analysis_count,
            "total_signals": self.signal_count,
            "signal_rate": f"%{(self.signal_count/max(self.analysis_count,1)*100):.1f}"
        }

# Global instance
fast_scalping_strategy = FastScalpingStrategy()
