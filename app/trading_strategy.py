import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from .config import settings

class TradingStrategy:
    """
    🛡️ Sahte Sinyal Korumalı EMA Kesişim Stratejisi
    
    Temel Sinyal: EMA(9,21) kesişimi
    Korumalar:
    - Trend Filtresi (EMA50)
    - Minimum Fiyat Hareketi 
    - RSI Filtresi
    - Sinyal Soğuma Süresi
    - Volatilite Filtresi (ATR)
    - Hacim Filtresi
    """
    
    def __init__(self, short_ema_period: int = 9, long_ema_period: int = 21):
        self.short_ema_period = short_ema_period
        self.long_ema_period = long_ema_period
        self.last_signal_time = {}  # Her symbol için son sinyal zamanı
        self.signal_count = {}  # Debug için sinyal sayacı
        print(f"🛡️ Sahte Sinyal Korumalı Strateji başlatıldı: EMA({self.short_ema_period}, {self.long_ema_period})")
        print(f"📊 Aktif Korumalar:")
        print(f"   Trend Filtresi: {'✅' if settings.TREND_FILTER_ENABLED else '❌'}")
        print(f"   Min. Fiyat Hareketi: {'✅' if settings.MIN_PRICE_MOVEMENT_ENABLED else '❌'}")
        print(f"   RSI Filtresi: {'✅' if settings.RSI_FILTER_ENABLED else '❌'}")
        print(f"   Sinyal Soğuma: {'✅' if settings.SIGNAL_COOLDOWN_ENABLED else '❌'}")
        print(f"   Volatilite Filtresi: {'✅' if settings.VOLATILITY_FILTER_ENABLED else '❌'}")
        print(f"   Hacim Filtresi: {'✅' if settings.VOLUME_FILTER_ENABLED else '❌'}")

    def analyze_klines(self, klines: list, symbol: str = "UNKNOWN") -> str:
        """
        🎯 Ana analiz fonksiyonu - sahte sinyal korumalı
        """
        # Debug için sinyal sayacı
        if symbol not in self.signal_count:
            self.signal_count[symbol] = {"LONG": 0, "SHORT": 0, "HOLD": 0, "FILTERED": 0}
            
        # Minimum data kontrolü - daha düşük threshold
        min_required = max(self.long_ema_period + 5, 30)  # En az 30 mum
        if len(klines) < min_required:
            print(f"⚠️ {symbol}: Yetersiz veri ({len(klines)}/{min_required})")
            return "HOLD"

        try:
            # DataFrame oluştur - DÜZELTME: Doğru column mapping
            df = self._prepare_dataframe(klines)
            
            if df is None or len(df) < min_required:
                print(f"❌ {symbol}: DataFrame oluşturulamadı veya yetersiz")
                return "HOLD"
            
            # Teknik indikatörleri hesapla
            df = self._calculate_indicators(df)
            
            # Debug: Son değerleri yazdır
            self._debug_current_values(df, symbol)
            
            # Temel EMA kesişim sinyali
            base_signal = self._get_base_ema_signal(df)
            
            print(f"🔍 {symbol} Temel EMA Sinyali: {base_signal}")
            
            if base_signal == "HOLD":
                self.signal_count[symbol]["HOLD"] += 1
                return "HOLD"
                
            # 🛡️ Sahte sinyal filtrelerini uygula - DAHA ESNEK
            if not self._pass_all_filters(df, base_signal, symbol):
                self.signal_count[symbol]["FILTERED"] += 1
                print(f"🚫 {symbol}: Sinyal filtrelendi - toplam filtrelenen: {self.signal_count[symbol]['FILTERED']}")
                return "HOLD"
                
            # Sinyal onaylandı - son sinyal zamanını güncelle
            self.last_signal_time[symbol] = datetime.now()
            self.signal_count[symbol][base_signal] += 1
            
            print(f"🎯 {symbol} için ONAYLANMIŞ sinyal: {base_signal}")
            print(f"📊 {symbol} Sinyal İstatistikleri: {self.signal_count[symbol]}")
            return base_signal
            
        except Exception as e:
            print(f"❌ {symbol} strateji analizi hatası: {e}")
            import traceback
            print(f"🔍 Detay: {traceback.format_exc()}")
            return "HOLD"

    def _prepare_dataframe(self, klines: list) -> pd.DataFrame:
        """DataFrame hazırla ve sayısal verileri dönüştür - DÜZELTME"""
        try:
            # DÜZELTME: Doğru column mapping
            columns = [
                'open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time',
                'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume',
                'taker_buy_quote_asset_volume', 'ignore'
            ]
            
            # Klines data kontrolü
            if not klines or len(klines) == 0:
                print("❌ Klines verisi boş")
                return None
                
            # İlk satırın yapısını kontrol et
            first_row = klines[0]
            print(f"🔍 İlk kline yapısı: {len(first_row)} eleman")
            
            # DataFrame oluştur
            df = pd.DataFrame(klines, columns=columns)
            
            # DÜZELTME: Sayısal dönüşümlerle null kontrolü
            numeric_columns = ['open', 'high', 'low', 'close', 'volume', 'quote_asset_volume']
            
            for col in numeric_columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                
            # NaN değerleri kontrol et
            if df[numeric_columns].isnull().any().any():
                print("⚠️ DataFrame'de NaN değerler tespit edildi, forward fill uygulanıyor")
                df[numeric_columns] = df[numeric_columns].fillna(method='ffill')
            
            # Son kontrol
            if df.empty or len(df) < 10:
                print(f"❌ DataFrame hazırlama başarısız: {len(df)} satır")
                return None
                
            print(f"✅ DataFrame hazırlandı: {len(df)} satır, {len(df.columns)} kolon")
            return df
            
        except Exception as e:
            print(f"❌ DataFrame hazırlama hatası: {e}")
            return None

    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Tüm teknik indikatörleri hesapla - DÜZELTME"""
        try:
            # EMA'lar - NaN kontrolü ile
            df['short_ema'] = df['close'].ewm(span=self.short_ema_period, adjust=False).mean()
            df['long_ema'] = df['close'].ewm(span=self.long_ema_period, adjust=False).mean()
            
            # Trend EMA - daha kısa period
            if settings.TREND_FILTER_ENABLED:
                trend_period = min(settings.TREND_EMA_PERIOD, 30)  # Max 30'a düşür
                df['trend_ema'] = df['close'].ewm(span=trend_period, adjust=False).mean()
            
            # RSI - daha kısa period
            if settings.RSI_FILTER_ENABLED:
                rsi_period = min(settings.RSI_PERIOD, 14)
                df['rsi'] = self._calculate_rsi(df['close'], rsi_period)
            
            # ATR - daha kısa period
            if settings.VOLATILITY_FILTER_ENABLED:
                atr_period = min(settings.ATR_PERIOD, 14)
                df['atr'] = self._calculate_atr(df, atr_period)
            
            # Hacim Ortalaması - daha kısa period
            if settings.VOLUME_FILTER_ENABLED:
                volume_period = min(settings.VOLUME_MA_PERIOD, 15)
                df['volume_ma'] = df['volume'].rolling(window=volume_period).mean()
            
            return df
            
        except Exception as e:
            print(f"❌ İndikatör hesaplama hatası: {e}")
            return df

    def _debug_current_values(self, df: pd.DataFrame, symbol: str):
        """Debug için mevcut değerleri yazdır"""
        try:
            if len(df) < 2:
                return
                
            last_row = df.iloc[-1]
            prev_row = df.iloc[-2]
            
            print(f"📊 {symbol} Son Değerler:")
            print(f"   Fiyat: {last_row['close']:.6f}")
            print(f"   Short EMA: {last_row['short_ema']:.6f}")
            print(f"   Long EMA: {last_row['long_ema']:.6f}")
            print(f"   EMA Farkı: {((last_row['short_ema'] - last_row['long_ema']) / last_row['long_ema'] * 100):.4f}%")
            
            if 'rsi' in last_row and not pd.isna(last_row['rsi']):
                print(f"   RSI: {last_row['rsi']:.2f}")
                
        except Exception as e:
            print(f"⚠️ Debug yazdırma hatası: {e}")

    def _get_base_ema_signal(self, df: pd.DataFrame) -> str:
        """Temel EMA kesişim sinyali - DÜZELTME"""
        try:
            if len(df) < 2:
                return "HOLD"
                
            last_row = df.iloc[-1]
            prev_row = df.iloc[-2]
            
            # NaN kontrolü
            required_values = [last_row['short_ema'], last_row['long_ema'], 
                             prev_row['short_ema'], prev_row['long_ema']]
            
            if any(pd.isna(val) for val in required_values):
                print("⚠️ EMA değerlerinde NaN tespit edildi")
                return "HOLD"
            
            # EMA kesişim kontrolü - daha hassas
            current_short = last_row['short_ema']
            current_long = last_row['long_ema']
            prev_short = prev_row['short_ema']
            prev_long = prev_row['long_ema']
            
            # Minimum fark kontrolü - çok küçük farkları filtrele
            min_diff_threshold = 0.0001  # %0.01
            current_diff_ratio = abs(current_short - current_long) / current_long
            
            if current_diff_ratio < min_diff_threshold:
                return "HOLD"
            
            # Yukarı kesişim (LONG)
            if (prev_short <= prev_long and current_short > current_long):
                return "LONG"
            # Aşağı kesişim (SHORT)
            elif (prev_short >= prev_long and current_short < current_long):
                return "SHORT"
            
            return "HOLD"
            
        except Exception as e:
            print(f"❌ EMA sinyal hesaplama hatası: {e}")
            return "HOLD"

    def _pass_all_filters(self, df: pd.DataFrame, signal: str, symbol: str) -> bool:
        """🛡️ Tüm sahte sinyal filtrelerini kontrol et - DAHA ESNEK"""
        
        last_row = df.iloc[-1]
        
        # 1. 📊 Trend Filtresi - DAHA ESNEK
        if settings.TREND_FILTER_ENABLED:
            if not self._pass_trend_filter(last_row, signal):
                print(f"🚫 {symbol} Trend filtresi: {signal} sinyali ana trend ile uyumsuz")
                return False
        
        # 2. 📈 Minimum Fiyat Hareketi Filtresi - DAHA ESNEK
        if settings.MIN_PRICE_MOVEMENT_ENABLED:
            if not self._pass_price_movement_filter(df):
                print(f"🚫 {symbol} Fiyat hareketi filtresi: Yetersiz volatilite")
                return False
        
        # 3. 🔄 RSI Filtresi - DAHA ESNEK
        if settings.RSI_FILTER_ENABLED:
            if not self._pass_rsi_filter(last_row, signal):
                print(f"🚫 {symbol} RSI filtresi: Aşırı alım/satım bölgesinde")
                return False
        
        # 4. ⏳ Sinyal Soğuma Filtresi - DAHA ESNEK
        if settings.SIGNAL_COOLDOWN_ENABLED:
            if not self._pass_cooldown_filter(symbol):
                print(f"🚫 {symbol} Soğuma filtresi: Son sinyalden yeterli zaman geçmedi")
                return False
        
        # 5. 🌊 Volatilite Filtresi - DAHA ESNEK (ATR)
        if settings.VOLATILITY_FILTER_ENABLED:
            if not self._pass_volatility_filter(last_row):
                print(f"🚫 {symbol} Volatilite filtresi: Yetersiz piyasa hareketi")
                return False
        
        # 6. 📊 Hacim Filtresi - DAHA ESNEK
        if settings.VOLUME_FILTER_ENABLED:
            if not self._pass_volume_filter(last_row):
                print(f"🚫 {symbol} Hacim filtresi: Yetersiz işlem hacmi")
                return False
        
        # 7. 💪 Sinyal Gücü Kontrolü - DAHA ESNEK
        if not self._pass_signal_strength_filter(last_row):
            print(f"🚫 {symbol} Sinyal gücü filtresi: EMA farkı çok düşük")
            return False
        
        print(f"✅ {symbol} tüm filtreleri geçti!")
        return True

    def _pass_trend_filter(self, row: pd.Series, signal: str) -> bool:
        """Trend filtresi - DAHA ESNEK"""
        if 'trend_ema' not in row or pd.isna(row['trend_ema']):
            return True  # Trend EMA yoksa geç
            
        current_price = row['close']
        trend_ema = row['trend_ema']
        
        # Daha esnek trend kontrolü - %0.1 tolerans
        tolerance = 0.001  # %0.1
        
        if signal == "LONG":
            return current_price >= trend_ema * (1 - tolerance)
        elif signal == "SHORT":
            return current_price <= trend_ema * (1 + tolerance)
            
        return True

    def _pass_price_movement_filter(self, df: pd.DataFrame) -> bool:
        """Minimum fiyat hareketi filtresi - DAHA ESNEK"""
        try:
            if len(df) < 3:  # 5'ten 3'e düşür
                return True
                
            # Son 3 mumda fiyat hareketi
            recent_high = df['high'].tail(3).max()
            recent_low = df['low'].tail(3).min()
            
            if recent_low == 0:
                return True
                
            price_movement = (recent_high - recent_low) / recent_low
            
            # Threshold'u yarıya düşür
            min_movement = settings.MIN_PRICE_MOVEMENT_PERCENT * 0.5
            
            return price_movement >= min_movement
            
        except Exception as e:
            print(f"⚠️ Fiyat hareketi filtresi hatası: {e}")
            return True

    def _pass_rsi_filter(self, row: pd.Series, signal: str) -> bool:
        """RSI filtresi - DAHA ESNEK"""
        if 'rsi' not in row or pd.isna(row['rsi']):
            return True  # RSI yoksa geç
            
        rsi = row['rsi']
        
        # Daha esnek RSI sınırları
        oversold = settings.RSI_OVERSOLD + 5  # 30 -> 35
        overbought = settings.RSI_OVERBOUGHT - 5  # 70 -> 65
        
        # LONG sinyali için RSI çok düşük olmasın
        if signal == "LONG" and rsi < oversold:
            return False
        # SHORT sinyali için RSI çok yüksek olmasın
        elif signal == "SHORT" and rsi > overbought:
            return False
            
        return True

    def _pass_cooldown_filter(self, symbol: str) -> bool:
        """Sinyal soğuma filtresi - DAHA ESNEK"""
        if symbol not in self.last_signal_time:
            return True
            
        time_since_last = datetime.now() - self.last_signal_time[symbol]
        
        # Cooldown'u yarıya düşür
        cooldown_period = timedelta(minutes=settings.SIGNAL_COOLDOWN_MINUTES * 0.5)
        
        return time_since_last >= cooldown_period

    def _pass_volatility_filter(self, row: pd.Series) -> bool:
        """Volatilite filtresi - DAHA ESNEK"""
        if 'atr' not in row or pd.isna(row['atr']):
            return True  # ATR yoksa geç
            
        atr = row['atr']
        current_price = row['close']
        
        if current_price == 0 or atr == 0:
            return True
            
        # ATR'nin fiyata oranı minimum eşiği geçmeli - daha düşük
        atr_ratio = atr / current_price
        min_atr_ratio = (settings.MIN_ATR_MULTIPLIER * 0.5) / 1000  # Yarıya düşür
        
        return atr_ratio >= min_atr_ratio

    def _pass_volume_filter(self, row: pd.Series) -> bool:
        """Hacim filtresi - DAHA ESNEK"""
        if 'volume_ma' not in row or pd.isna(row['volume_ma']) or row['volume_ma'] == 0:
            return True  # Volume MA yoksa geç
            
        current_volume = row['volume']
        avg_volume = row['volume_ma']
        
        # Daha düşük volume threshold
        min_volume_multiplier = settings.MIN_VOLUME_MULTIPLIER * 0.7  # %30 daha esnek
        
        return current_volume >= (avg_volume * min_volume_multiplier)

    def _pass_signal_strength_filter(self, row: pd.Series) -> bool:
        """Sinyal gücü filtresi - DAHA ESNEK"""
        try:
            short_ema = row['short_ema']
            long_ema = row['long_ema']
            
            if pd.isna(short_ema) or pd.isna(long_ema) or long_ema == 0:
                return True
            
            # EMA'lar arası fark yeterli mi? - threshold'u düşür
            ema_diff_ratio = abs(short_ema - long_ema) / long_ema
            
            # Threshold'u yarıya düşür
            min_threshold = settings.SIGNAL_STRENGTH_THRESHOLD * 0.5
            
            return ema_diff_ratio >= min_threshold
            
        except Exception as e:
            print(f"⚠️ Sinyal gücü filtresi hatası: {e}")
            return True

    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """RSI hesaplama - hata kontrolü ile"""
        try:
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            
            # Sıfıra bölme kontrolü
            rs = gain / loss.replace(0, np.nan)
            rsi = 100 - (100 / (1 + rs))
            
            return rsi
            
        except Exception as e:
            print(f"⚠️ RSI hesaplama hatası: {e}")
            return pd.Series([50] * len(prices), index=prices.index)

    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """ATR hesaplama - hata kontrolü ile"""
        try:
            high_low = df['high'] - df['low']
            high_close = np.abs(df['high'] - df['close'].shift())
            low_close = np.abs(df['low'] - df['close'].shift())
            
            tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            atr = tr.rolling(window=period).mean()
            
            return atr
            
        except Exception as e:
            print(f"⚠️ ATR hesaplama hatası: {e}")
            return pd.Series([0.001] * len(df), index=df.index)

    def get_filter_status(self, symbol: str) -> dict:
        """Filtrelerin durumunu döndür"""
        status = {
            "trend_filter": settings.TREND_FILTER_ENABLED,
            "price_movement_filter": settings.MIN_PRICE_MOVEMENT_ENABLED,
            "rsi_filter": settings.RSI_FILTER_ENABLED,
            "cooldown_filter": settings.SIGNAL_COOLDOWN_ENABLED,
            "volatility_filter": settings.VOLATILITY_FILTER_ENABLED,
            "volume_filter": settings.VOLUME_FILTER_ENABLED,
            "last_signal_time": self.last_signal_time.get(symbol),
            "signal_count": self.signal_count.get(symbol, {})
        }
        return status

# Global instance
trading_strategy = TradingStrategy(short_ema_period=9, long_ema_period=21)
