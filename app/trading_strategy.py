import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from .config import settings

class SimpleEMACrossStrategy:
    """
    🎯 BASİT EMA Cross Stratejisi - SORUN DÜZELTİLDİ
    - EMA 9 > EMA 21 OLURSA = LONG
    - EMA 9 < EMA 21 OLURSA = SHORT  
    - NaN handling ve Boolean operation sorunları düzeltildi!
    """
    
    def __init__(self):
        self.ema_fast = settings.EMA_FAST_PERIOD    # 9
        self.ema_slow = settings.EMA_SLOW_PERIOD    # 21
        
        # Signal tracking
        self.last_signal_time = {}     # Her symbol için son sinyal zamanı
        self.signal_count = {}         # Signal statistics
        
        print(f"🎯 DÜZELTİLMİŞ EMA CROSS Stratejisi:")
        print(f"   EMA Fast: {self.ema_fast}")
        print(f"   EMA Slow: {self.ema_slow}")
        print(f"   ✅ NaN handling düzeltildi!")
        print(f"   ✅ Boolean operations güvenli!")
        print(f"   📈 EMA9 > EMA21 keserse = LONG")
        print(f"   📉 EMA9 < EMA21 keserse = SHORT")

    def analyze_klines(self, klines: list, symbol: str = "UNKNOWN") -> str:
        """
        🎯 DÜZELTİLMİŞ EMA Cross analizi - NaN safe
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
            
            # EMA'ları hesapla - NaN safe
            df = self._calculate_emas_safe(df)
            
            # ✅ DÜZELTİLMİŞ EMA Cross sinyalini al
            signal = self._get_ema_cross_signal_safe(df, symbol)
            
            # Sinyal geçmişini güncelle
            if signal != "HOLD":
                self.last_signal_time[symbol] = datetime.now()
                
            self.signal_count[symbol][signal] += 1
            
            return signal
            
        except Exception as e:
            print(f"❌ {symbol} EMA analizi hatası: {e}")
            print(f"❌ Hata detayı: {type(e).__name__}")
            return "HOLD"

    def _prepare_dataframe(self, klines: list) -> pd.DataFrame:
        """DataFrame hazırla - güvenli"""
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
                
            # NaN kontrolü - forward fill ile doldur
            if df[numeric_columns].isnull().any().any():
                df[numeric_columns] = df[numeric_columns].fillna(method='ffill')
                
            # Hala NaN varsa backward fill
            if df[numeric_columns].isnull().any().any():
                df[numeric_columns] = df[numeric_columns].fillna(method='bfill')
            
            return df if not df.empty and len(df) >= 10 else None
            
        except Exception as e:
            print(f"❌ DataFrame hazırlama hatası: {e}")
            return None

    def _calculate_emas_safe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        ✅ DÜZELTİLMİŞ EMA hesaplama - NaN safe Boolean operations
        """
        try:
            # ✅ DOĞRU EMA Hesaplama
            df['ema9'] = df['close'].ewm(span=self.ema_fast, adjust=False).mean()
            df['ema21'] = df['close'].ewm(span=self.ema_slow, adjust=False).mean()
            
            # NaN kontrolü - EMA değerlerini kontrol et
            df['ema9'] = df['ema9'].fillna(df['close'])
            df['ema21'] = df['ema21'].fillna(df['close'])
            
            # ✅ GÜVENLI Boolean operasyonlar
            # fillna ile NaN değerleri False yapıyoruz
            df['ema9_above_ema21'] = (df['ema9'] > df['ema21']).fillna(False)
            
            # ✅ GÜVENLI shift operasyonu
            df['prev_ema9_above'] = df['ema9_above_ema21'].shift(1).fillna(False)
            
            # ✅ GÜVENLI Cross detection - NaN'lar False olarak işleniyor
            # Bullish cross: Önceki mum False, şimdiki True
            df['bullish_cross'] = (~df['prev_ema9_above']) & df['ema9_above_ema21']
            
            # Bearish cross: Önceki mum True, şimdiki False  
            df['bearish_cross'] = df['prev_ema9_above'] & (~df['ema9_above_ema21'])
            
            # Güvenlik için NaN'ları False yap
            df['bullish_cross'] = df['bullish_cross'].fillna(False)
            df['bearish_cross'] = df['bearish_cross'].fillna(False)
            
            return df
            
        except Exception as e:
            print(f"❌ EMA hesaplama hatası (DÜZELTİLDİ): {e}")
            # Hata durumunda temel hesaplama yap
            try:
                df['ema9'] = df['close'].rolling(window=self.ema_fast).mean()
                df['ema21'] = df['close'].rolling(window=self.ema_slow).mean()
                df['ema9_above_ema21'] = (df['ema9'] > df['ema21']).fillna(False)
                df['prev_ema9_above'] = df['ema9_above_ema21'].shift(1).fillna(False)
                df['bullish_cross'] = False
                df['bearish_cross'] = False
                print(f"⚠️ Fallback EMA hesaplama kullanıldı")
                return df
            except:
                print(f"❌ Fallback EMA de başarısız")
                return df

    def _get_ema_cross_signal_safe(self, df: pd.DataFrame, symbol: str) -> str:
        """
        ✅ DÜZELTİLMİŞ EMA Cross sinyal mantığı - tamamen güvenli
        """
        try:
            if len(df) < 3:
                return "HOLD"
                
            current_row = df.iloc[-1]
            prev_row = df.iloc[-2] if len(df) > 1 else current_row
            
            # NaN kontrolü - güvenli erişim
            def safe_get(row, column, default=0.0):
                try:
                    value = row.get(column, default)
                    return value if pd.notna(value) else default
                except:
                    return default
            
            def safe_get_bool(row, column, default=False):
                try:
                    value = row.get(column, default)
                    return bool(value) if pd.notna(value) else default
                except:
                    return default
            
            # Güvenli değer alma
            current_price = safe_get(current_row, 'close')
            ema9 = safe_get(current_row, 'ema9')
            ema21 = safe_get(current_row, 'ema21')
            ema9_above = safe_get_bool(current_row, 'ema9_above_ema21')
            bullish_cross = safe_get_bool(current_row, 'bullish_cross')
            bearish_cross = safe_get_bool(current_row, 'bearish_cross')
            
            # Temel validation
            if current_price <= 0 or ema9 <= 0 or ema21 <= 0:
                print(f"⚠️ {symbol}: Geçersiz fiyat değerleri")
                return "HOLD"
            
            # Debug bilgisi - daha az verbose
            if symbol.endswith('BTC') or symbol.endswith('ETH'):  # Sadece major coinler için log
                print(f"🔍 {symbol} EMA: Fiyat={current_price:.4f}, EMA9={ema9:.4f}, EMA21={ema21:.4f}")
                print(f"   EMA9>EMA21: {ema9_above}, Bull: {bullish_cross}, Bear: {bearish_cross}")
            
            # ===========================================
            # ✅ DÜZELTİLMİŞ EMA CROSS SİNYAL MANTIĞI
            # ===========================================
            
            # 🚀 BULLISH CROSS - EMA9 EMA21'i yukarı kestiği an
            if bullish_cross:
                print(f"🚀 {symbol}: BULLISH CROSS! EMA9 yukarı kesti EMA21'i → LONG")
                return "LONG"
            
            # 📉 BEARISH CROSS - EMA9 EMA21'i aşağı kestiği an  
            if bearish_cross:
                print(f"📉 {symbol}: BEARISH CROSS! EMA9 aşağı kesti EMA21'i → SHORT")
                return "SHORT"
            
            # Cross yok, HOLD
            return "HOLD"
            
        except Exception as e:
            print(f"❌ {symbol} sinyal hesaplama hatası (GÜVENLI): {e}")
            return "HOLD"

    def get_debug_info(self, klines: list, symbol: str) -> dict:
        """
        🐛 Debug için detaylı EMA bilgisi - güvenli
        """
        try:
            df = self._prepare_dataframe(klines)
            if df is None:
                return {"error": "DataFrame oluşturulamadı"}
            
            df = self._calculate_emas_safe(df)
            
            # Güvenli erişim
            if len(df) == 0:
                return {"error": "DataFrame boş"}
                
            last_row = df.iloc[-1]
            
            # Son 3 mumun detayları (daha az memory kullanımı)
            last_3 = df.tail(3)[['close', 'ema9', 'ema21', 'ema9_above_ema21', 'bullish_cross', 'bearish_cross']]
            
            return {
                "symbol": symbol,
                "total_candles": len(df),
                "current_price": float(last_row.get('close', 0)),
                "current_ema9": float(last_row.get('ema9', 0)),
                "current_ema21": float(last_row.get('ema21', 0)),
                "ema9_above": bool(last_row.get('ema9_above_ema21', False)),
                "bullish_cross": bool(last_row.get('bullish_cross', False)),
                "bearish_cross": bool(last_row.get('bearish_cross', False)),
                "last_3_candles": last_3.to_dict('records'),
                "fix_status": "NaN handling ve Boolean operations düzeltildi"
            }
        except Exception as e:
            return {"error": f"Debug hatası: {str(e)}"}

    def get_strategy_status(self, symbol: str) -> dict:
        """Strateji durumunu döndür"""
        return {
            "strategy_version": "1.2_fixed_nan_handling",
            "strategy_type": "safe_ema_cross",
            "symbol": symbol,
            "ema_fast": self.ema_fast,
            "ema_slow": self.ema_slow,
            "signal_count": self.signal_count.get(symbol, {}),
            "last_signal_time": self.last_signal_time.get(symbol),
            "description": "GÜVENLİ: NaN handling ve Boolean ops düzeltildi",
            "fix_notes": [
                "✅ NaN değerler güvenli şekilde handle ediliyor",
                "✅ Boolean operasyonlar fillna ile korunuyor", 
                "✅ ~ operatörü hataları düzeltildi",
                "✅ Cross detection tamamen güvenli",
                "✅ Fallback mekanizması eklendi"
            ]
        }

# Global instance - Düzeltilmiş güvenli strateji
trading_strategy = SimpleEMACrossStrategy()
