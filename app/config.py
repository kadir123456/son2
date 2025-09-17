import os
from dotenv import load_dotenv
from typing import Dict, Tuple, Any

load_dotenv()

class Settings:
    # --- Temel Ayarlar ---
    API_KEY: str = os.getenv("BINANCE_API_KEY")
    API_SECRET: str = os.getenv("BINANCE_API_SECRET")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "LIVE")
    BOT_USERNAME: str = os.getenv("BOT_USERNAME", "admin")
    BOT_PASSWORD: str = os.getenv("BOT_PASSWORD", "changeme123")
    BASE_URL = "https://fapi.binance.com" if os.getenv("ENVIRONMENT", "TEST") == "LIVE" else "https://testnet.binancefuture.com"
    WEBSOCKET_URL = "wss://fstream.binance.com" if os.getenv("ENVIRONMENT", "TEST") == "LIVE" else "wss://stream.binancefuture.com"

    # --- İşlem Parametreleri ---
    LEVERAGE: int = 20
    ORDER_SIZE_USDT: float = 35.0
    TIMEFRAME: str = "15m"
    
    # --- 🔧 DEBUG AYARLARI - FİLTRELER DEVRE DIŞI ---
    
    # DEBUG: Filtrelerin çoğunu kapat
    TREND_FILTER_ENABLED: bool = False          # KAPALI
    MOMENTUM_FILTER_ENABLED: bool = False       # KAPALI
    TREND_STRENGTH_FILTER_ENABLED: bool = False # KAPALI
    PRICE_ACTION_FILTER_ENABLED: bool = False   # KAPALI
    MIN_PRICE_MOVEMENT_ENABLED: bool = False    # KAPALI
    
    # Kritik filtreleri de gevşet
    RSI_FILTER_ENABLED: bool = False            # KAPALI (debug için)
    RSI_PERIOD: int = 14
    RSI_OVERSOLD: float = 15.0      # Çok gevşek
    RSI_OVERBOUGHT: float = 85.0    # Çok gevşek
    
    SIGNAL_COOLDOWN_ENABLED: bool = True        # Sadece bu açık (çok kısa)
    
    VOLATILITY_FILTER_ENABLED: bool = False     # KAPALI
    ATR_PERIOD: int = 14
    
    VOLUME_FILTER_ENABLED: bool = False         # KAPALI
    VOLUME_MA_PERIOD: int = 20
    MIN_VOLUME_MULTIPLIER: float = 1.0          # Çok düşük
    
    # --- DEBUG: ZAMAN DİLİMİ AYARLARI - ÇOK GEVŞETİLDİ ---
    TIMEFRAME_SETTINGS: Dict[str, Dict[str, float]] = {
        "1m": {
            "stop_loss_percent": 0.0015,
            "take_profit_percent": 0.0025,
            "min_price_movement": 0.0001,       # Çok düşük
            "signal_strength": 0.00001,         # Çok düşük
            "cooldown_minutes": 1,              # 1 dakika
            "atr_multiplier": 0.5               # Çok düşük
        },
        "3m": {
            "stop_loss_percent": 0.002,
            "take_profit_percent": 0.004,
            "min_price_movement": 0.0001,
            "signal_strength": 0.00001,
            "cooldown_minutes": 2,              # 2 dakika
            "atr_multiplier": 0.5
        },
        "5m": {
            "stop_loss_percent": 0.003,
            "take_profit_percent": 0.005,
            "min_price_movement": 0.0001,
            "signal_strength": 0.00001,
            "cooldown_minutes": 2,              # 2 dakika
            "atr_multiplier": 0.5
        },
        "15m": {
            "stop_loss_percent": 0.004,
            "take_profit_percent": 0.006,
            "min_price_movement": 0.0001,       # Çok düşük
            "signal_strength": 0.00001,         # Çok düşük
            "cooldown_minutes": 2,              # 2 dakika (15 yerine)
            "atr_multiplier": 0.5               # Çok düşük
        },
        "30m": {
            "stop_loss_percent": 0.006,
            "take_profit_percent": 0.009,
            "min_price_movement": 0.0001,
            "signal_strength": 0.00001,
            "cooldown_minutes": 5,              # 5 dakika
            "atr_multiplier": 0.5
        },
        "1h": {
            "stop_loss_percent": 0.008,
            "take_profit_percent": 0.012,
            "min_price_movement": 0.0001,
            "signal_strength": 0.00001,
            "cooldown_minutes": 5,              # 5 dakika
            "atr_multiplier": 0.5
        }
    }
    
    # Aktif zaman dilimi ayarlarını al
    @classmethod
    def get_current_settings(cls) -> Dict[str, float]:
        return cls.TIMEFRAME_SETTINGS.get(cls.TIMEFRAME, cls.TIMEFRAME_SETTINGS["15m"])
    
    # Dinamik özellikler
    @property
    def STOP_LOSS_PERCENT(self) -> float:
        return self.get_current_settings()["stop_loss_percent"]
    
    @property  
    def TAKE_PROFIT_PERCENT(self) -> float:
        return self.get_current_settings()["take_profit_percent"]
    
    @property
    def MIN_PRICE_MOVEMENT_PERCENT(self) -> float:
        return self.get_current_settings()["min_price_movement"]
    
    @property
    def SIGNAL_STRENGTH_THRESHOLD(self) -> float:
        return self.get_current_settings()["signal_strength"]
    
    @property
    def SIGNAL_COOLDOWN_MINUTES(self) -> int:
        return int(self.get_current_settings()["cooldown_minutes"])
    
    @property
    def MIN_ATR_MULTIPLIER(self) -> float:
        return self.get_current_settings()["atr_multiplier"]
    
    # --- DEBUG: TREND FİLTRESİ AYARLARI ---
    TREND_EMA_PERIODS: Dict[str, int] = {
        "1m": 20,
        "3m": 30,
        "5m": 40,
        "15m": 50,
        "30m": 60,
        "1h": 80
    }
    
    @property
    def TREND_EMA_PERIOD(self) -> int:
        return self.TREND_EMA_PERIODS.get(self.TIMEFRAME, 50)
    
    # --- DEBUG: RİSK YÖNETİMİ - ÇOK GEVŞEK ---
    MAX_DAILY_POSITIONS: int = 100              # Çok yüksek (8 yerine)
    MAX_DAILY_LOSS_PERCENT: float = 0.5         # %50 (çok yüksek)
    MIN_RISK_REWARD_RATIO: float = 1.0          # Çok düşük (1.3 yerine)
    MAX_CONSECUTIVE_LOSSES: int = 50             # Çok yüksek (3 yerine)
    
    # --- Rate Limiting ve Performance Ayarları ---
    MAX_REQUESTS_PER_MINUTE: int = 1200
    CACHE_DURATION_BALANCE: int = 10
    CACHE_DURATION_POSITION: int = 5
    CACHE_DURATION_PNL: int = 3
    
    # --- WebSocket Ayarları ---
    WEBSOCKET_PING_INTERVAL: int = 30
    WEBSOCKET_PING_TIMEOUT: int = 15
    WEBSOCKET_CLOSE_TIMEOUT: int = 10
    WEBSOCKET_MAX_RECONNECTS: int = 10
    
    # --- Status Update Intervals ---
    STATUS_UPDATE_INTERVAL: int = 10
    BALANCE_UPDATE_INTERVAL: int = 30

    @classmethod
    def set_timeframe(cls, timeframe: str):
        """Zaman dilimini değiştir"""
        if timeframe in cls.TIMEFRAME_SETTINGS:
            cls.TIMEFRAME = timeframe
            print(f"🕐 DEBUG: Zaman dilimi {timeframe} olarak ayarlandı")
            print(f"📊 DEBUG SL/TP: %{cls().STOP_LOSS_PERCENT*100:.2f}/%{cls().TAKE_PROFIT_PERCENT*100:.2f}")
            return True
        else:
            print(f"❌ DEBUG: Geçersiz zaman dilimi: {timeframe}")
            return False
    
    @classmethod
    def get_risk_reward_ratio(cls) -> float:
        """Risk/reward hesapla"""
        current = cls.get_current_settings()
        return current["take_profit_percent"] / current["stop_loss_percent"]
    
    @classmethod
    def validate_settings(cls):
        """DEBUG: Basit doğrulama"""
        warnings = []
        
        if not cls.API_KEY or not cls.API_SECRET:
            warnings.append("⚠️ DEBUG: API anahtarları eksik!")
        
        print(f"🔧 DEBUG: {len(warnings)} uyarı bulundu")
        return len(warnings) == 0

    @classmethod
    def print_settings(cls):
        """DEBUG ayarlarını yazdır"""
        current = cls.get_current_settings()
        risk_reward = cls.get_risk_reward_ratio()
        
        print("=" * 70)
        print("🔧 DEBUG MOD - SİNYAL ÜRETİM TESTİ")
        print("=" * 70)
        print(f"🌐 Ortam: {cls.ENVIRONMENT}")
        print(f"💰 İşlem Miktarı: {cls.ORDER_SIZE_USDT} USDT")
        print(f"📈 Kaldıraç: {cls.LEVERAGE}x")
        print(f"⏰ Zaman Dilimi: {cls.TIMEFRAME}")
        print("=" * 70)
        print("🔧 DEBUG FİLTRE DURUMU:")
        print(f"   📊 Trend Filtresi: {'❌ KAPALI' if not cls.TREND_FILTER_ENABLED else '✅ AÇIK'}")
        print(f"   ⚡ Momentum Filtresi: {'❌ KAPALI' if not cls.MOMENTUM_FILTER_ENABLED else '✅ AÇIK'}")
        print(f"   💪 Trend Gücü: {'❌ KAPALI' if not cls.TREND_STRENGTH_FILTER_ENABLED else '✅ AÇIK'}")
        print(f"   🔄 RSI Filtresi: {'❌ KAPALI' if not cls.RSI_FILTER_ENABLED else '✅ AÇIK'}")
        print(f"   📊 Hacim Filtresi: {'❌ KAPALI' if not cls.VOLUME_FILTER_ENABLED else '✅ AÇIK'}")
        print(f"   🌊 Volatilite: {'❌ KAPALI' if not cls.VOLATILITY_FILTER_ENABLED else '✅ AÇIK'}")
        print(f"   📈 Min. Hareket: {'❌ KAPALI' if not cls.MIN_PRICE_MOVEMENT_ENABLED else '✅ AÇIK'}")
        print(f"   ⏳ Soğuma: {'✅ AÇIK (2dk)' if cls.SIGNAL_COOLDOWN_ENABLED else '❌ KAPALI'}")
        print("=" * 70)
        print("💹 DEBUG TP/SL AYARLARI:")
        print(f"   🛑 Stop Loss: %{current['stop_loss_percent'] * 100:.2f}")
        print(f"   🎯 Take Profit: %{current['take_profit_percent'] * 100:.2f}")
        print(f"   ⚖️  Risk/Reward: 1:{risk_reward:.2f}")
        print(f"   ⏳ Soğuma: {current['cooldown_minutes']} dakika")
        print("=" * 70)
        print("🔒 DEBUG RİSK YÖNETİMİ:")
        print(f"   📊 Max. Günlük Pozisyon: {cls.MAX_DAILY_POSITIONS} (çok yüksek)")
        print(f"   💸 Max. Günlük Kayıp: %{cls.MAX_DAILY_LOSS_PERCENT * 100} (çok yüksek)")
        print(f"   🚫 Max. Ardışık Kayıp: {cls.MAX_CONSECUTIVE_LOSSES} (çok yüksek)")
        print("=" * 70)
        print("🔧 DEBUG MODU: Sinyal üretim testi için tüm kısıtlamalar kaldırıldı")
        print("⚠️  GERÇEK TİCARET İÇİN KULLANMAYIN!")
        print("=" * 70)

