import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from .config import settings

class SimpleEMACrossStrategy:
    """
    🎯 BASİT EMA Cross Stratejisi - DÜZELTILDI
    - EMA 9 > EMA 21 OLURSA = LONG
    - EMA 9 < EMA 21 OLURSA = SHORT
    - Cross mantığı düzeltildi!
    """
    
    def __init__(self):
        self.ema_fast = settings.EMA_FAST_PERIOD    # 9
        self.ema_slow = settings.EMA_SLOW_PERIOD    # 21
        
        # Signal tracking
        self.last_signal_time = {}     # Her symbol için son sinyal zamanı
        self.signal_count = {}         # Signal statistics
        
        print(f"🎯 DÜZELTILMIŞ EMA CROSS Stratejisi:")
        print(f"   EMA Fast: {self.ema_fast}")
        print(f"   EMA Slow: {self.ema_slow}")
        print(f"   ✅ Cross mantığı düzeltildi!")
        print(f"   📈 EMA9 > EMA21 keserse = LONG")
        print(f"   📉 EMA9 < EMA21 keserse = SHORT")

    def analyze_klines(self, klines: list, symbol: str = "UNKNOWN") -> str:
        """
        🎯 DÜZELTILMIŞ EMA Cross analizi
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
            
            # ✅ DÜZELTILMIŞ EMA Cross sinyalini al
            signal = self._get_ema_cross_signal_fixed(df, symbol)
            
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
        """EMA'ları hesapla - Doğru formül"""
        try:
            # ✅ DOĞRU EMA Hesaplama
            # EMA 9 (Hızlı) - span=9 kullan
            df['ema9'] = df['close'].ewm(span=self.ema_fast, adjust=False).mean()
            
            # EMA 21 (Yavaş) - span=21 kullan
            df['ema21'] = df['close'].ewm(span=self.ema_slow, adjust=False).mean()
            
            # ✅ DOĞRU Cross durumu - Boolean değerler
            df['ema9_above_ema21'] = df['ema9'] > df['ema21']
            
            # ✅ DOĞRU Cross detection - Bir önceki ile karşılaştır
            df['prev_ema9_above'] = df['ema9_above_ema21'].shift(1)
            
            # Cross flag'leri
            df['bullish_cross'] = (~df['prev_ema9_above']) & df['ema9_above_ema21']  # False → True
            df['bearish_cross'] = df['prev_ema9_above'] & (~df['ema9_above_ema21'])  # True → False
            
            return df
            
        except Exception as e:
            print(f"❌ EMA hesaplama hatası: {e}")
            return df

    def _get_ema_cross_signal_fixed(self, df: pd.DataFrame, symbol: str) -> str:
        """
        ✅ DÜZELTILMIŞ EMA Cross sinyal mantığı
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
            current_price = current_row['close']
            ema9 = current_row['ema9']
            ema21 = current_row['ema21']
            ema9_above = current_row['ema9_above_ema21']
            bullish_cross = current_row['bullish_cross']
            bearish_cross = current_row['bearish_cross']
            
            # Debug bilgisi
            print(f"🔍 {symbol} DÜZELTILMIŞ EMA Analizi:")
            print(f"   📊 Fiyat: {current_price:.6f}")
            print(f"   📈 EMA9:  {ema9:.6f}")
            print(f"   📊 EMA21: {ema21:.6f}")
            print(f"   ⚖️  EMA9 > EMA21: {ema9_above}")
            print(f"   🚀 Bullish Cross: {bullish_cross}")
            print(f"   📉 Bearish Cross: {bearish_cross}")
            
            # ===========================================
            # ✅ DÜZELTILMIŞ EMA CROSS SİNYAL MANTIĞI
            # ===========================================
            
            # 🚀 BULLISH CROSS - EMA9 EMA21'i yukarı kestiği an
            if bullish_cross:
                print(f"🚀 {symbol}: BULLISH CROSS! EMA9 yukarı kesti EMA21'i → LONG")
                return "LONG"
            
            # 📉 BEARISH CROSS - EMA9 EMA21'i aşağı kestiği an  
            if bearish_cross:
                print(f"📉 {symbol}: BEARISH CROSS! EMA9 aşağı kesti EMA21'i → SHORT")
                return "SHORT"
            
            # Cross yok, mevcut trend devam ediyor
            trend = "YUKARIDA" if ema9_above else "AŞAĞIDA"
            print(f"⏸️ {symbol}: Cross yok, EMA9 {trend} → HOLD")
            return "HOLD"
            
        except Exception as e:
            print(f"❌ {symbol} sinyal hesaplama hatası: {e}")
            return "HOLD"

    def get_debug_info(self, klines: list, symbol: str) -> dict:
        """
        🐛 Debug için detaylı EMA bilgisi
        """
        try:
            df = self._prepare_dataframe(klines)
            if df is None:
                return {"error": "DataFrame oluşturulamadı"}
            
            df = self._calculate_emas(df)
            
            # Son 5 mumun detayları
            last_5 = df.tail(5)[['close', 'ema9', 'ema21', 'ema9_above_ema21', 'bullish_cross', 'bearish_cross']]
            
            return {
                "symbol": symbol,
                "total_candles": len(df),
                "current_price": float(df.iloc[-1]['close']),
                "current_ema9": float(df.iloc[-1]['ema9']),
                "current_ema21": float(df.iloc[-1]['ema21']),
                "ema9_above": bool(df.iloc[-1]['ema9_above_ema21']),
                "bullish_cross": bool(df.iloc[-1]['bullish_cross']),
                "bearish_cross": bool(df.iloc[-1]['bearish_cross']),
                "last_5_candles": last_5.to_dict('records')
            }
        except Exception as e:
            return {"error": str(e)}

    def get_strategy_status(self, symbol: str) -> dict:
        """Strateji durumunu döndür"""
        return {
            "strategy_version": "1.1_fixed_ema_cross",
            "strategy_type": "fixed_ema_cross",
            "symbol": symbol,
            "ema_fast": self.ema_fast,
            "ema_slow": self.ema_slow,
            "signal_count": self.signal_count.get(symbol, {}),
            "last_signal_time": self.last_signal_time.get(symbol),
            "description": "DÜZELTILDI: EMA 9/21 doğru cross sinyalleri",
            "fix_notes": [
                "✅ Cross mantığı düzeltildi",
                "✅ Bullish cross: EMA9 yukarı kesti EMA21",
                "✅ Bearish cross: EMA9 aşağı kesti EMA21",
                "✅ Debug bilgileri eklendi"
            ]
        }

# Global instance - Düzeltilmiş strateji
trading_strategy = SimpleEMACrossStrategy()
