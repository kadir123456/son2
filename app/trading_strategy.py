import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from .config import settings

class BollingerBandsTradingStrategy:
    """
    🎯 Bollinger Bands + RSI Kombinasyonu Stratejisi
    
    Sinyal Mantığı:
    - %B < 0.2 + RSI < 40 = STRONG LONG
    - %B > 0.8 + RSI > 60 = STRONG SHORT
    - Fiyat alt bandı geçerse = LONG
    - Fiyat üst bandı geçerse = SHORT
    - Orta bant civarı = HOLD
    """
    
    def __init__(self, bb_period: int = 20, bb_std: float = 2.0):
        self.bb_period = bb_period  # Bollinger Bands period
        self.bb_std = bb_std        # Standard deviation multiplier
        self.rsi_period = 14
        self.last_signal_time = {}  # Her symbol için son sinyal zamanı
        self.signal_count = {}      # Debug için sinyal sayacı
        self.debug_enabled = True
        
        print(f"🎯 Bollinger Bands Stratejisi başlatıldı:")
        print(f"   BB Period: {self.bb_period}")
        print(f"   BB Std Dev: {self.bb_std}")
        print(f"   RSI Period: {self.rsi_period}")
        print(f"🛡️ Sahte sinyal korumaları:")
        print(f"   Min. fiyat hareketi: {'✅' if settings.MIN_PRICE_MOVEMENT_ENABLED else '❌'}")
        print(f"   Sinyal soğuma: {'✅' if settings.SIGNAL_COOLDOWN_ENABLED else '❌'}")
        print(f"   Hacim filtresi: {'✅' if settings.VOLUME_FILTER_ENABLED else '❌'}")

    def analyze_klines(self, klines: list, symbol: str = "UNKNOWN") -> str:
        """
        🎯 Ana Bollinger Bands analiz fonksiyonu
        """
        # Debug için sinyal sayacı
        if symbol not in self.signal_count:
            self.signal_count[symbol] = {"LONG": 0, "SHORT": 0, "HOLD": 0, "FILTERED": 0}
            
        # Minimum data kontrolü
        min_required = max(self.bb_period + 10, 35)
        if len(klines) < min_required:
            print(f"⚠️ {symbol}: Yetersiz veri ({len(klines)}/{min_required})")
            return "HOLD"

        try:
            # DataFrame oluştur
            df = self._prepare_dataframe(klines)
            
            if df is None or len(df) < min_required:
                print(f"❌ {symbol}: DataFrame oluşturulamadı")
                return "HOLD"
            
            # Bollinger Bands ve RSI hesapla
            df = self._calculate_bollinger_bands(df)
            df = self._calculate_rsi(df)
            
            # Debug: Son değerleri yazdır
            self._debug_current_values(df, symbol)
            
            # Bollinger Bands sinyali al
            bb_signal = self._get_bollinger_signal(df, symbol)
            
            print(f"🎯 {symbol} Bollinger Bands Sinyali: {bb_signal}")
            
            if bb_signal == "HOLD":
                self.signal_count[symbol]["HOLD"] += 1
                return "HOLD"
                
            # 🛡️ Basit filtreler uygula (daha az katı)
            if not self._pass_basic_filters(df, bb_signal, symbol):
                self.signal_count[symbol]["FILTERED"] += 1
                print(f"🚫 {symbol}: Sinyal filtrelendi - toplam: {self.signal_count[symbol]['FILTERED']}")
                return "HOLD"
                
            # Sinyal onaylandı
            self.last_signal_time[symbol] = datetime.now()
            self.signal_count[symbol][bb_signal] += 1
            
            print(f"✅ {symbol} ONAYLANMIŞ BOLLINGER SİNYAL: {bb_signal}")
            print(f"📊 {symbol} Sinyal İstatistikleri: {self.signal_count[symbol]}")
            return bb_signal
            
        except Exception as e:
            print(f"❌ {symbol} Bollinger Bands analizi hatası: {e}")
            import traceback
            print(f"🔍 Detay: {traceback.format_exc()}")
            return "HOLD"

    def _prepare_dataframe(self, klines: list) -> pd.DataFrame:
        """DataFrame hazırla - geliştirilmiş"""
        try:
            if not klines or len(klines) == 0:
                print("❌ Klines verisi boş")
                return None
                
            # Doğru column mapping
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
            
            if df.empty or len(df) < 10:
                return None
                
            return df
            
        except Exception as e:
            print(f"❌ DataFrame hazırlama hatası: {e}")
            return None

    def _calculate_bollinger_bands(self, df: pd.DataFrame) -> pd.DataFrame:
        """Bollinger Bands hesapla"""
        try:
            # Simple Moving Average (SMA)
            df['bb_middle'] = df['close'].rolling(window=self.bb_period).mean()
            
            # Standard Deviation
            df['bb_std'] = df['close'].rolling(window=self.bb_period).std()
            
            # Upper and Lower Bands
            df['bb_upper'] = df['bb_middle'] + (df['bb_std'] * self.bb_std)
            df['bb_lower'] = df['bb_middle'] - (df['bb_std'] * self.bb_std)
            
            # %B indikatörü (0-1 arası, 0=alt band, 1=üst band)
            df['bb_percent'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
            
            # Bandwidth (volatilite ölçüsü)
            df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
            
            return df
            
        except Exception as e:
            print(f"❌ Bollinger Bands hesaplama hatası: {e}")
            return df

    def _calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """RSI hesapla - destek amaçlı"""
        try:
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            
            # Sıfıra bölme kontrolü
            rs = gain / loss.replace(0, np.nan)
            df['rsi'] = 100 - (100 / (1 + rs))
            
            return df
            
        except Exception as e:
            print(f"⚠️ RSI hesaplama hatası: {e}")
            df['rsi'] = 50  # Varsayılan nötr RSI
            return df

    def _debug_current_values(self, df: pd.DataFrame, symbol: str):
        """Debug için mevcut değerleri yazdır"""
        try:
            if len(df) < 2:
                return
                
            last_row = df.iloc[-1]
            
            print(f"📊 {symbol} Bollinger Bands Değerleri:")
            print(f"   Fiyat: {last_row['close']:.6f}")
            print(f"   Üst Band: {last_row['bb_upper']:.6f}")
            print(f"   Orta Band: {last_row['bb_middle']:.6f}")
            print(f"   Alt Band: {last_row['bb_lower']:.6f}")
            print(f"   %B: {last_row['bb_percent']:.4f}")
            print(f"   Band Genişliği: {last_row['bb_width']:.4f}")
            print(f"   RSI: {last_row['rsi']:.2f}")
            
        except Exception as e:
            print(f"⚠️ Debug yazdırma hatası: {e}")

    def _get_bollinger_signal(self, df: pd.DataFrame, symbol: str) -> str:
        """Bollinger Bands sinyal mantığı - DÜZELTİLMİŞ"""
        try:
            if len(df) < 2:
                return "HOLD"
                
            current_row = df.iloc[-1]
            prev_row = df.iloc[-2]
            
            # NaN kontrolü
            required_values = [
                current_row['close'], current_row['bb_upper'], 
                current_row['bb_lower'], current_row['bb_percent']
            ]
            
            if any(pd.isna(val) for val in required_values):
                print(f"⚠️ {symbol}: Bollinger Bands değerlerinde NaN")
                return "HOLD"
            
            current_price = current_row['close']
            bb_percent = current_row['bb_percent']
            rsi = current_row.get('rsi', 50)
            bb_width = current_row.get('bb_width', 0)
            
            # Minimum volatilite kontrolü (çok dar bantları filtrele)
            if bb_width < 0.01:  # %1'den az genişlik
                print(f"⚠️ {symbol}: Bollinger Bands çok dar - volatilite düşük")
                return "HOLD"
            
            print(f"🔍 {symbol} Sinyal Analizi:")
            print(f"   %B: {bb_percent:.4f}")
            print(f"   RSI: {rsi:.2f}")
            print(f"   Band Genişliği: {bb_width:.4f}")
            
            # ===========================================
            # YENİ BOLLINGER BANDS SİNYAL MANTITI
            # ===========================================
            
            # GÜÇLÜ LONG Sinyali - Alt bant yakını + düşük RSI
            if bb_percent < 0.25 and rsi < 45:
                print(f"🚀 {symbol}: GÜÇLÜ LONG sinyali (%B={bb_percent:.3f}, RSI={rsi:.1f})")
                return "LONG"
            
            # GÜÇLÜ SHORT Sinyali - Üst bant yakını + yüksek RSI  
            if bb_percent > 0.75 and rsi > 55:
                print(f"📉 {symbol}: GÜÇLÜ SHORT sinyali (%B={bb_percent:.3f}, RSI={rsi:.1f})")
                return "SHORT"
            
            # ORTA SEVIYE LONG - Alt bant temas
            if bb_percent < 0.15:
                print(f"📈 {symbol}: LONG sinyali - Alt banta yakın (%B={bb_percent:.3f})")
                return "LONG"
                
            # ORTA SEVIYE SHORT - Üst bant temas
            if bb_percent > 0.85:
                print(f"📉 {symbol}: SHORT sinyali - Üst banta yakın (%B={bb_percent:.3f})")
                return "SHORT"
            
            # Fiyat bandın dışına çıkmış mı? (squeeze sonrası breakout)
            if current_price > current_row['bb_upper'] and prev_row['close'] <= prev_row['bb_upper']:
                if rsi < 70:  # Aşırı alımda değilse
                    print(f"💥 {symbol}: BREAKOUT LONG - Üst bandı kırma")
                    return "LONG"
                    
            if current_price < current_row['bb_lower'] and prev_row['close'] >= prev_row['bb_lower']:
                if rsi > 30:  # Aşırı satımda değilse
                    print(f"💥 {symbol}: BREAKOUT SHORT - Alt bandı kırma")
                    return "SHORT"
            
            # Orta bant yakını - bekle
            if 0.4 <= bb_percent <= 0.6:
                print(f"⏸️ {symbol}: Orta bant bölgesi - bekleme (%B={bb_percent:.3f})")
                
            print(f"⏸️ {symbol}: Net sinyal yok - HOLD")
            return "HOLD"
            
        except Exception as e:
            print(f"❌ {symbol} Bollinger sinyali hesaplama hatası: {e}")
            return "HOLD"

    def _pass_basic_filters(self, df: pd.DataFrame, signal: str, symbol: str) -> bool:
        """🛡️ Basit filtreler - daha az katı"""
        
        last_row = df.iloc[-1]
        
        # 1. ⏳ Sinyal Soğuma Filtresi (AZALTILDI)
        if settings.SIGNAL_COOLDOWN_ENABLED:
            if not self._pass_cooldown_filter(symbol):
                print(f"🚫 {symbol} Soğuma filtresi: Son sinyalden yeterli zaman geçmedi")
                return False
        
        # 2. 📈 Minimum Fiyat Hareketi (AZALTILDI)
        if settings.MIN_PRICE_MOVEMENT_ENABLED:
            if not self._pass_price_movement_filter(df):
                print(f"🚫 {symbol} Fiyat hareketi filtresi: Yetersiz volatilite")
                return False
        
        # 3. 📊 Hacim Filtresi (AZALTILDI)
        if settings.VOLUME_FILTER_ENABLED:
            if not self._pass_volume_filter(df):
                print(f"🚫 {symbol} Hacim filtresi: Yetersiz işlem hacmi")
                return False
        
        print(f"✅ {symbol} tüm filtreleri geçti!")
        return True

    def _pass_cooldown_filter(self, symbol: str) -> bool:
        """Sinyal soğuma filtresi - AZALTILMIŞ"""
        if symbol not in self.last_signal_time:
            return True
            
        time_since_last = datetime.now() - self.last_signal_time[symbol]
        
        # Cooldown'u daha da düşür (5 dakika)
        cooldown_period = timedelta(minutes=5)
        
        return time_since_last >= cooldown_period

    def _pass_price_movement_filter(self, df: pd.DataFrame) -> bool:
        """Minimum fiyat hareketi filtresi - AZALTILMIŞ"""
        try:
            if len(df) < 5:
                return True
                
            # Son 5 mumda fiyat hareketi
            recent_high = df['high'].tail(5).max()
            recent_low = df['low'].tail(5).min()
            
            if recent_low == 0:
                return True
                
            price_movement = (recent_high - recent_low) / recent_low
            
            # Çok düşük threshold - %0.1
            min_movement = 0.001  # %0.1
            
            return price_movement >= min_movement
            
        except Exception as e:
            print(f"⚠️ Fiyat hareketi filtresi hatası: {e}")
            return True

    def _pass_volume_filter(self, df: pd.DataFrame) -> bool:
        """Hacim filtresi - AZALTILMIŞ"""
        try:
            if len(df) < 10:
                return True
                
            current_volume = df['volume'].iloc[-1]
            avg_volume = df['volume'].tail(10).mean()
            
            if avg_volume == 0:
                return True
            
            # Çok düşük multiplier - sadece %5 fazla hacim yeterli
            min_volume_multiplier = 1.05
            
            return current_volume >= (avg_volume * min_volume_multiplier)
            
        except Exception as e:
            print(f"⚠️ Hacim filtresi hatası: {e}")
            return True

    def get_filter_status(self, symbol: str) -> dict:
        """Filtrelerin durumunu döndür"""
        return {
            "strategy_type": "bollinger_bands",
            "bb_period": self.bb_period,
            "bb_std": self.bb_std,
            "cooldown_filter": settings.SIGNAL_COOLDOWN_ENABLED,
            "price_movement_filter": settings.MIN_PRICE_MOVEMENT_ENABLED,
            "volume_filter": settings.VOLUME_FILTER_ENABLED,
            "last_signal_time": self.last_signal_time.get(symbol),
            "signal_count": self.signal_count.get(symbol, {})
        }

# Global instance - Bollinger Bands stratejisi
trading_strategy = BollingerBandsTradingStrategy(bb_period=20, bb_std=2.0)
