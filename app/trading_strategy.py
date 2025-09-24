import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from .config import settings

class SimpleEMACrossStrategy:
    """
    🎯 BASİT EMA Cross Stratejisi
    - Sadece EMA 9/21 kesişimi
    - EMA9 > EMA21 = LONG
    - EMA9 < EMA21 = SHORT
    """
    
    def __init__(self):
        self.ema_fast = 9       # Hızlı EMA
        self.ema_slow = 21      # Yavaş EMA
        
        # Signal tracking
        self.last_signal_time = {}     # Her symbol için son sinyal zamanı
        self.signal_count = {}         # Signal statistics
        
        print(f"🎯 BASİT EMA CROSS Stratejisi:")
        print(f"   EMA Fast: {self.ema_fast}")
        print(f"   EMA Slow: {self.ema_slow}")
        print(f"   Strateji: Sadece kesişim sinyalleri")

    def analyze_klines(self, klines: list, symbol: str = "UNKNOWN") -> str:
        """
        🎯 Basit EMA Cross analizi
        """
        # Sayaçları başlat
        if symbol not in self.signal_count:
            self.signal_count[symbol] = {"LONG": 0, "SHORT": 0, "HOLD": 0}
            
        # Minimum data kontrolü
        min_required = max(self.ema_slow + 5, 30)
        if len(klines) < min_required:
            print(f"⚠️ {symbol}: Yetersiz veri ({len(klines)}/{min_required})")
            return "HOLD"

        try:
            # DataFrame oluştur
            df = self._prepare_dataframe(klines)
            
            if df is None or len(df) < min_required:
                print(f"❌ {symbol}: DataFrame oluşturulamadı")
                return "HOLD"
            
            # EMA'ları hesapla
            df = self._calculate_emas(df)
            
            # EMA Cross sinyalini al
            signal = self._get_ema_cross_signal(df, symbol)
            
            # Sinyal geçmişini güncelle
            if signal != "HOLD":
                self.last_signal_time[symbol] = datetime.now()
                
            self.signal_count[symbol][signal] += 1
            
            return signal
            
        except Exception as e:
            print(f"❌ {symbol} analizi hatası: {e}")
            return "HOLD"

    def _prepare_dataframe(self, klines: list) -> pd.DataFrame:
        """DataFrame hazırla"""
        try:
            if not klines or len(klines) == 0:
                return None
                
            columns = [
                'open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time',
                'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume',
                'taker_buy_quote_asset_volume', 'ignore'
            ]
            
            df = pd.DataFrame(klines, columns=columns)
            
            # Sayısal dönüşümler
            numeric_columns = ['open', 'high', 'low', 'close', 'volume']
            
            for col in numeric_columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                
            # NaN kontrolü
            if df[numeric_columns].isnull().any().any():
                df[numeric_columns] = df[numeric_columns].fillna(method='ffill')
            
            return df if not df.empty and len(df) >= 10 else None
            
        except Exception as e:
            print(f"❌ DataFrame hazırlama hatası: {e}")
            return None

    def _calculate_emas(self, df: pd.DataFrame) -> pd.DataFrame:
        """EMA'ları hesapla - sadece 9 ve 21"""
        try:
            # EMA 9 (Hızlı)
            df['ema9'] = df['close'].ewm(span=self.ema_fast).mean()
            
            # EMA 21 (Yavaş)
            df['ema21'] = df['close'].ewm(span=self.ema_slow).mean()
            
            # Cross durumu
            df['ema9_above_ema21'] = df['ema9'] > df['ema21']
            
            # Cross detection (yeni cross)
            df['cross'] = df['ema9_above_ema21'].diff()
            
            return df
            
        except Exception as e:
            print(f"❌ EMA hesaplama hatası: {e}")
            return df

    def _get_ema_cross_signal(self, df: pd.DataFrame, symbol: str) -> str:
        """
        🎯 Basit EMA Cross sinyal mantığı
        """
        try:
            if len(df) < 3:
                return "HOLD"
                
            current_row = df.iloc[-1]
            prev_row = df.iloc[-2]
            
            # NaN kontrolü
            if pd.isna(current_row['ema9']) or pd.isna(current_row['ema21']):
                print(f"⚠️ {symbol}: EMA değerlerinde NaN")
                return "HOLD"
            
            # Mevcut değerler
            ema9 = current_row['ema9']
            ema21 = current_row['ema21']
            cross = current_row['cross']
            
            print(f"🔍 {symbol} EMA Analizi:")
            print(f"   EMA9: {ema9:.6f}")
            print(f"   EMA21: {ema21:.6f}")
            print(f"   EMA9 {'>' if ema9 > ema21 else '<'} EMA21")
            print(f"   Cross: {cross}")
            
            # ===========================================
            # 🎯 EMA CROSS SİNYAL MANTIĞI
            # ===========================================
            
            # 🚀 BULLISH CROSS - EMA9 kesip yukarı çıktı
            if cross == 1.0:  # True'dan False'a geçiş = bullish cross
                print(f"🚀 {symbol}: BULLISH EMA CROSS - EMA9 kesip yukarı çıktı")
                return "LONG"
            
            # 📉 BEARISH CROSS - EMA9 kesip aşağı indi
            if cross == -1.0:  # False'dan True'ya geçiş = bearish cross
                print(f"📉 {symbol}: BEARISH EMA CROSS - EMA9 kesip aşağı indi")
                return "SHORT"
            
            # Kesişim yok
            print(f"⏸️ {symbol}: Kesişim yok, bekleniyor...")
            return "HOLD"
            
        except Exception as e:
            print(f"❌ {symbol} sinyal hesaplama hatası: {e}")
            return "HOLD"

    def get_strategy_status(self, symbol: str) -> dict:
        """Strateji durumunu döndür"""
        return {
            "strategy_version": "1.0_simple_ema_cross",
            "strategy_type": "simple_ema_cross",
            "symbol": symbol,
            "ema_fast": self.ema_fast,
            "ema_slow": self.ema_slow,
            "signal_count": self.signal_count.get(symbol, {}),
            "last_signal_time": self.last_signal_time.get(symbol),
            "description": "Sadece EMA 9/21 kesişim sinyalleri"
        }

# Global instance - Basit strateji
trading_strategy = SimpleEMACrossStrategy()