settings = Settings()

# DEBUG modu aktif etme fonksiyonu
def enable_debug_mode():
    """Debug modunu aktif et"""
    print("🔧 DEBUG MODU AKTİF EDİLİYOR...")
    
    # Tüm filtreleri kapat
    settings.TREND_FILTER_ENABLED = False
    settings.MOMENTUM_FILTER_ENABLED = False
    settings.TREND_STRENGTH_FILTER_ENABLED = False
    settings.PRICE_ACTION_FILTER_ENABLED = False
    settings.MIN_PRICE_MOVEMENT_ENABLED = False
    settings.RSI_FILTER_ENABLED = False
    settings.VOLATILITY_FILTER_ENABLED = False
    settings.VOLUME_FILTER_ENABLED = False
    
    # Soğuma süresini minimal yap
    settings.SIGNAL_COOLDOWN_ENABLED = True
    
    # Risk limitlerini çok yüksek yap
    settings.MAX_DAILY_POSITIONS = 100
    settings.MAX_CONSECUTIVE_LOSSES = 50
    settings.MAX_DAILY_LOSS_PERCENT = 0.5
    
    print("✅ DEBUG MODU AKTİF - Tüm filtreler devre dışı!")

def disable_debug_mode():
    """Debug modunu kapat ve normal ayarları geri yükle"""
    print("🔄 NORMAL MOD GERİ YÜKLENİYOR...")
    
    # Filtreleri geri açs
    settings.TREND_FILTER_ENABLED = True
    settings.MOMENTUM_FILTER_ENABLED = True
    settings.TREND_STRENGTH_FILTER_ENABLED = True
    settings.RSI_FILTER_ENABLED = True
    settings.VOLATILITY_FILTER_ENABLED = True
    settings.VOLUME_FILTER_ENABLED = True
    settings.MIN_PRICE_MOVEMENT_ENABLED = True
    
    # Normal risk limitlerini geri yükle
    settings.MAX_DAILY_POSITIONS = 8
    settings.MAX_CONSECUTIVE_LOSSES = 3
    settings.MAX_DAILY_LOSS_PERCENT = 0.05
    
    print("✅ NORMAL MOD GERİ YÜKLENDİ")

# Başlangıçta debug ayarlarını göster
if __name__ == "__main__":
    settings.validate_settings()
    settings.print_settings()
