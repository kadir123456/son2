# app/scalping_strategy.py - DAKİKALIK SCALPING STRATEJİSİ

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from .config import settings
from .gemini_analyzer import gemini_analyzer

class ScalpingStrategy:
    """
    ⚡ 1 Dakikalık Scalping Stratejisi
    
    ÖZELLİKLER:
    - 1m + 5m çoklu timeframe analizi
    - Gemini AI sinyal doğrulaması
    - Sıkı TP/SL (%0.3-0.5)
    - Yüksek volume gereksinimleri
    - Düşük spread kontrolü
    """
    
    def __init__(self):
        self.timeframe_1m = "1m"
        self.timeframe_5m = "5m"
        
        # Scalping parametreleri
        self.min_volume_ratio = 1.3      # Min %130 volume artışı
        self.min_volatility = 0.05       # Min %0.05 volatilite
        self.max_volatility = 0.5        # Max %0.5 volatilite
        self.min_confidence = 75         # Min %75 AI güven skoru
        
        # TP/SL oranları - daha sıkı
        self.default_tp_percent = 0.004  # %0.4 kar al
        self.default_sl_percent = 0.003  # %0.3 zarar durdur
        
        # Risk yönetimi
        self.max_daily_trades = 30       # Günlük max 30 işlem
        self.daily_trades_count = 0
        self.daily_reset_time = datetime.now().date()
        
        # Signal tracking
        self.last_signal_time = {}
        self.signal_cooldown = 120       # 2 dakika cooldown
        
        print("⚡ 1 Dakikalık Scalping Stratejisi aktif")
        print(f"   Min Volume Ratio: {self.min_volume_ratio}x")
        print(f"   TP: %{self.default_tp_percent*100:.2f}")
        print(f"   SL: %{self.default_sl_percent*100:.2f}")
        print(f"   Max Günlük İşlem: {self.max_daily_trades}")
    
    async def analyze_scalping_opportunity(
        self,
        symbol: str,
        current_price: float,
        klines_1m: List,
        klines_5m: List,
        binance_client
    ) -> Dict:
        """
        🎯 Dakikalık scalping fırsatı analizi
        
        Returns:
        {
            "signal": "LONG" | "SHORT" | "HOLD",
            "should_trade": bool,
            "confidence": float,
            "entry_price": float,
            "stop_loss": float,
            "take_profit": float,
            "reasoning": str,
            "ai_validated": bool
        }
        """
        
        # Günlük trade limiti kontrolü
        if not self._check_daily_limit():
            return self._hold_response("Günlük trade limiti aşıldı")
        
        # Cooldown kontrolü
        if not self._check_cooldown(symbol):
            return self._hold_response("Cooldown aktif")
        
        # Minimum veri kontrolü
        if len(klines_1m) < 20 or len(klines_5m) < 10:
            return self._hold_response("Yetersiz veri")
        
        try:
            # 1. Temel teknik analiz
            df_1m = self._prepare_dataframe(klines_1m)
            df_5m = self._prepare_dataframe(klines_5m)
            
            if df_1m is None or df_5m is None:
                return self._hold_response("DataFrame hazırlama hatası")
            
            # 2. Volume analizi
            volume_analysis = self._analyze_volume(df_1m)
            if not volume_analysis['is_valid']:
                return self._hold_response(f"Volume yetersiz: {volume_analysis['ratio']:.2f}x")
            
            # 3. Volatilite kontrolü
            volatility = self._calculate_volatility(df_1m)
            if volatility < self.min_volatility:
                return self._hold_response(f"Volatilite düşük: %{volatility*100:.3f}")
            if volatility > self.max_volatility:
                return self._hold_response(f"Volatilite çok yüksek: %{volatility*100:.3f}")
            
            # 4. Multi-timeframe trend analizi
            trend_1m = self._analyze_trend(df_1m)
            trend_5m = self._analyze_trend(df_5m)
            
            # Trendler uyumlu mu?
            if trend_1m['direction'] != trend_5m['direction']:
                return self._hold_response("Multi-timeframe trend uyumsuz")
            
            # 5. Basit sinyal
            basic_signal = trend_1m['direction']
            if basic_signal == 'HOLD':
                return self._hold_response("Trend belirsiz")
            
            # 6. Gemini AI doğrulaması
            ai_analysis = await gemini_analyzer.analyze_scalping_opportunity(
                symbol=symbol,
                current_price=current_price,
                klines_1m=klines_1m,
                klines_5m=klines_5m,
                ema_signal=basic_signal,
                volume_data=volume_analysis
            )
            
            # AI onayı gerekli
            if not ai_analysis['should_trade']:
                return self._hold_response(f"AI onaylamadı: {ai_analysis['reasoning']}")
            
            if ai_analysis['confidence'] < self.min_confidence:
                return self._hold_response(f"AI güven düşük: %{ai_analysis['confidence']:.0f}")
            
            # 7. TP/SL hesapla
            final_signal = ai_analysis['signal']
            tp_percent = ai_analysis.get('take_profit_percent', self.default_tp_percent) / 100
            sl_percent = ai_analysis.get('stop_loss_percent', self.default_sl_percent) / 100
            
            if final_signal == 'LONG':
                stop_loss = current_price * (1 - sl_percent)
                take_profit = current_price * (1 + tp_percent)
            else:  # SHORT
                stop_loss = current_price * (1 + sl_percent)
                take_profit = current_price * (1 - tp_percent)
            
            # 8. Risk/Reward kontrolü
            risk = abs(current_price - stop_loss)
            reward = abs(take_profit - current_price)
            rr_ratio = reward / risk if risk > 0 else 0
            
            if rr_ratio < 1.3:  # Min 1:1.3 R/R
                return self._hold_response(f"R/R düşük: {rr_ratio:.2f}")
            
            # ✅ TÜM KONTROLLERİ GEÇTİ
            self._update_signal_time(symbol)
            
            return {
                'signal': final_signal,
                'should_trade': True,
                'confidence': ai_analysis['confidence'],
                'entry_price': current_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'stop_loss_percent': sl_percent * 100,
                'take_profit_percent': tp_percent * 100,
                'risk_reward_ratio': rr_ratio,
                'reasoning': ai_analysis['reasoning'],
                'ai_validated': True,
                'ai_risk_score': ai_analysis['risk_score'],
                'volume_ratio': volume_analysis['ratio'],
                'volatility': volatility * 100,
                'trend_strength_1m': trend_1m['strength'],
                'trend_strength_5m': trend_5m['strength']
            }
            
        except Exception as e:
            print(f"❌ {symbol} scalping analiz hatası: {e}")
            return self._hold_response(f"Analiz hatası: {str(e)}")
    
    def _prepare_dataframe(self, klines: List) -> Optional[pd.DataFrame]:
        """Kline verilerini DataFrame'e çevir"""
        try:
            data = []
            for kline in klines:
                data.append({
                    'open': float(kline[1]),
                    'high': float(kline[2]),
                    'low': float(kline[3]),
                    'close': float(kline[4]),
                    'volume': float(kline[5])
                })
            
            df = pd.DataFrame(data)
            df = df[df['close'] > 0].copy()
            
            return df if len(df) >= 5 else None
            
        except Exception as e:
            print(f"❌ DataFrame hazırlama hatası: {e}")
            return None
    
    def _analyze_volume(self, df: pd.DataFrame) -> Dict:
        """Volume analizi"""
        try:
            if len(df) < 10:
                return {'is_valid': False, 'ratio': 0}
            
            # Son 10 mum ortalama volume
            avg_volume = df['volume'].tail(10).mean()
            
            # Son mum volume
            current_volume = df['volume'].iloc[-1]
            
            # Volume oranı
            ratio = current_volume / avg_volume if avg_volume > 0 else 0
            
            is_valid = ratio >= self.min_volume_ratio
            
            return {
                'is_valid': is_valid,
                'ratio': ratio,
                'current_volume': current_volume,
                'avg_volume': avg_volume
            }
            
        except Exception as e:
            print(f"❌ Volume analiz hatası: {e}")
            return {'is_valid': False, 'ratio': 0}
    
    def _calculate_volatility(self, df: pd.DataFrame) -> float:
        """Volatilite hesapla (ATR benzeri)"""
        try:
            if len(df) < 5:
                return 0
            
            # Son 10 mum için true range
            df['tr'] = df['high'] - df['low']
            
            # Ortalama true range
            atr = df['tr'].tail(10).mean()
            
            # Current price'a göre yüzde
            current_price = df['close'].iloc[-1]
            volatility_percent = (atr / current_price) if current_price > 0 else 0
            
            return volatility_percent
            
        except Exception as e:
            print(f"❌ Volatilite hesaplama hatası: {e}")
            return 0
    
    def _analyze_trend(self, df: pd.DataFrame) -> Dict:
        """Basit trend analizi"""
        try:
            if len(df) < 5:
                return {'direction': 'HOLD', 'strength': 0}
            
            # Son 5 mum
            recent = df.tail(5)
            
            # Fiyat değişimi
            price_change = (recent['close'].iloc[-1] - recent['close'].iloc[0]) / recent['close'].iloc[0]
            
            # Kaç mum aynı yönde?
            bullish_candles = sum(recent['close'] > recent['open'])
            bearish_candles = sum(recent['close'] < recent['open'])
            
            # Trend gücü
            strength = abs(price_change) * 100
            
            # Trend yönü
            if bullish_candles >= 4 and price_change > 0.001:  # %0.1+
                direction = 'LONG'
            elif bearish_candles >= 4 and price_change < -0.001:  # -%0.1+
                direction = 'SHORT'
            else:
                direction = 'HOLD'
            
            return {
                'direction': direction,
                'strength': strength,
                'bullish_candles': bullish_candles,
                'bearish_candles': bearish_candles,
                'price_change_percent': price_change * 100
            }
            
        except Exception as e:
            print(f"❌ Trend analiz hatası: {e}")
            return {'direction': 'HOLD', 'strength': 0}
    
    def _check_daily_limit(self) -> bool:
        """Günlük trade limiti kontrolü"""
        today = datetime.now().date()
        
        # Yeni gün başladıysa resetle
        if today != self.daily_reset_time:
            self.daily_trades_count = 0
            self.daily_reset_time = today
        
        return self.daily_trades_count < self.max_daily_trades
    
    def _check_cooldown(self, symbol: str) -> bool:
        """Sinyal cooldown kontrolü"""
        if symbol not in self.last_signal_time:
            return True
        
        elapsed = (datetime.now() - self.last_signal_time[symbol]).total_seconds()
        return elapsed >= self.signal_cooldown
    
    def _update_signal_time(self, symbol: str):
        """Sinyal zamanını güncelle"""
        self.last_signal_time[symbol] = datetime.now()
        self.daily_trades_count += 1
    
    def _hold_response(self, reason: str) -> Dict:
        """HOLD yanıtı"""
        return {
            'signal': 'HOLD',
            'should_trade': False,
            'confidence': 0,
            'entry_price': 0,
            'stop_loss': 0,
            'take_profit': 0,
            'reasoning': reason,
            'ai_validated': False
        }
    
    def get_status(self) -> Dict:
        """Strateji durumu"""
        return {
            'strategy_type': 'scalping_1m_ai',
            'timeframe_primary': self.timeframe_1m,
            'timeframe_secondary': self.timeframe_5m,
            'daily_trades': self.daily_trades_count,
            'daily_limit': self.max_daily_trades,
            'remaining_trades': self.max_daily_trades - self.daily_trades_count,
            'min_volume_ratio': self.min_volume_ratio,
            'min_confidence': self.min_confidence,
            'default_tp': f"{self.default_tp_percent*100:.2f}%",
            'default_sl': f"{self.default_sl_percent*100:.2f}%",
            'ai_enabled': gemini_analyzer.enabled,
            'cooldown_seconds': self.signal_cooldown
        }

# Global instance
scalping_strategy = ScalpingStrategy()
