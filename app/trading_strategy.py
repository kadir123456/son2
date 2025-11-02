# app/trading_strategy.py - KAR ODAKLI STRATEJI v2.0

import pandas as pd
import numpy as np
import warnings
from datetime import datetime, timedelta
from .config import settings

warnings.filterwarnings("ignore", message="Downcasting object dtype arrays")
pd.set_option('future.no_silent_downcasting', True)

class ProfitFocusedEMAStrategy:
    """
    💰 KAR ODAKLI EMA Cross Stratejisi v2.0
    - Gevşetilmiş filtreler (daha fazla sinyal)
    - Hızlı EMA 7/20
    - Minimal cooldown (1 dakika)
    - Whipsaw koruması hafif
    """
    
    def __init__(self):
        self.ema_fast = settings.EMA_FAST_PERIOD
        self.ema_slow = settings.EMA_SLOW_PERIOD
        
        # Signal tracking
        self.last_signal_time = {}
        self.signal_count = {}
        self.last_ema_values = {}
        self.signal_cooldown = {}
        
        # Performance tracking
        self.analysis_count = 0
        self.successful_signals = 0
        
        print(f"💰 KAR ODAKLI EMA CROSS v2.0:")
        print(f"   EMA Fast: {self.ema_fast}")
        print(f"   EMA Slow: {self.ema_slow}")
        print(f"   ⚡ GEVŞETİLMİŞ FİLTRELER - Daha fazla sinyal!")

    def analyze_klines(self, klines: list, symbol: str = "UNKNOWN") -> str:
        """💰 Kar odaklı EMA analizi - Gevşek filtreler"""
        self.analysis_count += 1
        
        if symbol not in self.signal_count:
            self.signal_count[symbol] = {"LONG": 0, "SHORT": 0, "HOLD": 0}
            
        # Minimum data kontrolü
        min_required = max(self.ema_slow + 3, 25)
        if not klines or len(klines) < min_required:
            return "HOLD"

        try:
            df = self._prepare_dataframe_fixed(klines)
            
            if df is None or len(df) < min_required:
                return "HOLD"
            
            # EMA hesapla
            df = self._calculate_emas_profit_focused(df, symbol)
            
            # Sinyal al - GEVŞETİLMİŞ
            signal = self._get_signal_profit_focused(df, symbol)
            
            if signal != "HOLD":
                self.last_signal_time[symbol] = datetime.now()
                self.successful_signals += 1
                
            self.signal_count[symbol][signal] += 1
            
            # Cache EMA değerleri
            if len(df) > 0:
                last_row = df.iloc[-1]
                self.last_ema_values[symbol] = {
                    'ema_fast': float(last_row.get('ema_fast', 0)),
                    'ema_slow': float(last_row.get('ema_slow', 0)),
                    'price': float(last_row.get('close', 0))
                }
            
            return signal
            
        except Exception as e:
            print(f"❌ {symbol} EMA analizi hatası: {e}")
            return "HOLD"

    def _prepare_dataframe_fixed(self, klines: list) -> pd.DataFrame:
        """DataFrame hazırlama"""
        try:
            if not klines or len(klines) == 0:
                return None
            
            klines_data = []
            for kline in klines:
                try:
                    close_price = float(kline[4])
                    volume = float(kline[5])
                    
                    if close_price <= 0 or np.isnan(close_price) or np.isinf(close_price):
                        continue
                        
                    klines_data.append({
                        'close': close_price,
                        'volume': volume if volume > 0 and not (np.isnan(volume) or np.isinf(volume)) else 1.0
                    })
                except (ValueError, IndexError, TypeError):
                    continue
                    
            if not klines_data or len(klines_data) < 10:
                return None
                
            df = pd.DataFrame(klines_data)
            df = df[df['close'] > 0].copy()
            df = df.dropna().copy()
            
            return df if len(df) >= 10 else None
            
        except Exception as e:
            print(f"❌ DataFrame hatası: {e}")
            return None

    def _calculate_emas_profit_focused(self, df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """💰 Kar odaklı EMA hesaplama"""
        try:
            # EMA hesapla
            df['ema_fast'] = df['close'].ewm(span=self.ema_fast, adjust=False).mean()
            df['ema_slow'] = df['close'].ewm(span=self.ema_slow, adjust=False).mean()
            
            # Element-wise temizleme
            def clean_series(series, fallback_series):
                cleaned = series.copy()
                for i in range(len(cleaned)):
                    val = cleaned.iloc[i]
                    if pd.isna(val) or np.isinf(val):
                        cleaned.iloc[i] = fallback_series.iloc[i]
                return cleaned
            
            df['ema_fast'] = clean_series(df['ema_fast'], df['close'])
            df['ema_slow'] = clean_series(df['ema_slow'], df['close'])
            
            # Boolean array - güvenli
            ema_fast_safe = pd.to_numeric(df['ema_fast'], errors='coerce').fillna(0)
            ema_slow_safe = pd.to_numeric(df['ema_slow'], errors='coerce').fillna(0)
            
            df['fast_above_slow'] = (ema_fast_safe > ema_slow_safe).astype(bool)
            df['prev_fast_above'] = df['fast_above_slow'].shift(1).fillna(False).astype(bool)
            
            # Cross detection
            current_above = df['fast_above_slow'].astype(bool)
            prev_above = df['prev_fast_above'].astype(bool)
            
            df['bullish_cross'] = (~prev_above) & current_above
            df['bearish_cross'] = prev_above & (~current_above)
            
            df['bullish_cross'] = df['bullish_cross'].fillna(False).astype(bool)
            df['bearish_cross'] = df['bearish_cross'].fillna(False).astype(bool)
            
            return df
            
        except Exception as e:
            print(f"❌ {symbol} EMA hesaplama hatası: {e}")
            # Fallback SMA
            try:
                df['ema_fast'] = df['close'].rolling(window=self.ema_fast, min_periods=1).mean()
                df['ema_slow'] = df['close'].rolling(window=self.ema_slow, min_periods=1).mean()
                df['ema_fast'] = df['ema_fast'].fillna(df['close'])
                df['ema_slow'] = df['ema_slow'].fillna(df['close'])
                df['fast_above_slow'] = (df['ema_fast'] > df['ema_slow']).astype(bool)
                df['prev_fast_above'] = df['fast_above_slow'].shift(1).fillna(False).astype(bool)
                df['bullish_cross'] = False
                df['bearish_cross'] = False
                return df
            except Exception as fallback_error:
                print(f"❌ {symbol} Fallback de başarısız: {fallback_error}")
                return df

    def _get_signal_profit_focused(self, df: pd.DataFrame, symbol: str) -> str:
        """💰 KAR ODAKLI sinyal mantığı - GEVŞETİLMİŞ"""
        try:
            if len(df) < 2:
                return "HOLD"
                
            current_row = df.iloc[-1]
            
            def safe_get_numeric(row, column, default=0.0):
                try:
                    value = row.get(column, default)
                    if pd.isna(value) or np.isinf(value):
                        return float(default)
                    return float(value)
                except (ValueError, TypeError):
                    return float(default)
            
            def safe_get_boolean(row, column, default=False):
                try:
                    value = row.get(column, default)
                    if pd.isna(value):
                        return default
                    return bool(value)
                except (ValueError, TypeError):
                    return default
            
            current_price = safe_get_numeric(current_row, 'close')
            ema_fast = safe_get_numeric(current_row, 'ema_fast')
            ema_slow = safe_get_numeric(current_row, 'ema_slow')
            bullish_cross = safe_get_boolean(current_row, 'bullish_cross')
            bearish_cross = safe_get_boolean(current_row, 'bearish_cross')
            
            if current_price <= 0 or ema_fast <= 0 or ema_slow <= 0:
                return "HOLD"
            
            # ⚡ MINIMAL COOLDOWN (settings'ten al)
            current_time = datetime.now()
            if symbol in self.signal_cooldown:
                last_signal_time = self.signal_cooldown[symbol]
                time_diff = (current_time - last_signal_time).total_seconds()
                cooldown_seconds = settings.SIGNAL_COOLDOWN_MINUTES * 60
                
                if time_diff < cooldown_seconds:
                    return "HOLD"
            
            # 🚀 BULLISH CROSS - GEVŞETİLMİŞ FİLTRE
            if bullish_cross:
                # Sadece temel kontrol
                ema_spread = abs(ema_fast - ema_slow) / ema_slow
                
                # ✅ settings'ten kontrol et, yoksa False
                if hasattr(settings, 'CONFIRM_PRICE_ABOVE_EMA') and settings.CONFIRM_PRICE_ABOVE_EMA:
                    price_check = current_price > ema_slow
                else:
                    price_check = True  # Fiyat kontrolü KAPALI
                
                # ✅ Minimal spread kontrolü
                min_spread = settings.MIN_EMA_SPREAD_PERCENT if hasattr(settings, 'MIN_EMA_SPREAD_PERCENT') else 0.0003
                spread_check = ema_spread > min_spread
                
                if price_check and spread_check:
                    self.signal_cooldown[symbol] = current_time
                    print(f"🚀 {symbol}: BULLISH CROSS! Fast({ema_fast:.6f}) > Slow({ema_slow:.6f}) → LONG")
                    return "LONG"
                elif settings.VERBOSE_LOGGING:
                    print(f"⚠️ {symbol}: Zayıf bullish (P:{price_check}, S:{spread_check})")
            
            # 📉 BEARISH CROSS - GEVŞETİLMİŞ FİLTRE
            if bearish_cross:
                ema_spread = abs(ema_fast - ema_slow) / ema_slow
                
                if hasattr(settings, 'CONFIRM_PRICE_ABOVE_EMA') and settings.CONFIRM_PRICE_ABOVE_EMA:
                    price_check = current_price < ema_slow
                else:
                    price_check = True
                
                min_spread = settings.MIN_EMA_SPREAD_PERCENT if hasattr(settings, 'MIN_EMA_SPREAD_PERCENT') else 0.0003
                spread_check = ema_spread > min_spread
                
                if price_check and spread_check:
                    self.signal_cooldown[symbol] = current_time
                    print(f"📉 {symbol}: BEARISH CROSS! Fast({ema_fast:.6f}) < Slow({ema_slow:.6f}) → SHORT")
                    return "SHORT"
                elif settings.VERBOSE_LOGGING:
                    print(f"⚠️ {symbol}: Zayıf bearish (P:{price_check}, S:{spread_check})")
            
            return "HOLD"
            
        except Exception as e:
            print(f"❌ {symbol} sinyal hatası: {e}")
            return "HOLD"

    def get_debug_info_optimized(self, klines: list, symbol: str) -> dict:
        """Debug bilgisi"""
        try:
            df = self._prepare_dataframe_fixed(klines)
            if df is None:
                return {"error": "DataFrame oluşturulamadı"}
            
            df = self._calculate_emas_profit_focused(df, symbol)
            
            if len(df) == 0:
                return {"error": "DataFrame boş"}
                
            last_row = df.iloc[-1]
            
            analysis_efficiency = 0
            if self.analysis_count > 0:
                analysis_efficiency = (self.successful_signals / self.analysis_count) * 100
            
            return {
                "symbol": symbol,
                "strategy_version": "profit_focused_v2.0",
                "total_candles": len(df),
                "current_price": float(last_row.get('close', 0)),
                "ema_fast": float(last_row.get('ema_fast', 0)),
                "ema_slow": float(last_row.get('ema_slow', 0)),
                "fast_above_slow": bool(last_row.get('fast_above_slow', False)),
                "bullish_cross": bool(last_row.get('bullish_cross', False)),
                "bearish_cross": bool(last_row.get('bearish_cross', False)),
                "has_cooldown": symbol in self.signal_cooldown,
                "performance": {
                    "analysis_count": self.analysis_count,
                    "successful_signals": self.successful_signals,
                    "efficiency": f"{analysis_efficiency:.1f}%"
                },
                "optimizations": [
                    "✅ Gevşetilmiş filtreler",
                    "✅ Minimal cooldown",
                    "✅ Whipsaw koruması hafif",
                    "✅ Daha fazla sinyal üretimi"
                ]
            }
        except Exception as e:
            return {"error": f"Debug hatası: {str(e)}"}

    def get_strategy_status_optimized(self, symbol: str) -> dict:
        """Strateji durumu"""
        total_signals = sum(self.signal_count.get(symbol, {}).values())
        
        return {
            "strategy_version": "2.0_profit_focused",
            "strategy_type": "relaxed_ema_cross_high_frequency",
            "symbol": symbol,
            "ema_fast": self.ema_fast,
            "ema_slow": self.ema_slow,
            "signal_count": self.signal_count.get(symbol, {}),
            "total_signals": total_signals,
            "last_signal_time": self.last_signal_time.get(symbol),
            "has_cooldown": symbol in self.signal_cooldown,
            "cached_ema_values": self.last_ema_values.get(symbol, {}),
            "global_performance": {
                "total_analysis": self.analysis_count,
                "successful_signals": self.successful_signals,
                "efficiency": f"{(self.successful_signals/max(self.analysis_count,1))*100:.1f}%"
            },
            "profit_optimizations": [
                "✅ GEVŞETİLMİŞ filtreler",
                "✅ 1 dakika cooldown (hızlı)",
                "✅ Minimal spread kontrolü",
                "✅ Opsiyonel fiyat kontrolü",
                "✅ Yüksek sinyal üretimi"
            ]
        }
    
    def clear_cache(self, symbol: str = None):
        """Cache temizleme"""
        if symbol:
            self.last_ema_values.pop(symbol, None)
            self.signal_cooldown.pop(symbol, None)
            print(f"🧹 {symbol} cache temizlendi")
        else:
            self.last_ema_values.clear()
            self.signal_cooldown.clear()
            print("🧹 Tüm cache temizlendi")

# Global instance
trading_strategy = ProfitFocusedEMAStrategy()
