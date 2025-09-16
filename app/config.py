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
    TIMEFRAME: str = "15m"  # Varsayılan, dinamik olarak değişecek
    
    # --- Zaman Dilimine Göre Dinamik TP/SL Ayarları ---
    TIMEFRAME_SETTINGS: Dict[str, Dict[str, float]] = {
        "1m": {
            "stop_loss_percent": 0.0015,    # %0.15 - Çok dar SL
            "take_profit_percent": 0.0025,  # %0.25 - Hızlı kar alma
            "min_price_movement": 0.0008,   # %0.08 - Minimum hareket
            "signal_strength": 0.0001,      # Çok hassas sinyal
            "cooldown_minutes": 3,          # 3 dakika soğuma
            "atr_multiplier": 1.2           # Düşük volatilite eşiği
        },
        "3m": {
            "stop_loss_percent": 0.002,     # %0.2
            "take_profit_percent": 0.004,   # %0.4
            "min_price_movement": 0.0012,   # %0.12
            "signal_strength": 0.0001,
            "cooldown_minutes": 5,          # 5 dakika soğuma
            "atr_multiplier": 1.3
        },
        "5m": {
            "stop_loss_percent": 0.003,     # %0.3
            "take_profit_percent": 0.005,   # %0.5
            "min_price_movement": 0.0015,   # %0.15
            "signal_strength": 0.00015,
            "cooldown_minutes": 8,          # 8 dakika soğuma
            "atr_multiplier": 1.4
        },
        "15m": {
            "stop_loss_percent": 0.004,     # %0.4 - Mevcut
            "take_profit_percent": 0.006,   # %0.6 - Mevcut
            "min_price_movement": 0.003,    # %0.3
            "signal_strength": 0.0002,
            "cooldown_minutes": 15,         # 15 dakika soğuma
            "atr_multiplier": 1.5
        },
        "30m": {
            "stop_loss_percent": 0.006,     # %0.6 - Daha geniş SL
            "take_profit_percent": 0.009,   # %0.9 - Daha büyük hedef
            "min_price_movement": 0.004,    # %0.4
            "signal_strength": 0.0003,
            "cooldown_minutes": 25,         # 25 dakika soğuma
            "atr_multiplier": 1.6
        },
        "1h": {
            "stop_loss_percent": 0.008,     # %0.8 - En geniş SL
            "take_profit_percent": 0.012,   # %1.2 - En büyük hedef
            "min_price_movement": 0.005,    # %0.5
            "signal_strength": 0.0004,
            "cooldown_minutes": 45,         # 45 dakika soğuma
            "atr_multiplier": 1.8
        }
    }
    
    # Aktif zaman dilimi ayarlarını al
    @classmethod
    def get_current_settings(cls) -> Dict[str, float]:
        """Seçili zaman dilimine göre ayarları döndür"""
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
    
    # --- GÜÇLENDİRİLMİŞ SAHTE SİNYAL KORUMASI AYARLARI ---
    
    # Trend Filtresi - Zaman dilimine göre EMA
    TREND_FILTER_ENABLED: bool = True
    TREND_EMA_PERIODS: Dict[str, int] = {
        "1m": 20,   # Kısa vadeli trend
        "3m": 30,
        "5m": 40,
        "15m": 50,  # Mevcut
        "30m": 60,
        "1h": 80    # Uzun vadeli trend
    }
    
    @property
    def TREND_EMA_PERIOD(self) -> int:
        return self.TREND_EMA_PERIODS.get(self.TIMEFRAME, 50)
    
    # RSI Filtresi - Sıkılaştırılmış
    RSI_FILTER_ENABLED: bool = True
    RSI_PERIOD: int = 14
    RSI_OVERSOLD: float = 25.0      # Daha sıkı (30 -> 25)
    RSI_OVERBOUGHT: float = 75.0    # Daha sıkı (70 -> 75)
    
    # Sinyal Soğuma Süresi - Dinamik
    SIGNAL_COOLDOWN_ENABLED: bool = True
    
    # Volatilite Filtresi - Sıkılaştırılmış
    VOLATILITY_FILTER_ENABLED: bool = True
    ATR_PERIOD: int = 14
    
    # Hacim Filtresi - Güçlendirilmiş
    VOLUME_FILTER_ENABLED: bool = True
    VOLUME_MA_PERIOD: int = 20
    MIN_VOLUME_MULTIPLIER: float = 1.5  # 1.2 -> 1.5 (Daha yüksek hacim gereksinimi)
    
    # Minimum Fiyat Hareketi Filtresi - Dinamik
    MIN_PRICE_MOVEMENT_ENABLED: bool = True
    
    # --- YENİ EKLENDİ: MOMENTUM VE TREND GÜCÜ FİLTRELERİ ---
    
    # Momentum Filtresi
    MOMENTUM_FILTER_ENABLED: bool = True
    MOMENTUM_PERIOD: int = 10
    MIN_MOMENTUM_STRENGTH: float = 0.5
    
    # Trend Gücü Filtresi (ADX benzeri)
    TREND_STRENGTH_FILTER_ENABLED: bool = True
    MIN_TREND_STRENGTH: float = 0.3
    
    # Fiyat Aksiyon Filtresi
    PRICE_ACTION_FILTER_ENABLED: bool = True
    ENGULFING_REQUIRED: bool = False  # Engulfing pattern gereksinimi
    
    # --- RISK YÖNETİMİ GÜVENLİK AYARLARI ---
    
    # Maksimum günlük pozisyon sayısı
    MAX_DAILY_POSITIONS: int = 8
    
    # Maksimum kayıp oranı (günlük bakiyenin %5'i)
    MAX_DAILY_LOSS_PERCENT: float = 0.05
    
    # Minimum risk/reward oranı
    MIN_RISK_REWARD_RATIO: float = 1.3  # TP en az SL'nin 1.3 katı olmalı
    
    # Whipsaw koruması - ard arda kayıp pozisyon limiti
    MAX_CONSECUTIVE_LOSSES: int = 3
    
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
        """Zaman dilimini değiştir ve ayarları güncelle"""
        if timeframe in cls.TIMEFRAME_SETTINGS:
            cls.TIMEFRAME = timeframe
            print(f"🕐 Zaman dilimi {timeframe} olarak ayarlandı")
            print(f"📊 SL: %{cls().STOP_LOSS_PERCENT*100:.2f} | TP: %{cls().TAKE_PROFIT_PERCENT*100:.2f}")
            return True
        else:
            print(f"❌ Geçersiz zaman dilimi: {timeframe}")
            return False
    
    @classmethod
    def get_risk_reward_ratio(cls) -> float:
        """Mevcut TP/SL oranına göre risk/reward hesapla"""
        current = cls.get_current_settings()
        return current["take_profit_percent"] / current["stop_loss_percent"]
    
    @classmethod
    def validate_settings(cls):
        """Ayarları doğrula ve gerekirse uyar"""
        warnings = []
        
        if not cls.API_KEY or not cls.API_SECRET:
            warnings.append("⚠️ BINANCE_API_KEY veya BINANCE_API_SECRET ayarlanmamış!")
        
        if cls.LEVERAGE < 1 or cls.LEVERAGE > 125:
            warnings.append(f"⚠️ Kaldıraç değeri geçersiz: {cls.LEVERAGE}. 1-125 arası olmalı.")
        
        if cls.ORDER_SIZE_USDT < 5:
            warnings.append(f"⚠️ İşlem miktarı çok düşük: {cls.ORDER_SIZE_USDT}. Minimum 5 USDT önerilir.")
        
        # Risk/reward oranı kontrolü
        current_rr = cls.get_risk_reward_ratio()
        if current_rr < cls.MIN_RISK_REWARD_RATIO:
            warnings.append(f"⚠️ Risk/Reward oranı çok düşük: {current_rr:.2f}. Minimum {cls.MIN_RISK_REWARD_RATIO}")
        
        # Zaman dilimi kontrolü
        if cls.TIMEFRAME not in cls.TIMEFRAME_SETTINGS:
            warnings.append(f"⚠️ Geçersiz zaman dilimi: {cls.TIMEFRAME}")
        
        for warning in warnings:
            print(warning)
        
        return len(warnings) == 0

    @classmethod
    def print_settings(cls):
        """Mevcut ayarları yazdır"""
        current = cls.get_current_settings()
        risk_reward = cls.get_risk_reward_ratio()
        
        print("=" * 70)
        print("🚀 DİNAMİK TP/SL VE GÜÇLENDİRİLMİŞ SAHTEKİ SİNYAL KORUMASLI BOT")
        print("=" * 70)
        print(f"🌐 Ortam: {cls.ENVIRONMENT}")
        print(f"💰 İşlem Miktarı: {cls.ORDER_SIZE_USDT} USDT")
        print(f"📈 Kaldıraç: {cls.LEVERAGE}x")
        print(f"⏰ Zaman Dilimi: {cls.TIMEFRAME}")
        print("=" * 70)
        print("💹 DİNAMİK TP/SL AYARLARI:")
        print(f"   🛑 Stop Loss: %{current['stop_loss_percent'] * 100:.2f}")
        print(f"   🎯 Take Profit: %{current['take_profit_percent'] * 100:.2f}")
        print(f"   ⚖️  Risk/Reward: 1:{risk_reward:.2f}")
        print(f"   ⏳ Soğuma Süresi: {current['cooldown_minutes']} dakika")
        print(f"   📊 Min. Hareket: %{current['min_price_movement'] * 100:.2f}")
        print("=" * 70)
        print("🛡️ GÜÇLENDİRİLMİŞ SAHTEKİ SİNYAL KORUMALARI:")
        print(f"   📊 Trend Filtresi (EMA{cls().TREND_EMA_PERIOD}): {'✅' if cls.TREND_FILTER_ENABLED else '❌'}")
        print(f"   📈 Min. Fiyat Hareketi: {'✅' if cls.MIN_PRICE_MOVEMENT_ENABLED else '❌'}")
        print(f"   🔄 RSI Filtresi ({cls.RSI_OVERSOLD}-{cls.RSI_OVERBOUGHT}): {'✅' if cls.RSI_FILTER_ENABLED else '❌'}")
        print(f"   ⏳ Sinyal Soğuma: {'✅' if cls.SIGNAL_COOLDOWN_ENABLED else '❌'}")
        print(f"   🌊 Volatilite Filtresi: {'✅' if cls.VOLATILITY_FILTER_ENABLED else '❌'}")
        print(f"   📊 Hacim Filtresi ({cls.MIN_VOLUME_MULTIPLIER}x): {'✅' if cls.VOLUME_FILTER_ENABLED else '❌'}")
        print(f"   ⚡ Momentum Filtresi: {'✅' if cls.MOMENTUM_FILTER_ENABLED else '❌'}")
        print(f"   💪 Trend Gücü Filtresi: {'✅' if cls.TREND_STRENGTH_FILTER_ENABLED else '❌'}")
        print("=" * 70)
        print("🔒 RİSK YÖNETİMİ:")
        print(f"   📊 Max. Günlük Pozisyon: {cls.MAX_DAILY_POSITIONS}")
        print(f"   💸 Max. Günlük Kayıp: %{cls.MAX_DAILY_LOSS_PERCENT * 100}")
        print(f"   ⚖️  Min. Risk/Reward: 1:{cls.MIN_RISK_REWARD_RATIO}")
        print(f"   🚫 Max. Ardışık Kayıp: {cls.MAX_CONSECUTIVE_LOSSES}")
        print("=" * 70)
        print("💡 Bu sistem yalnızca yüksek kazanç potansiyelli pozisyonlara girer")
        print("🎯 Para kaybetmemek öncelikli hedef - sadece kaliteli sinyaller işlenir")
        print("=" * 70)

settings = Settings()

# Başlangıçta ayarları doğrula
if __name__ == "__main__":
    settings.validate_settings()
    settings.print_settings()
