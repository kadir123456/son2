import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from .config import settings

class EMAScalpingTradingStrategy:
    """
    🎯 EMA Cross + RSI + Volume Scalping Stratejisi
    
    Piyasanın en popüler ve başarılı scalping stratejisi:
    - EMA 9/21 Cross (ana sinyal)
    - RSI confirmation (momentum)
    - Volume spike (güç konfirmasyonu)
    - EMA 50 trend filter (isteğe bağlı)
    
    Sinyal Mantığı:
    LONG: EMA9 > EMA21 + RSI > 25 + Volume > 1.2x avg + price > EMA50
    SHORT: EMA9 < EMA21 + RSI < 75 + Volume > 1.2x avg + price < EMA50
    """
    
    def __init__(self, ema_fast: int = 9, ema_slow: int = 21, ema_trend: int = 50):
        self.ema_fast = ema_fast       # Hızlı EMA (9)
        self.ema_slow = ema_slow       # Yavaş EMA (21)
        self.ema_trend = ema_trend     # Trend EMA (50)
        self.rsi_period = 14
        self.volume_period = 20        # Volume average period
        self.last_signal_time = {}     # Her symbol için son sinyal zamanı
        self.signal_count = {}         # Debug için sinyal sayacı
        self.debug_enabled = True
        
        print(f"🎯 EMA CROSS SCALPING Stratejisi başlatıldı:")
        print(f"   EMA Fast: {self.ema_fast}")
        print(f"   EMA Slow: {self.ema_slow}")
        print(f"   EMA Trend: {self.ema_trend}")
        print(f"   RSI Period: {self.rsi_period}")
        print(f"   Volume Period: {self.volume_period}")
        print(f"🛡️ Scalping sahte sinyal korumaları:")
        print(f"   Min. fiyat hareketi: {'✅' if settings.MIN_PRICE_MOVEMENT_ENABLED else '❌'}")
        print(f"   Sinyal soğuma: {'✅' if settings.SIGNAL_COOLDOWN_ENABLED else '❌'}")
        print(f"   Hacim filtresi: {'✅' if settings.VOLUME_FILTER_ENABLED else '❌'}")

    def analyze_klines(self, klines: list, symbol: str = "UNKNOWN") -> str:
        """
        🎯 Ana EMA Cross Scalping analiz fonksiyonu
        """
        # Debug için sinyal sayacı
        if symbol not in self.signal_count:
            self.signal_count[symbol] = {"LONG": 0, "SHORT": 0, "HOLD": 0, "FILTERED": 0}
            
        # Minimum data kontrolü
        min_required = max(self.ema_trend + 10, 60)  # EMA50 için 60 mum minimum
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
            df = self._calculate_rsi(df)
            df = self._calculate_volume_avg(df)
            
            # Debug: Son değerleri yazdır
            self._debug_current_values(df, symbol)
            
            # EMA Cross sinyali al
            ema_signal = self._get_ema_cross_signal(df, symbol)
            
            print(f"🎯 {symbol} EMA Cross Sinyali: {ema_signal}")
            
            if ema_signal == "HOLD":
                self.signal_count[symbol]["HOLD"] += 1
                return "HOLD"
                
            # 🛡️ Scalping filtreleri uygula (agresif)
            if not self._pass_scalping_filters(df, ema_signal, symbol):
                self.signal_count[symbol]["FILTERED"] += 1
                print(f"🚫 {symbol}: Sinyal filtrelendi - toplam: {self.signal_count[symbol]['FILTERED']}")
                return "HOLD"
                
            # Sinyal onaylandı
            self.last_signal_time[symbol] = datetime.now()
            self.signal_count[symbol][ema_signal] += 1
            
            print(f"✅ {symbol} ONAYLANMIŞ EMA CROSS SİNYAL: {ema_signal}")
            print(f"📊 {symbol} Sinyal İstatistikleri: {self.signal_count[symbol]}")
            return ema_signal
            
        except Exception as e:
            print(f"❌ {symbol} EMA Cross analizi hatası: {e}")
            import traceback
            print(f"🔍 Detay: {traceback.format_exc()}")
            return "HOLD"

    def _prepare_dataframe(self, klines: list) -> pd.DataFrame:
        """DataFrame hazırla - aynı"""
        try:
            if not klines or len(klines) == 0:
                print("❌ Klines verisi boş")
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
            
            if df.empty or len(df) < 10:
                return None
                
            return df
            
        except Exception as e:
            print(f"❌ DataFrame hazırlama hatası: {e}")
            return None

    def _calculate_emas(self, df: pd.DataFrame) -> pd.DataFrame:
        """EMA'ları hesapla - SCALPING'İN KALBI"""
        try:
            # EMA 9 (Hızlı)
            df['ema_fast'] = df['close'].ewm(span=self.ema_fast).mean()
            
            # EMA 21 (Yavaş)
            df['ema_slow'] = df['close'].ewm(span=self.ema_slow).mean()
            
            # EMA 50 (Trend)
            df['ema_trend'] = df['close'].ewm(span=self.ema_trend).mean()
            
            # EMA Cross momentum (EMA9 - EMA21)
            df['ema_momentum'] = df['ema_fast'] - df['ema_slow']
            
            # EMA Cross direction (1: bullish, -1: bearish, 0: neutral)
            df['ema_direction'] = 0
            df.loc[df['ema_fast'] > df['ema_slow'], 'ema_direction'] = 1
            df.loc[df['ema_fast'] < df['ema_slow'], 'ema_direction'] = -1
            
            # Cross detection (yeni cross mu?)
            df['ema_cross'] = df['ema_direction'].diff()
            
            return df
            
        except Exception as e:
            print(f"❌ EMA hesaplama hatası: {e}")
            return df

    def _calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """RSI hesapla - momentum konfirmasyonu"""
        try:
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            
            rs = gain / loss.replace(0, np.nan)
            df['rsi'] = 100 - (100 / (1 + rs))
            
            return df
            
        except Exception as e:
            print(f"⚠️ RSI hesaplama hatası: {e}")
            df['rsi'] = 50  # Varsayılan nötr RSI
            return df

    def _calculate_volume_avg(self, df: pd.DataFrame) -> pd.DataFrame:
        """Volume ortalama hesapla - güç konfirmasyonu"""
        try:
            # Volume moving average
            df['volume_avg'] = df['volume'].rolling(window=self.volume_period).mean()
            
            # Volume ratio (current / average)
            df['volume_ratio'] = df['volume'] / df['volume_avg']
            
            return df
            
        except Exception as e:
            print(f"⚠️ Volume hesaplama hatası: {e}")
            df['volume_avg'] = df['volume']
            df['volume_ratio'] = 1.0
            return df

    def _debug_current_values(self, df: pd.DataFrame, symbol: str):
        """Debug için mevcut değerleri yazdır"""
        try:
            if len(df) < 2:
                return
                
            last_row = df.iloc[-1]
            prev_row = df.iloc[-2]
            
            print(f"📊 {symbol} EMA Cross Scalping Değerleri:")
            print(f"   Fiyat: {last_row['close']:.6f}")
            print(f"   EMA 9: {last_row['ema_fast']:.6f}")
            print(f"   EMA 21: {last_row['ema_slow']:.6f}")
            print(f"   EMA 50: {last_row['ema_trend']:.6f}")
            print(f"   EMA Momentum: {last_row['ema_momentum']:.6f}")
            print(f"   EMA Direction: {last_row['ema_direction']}")
            print(f"   RSI: {last_row['rsi']:.2f}")
            print(f"   Volume Ratio: {last_row['volume_ratio']:.2f}")
            
            # Cross detection
            if last_row['ema_cross'] == 2:
                print(f"   🔥 BULLISH CROSS: EMA9 yukarı kesti!")
            elif last_row['ema_cross'] == -2:
                print(f"   🔥 BEARISH CROSS: EMA9 aşağı kesti!")
            
        except Exception as e:
            print(f"⚠️ Debug yazdırma hatası: {e}")

    def _get_ema_cross_signal(self, df: pd.DataFrame, symbol: str) -> str:
        """EMA Cross sinyal mantığı - SCALPING OPTIMIZED"""
        try:
            if len(df) < 3:
                return "HOLD"
                
            current_row = df.iloc[-1]
            prev_row = df.iloc[-2]
            prev2_row = df.iloc[-3]
            
            # NaN kontrolü
            required_values = [
                current_row['close'], current_row['ema_fast'], 
                current_row['ema_slow'], current_row['ema_trend'],
                current_row['rsi'], current_row['volume_ratio']
            ]
            
            if any(pd.isna(val) for val in required_values):
                print(f"⚠️ {symbol}: EMA Cross değerlerinde NaN")
                return "HOLD"
            
            # Mevcut değerler
            price = current_row['close']
            ema9 = current_row['ema_fast']
            ema21 = current_row['ema_slow']
            ema50 = current_row['ema_trend']
            rsi = current_row['rsi']
            volume_ratio = current_row['volume_ratio']
            ema_cross = current_row['ema_cross']
            
            print(f"🔍 {symbol} EMA Cross Analizi:")
            print(f"   EMA9: {ema9:.6f} {'>' if ema9 > ema21 else '<'} EMA21: {ema21:.6f}")
            print(f"   Price: {price:.6f} {'>' if price > ema50 else '<'} EMA50: {ema50:.6f}")
            print(f"   RSI: {rsi:.2f}")
            print(f"   Volume: {volume_ratio:.2f}x")
            print(f"   Cross: {ema_cross}")
            
            # ===========================================
            # EMA CROSS SCALPING SİNYAL MANTIĞI
            # ===========================================
            
            # 🚀 GÜÇLÜ LONG Sinyali - Fresh bullish cross + confirmations
            if (ema_cross == 2 and  # Yeni bullish cross
                ema9 > ema21 and     # EMA9 üstte
                price > ema50 and    # Fiyat trend üstünde
                rsi > 35 and rsi < 80 and  # RSI güçlü ama aşırı alımda değil
                volume_ratio > 1.2):       # Volume spike
                print(f"🚀 {symbol}: GÜÇLÜ LONG - Fresh EMA Cross + Konfirmasyonlar")
                return "LONG"
            
            # 📉 GÜÇLÜ SHORT Sinyali - Fresh bearish cross + confirmations
            if (ema_cross == -2 and  # Yeni bearish cross
                ema9 < ema21 and      # EMA9 altta
                price < ema50 and     # Fiyat trend altında
                rsi < 65 and rsi > 20 and  # RSI zayıf ama aşırı satımda değil
                volume_ratio > 1.2):        # Volume spike
                print(f"📉 {symbol}: GÜÇLÜ SHORT - Fresh EMA Cross + Konfirmasyonlar")
                return "SHORT"
            
            # 📈 TREND TAKIP LONG - Strong uptrend continuation
            if (ema9 > ema21 and      # Bullish alignment
                price > ema9 and      # Price above fast EMA
                price > ema50 and     # Uptrend confirmed
                rsi > 40 and rsi < 75 and  # Momentum good but not overbought
                volume_ratio > 1.1 and     # Volume support
                (ema9 - ema21) > (prev_row['ema_fast'] - prev_row['ema_slow'])):  # Momentum increasing
                print(f"📈 {symbol}: TREND LONG - Strong momentum continuation")
                return "LONG"
                
            # 📉 TREND TAKIP SHORT - Strong downtrend continuation  
            if (ema9 < ema21 and      # Bearish alignment
                price < ema9 and      # Price below fast EMA
                price < ema50 and     # Downtrend confirmed
                rsi < 60 and rsi > 25 and  # Momentum weak but not oversold
                volume_ratio > 1.1 and     # Volume support
                (ema21 - ema9) > (prev_row['ema_slow'] - prev_row['ema_fast'])):  # Momentum increasing
                print(f"📉 {symbol}: TREND SHORT - Strong momentum continuation")
                return "SHORT"
            
            # 💥 SCALPING REVERSAL LONG - RSI oversold + price near EMA support
            if (price < ema21 and price > ema21 * 0.999 and  # Price near EMA21 support
                rsi < 30 and rsi > 15 and                     # RSI oversold but not extreme
                volume_ratio > 1.3 and                       # Strong volume
                ema9 > ema50):                                # Still in uptrend context
                print(f"💥 {symbol}: SCALPING LONG - RSI oversold reversal")
                return "LONG"
                
            # 💥 SCALPING REVERSAL SHORT - RSI overbought + price near EMA resistance
            if (price > ema21 and price < ema21 * 1.001 and  # Price near EMA21 resistance
                rsi > 70 and rsi < 85 and                     # RSI overbought but not extreme
                volume_ratio > 1.3 and                       # Strong volume
                ema9 < ema50):                                # Still in downtrend context
                print(f"💥 {symbol}: SCALPING SHORT - RSI overbought reversal")
                return "SHORT"
            
            # Sinyal koşulları sağlanmadı
            print(f"⏸️ {symbol}: EMA Cross koşulları sağlanmadı - HOLD")
            return "HOLD"
            
        except Exception as e:
            print(f"❌ {symbol} EMA Cross sinyali hesaplama hatası: {e}")
            return "HOLD"

    def _pass_scalping_filters(self, df: pd.DataFrame, signal: str, symbol: str) -> bool:
        """🛡️ Scalping filtreleri - agresif scalping için optimize"""
        
        last_row = df.iloc[-1]
        
        # 1. ⏳ Sinyal Soğuma Filtresi (SCALPING İÇİN KISA)
        if settings.SIGNAL_COOLDOWN_ENABLED:
            if not self._pass_cooldown_filter(symbol):
                print(f"🚫 {symbol} Soğuma filtresi: Son sinyalden yeterli zaman geçmedi")
                return False
        
        # 2. 📈 Minimum Fiyat Hareketi (SCALPING İÇİN DÜZ)
        if settings.MIN_PRICE_MOVEMENT_ENABLED:
            if not self._pass_price_movement_filter(df):
                print(f"🚫 {symbol} Fiyat hareketi filtresi: Yetersiz volatilite")
                return False
        
        # 3. 📊 Hacim Filtresi (SCALPING İÇİN SIKI)
        if settings.VOLUME_FILTER_ENABLED:
            if not self._pass_volume_filter(df):
                print(f"🚫 {symbol} Hacim filtresi: Yetersiz işlem hacmi")
                return False
        
        # 4. 🎯 SCALPING ÖZEL FİLTRELER
        
        # EMA spread kontrolü (çok dar spread scalping riskli)
        ema_spread = abs(last_row['ema_fast'] - last_row['ema_slow']) / last_row['close']
        if ema_spread < 0.0005:  # %0.05'ten az spread
            print(f"🚫 {symbol} EMA spread çok dar: {ema_spread*100:.3f}%")
            return False
        
        # RSI extreme kontrolü (aşırı seviyelerde scalping riskli)
        rsi = last_row['rsi']
        if rsi < 15 or rsi > 85:
            print(f"🚫 {symbol} RSI aşırı seviyede: {rsi:.1f}")
            return False
            
        # Volume spike kontrolü (minimum hacim gereksinimi)
        volume_ratio = last_row['volume_ratio']
        if volume_ratio < 1.0:
            print(f"🚫 {symbol} Hacim ortalamanın altında: {volume_ratio:.2f}x")
            return False
        
        print(f"✅ {symbol} tüm scalping filtrelerini geçti!")
        return True

    def _pass_cooldown_filter(self, symbol: str) -> bool:
        """Sinyal soğuma filtresi - SCALPING İÇİN KISA"""
        if symbol not in self.last_signal_time:
            return True
            
        time_since_last = datetime.now() - self.last_signal_time[symbol]
        
        # Scalping için çok kısa cooldown (2 dakika)
        cooldown_period = timedelta(minutes=2)
        
        return time_since_last >= cooldown_period

    def _pass_price_movement_filter(self, df: pd.DataFrame) -> bool:
        """Minimum fiyat hareketi filtresi - SCALPING İÇİN MINIMAL"""
        try:
            if len(df) < 3:
                return True
                
            # Son 3 mumda fiyat hareketi (scalping için kısa period)
            recent_high = df['high'].tail(3).max()
            recent_low = df['low'].tail(3).min()
            
            if recent_low == 0:
                return True
                
            price_movement = (recent_high - recent_low) / recent_low
            
            # Çok düşük threshold - %0.05 (scalping için minimal)
            min_movement = 0.0005  # %0.05
            
            return price_movement >= min_movement
            
        except Exception as e:
            print(f"⚠️ Fiyat hareketi filtresi hatası: {e}")
            return True

    def _pass_volume_filter(self, df: pd.DataFrame) -> bool:
        """Hacim filtresi - SCALPING İÇİN SIKI"""
        try:
            if len(df) < 5:
                return True
                
            current_volume = df['volume'].iloc[-1]
            avg_volume = df['volume'].tail(5).mean()  # Kısa period average
            
            if avg_volume == 0:
                return True
            
            # Scalping için yüksek multiplier - %20 fazla hacim gerekli
            min_volume_multiplier = 1.2
            
            return current_volume >= (avg_volume * min_volume_multiplier)
            
        except Exception as e:
            print(f"⚠️ Hacim filtresi hatası: {e}")
            return True

    def get_filter_status(self, symbol: str) -> dict:
        """Filtrelerin durumunu döndür"""
        return {
            "strategy_type": "ema_cross_scalping",
            "ema_fast": self.ema_fast,
            "ema_slow": self.ema_slow,
            "ema_trend": self.ema_trend,
            "rsi_period": self.rsi_period,
            "volume_period": self.volume_period,
            "cooldown_filter": settings.SIGNAL_COOLDOWN_ENABLED,
            "price_movement_filter": settings.MIN_PRICE_MOVEMENT_ENABLED,
            "volume_filter": settings.VOLUME_FILTER_ENABLED,
            "last_signal_time": self.last_signal_time.get(symbol),
            "signal_count": self.signal_count.get(symbol, {}),
            "scalping_optimized": True,
            "timeframes": ["5m", "15m"],
            "success_rate_expected": "70-80%"
        }

# Global instance - EMA Cross Scalping stratejisi
trading_strategy = EMAScalpingTradingStrategy(ema_fast=9, ema_slow=21, ema_trend=50)
