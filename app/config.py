# app/config.py - SAF EMA CROSS BOT AYARLARI

import os
from dotenv import load_dotenv

load_dotenv()

class SimpleEMACrossSettings:
    """
    📈 SAF EMA CROSS Trading Bot Ayarları
    - Filtre yok, sadece EMA kesişimi
    - Çoklu zaman dilimi desteği
    - Otomatik TP/SL (zaman dilimine göre)
    """
    
    # --- Temel Ayarlar ---
    API_KEY: str = os.getenv("BINANCE_API_KEY")
    API_SECRET: str = os.getenv("BINANCE_API_SECRET")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "LIVE")
    BASE_URL = "https://fapi.binance.com" if os.getenv("ENVIRONMENT", "TEST") == "LIVE" else "https://testnet.binancefuture.com"
    WEBSOCKET_URL = "wss://fstream.binance.com" if os.getenv("ENVIRONMENT", "TEST") == "LIVE" else "wss://stream.binancefuture.com"

    # --- Firebase ---
    FIREBASE_CREDENTIALS_JSON: str = os.getenv("FIREBASE_CREDENTIALS_JSON")
    FIREBASE_DATABASE_URL: str = os.getenv("FIREBASE_DATABASE_URL")

    # --- 📈 EMA Parametreleri ---
    EMA_FAST_PERIOD: int = 9
    EMA_SLOW_PERIOD: int = 21
    
    # --- ⏰ Zaman Dilimi (Kullanıcı Seçimi) ---
    TIMEFRAME: str = "15m"  # Varsayılan, UI'den değiştirilebilir
    AVAILABLE_TIMEFRAMES = ["1m", "3m", "5m", "15m", "1h"]
    
    # --- 💰 Kaldıraç ve Pozisyon ---
    LEVERAGE: int = 10  # Sabit 10x
    MAX_POSITION_SIZE_PERCENT: float = 0.90  # %90 bakiye kullanımı
    MIN_BALANCE_USDT: float = 50.0
    
    # --- 🎯 TP/SL Ayarları (Zaman Dilimine Göre) ---
    TP_SL_SETTINGS = {
        "1m": {"tp_percent": 0.010, "sl_percent": 0.005},   # TP: %1.0, SL: %0.5
        "3m": {"tp_percent": 0.015, "sl_percent": 0.008},   # TP: %1.5, SL: %0.8
        "5m": {"tp_percent": 0.020, "sl_percent": 0.010},   # TP: %2.0, SL: %1.0
        "15m": {"tp_percent": 0.030, "sl_percent": 0.015},  # TP: %3.0, SL: %1.5
        "1h": {"tp_percent": 0.050, "sl_percent": 0.025},   # TP: %5.0, SL: %2.5
    }
    
    # Dinamik TP/SL alma
    @classmethod
    def get_tp_sl(cls, timeframe: str = None):
        tf = timeframe or cls.TIMEFRAME
        return cls.TP_SL_SETTINGS.get(tf, cls.TP_SL_SETTINGS["15m"])
    
    # --- 🚀 API Rate Limiting ---
    API_CALL_DELAY: float = 0.08  # 80ms = ~12.5 request/second
    MAX_REQUESTS_PER_SECOND: int = 12
    
    # --- 🌐 WebSocket Ayarları ---
    WEBSOCKET_PING_INTERVAL: int = 30
    WEBSOCKET_PING_TIMEOUT: int = 15
    WEBSOCKET_CLOSE_TIMEOUT: int = 10
    
    # --- 📊 Multi-Coin Tarama ---
    MAX_COINS: int = 100
    MAX_CONCURRENT_POSITIONS: int = 1  # Aynı anda 1 pozisyon
    
    # --- 💾 Memory Management ---
    MAX_KLINES_PER_SYMBOL: int = 50
    STATUS_UPDATE_INTERVAL: int = 30
    
    # --- 🔍 Debug ---
    DEBUG_MODE: bool = True
    TEST_MODE: bool = False
    VERBOSE_LOGGING: bool = True
    
    @classmethod
    def validate_settings(cls):
        """Ayar doğrulama"""
        errors = []
        warnings = []
        
        if not cls.API_KEY or not cls.API_SECRET:
            errors.append("❌ BINANCE_API_KEY veya BINANCE_API_SECRET eksik!")
        
        if cls.TIMEFRAME not in cls.AVAILABLE_TIMEFRAMES:
            warnings.append(f"⚠️ Geçersiz timeframe: {cls.TIMEFRAME}")
            cls.TIMEFRAME = "15m"
        
        if cls.LEVERAGE > 20:
            warnings.append(f"⚠️ Yüksek kaldıraç: {cls.LEVERAGE}x")
        
        for error in errors:
            print(error)
        for warning in warnings:
            print(warning)
        
        return len(errors) == 0
    
    @classmethod
    def print_settings(cls):
        """Ayarları göster"""
        tp_sl = cls.get_tp_sl()
        
        print("=" * 70)
        print("📈 SAF EMA CROSS BOT")
        print("=" * 70)
        print(f"🌐 Ortam: {cls.ENVIRONMENT}")
        print(f"🧪 Test Modu: {'AÇIK' if cls.TEST_MODE else 'KAPALI (CANLI)'}")
        print(f"📈 EMA: {cls.EMA_FAST_PERIOD}/{cls.EMA_SLOW_PERIOD}")
        print(f"⏰ Zaman Dilimi: {cls.TIMEFRAME}")
        print(f"💰 Kaldıraç: {cls.LEVERAGE}x")
        print(f"💵 Pozisyon: %{cls.MAX_POSITION_SIZE_PERCENT*100:.0f} bakiye")
        print(f"🎯 TP: %{tp_sl['tp_percent']*100:.1f} | SL: %{tp_sl['sl_percent']*100:.1f}")
        print(f"📊 Max Coin: {cls.MAX_COINS}")
        print(f"⚡ Rate Limit: {cls.MAX_REQUESTS_PER_SECOND} req/s")
        print("=" * 70)
        print("✅ FİLTRE YOK - SAF EMA KESİŞİMİ")
        print("=" * 70)

# Global settings instance
settings = SimpleEMACrossSettings()

if __name__ == "__main__":
    if settings.validate_settings():
        settings.print_settings()
