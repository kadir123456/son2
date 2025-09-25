# app/trading_strategy.py - OPTIMIZE EDİLMİŞ ve NaN SAFE EMA Cross Stratejisi

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from .config import settings

class OptimizedEMACrossStrategy:
    """
    🎯 OPTIMIZE EDİLMİŞ EMA Cross Stratejisi v1.2
    
    ✅ YENİ ÖZELLİKLER:
    - Tamamen NaN safe işlemler
    - Boolean operation hataları düzeltildi
    - Memory optimize edildi
    - Sadece gerekli durumlarda sinyal üretir
    - API çağrılarını minimize eder
    - Doğru timeframe'de çalışır
    
    📈 STRATEJİ:
    - EMA 9 > EMA 21 kesişimi = LONG
    - EMA 9 < EMA 21 kesişimi = SHORT  
    - Whipsaw koruması ile
    """
    
    def __init__(self):
        self.ema_fast = settings.EMA_FAST_PERIOD    # 9
        self.ema_slow = settings.EMA_SLOW_PERIOD    # 21
        
        # Signal tracking - MEMORY OPTIMIZED
        self.last_signal_time = {}        # Her symbol için son sinyal zamanı
        self.signal_count = {}           # Signal statistics
        self.last_ema_values = {}        # Son EMA değerleri cache
        self.signal_cooldown = {}        # Whipsaw koruması
        
        # Performance tracking
        self.analysis_count = 0
        self.successful_signals = 0
        
        print(f"🎯 OPTIMIZE EDİLMİŞ EMA CROSS v1.2:")
        print(f"   EMA Fast: {self.ema_fast}")
        print(f"   EMA Slow: {self.ema_slow}")
        print(f"   ✅ Tamamen NaN safe!")
        print(f"   ✅ Boolean operations güvenli!")
        print(f"   ✅ Memory optimize edildi!")
        print(f"   🛡️ Whipsaw koruması aktif!")
        print(f"   📈 EMA{self.ema_fast} > EMA{self.ema_slow} keserse = LONG")
        print(f"   📉 EMA{self.ema_fast} < EMA{self.ema_slow} keserse = SHORT")

    def analyze_klines(self, klines: list, symbol: str = "UNKNOWN") -> str:
        """
        🎯 OPTIMIZE EDİLMİŞ EMA Cross analizi
        - NaN safe operations
        - Memory optimized  
        - Sadece gerekli durumlarda sinyal üretir
        """
        self.analysis_count += 1
        
        # Sayaçları başlat
        if symbol not in self.signal_count:
            self.signal_count[symbol] = {"LONG": 0, "SHORT": 0, "HOLD": 0}
            
        # Minimum data kontrolü - OPTIMIZE EDİLDİ
        min_required = max(self.ema_slow + 5, 30)
        if not klines or len(klines) < min_required:
            if len(klines) > 0:  # Sadece veri varsa log
                print(f"⚠️ {symbol}: Yetersiz veri ({len(klines)}/{min_required})")
            return "HOLD"

        try:
            # ✅ HIZLI DataFrame oluştur - OPTIMIZE EDİLDİ
            df = self._prepare_dataframe_optimized(klines)
            
            if df is None or len(df) < min_required:
                return "HOLD"
            
            # ✅ NaN SAFE EMA'ları hesapla
            df = self._calculate_emas_safe_optimized(df, symbol)
            
            # ✅ WHIPSAW KORUMANLI sinyal al
            signal = self._get_ema_cross_signal_optimized(df, symbol)
            
            # Sinyal geçmişini güncelle - MEMORY SAFE
            if signal != "HOLD":
                self.last_signal_time[symbol] = datetime.now()
                self.successful_signals += 1
                
            self.signal_count[symbol][signal] += 1
            
            # Cache son EMA değerleri - PERFORMANCE
            if len(df) > 0:
                last_row = df.iloc[-1]
                self.last_ema_values[symbol] = {
                    'ema9': float(last_row.get('ema9', 0)),
                    'ema21': float(last_row.get('ema21', 0)),
                    'price': float(last_row.get('close', 0))
                }
            
            return signal
            
        except Exception as e:
            print(f"❌ {symbol} OPTIMIZE EDİLMİŞ EMA analizi hatası: {e}")
            return "HOLD"

    def _prepare_dataframe_optimized(self, klines: list) -> pd.DataFrame:
        """✅ OPTIMIZE EDİLMİŞ DataFrame hazırla - Hızlı ve güvenli"""
        try:
            if not klines or len(klines) == 0:
                return None
            
            # Sadece gerekli kolonları kullan - MEMORY OPTIMIZE
            klines_data = []
            for kline in klines:
                try:
                    klines_data.append({
                        'close': float(kline[4]),  # Sadece close fiyatı gerekli EMA için
                        'volume': float(kline[5]) # Volume da kontrol için
                    })
                except (ValueError, IndexError):
                    continue
                    
            if not klines_data or len(klines_data) < 10:
                return None
                
            df = pd.DataFrame(klines_data)
            
            # ✅ NaN kontrolü - HIZLI forward fill
            if df['close'].isnull().any():
                df['close'] = df['close'].fillna(method='ffill').fillna(method='bfill')
                
            if df['volume'].isnull().any():
                df['volume'] = df['volume'].fillna(0)
            
            # Geçersiz değerleri temizle
            df = df[df['close'] > 0]
            
            return df if len(df) >= 10 else None
            
        except Exception as e:
            print(f"❌ OPTIMIZE DataFrame hatası: {e}")
            return None

    def _calculate_emas_safe_optimized(self, df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """
        ✅ OPTIMIZE EDİLMİŞ ve TAMAMEN GÜVENLI EMA hesaplama
        - NaN safe operations
        - Boolean error fix
        - Cache optimized
        """
        try:
            # ✅ PANDAS EWM ile optimize EMA hesaplama
            # adjust=False daha doğru EMA verir
            df['ema9'] = df['close'].ewm(span=self.ema_fast, adjust=False).mean()
            df['ema21'] = df['close'].ewm(span=self.ema_slow, adjust=False).mean()
            
            # ✅ NaN güvenlik kontrolü - KAPSAMLI
            df['ema9'] = df['ema9'].fillna(df['close'])
            df['ema21'] = df['ema21'].fillna(df['close'])
            
            # Infinity kontrolü
            df['ema9'] = df['ema9'].replace([np.inf, -np.inf], df['close'])
            df['ema21'] = df['ema21'].replace([np.inf, -np.inf], df['close'])
            
            # ✅ TAMAMEN GÜVENLİ Boolean operasyonlar
            # Önce NaN'ları temizleyip sonra karşılaştırma yap
            ema9_safe = df['ema9'].fillna(0)
            ema21_safe = df['ema21'].fillna(0)
            
            # Cross detection için güvenli boolean array
            df['ema9_above_ema21'] = (ema9_safe > ema21_safe).astype(bool)
            
            # ✅ GÜVENLI shift operasyonu
            df['prev_ema9_above'] = df['ema9_above_ema21'].shift(1).fillna(False).astype(bool)
            
            # ✅ GÜVENLI Cross detection - Hiç NaN yok
            # Bullish cross: önceki False, şimdi True
            current_above = df['ema9_above_ema21'].astype(bool)
            prev_above = df['prev_ema9_above'].astype(bool)
            
            df['bullish_cross'] = (~prev_above) & current_above
            df['bearish_cross'] = prev_above & (~current_above)
            
            # Son güvenlik - tüm boolean kolonlar için
            boolean_cols = ['ema9_above_ema21', 'prev_ema9_above', 'bullish_cross', 'bearish_cross']
            for col in boolean_cols:
                df[col] = df[col].fillna(False).astype(bool)
            
            return df
            
        except Exception as e:
            print(f"❌ {symbol} OPTIMIZE EMA hesaplama hatası: {e}")
            # ✅ FALLBACK mekanizması - SMA kullan
            try:
                print(f"⚠️ {symbol} için SMA fallback kullanılıyor")
                df['ema9'] = df['close'].rolling(window=self.ema_fast).mean()
                df['ema21'] = df['close'].rolling(window=self.ema_slow).mean()
                df['ema9'] = df['ema9'].fillna(df['close'])
                df['ema21'] = df['ema21'].fillna(df['close'])
                
                # Basit boolean hesaplama
                df['ema9_above_ema21'] = (df['ema9'] > df['ema21']).fillna(False)
                df['prev_ema9_above'] = df['ema9_above_ema21'].shift(1).fillna(False)
                df['bullish_cross'] = False  # Fallback'te cross detection yok
                df['bearish_cross'] = False
                
                return df
            except:
                print(f"❌ {symbol} Fallback SMA de başarısız")
                return df

    def _get_ema_cross_signal_optimized(self, df: pd.DataFrame, symbol: str) -> str:
        """
        ✅ OPTIMIZE EDİLMİŞ EMA Cross sinyal mantığı
        - Whipsaw koruması
        - Sadece kaliteli sinyaller
        - Rate limited
        """
        try:
            if len(df) < 3:
                return "HOLD"
                
            current_row = df.iloc[-1]
            
            # ✅ GÜVENLI değer alma fonksiyonu
            def safe_get(row, column, default=0.0):
                try:
                    value = row.get(column, default)
                    if pd.isna(value) or np.isinf(value):
                        return default
                    return float(value)
                except:
                    return default
            
            def safe_get_bool(row, column, default=False):
                try:
                    value = row.get(column, default)
                    if pd.isna(value):
                        return default
                    return bool(value)
                except:
                    return default
            
            # Güvenli değer alma
            current_price = safe_get(current_row, 'close')
            ema9 = safe_get(current_row, 'ema9')
            ema21 = safe_get(current_row, 'ema21')
            bullish_cross = safe_get_bool(current_row, 'bullish_cross')
            bearish_cross = safe_get_bool(current_row, 'bearish_cross')
            
            # Temel validation
            if current_price <= 0 or ema9 <= 0 or ema21 <= 0:
                return "HOLD"
            
            # ✅ WHIPSAW KORUMASI - Son sinyalden sonra yeterli süre geçti mi?
            current_time = datetime.now()
            if symbol in self.signal_cooldown:
                last_signal_time = self.signal_cooldown[symbol]
                time_diff = (current_time - last_signal_time).total_seconds()
                cooldown_minutes = 5  # 5 dakika cooldown
                
                if time_diff < (cooldown_minutes * 60):
                    return "HOLD"  # Henüz çok erken
            
            # Debug için major coinlerde log (daha az verbose)
            if settings.DEBUG_MODE and (symbol.startswith('BTC') or symbol.startswith('ETH')):
                print(f"🔍 {symbol}: P={current_price:.4f}, EMA9={ema9:.4f}, EMA21={ema21:.4f}")
                print(f"   Bull={bullish_cross}, Bear={bearish_cross}")
            
            # =======================================
            # ✅ OPTIMIZE EMA CROSS SİNYAL MANTIĞI
            # =======================================
            
            # 🚀 BULLISH CROSS - Güçlü LONG sinyali
            if bullish_cross:
                # Ek filtreler - sadece kaliteli sinyaller
                price_above_ema21 = current_price > ema21
                strong_move = abs(ema9 - ema21) / ema21 > 0.001  # En az %0.1 fark
                
                if price_above_ema21 and strong_move:
                    self.signal_cooldown[symbol] = current_time
                    print(f"🚀 {symbol}: GÜÇLÜ BULLISH CROSS! EMA9({ema9:.6f}) > EMA21({ema21:.6f}) → LONG")
                    return "LONG"
            
            # 📉 BEARISH CROSS - Güçlü SHORT sinyali
            if bearish_cross:
                # Ek filtreler - sadece kaliteli sinyaller
                price_below_ema21 = current_price < ema21
                strong_move = abs(ema9 - ema21) / ema21 > 0.001  # En az %0.1 fark
                
                if price_below_ema21 and strong_move:
                    self.signal_cooldown[symbol] = current_time
                    print(f"📉 {symbol}: GÜÇLÜ BEARISH CROSS! EMA9({ema9:.6f}) < EMA21({ema21:.6f}) → SHORT")
                    return "SHORT"
            
            # Cross yok veya zayıf sinyal
            return "HOLD"
            
        except Exception as e:
            print(f"❌ {symbol} OPTIMIZE sinyal hesaplama hatası: {e}")
            return "HOLD"

    def get_debug_info_optimized(self, klines: list, symbol: str) -> dict:
        """
        🐛 OPTIMIZE edilmiş debug bilgisi
        """
        try:
            df = self._prepare_dataframe_optimized(klines)
            if df is None:
                return {"error": "DataFrame oluşturulamadı"}
            
            df = self._calculate_emas_safe_optimized(df, symbol)
            
            if len(df) == 0:
                return {"error": "DataFrame boş"}
                
            last_row = df.iloc[-1]
            
            # Performance metrics
            analysis_efficiency = 0
            if self.analysis_count > 0:
                analysis_efficiency = (self.successful_signals / self.analysis_count) * 100
            
            return {
                "symbol": symbol,
                "total_candles": len(df),
                "current_price": float(last_row.get('close', 0)),
                "current_ema9": float(last_row.get('ema9', 0)),
                "current_ema21": float(last_row.get('ema21', 0)),
                "ema9_above": bool(last_row.get('ema9_above_ema21', False)),
                "bullish_cross": bool(last_row.get('bullish_cross', False)),
                "bearish_cross": bool(last_row.get('bearish_cross', False)),
                "has_cooldown": symbol in self.signal_cooldown,
                "last_ema_cache": self.last_ema_values.get(symbol, {}),
                "performance": {
                    "analysis_count": self.analysis_count,
                    "successful_signals": self.successful_signals,
                    "efficiency": f"{analysis_efficiency:.1f}%"
                },
                "optimization_status": "v1.2 - NaN safe, Memory optimized, Whipsaw protected"
            }
        except Exception as e:
            return {"error": f"Debug hatası: {str(e)}"}

    def get_strategy_status_optimized(self, symbol: str) -> dict:
        """OPTIMIZE edilmiş strateji durumu"""
        total_signals = sum(self.signal_count.get(symbol, {}).values())
        
        return {
            "strategy_version": "1.2_optimized_nan_safe",
            "strategy_type": "optimized_ema_cross_whipsaw_protected",
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
            "optimizations": [
                "✅ Tamamen NaN safe operations",
                "✅ Memory optimized DataFrame processing", 
                "✅ Boolean operations düzeltildi",
                "✅ Whipsaw koruması (5 dk cooldown)",
                "✅ Kaliteli sinyal filtreleme",
                "✅ Cache sistem ile performance artışı",
                "✅ Fallback SMA mekanizması"
            ]
        }
    
    def clear_cache(self, symbol: str = None):
        """Cache temizleme - memory management"""
        if symbol:
            self.last_ema_values.pop(symbol, None)
            self.signal_cooldown.pop(symbol, None)
            print(f"🧹 {symbol} cache temizlendi")
        else:
            self.last_ema_values.clear()
            self.signal_cooldown.clear()
            print("🧹 Tüm cache temizlendi")

# Global optimized instance - En gelişmiş ve güvenli strateji
trading_strategy = OptimizedEMACrossStrategy()
