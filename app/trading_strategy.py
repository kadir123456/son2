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
        if len(klines) < max(self.long_ema_period, settings.TREND_EMA_PERIOD, settings.RSI_PERIOD, settings.ATR_PERIOD):
            return "HOLD"

        try:
            # DataFrame oluştur
            df = self._prepare_dataframe(klines)
            
            # Teknik indikatörleri hesapla
            df = self._calculate_indicators(df)
            
            # Temel EMA kesişim sinyali
            base_signal = self._get_base_ema_signal(df)
            
            if base_signal == "HOLD":
                return "HOLD"
                
            # 🛡️ Sahte sinyal filtrelerini uygula
            if not self._pass_all_filters(df, base_signal, symbol):
                return "HOLD"
                
            # Sinyal onaylandı - son sinyal zamanını güncelle
            self.last_signal_time[symbol] = datetime.now()
            
            print(f"🎯 {symbol} için onaylanmış sinyal: {base_signal}")
            return base_signal
            
        except Exception as e:
            print(f"❌ {symbol} strateji analizi hatası: {e}")
            return "HOLD"

    def _prepare_dataframe(self, klines: list) -> pd.DataFrame:
        """DataFrame hazırla ve sayısal verileri dönüştür"""
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

    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Tüm teknik indikatörleri hesapla"""
        
        # EMA'lar
        df['short_ema'] = df['close'].ewm(span=self.short_ema_period, adjust=False).mean()
        df['long_ema'] = df['close'].ewm(span=self.long_ema_period, adjust=False).mean()
        
        if settings.TREND_FILTER_ENABLED:
            df['trend_ema'] = df['close'].ewm(span=settings.TREND_EMA_PERIOD, adjust=False).mean()
        
        # RSI
        if settings.RSI_FILTER_ENABLED:
            df['rsi'] = self._calculate_rsi(df['close'], settings.RSI_PERIOD)
        
        # ATR (Average True Range)
        if settings.VOLATILITY_FILTER_ENABLED:
            df['atr'] = self._calculate_atr(df, settings.ATR_PERIOD)
        
        # Hacim Ortalaması
        if settings.VOLUME_FILTER_ENABLED:
            df['volume_ma'] = df['volume'].rolling(window=settings.VOLUME_MA_PERIOD).mean()
        
        return df

    def _get_base_ema_signal(self, df: pd.DataFrame) -> str:
        """Temel EMA kesişim sinyali"""
        if len(df) < 2:
            return "HOLD"
            
        last_row = df.iloc[-1]
        prev_row = df.iloc[-2]
        
        # EMA kesişim kontrolü
        if (prev_row['short_ema'] < prev_row['long_ema'] and 
            last_row['short_ema'] > last_row['long_ema']):
            return "LONG"
        elif (prev_row['short_ema'] > prev_row['long_ema'] and 
              last_row['short_ema'] < last_row['long_ema']):
            return "SHORT"
        
        return "HOLD"

    def _pass_all_filters(self, df: pd.DataFrame, signal: str, symbol: str) -> bool:
        """🛡️ Tüm sahte sinyal filtrelerini kontrol et"""
        
        last_row = df.iloc[-1]
        
        # 1. 📊 Trend Filtresi
        if settings.TREND_FILTER_ENABLED:
            if not self._pass_trend_filter(last_row, signal):
                print(f"🚫 {symbol} Trend filtresi: {signal} sinyali ana trend ile uyumsuz")
                return False
        
        # 2. 📈 Minimum Fiyat Hareketi Filtresi
        if settings.MIN_PRICE_MOVEMENT_ENABLED:
            if not self._pass_price_movement_filter(df):
                print(f"🚫 {symbol} Fiyat hareketi filtresi: Yetersiz volatilite")
                return False
        
        # 3. 🔄 RSI Filtresi
        if settings.RSI_FILTER_ENABLED:
            if not self._pass_rsi_filter(last_row, signal):
                print(f"🚫 {symbol} RSI filtresi: Aşırı alım/satım bölgesinde")
                return False
        
        # 4. ⏳ Sinyal Soğuma Filtresi
        if settings.SIGNAL_COOLDOWN_ENABLED:
            if not self._pass_cooldown_filter(symbol):
                print(f"🚫 {symbol} Soğuma filtresi: Son sinyalden yeterli zaman geçmedi")
                return False
        
        # 5. 🌊 Volatilite Filtresi (ATR)
        if settings.VOLATILITY_FILTER_ENABLED:
            if not self._pass_volatility_filter(last_row):
                print(f"🚫 {symbol} Volatilite filtresi: Yetersiz piyasa hareketi")
                return False
        
        # 6. 📊 Hacim Filtresi
        if settings.VOLUME_FILTER_ENABLED:
            if not self._pass_volume_filter(last_row):
                print(f"🚫 {symbol} Hacim filtresi: Yetersiz işlem hacmi")
                return False
        
        # 7. 💪 Sinyal Gücü Kontrolü
        if not self._pass_signal_strength_filter(last_row):
            print(f"🚫 {symbol} Sinyal gücü filtresi: EMA farkı çok düşük")
            return False
        
        print(f"✅ {symbol} tüm filtreleri geçti!")
        return True

    def _pass_trend_filter(self, row: pd.Series, signal: str) -> bool:
        """Trend filtresi - ana trend yönünde sinyal ver"""
        if 'trend_ema' not in row:
            return True
            
        current_price = row['close']
        trend_ema = row['trend_ema']
        
        # LONG sinyali için fiyat trend EMA'sının üstünde olmalı
        if signal == "LONG" and current_price > trend_ema:
            return True
        # SHORT sinyali için fiyat trend EMA'sının altında olmalı  
        elif signal == "SHORT" and current_price < trend_ema:
            return True
            
        return False

    def _pass_price_movement_filter(self, df: pd.DataFrame) -> bool:
        """Minimum fiyat hareketi filtresi"""
        if len(df) < 5:
            return True
            
        # Son 5 mumda fiyat hareketi
        recent_high = df['high'].tail(5).max()
        recent_low = df['low'].tail(5).min()
        price_movement = (recent_high - recent_low) / recent_low
        
        return price_movement >= settings.MIN_PRICE_MOVEMENT_PERCENT

    def _pass_rsi_filter(self, row: pd.Series, signal: str) -> bool:
        """RSI filtresi - aşırı alım/satım bölgelerini filtrele"""
        if 'rsi' not in row or pd.isna(row['rsi']):
            return True
            
        rsi = row['rsi']
        
        # LONG sinyali için RSI aşırı satım bölgesinde olmamalı
        if signal == "LONG" and rsi < settings.RSI_OVERSOLD:
            return False
        # SHORT sinyali için RSI aşırı alım bölgesinde olmamalı
        elif signal == "SHORT" and rsi > settings.RSI_OVERBOUGHT:
            return False
            
        return True

    def _pass_cooldown_filter(self, symbol: str) -> bool:
        """Sinyal soğuma filtresi"""
        if symbol not in self.last_signal_time:
            return True
            
        time_since_last = datetime.now() - self.last_signal_time[symbol]
        cooldown_period = timedelta(minutes=settings.SIGNAL_COOLDOWN_MINUTES)
        
        return time_since_last >= cooldown_period

    def _pass_volatility_filter(self, row: pd.Series) -> bool:
        """Volatilite filtresi - ATR kontrolü"""
        if 'atr' not in row or pd.isna(row['atr']):
            return True
            
        atr = row['atr']
        current_price = row['close']
        
        # ATR'nin fiyata oranı minimum eşiği geçmeli
        atr_ratio = atr / current_price
        min_atr_ratio = settings.MIN_ATR_MULTIPLIER / 1000  # 1.5 -> 0.0015
        
        return atr_ratio >= min_atr_ratio

    def _pass_volume_filter(self, row: pd.Series) -> bool:
        """Hacim filtresi"""
        if 'volume_ma' not in row or pd.isna(row['volume_ma']):
            return True
            
        current_volume = row['volume']
        avg_volume = row['volume_ma']
        
        return current_volume >= (avg_volume * settings.MIN_VOLUME_MULTIPLIER)

    def _pass_signal_strength_filter(self, row: pd.Series) -> bool:
        """Sinyal gücü filtresi - EMA farkı kontrolü"""
        short_ema = row['short_ema']
        long_ema = row['long_ema']
        
        # EMA'lar arası fark yeterli mi?
        ema_diff_ratio = abs(short_ema - long_ema) / long_ema
        
        return ema_diff_ratio >= settings.SIGNAL_STRENGTH_THRESHOLD

    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """RSI hesaplama"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """ATR (Average True Range) hesaplama"""
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        return atr

    def get_filter_status(self, symbol: str) -> dict:
        """Filtrelerin durumunu döndür"""
        status = {
            "trend_filter": settings.TREND_FILTER_ENABLED,
            "price_movement_filter": settings.MIN_PRICE_MOVEMENT_ENABLED,
            "rsi_filter": settings.RSI_FILTER_ENABLED,
            "cooldown_filter": settings.SIGNAL_COOLDOWN_ENABLED,
            "volatility_filter": settings.VOLATILITY_FILTER_ENABLED,
            "volume_filter": settings.VOLUME_FILTER_ENABLED,
            "last_signal_time": self.last_signal_time.get(symbol)
        }
        return status

# Global instance
trading_strategy = TradingStrategy(short_ema_period=9, long_ema_period=21)
