# app/trading_strategy.py - SAF EMA CROSS STRATEJİSİ

import pandas as pd
import numpy as np
import warnings
from .config import settings

warnings.filterwarnings("ignore")
pd.set_option('future.no_silent_downcasting', True)

class PureEMAStrategy:
    """
    📈 SAF EMA Cross Stratejisi
    - Filtre YOK
    - Sadece EMA9 ve EMA21 kesişimi
    - Cooldown YOK
    - Whipsaw koruması YOK
    """
    
    def __init__(self):
        self.ema_fast = settings.EMA_FAST_PERIOD
        self.ema_slow = settings.EMA_SLOW_PERIOD
        
        # Tracking
        self.analysis_count = 0
        self.signal_count = {"LONG": 0, "SHORT": 0, "HOLD": 0}
        
        print(f"📈 SAF EMA CROSS: {self.ema_fast}/{self.ema_slow}")
        print("✅ FİLTRE YOK - Saf EMA kesişimi")

    def analyze_klines(self, klines: list, symbol: str = "UNKNOWN") -> str:
        """
        📈 Saf EMA analizi - FİLTRE YOK
        
        Returns: "LONG" | "SHORT" | "HOLD"
        """
        self.analysis_count += 1
        
        min_required = max(self.ema_slow + 5, 30)
        if not klines or len(klines) < min_required:
            return "HOLD"

        try:
            df = self._prepare_dataframe(klines)
            
            if df is None or len(df) < min_required:
                return "HOLD"
            
            # EMA hesapla
            df['ema_fast'] = df['close'].ewm(span=self.ema_fast, adjust=False).mean()
            df['ema_slow'] = df['close'].ewm(span=self.ema_slow, adjust=False).mean()
            
            # NaN temizle
            df['ema_fast'] = df['ema_fast'].fillna(df['close'])
            df['ema_slow'] = df['ema_slow'].fillna(df['close'])
            
            # Kesişim kontrolü
            df['fast_above'] = df['ema_fast'] > df['ema_slow']
            df['prev_fast_above'] = df['fast_above'].shift(1).fillna(False)
            
            # Cross detection
            df['bullish_cross'] = (~df['prev_fast_above']) & df['fast_above']
            df['bearish_cross'] = df['prev_fast_above'] & (~df['fast_above'])
            
            # Son mum
            last_row = df.iloc[-1]
            
            if last_row['bullish_cross']:
                signal = "LONG"
                print(f"🚀 {symbol}: EMA BULLISH CROSS → LONG")
            elif last_row['bearish_cross']:
                signal = "SHORT"
                print(f"📉 {symbol}: EMA BEARISH CROSS → SHORT")
            else:
                signal = "HOLD"
            
            self.signal_count[signal] += 1
            
            return signal
            
        except Exception as e:
            print(f"❌ {symbol} EMA analiz hatası: {e}")
            return "HOLD"

    def _prepare_dataframe(self, klines: list) -> pd.DataFrame:
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
            df = self._prepare_dataframe(klines)
            if df is None:
                return {"error": "DataFrame oluşturulamadı"}
            
            df['ema_fast'] = df['close'].ewm(span=self.ema_fast, adjust=False).mean()
            df['ema_slow'] = df['close'].ewm(span=self.ema_slow, adjust=False).mean()
            df['ema_fast'] = df['ema_fast'].fillna(df['close'])
            df['ema_slow'] = df['ema_slow'].fillna(df['close'])
            
            last_row = df.iloc[-1]
            
            return {
                "symbol": symbol,
                "strategy": "pure_ema_cross",
                "current_price": float(last_row['close']),
                "ema_fast": float(last_row['ema_fast']),
                "ema_slow": float(last_row['ema_slow']),
                "fast_above_slow": bool(last_row['ema_fast'] > last_row['ema_slow']),
                "total_analysis": self.analysis_count,
                "signal_count": self.signal_count
            }
        except Exception as e:
            return {"error": f"Debug hatası: {str(e)}"}

# Global instance
trading_strategy = PureEMAStrategy()
