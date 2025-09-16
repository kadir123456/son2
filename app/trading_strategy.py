import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from .config import settings

class TradingStrategy:
    """
    🛡️ Güçlendirilmiş Sahte Sinyal Korumalı EMA Kesişim Stratejisi
    
    Temel Sinyal: EMA(9,21) kesişimi
    Gelişmiş Korumalar:
    - Dinamik Trend Filtresi (zaman dilimine göre EMA)
    - Gelişmiş Momentum Filtresi
    - Trend Gücü Analizi
    - Dinamik Volatilite Kontrolü
    - Güçlendirilmiş Hacim Filtresi
    - Risk Yönetimi ve Consecutive Loss Tracking
    - Günlük Pozisyon ve Kayıp Limiti
    """
    
    def __init__(self, short_ema_period: int = 9, long_ema_period: int = 21):
        self.short_ema_period = short_ema_period
        self.long_ema_period = long_ema_period
        self.last_signal_time = {}  # Her symbol için son sinyal zamanı
        self.consecutive_losses = {}  # Her symbol için ardışık kayıp sayısı
        self.daily_positions = {}  # Günlük pozisyon sayısı
        self.daily_loss = {}  # Günlük kayıp miktarı
        self.daily_reset_time = {}  # Son günlük reset zamanı
        
        print(f"🛡️ Güçlendirilmiş Sahte Sinyal Korumalı Strateji başlatıldı: EMA({self.short_ema_period}, {self.long_ema_period})")
        print(f"📊 Aktif Korumalar:")
        print(f"   Dinamik Trend Filtresi: {'✅' if settings.TREND_FILTER_ENABLED else '❌'}")
        print(f"   Gelişmiş Momentum: {'✅' if settings.MOMENTUM_FILTER_ENABLED else '❌'}")
        print(f"   Trend Gücü Analizi: {'✅' if settings.TREND_STRENGTH_FILTER_ENABLED else '❌'}")
        print(f"   Dinamik Min. Hareket: {'✅' if settings.MIN_PRICE_MOVEMENT_ENABLED else '❌'}")
        print(f"   Sıkılaştırılmış RSI: {'✅' if settings.RSI_FILTER_ENABLED else '❌'}")
        print(f"   Dinamik Sinyal Soğuma: {'✅' if settings.SIGNAL_COOLDOWN_ENABLED else '❌'}")
        print(f"   Adaptif Volatilite: {'✅' if settings.VOLATILITY_FILTER_ENABLED else '❌'}")
        print(f"   Güçlendirilmiş Hacim: {'✅' if settings.VOLUME_FILTER_ENABLED else '❌'}")

    def analyze_klines(self, klines: list, symbol: str = "UNKNOWN") -> str:
        """
        🎯 Ana analiz fonksiyonu - gelişmiş sahte sinyal korumalı
        """
        required_periods = max(
            self.long_ema_period, 
            settings.TREND_EMA_PERIOD, 
            settings.RSI_PERIOD, 
            settings.ATR_PERIOD,
            settings.MOMENTUM_PERIOD if settings.MOMENTUM_FILTER_ENABLED else 0,
            50  # Trend strength için minimum
        )
        
        if len(klines) < required_periods:
            print(f"⚠️ {symbol} yetersiz veri: {len(klines)}/{required_periods}")
            return "HOLD"

        try:
            # Günlük limitleri kontrol et
            if not self._check_daily_limits(symbol):
                return "HOLD"
            
            # DataFrame oluştur
            df = self._prepare_dataframe(klines)
            
            # Teknik indikatörleri hesapla
            df = self._calculate_indicators(df)
            
            # Temel EMA kesişim sinyali
            base_signal = self._get_base_ema_signal(df)
            
            if base_signal == "HOLD":
                return "HOLD"
                
            # 🛡️ Gelişmiş sahte sinyal filtrelerini uygula
            if not self._pass_all_enhanced_filters(df, base_signal, symbol):
                return "HOLD"
                
            # Risk/Reward kontrolü
            if not self._validate_risk_reward(df, base_signal):
                print(f"🚫 {symbol} Risk/Reward oranı yetersiz")
                return "HOLD"
                
            # Sinyal onaylandı
            self._update_signal_success(symbol)
            
            print(f"🎯 {symbol} için KALITELI sinyal: {base_signal} | RR: 1:{settings.get_risk_reward_ratio():.2f}")
            return base_signal
            
        except Exception as e:
            print(f"❌ {symbol} strateji analizi hatası: {e}")
            return "HOLD"

    def _check_daily_limits(self, symbol: str) -> bool:
        """Günlük pozisyon ve kayıp limitlerini kontrol et"""
        current_date = datetime.now().date()
        
        # Günlük reset kontrolü
        if symbol not in self.daily_reset_time or self.daily_reset_time[symbol] != current_date:
            self.daily_positions[symbol] = 0
            self.daily_loss[symbol] = 0.0
            self.daily_reset_time[symbol] = current_date
        
        # Günlük pozisyon limiti
        if self.daily_positions.get(symbol, 0) >= settings.MAX_DAILY_POSITIONS:
            print(f"🚫 {symbol} günlük pozisyon limiti aşıldı: {self.daily_positions[symbol]}")
            return False
        
        # Ardışık kayıp limiti
        if self.consecutive_losses.get(symbol, 0) >= settings.MAX_CONSECUTIVE_LOSSES:
            print(f"🚫 {symbol} ardışık kayıp limiti aşıldı: {self.consecutive_losses[symbol]}")
            return False
        
        return True

    def _prepare_dataframe(self, klines: list) -> pd.DataFrame:
        """DataFrame hazırla ve sayısal verileri dönüştür"""
        df = pd.DataFrame(klines, columns=[
            'open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time',
            'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume',
            'taker_buy_quote_asset_volume', 'ignore'
        ])
        
        # Sayısal dönüşümler
        numeric_columns = ['open', 'high', 'low', 'close', 'volume', 'number_of_trades']
        for col in numeric_columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        return df

    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Gelişmiş teknik indikatörleri hesapla"""
        
        # EMA'lar
        df['short_ema'] = df['close'].ewm(span=self.short_ema_period, adjust=False).mean()
        df['long_ema'] = df['close'].ewm(span=self.long_ema_period, adjust=False).mean()
        
        # Dinamik Trend EMA
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
            df['volume_ratio'] = df['volume'] / df['volume_ma']
        
        # YENİ: Momentum İndikatörü
        if settings.MOMENTUM_FILTER_ENABLED:
            df['momentum'] = self._calculate_momentum(df['close'], settings.MOMENTUM_PERIOD)
        
        # YENİ: Trend Gücü (ADX benzeri)
        if settings.TREND_STRENGTH_FILTER_ENABLED:
            df['trend_strength'] = self._calculate_trend_strength(df)
        
        # YENİ: Price Action Patterns
        if settings.PRICE_ACTION_FILTER_ENABLED:
            df['engulfing'] = self._detect_engulfing_patterns(df)
        
        # EMA Mesafe ve Gücü
        df['ema_distance'] = abs(df['short_ema'] - df['long_ema']) / df['close']
        df['ema_slope_short'] = df['short_ema'].diff(3) / df['short_ema'].shift(3)
        df['ema_slope_long'] = df['long_ema'].diff(5) / df['long_ema'].shift(5)
        
        return df

    def _get_base_ema_signal(self, df: pd.DataFrame) -> str:
        """Güçlendirilmiş EMA kesişim sinyali"""
        if len(df) < 3:
            return "HOLD"
            
        last_row = df.iloc[-1]
        prev_row = df.iloc[-2]
        prev_prev_row = df.iloc[-3]
        
        # EMA kesişim kontrolü + eğim doğrulama
        short_ema_current = last_row['short_ema']
        long_ema_current = last_row['long_ema']
        short_ema_prev = prev_row['short_ema']
        long_ema_prev = prev_row['long_ema']
        
        # LONG sinyali: EMA kesişimi + pozitif eğim
        if (short_ema_prev <= long_ema_prev and 
            short_ema_current > long_ema_current and
            last_row['ema_slope_short'] > 0.001):  # Pozitif eğim kontrolü
            return "LONG"
        
        # SHORT sinyali: EMA kesişimi + negatif eğim  
        elif (short_ema_prev >= long_ema_prev and 
              short_ema_current < long_ema_current and
              last_row['ema_slope_short'] < -0.001):  # Negatif eğim kontrolü
            return "SHORT"
        
        return "HOLD"

    def _pass_all_enhanced_filters(self, df: pd.DataFrame, signal: str, symbol: str) -> bool:
        """🛡️ Gelişmiş tüm sahte sinyal filtrelerini kontrol et"""
        
        last_row = df.iloc[-1]
        
        # 1. 📊 Dinamik Trend Filtresi
        if settings.TREND_FILTER_ENABLED:
            if not self._pass_enhanced_trend_filter(df, last_row, signal):
                print(f"🚫 {symbol} Trend filtresi: {signal} ana trend ile uyumsuz")
                return False
        
        # 2. ⚡ Momentum Filtresi  
        if settings.MOMENTUM_FILTER_ENABLED:
            if not self._pass_momentum_filter(last_row, signal):
                print(f"🚫 {symbol} Momentum filtresi: Yetersiz momentum gücü")
                return False
        
        # 3. 💪 Trend Gücü Filtresi
        if settings.TREND_STRENGTH_FILTER_ENABLED:
            if not self._pass_trend_strength_filter(last_row):
                print(f"🚫 {symbol} Trend gücü filtresi: Zayıf trend")
                return False
        
        # 4. 📈 Dinamik Fiyat Hareketi Filtresi
        if settings.MIN_PRICE_MOVEMENT_ENABLED:
            if not self._pass_dynamic_price_movement_filter(df, signal):
                print(f"🚫 {symbol} Fiyat hareketi filtresi: Yetersiz volatilite")
                return False
        
        # 5. 🔄 Sıkılaştırılmış RSI Filtresi
        if settings.RSI_FILTER_ENABLED:
            if not self._pass_enhanced_rsi_filter(last_row, signal):
                print(f"🚫 {symbol} RSI filtresi: Aşırı alım/satım bölgesinde")
                return False
        
        # 6. ⏳ Dinamik Sinyal Soğuma Filtresi
        if settings.SIGNAL_COOLDOWN_ENABLED:
            if not self._pass_dynamic_cooldown_filter(symbol):
                print(f"🚫 {symbol} Soğuma filtresi: {settings.SIGNAL_COOLDOWN_MINUTES}dk beklenmeli")
                return False
        
        # 7. 🌊 Adaptif Volatilite Filtresi
        if settings.VOLATILITY_FILTER_ENABLED:
            if not self._pass_adaptive_volatility_filter(last_row):
                print(f"🚫 {symbol} Volatilite filtresi: Yetersiz piyasa hareketi")
                return False
        
        # 8. 📊 Güçlendirilmiş Hacim Filtresi
        if settings.VOLUME_FILTER_ENABLED:
            if not self._pass_enhanced_volume_filter(df, last_row):
                print(f"🚫 {symbol} Hacim filtresi: Yetersiz hacim konfirmasyonu")
                return False
        
        # 9. 📋 Fiyat Aksiyonu Filtresi
        if settings.PRICE_ACTION_FILTER_ENABLED:
            if not self._pass_price_action_filter(df, last_row, signal):
                print(f"🚫 {symbol} Fiyat aksiyonu filtresi: Zayıf pattern")
                return False
        
        # 10. 💪 EMA Gücü ve Mesafe Filtresi
        if not self._pass_ema_strength_filter(last_row):
            print(f"🚫 {symbol} EMA gücü filtresi: Yetersiz ayrışma")
            return False
        
        print(f"✅ {symbol} TÜM gelişmiş filtreleri geçti! Kaliteli sinyal onaylandı.")
        return True

    def _pass_enhanced_trend_filter(self, df: pd.DataFrame, row: pd.Series, signal: str) -> bool:
        """Gelişmiş trend filtresi"""
        if 'trend_ema' not in row:
            return True
            
        current_price = row['close']
        trend_ema = row['trend_ema']
        
        # Trend EMA'nın eğimi de kontrol edilir
        trend_slope = df['trend_ema'].iloc[-1] - df['trend_ema'].iloc[-5]
        trend_slope_ratio = trend_slope / df['trend_ema'].iloc[-5]
        
        if signal == "LONG":
            # Fiyat trend üstünde + trend yükselişte
            return (current_price > trend_ema and trend_slope_ratio > 0.002)
        elif signal == "SHORT":
            # Fiyat trend altında + trend düşüşte
            return (current_price < trend_ema and trend_slope_ratio < -0.002)
            
        return False

    def _pass_momentum_filter(self, row: pd.Series, signal: str) -> bool:
        """Momentum filtresi"""
        if 'momentum' not in row or pd.isna(row['momentum']):
            return True
            
        momentum = row['momentum']
        
        if signal == "LONG":
            return momentum > settings.MIN_MOMENTUM_STRENGTH
        elif signal == "SHORT":
            return momentum < -settings.MIN_MOMENTUM_STRENGTH
            
        return False

    def _pass_trend_strength_filter(self, row: pd.Series) -> bool:
        """Trend gücü filtresi"""
        if 'trend_strength' not in row or pd.isna(row['trend_strength']):
            return True
            
        return row['trend_strength'] > settings.MIN_TREND_STRENGTH

    def _pass_dynamic_price_movement_filter(self, df: pd.DataFrame, signal: str) -> bool:
        """Dinamik fiyat hareketi filtresi"""
        # Zaman dilimine göre dinamik period
        lookback_period = {
            "1m": 3,
            "3m": 5,
            "5m": 8,
            "15m": 10,
            "30m": 12,
            "1h": 15
        }.get(settings.TIMEFRAME, 10)
        
        recent_data = df.tail(lookback_period)
        recent_high = recent_data['high'].max()
        recent_low = recent_data['low'].min()
        price_movement = (recent_high - recent_low) / recent_low
        
        # Sinyal yönünde hareket var mı?
        price_direction = (df['close'].iloc[-1] - df['close'].iloc[-lookback_period]) / df['close'].iloc[-lookback_period]
        
        movement_ok = price_movement >= settings.MIN_PRICE_MOVEMENT_PERCENT
        direction_ok = ((signal == "LONG" and price_direction > 0) or 
                       (signal == "SHORT" and price_direction < 0))
        
        return movement_ok and direction_ok

    def _pass_enhanced_rsi_filter(self, row: pd.Series, signal: str) -> bool:
        """Sıkılaştırılmış RSI filtresi"""
        if 'rsi' not in row or pd.isna(row['rsi']):
            return True
            
        rsi = row['rsi']
        
        # Daha sıkı aralıklar
        if signal == "LONG":
            return settings.RSI_OVERSOLD < rsi < 65  # Aşırı satımdan çıkmış ama aşırı alımda değil
        elif signal == "SHORT":
            return 35 < rsi < settings.RSI_OVERBOUGHT  # Aşırı alımdan çıkmış ama aşırı satımda değil
            
        return True

    def _pass_dynamic_cooldown_filter(self, symbol: str) -> bool:
        """Dinamik sinyal soğuma filtresi"""
        if symbol not in self.last_signal_time:
            return True
            
        time_since_last = datetime.now() - self.last_signal_time[symbol]
        cooldown_period = timedelta(minutes=settings.SIGNAL_COOLDOWN_MINUTES)
        
        return time_since_last >= cooldown_period

    def _pass_adaptive_volatility_filter(self, row: pd.Series) -> bool:
        """Adaptif volatilite filtresi"""
        if 'atr' not in row or pd.isna(row['atr']):
            return True
            
        atr = row['atr']
        current_price = row['close']
        
        # Zaman dilimine göre adaptif ATR multiplier
        atr_ratio = atr / current_price
        min_atr_ratio = settings.MIN_ATR_MULTIPLIER / 1000
        
        return atr_ratio >= min_atr_ratio

    def _pass_enhanced_volume_filter(self, df: pd.DataFrame, row: pd.Series) -> bool:
        """Güçlendirilmiş hacim filtresi"""
        if 'volume_ratio' not in row or pd.isna(row['volume_ratio']):
            return True
        
        current_volume_ratio = row['volume_ratio']
        
        # Son 3 mumun hacim ortalaması da kontrol edilir
        recent_volume_avg = df['volume_ratio'].tail(3).mean()
        
        return (current_volume_ratio >= settings.MIN_VOLUME_MULTIPLIER and 
                recent_volume_avg >= (settings.MIN_VOLUME_MULTIPLIER * 0.8))

    def _pass_price_action_filter(self, df: pd.DataFrame, row: pd.Series, signal: str) -> bool:
        """Fiyat aksiyonu filtresi"""
        if not settings.ENGULFING_REQUIRED:
            return True
            
        if 'engulfing' not in row:
            return True
            
        # Engulfing pattern sinyal yönü ile uyumlu mu?
        engulfing = row['engulfing']
        if engulfing == 0:  # Pattern yok
            return True
        elif engulfing == 1 and signal == "LONG":  # Bullish engulfing + LONG
            return True
        elif engulfing == -1 and signal == "SHORT":  # Bearish engulfing + SHORT
            return True
            
        return False

    def _pass_ema_strength_filter(self, row: pd.Series) -> bool:
        """EMA gücü ve mesafe filtresi"""
        if 'ema_distance' not in row:
            return True
            
        # EMA'lar arası mesafe yeterli mi?
        ema_distance = row['ema_distance']
        return ema_distance >= settings.SIGNAL_STRENGTH_THRESHOLD

    def _validate_risk_reward(self, df: pd.DataFrame, signal: str) -> bool:
        """Risk/Reward oranı kontrolü"""
        current_rr = settings.get_risk_reward_ratio()
        return current_rr >= settings.MIN_RISK_REWARD_RATIO

    # --- YENİ HELPer METHODLAR ---
    
    def _calculate_momentum(self, prices: pd.Series, period: int = 10) -> pd.Series:
        """Momentum hesaplama"""
        return (prices - prices.shift(period)) / prices.shift(period) * 100

    def _calculate_trend_strength(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Trend gücü hesaplama (ADX benzeri)"""
        high_diff = df['high'].diff()
        low_diff = df['low'].diff()
        
        plus_dm = np.where((high_diff > low_diff) & (high_diff > 0), high_diff, 0)
        minus_dm = np.where((low_diff > high_diff) & (low_diff > 0), low_diff, 0)
        
        plus_dm_ma = pd.Series(plus_dm).rolling(window=period).mean()
        minus_dm_ma = pd.Series(minus_dm).rolling(window=period).mean()
        
        atr = self._calculate_atr(df, period)
        
        plus_di = (plus_dm_ma / atr) * 100
        minus_di = (minus_dm_ma / atr) * 100
        
        dx = abs(plus_di - minus_di) / (plus_di + minus_di) * 100
        adx = dx.rolling(window=period).mean() / 100
        
        return adx

    def _detect_engulfing_patterns(self, df: pd.DataFrame) -> pd.Series:
        """Engulfing pattern tespiti"""
        engulfing = pd.Series(0, index=df.index)
        
        for i in range(1, len(df)):
            curr = df.iloc[i]
            prev = df.iloc[i-1]
            
            # Bullish Engulfing
            if (prev['close'] < prev['open'] and  # Önceki mum kırmızı
                curr['close'] > curr['open'] and  # Mevcut mum yeşil
                curr['open'] < prev['close'] and  # Mevcut açılış önceki kapanışın altında
                curr['close'] > prev['open']):    # Mevcut kapanış önceki açılışın üstünde
                engulfing.iloc[i] = 1
            
            # Bearish Engulfing
            elif (prev['close'] > prev['open'] and  # Önceki mum yeşil
                  curr['close'] < curr['open'] and  # Mevcut mum kırmızı
                  curr['open'] > prev['close'] and  # Mevcut açılış önceki kapanışın üstünde
                  curr['close'] < prev['open']):    # Mevcut kapanış önceki açılışın altında
                engulfing.iloc[i] = -1
        
        return engulfing

    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """RSI hesaplama"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """ATR hesaplama"""
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        return atr

    # --- TRADİNG OUTCOME TRAKİNG ---
    
    def _update_signal_success(self, symbol: str):
        """Başarılı sinyal sonrası güncelleme"""
        self.last_signal_time[symbol] = datetime.now()
        
        # Günlük pozisyon sayısını artır
        if symbol not in self.daily_positions:
            self.daily_positions[symbol] = 0
        self.daily_positions[symbol] += 1
        
        print(f"📊 {symbol} günlük pozisyon: {self.daily_positions[symbol]}/{settings.MAX_DAILY_POSITIONS}")

    def update_trade_result(self, symbol: str, pnl: float):
        """Trade sonucunu güncelle"""
        if pnl < 0:
            # Kayıplar
            if symbol not in self.consecutive_losses:
                self.consecutive_losses[symbol] = 0
            self.consecutive_losses[symbol] += 1
            
            # Günlük kayıp
            if symbol not in self.daily_loss:
                self.daily_loss[symbol] = 0.0
            self.daily_loss[symbol] += abs(pnl)
            
            print(f"📉 {symbol} ardışık kayıp: {self.consecutive_losses[symbol]}/{settings.MAX_CONSECUTIVE_LOSSES}")
        else:
            # Kazanç - ardışık kayıp sıfırla
            self.consecutive_losses[symbol] = 0
            print(f"📈 {symbol} kazanç - ardışık kayıp sıfırlandı")

    def get_filter_status(self, symbol: str) -> dict:
        """Filtrelerin durumunu döndür"""
        status = {
            "timeframe": settings.TIMEFRAME,
            "risk_reward_ratio": settings.get_risk_reward_ratio(),
            "stop_loss_percent": settings.STOP_LOSS_PERCENT * 100,
            "take_profit_percent": settings.TAKE_PROFIT_PERCENT * 100,
            "filters": {
                "trend_filter": settings.TREND_FILTER_ENABLED,
                "momentum_filter": settings.MOMENTUM_FILTER_ENABLED,
                "trend_strength_filter": settings.TREND_STRENGTH_FILTER_ENABLED,
                "price_movement_filter": settings.MIN_PRICE_MOVEMENT_ENABLED,
                "rsi_filter": settings.RSI_FILTER_ENABLED,
                "cooldown_filter": settings.SIGNAL_COOLDOWN_ENABLED,
                "volatility_filter": settings.VOLATILITY_FILTER_ENABLED,
                "volume_filter": settings.VOLUME_FILTER_ENABLED,
            },
            "risk_management": {
                "daily_positions": self.daily_positions.get(symbol, 0),
                "daily_positions_limit": settings.MAX_DAILY_POSITIONS,
                "consecutive_losses": self.consecutive_losses.get(symbol, 0),
                "consecutive_losses_limit": settings.MAX_CONSECUTIVE_LOSSES,
                "daily_loss": self.daily_loss.get(symbol, 0.0),
            },
            "last_signal_time": self.last_signal_time.get(symbol)
        }
        return status

# Global instance
trading_strategy = TradingStrategy(short_ema_period=9, long_ema_period=21)
