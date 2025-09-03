import pandas as pd
import numpy as np

class TradingStrategy:
    """
    Geliştirilmiş EMA Crossover Stratejisi:
    - EMA 9 ve EMA 21 kesişimi
    - Ek filtreleme mekanizmaları
    - Daha güvenilir sinyal üretimi
    """
    def __init__(self, short_ema_period: int = 9, long_ema_period: int = 21):
        self.short_ema_period = short_ema_period
        self.long_ema_period = long_ema_period
        self.last_signals = {}  # Her coin için son sinyalleri tutar
        print(f"✅ Geliştirilmiş EMA Stratejisi başlatıldı: EMA({self.short_ema_period}, {self.long_ema_period})")

    def analyze_klines(self, klines: list, symbol: str = "DEFAULT") -> str:
        """
        Geliştirilmiş sinyal analizi:
        1. EMA kesişimi kontrolü
        2. Trend gücü analizi
        3. Sinyal filtreleme
        """
        if len(klines) < self.long_ema_period + 5:  # Daha fazla veri gereksinimi
            return "HOLD"

        try:
            # DataFrame oluştur
            df = pd.DataFrame(klines, columns=[
                'open_time', 'open', 'high', 'low', 'close', 'volume', 
                'close_time', 'quote_asset_volume', 'number_of_trades', 
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            # Numerik dönüşümler
            df['close'] = pd.to_numeric(df['close'])
            df['high'] = pd.to_numeric(df['high'])
            df['low'] = pd.to_numeric(df['low'])
            df['volume'] = pd.to_numeric(df['volume'])
            
            # EMA hesaplamaları
            df['short_ema'] = df['close'].ewm(span=self.short_ema_period, adjust=False).mean()
            df['long_ema'] = df['close'].ewm(span=self.long_ema_period, adjust=False).mean()
            
            # Trend gücü için ek göstergeler
            df['ema_diff'] = df['short_ema'] - df['long_ema']
            df['ema_diff_pct'] = (df['ema_diff'] / df['long_ema']) * 100
            
            # RSI hesaplama (momentum kontrolü için)
            rsi = self._calculate_rsi(df['close'], period=14)
            
            # Son birkaç mumun verilerini al
            current = df.iloc[-1]
            prev_1 = df.iloc[-2]
            prev_2 = df.iloc[-3] if len(df) > 2 else prev_1
            
            # Temel EMA kesişim sinyali
            signal = self._get_crossover_signal(prev_1, current)
            
            # Sinyal filtreleme ve iyileştirme
            filtered_signal = self._filter_signal(signal, df, rsi, symbol)
            
            # Son sinyal geçmişini güncelle
            self._update_signal_history(symbol, filtered_signal)
            
            return filtered_signal
            
        except Exception as e:
            print(f"❌ Strateji analizi hatası ({symbol}): {e}")
            return "HOLD"
    
    def _get_crossover_signal(self, prev_row, current_row) -> str:
        """Temel EMA kesişim sinyali"""
        # Bullish crossover: Short EMA yukarı keser Long EMA'yı
        if (prev_row['short_ema'] <= prev_row['long_ema'] and 
            current_row['short_ema'] > current_row['long_ema']):
            return "LONG"
        
        # Bearish crossover: Short EMA aşağı keser Long EMA'yı
        elif (prev_row['short_ema'] >= prev_row['long_ema'] and 
              current_row['short_ema'] < current_row['long_ema']):
            return "SHORT"
        
        return "HOLD"
    
    def _filter_signal(self, signal: str, df: pd.DataFrame, rsi: pd.Series, symbol: str) -> str:
        """Sinyal filtreleme ve doğrulama"""
        if signal == "HOLD":
            return "HOLD"
        
        current = df.iloc[-1]
        
        # 1. Minimum EMA fark kontrolü (çok küçük farklar yoksayılır)
        min_ema_diff_pct = 0.1  # %0.1 minimum fark
        if abs(current['ema_diff_pct']) < min_ema_diff_pct:
            print(f"📊 {symbol}: EMA farkı çok küçük ({current['ema_diff_pct']:.3f}%), sinyal yoksayıldı")
            return "HOLD"
        
        # 2. RSI aşırı alım/satım kontrolü
        current_rsi = rsi.iloc[-1] if len(rsi) > 0 else 50
        
        if signal == "LONG" and current_rsi > 75:
            print(f"📊 {symbol}: RSI aşırı alım bölgesinde ({current_rsi:.1f}), LONG sinyali yoksayıldı")
            return "HOLD"
        elif signal == "SHORT" and current_rsi < 25:
            print(f"📊 {symbol}: RSI aşırı satım bölgesinde ({current_rsi:.1f}), SHORT sinyali yoksayıldı")
            return "HOLD"
        
        # 3. Hacim kontrolü (son 5 mumun ortalama hacmine göre)
        avg_volume = df['volume'].rolling(window=5).mean().iloc[-1]
        current_volume = current['volume']
        
        if current_volume < avg_volume * 0.5:  # Hacim çok düşükse
            print(f"📊 {symbol}: Düşük hacim nedeniyle sinyal zayıf, yoksayıldı")
            return "HOLD"
        
        # 4. Trend gücü kontrolü
        trend_strength = abs(current['ema_diff_pct'])
        if trend_strength < 0.2:  # %0.2'den küçük trend gücü
            print(f"📊 {symbol}: Trend gücü zayıf ({trend_strength:.3f}%), sinyal yoksayıldı")
            return "HOLD"
        
        # Tüm filtrelerden geçtiyse sinyali onayla
        print(f"✅ {symbol}: {signal} sinyali onaylandı (RSI: {current_rsi:.1f}, Trend: {trend_strength:.3f}%)")
        return signal
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """RSI (Relative Strength Index) hesaplama"""
        try:
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return rsi.fillna(50)  # NaN değerleri 50 ile doldur
        except:
            return pd.Series([50] * len(prices))  # Hata durumunda nötr RSI döndür
    
    def _update_signal_history(self, symbol: str, signal: str):
        """Son sinyal geçmişini güncelle"""
        if symbol not in self.last_signals:
            self.last_signals[symbol] = []
        
        self.last_signals[symbol].append(signal)
        
        # Son 5 sinyali tut
        if len(self.last_signals[symbol]) > 5:
            self.last_signals[symbol].pop(0)
    
    def get_signal_confidence(self, symbol: str) -> float:
        """
        Sinyal güven derecesi (0.0 - 1.0)
        Aynı yönde art arda gelen sinyaller güven artırır
        """
        if symbol not in self.last_signals or len(self.last_signals[symbol]) < 2:
            return 0.5  # Nötr güven
        
        recent_signals = self.last_signals[symbol][-3:]  # Son 3 sinyal
        
        if len(set(recent_signals)) == 1:  # Hepsi aynı
            return 0.9  # Yüksek güven
        elif recent_signals[-1] == recent_signals[-2]:  # Son 2 aynı
            return 0.7  # Orta-yüksek güven
        else:
            return 0.3  # Düşük güven
    
    def should_reverse_position(self, symbol: str, current_position: str, new_signal: str) -> bool:
        """
        Pozisyon değişimi gerekli mi?
        - Güvenilirlik kontrolü
        - Gereksiz değişimleri önleme
        """
        if not current_position or current_position == new_signal:
            return False
        
        if new_signal == "HOLD":
            return False
        
        # Sinyal güven derecesini kontrol et
        confidence = self.get_signal_confidence(symbol)
        
        if confidence >= 0.6:  # Yeterli güvenilirlik
            print(f"🔄 {symbol}: Pozisyon değişimi onaylandı ({current_position} -> {new_signal}, Güven: {confidence:.2f})")
            return True
        else:
            print(f"⚠️ {symbol}: Düşük güven nedeniyle pozisyon değişimi reddedildi (Güven: {confidence:.2f})")
            return False

# Global strateji instance'ı
trading_strategy = TradingStrategy(short_ema_period=9, long_ema_period=21)
