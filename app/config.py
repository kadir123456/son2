# app/config.py - HIZLI SCALPING AYARLARI

import os
from dotenv import load_dotenv

load_dotenv()

class FastScalpingSettings:
    """
    ⚡ HIZLI SCALPING AYARLARI
    - 30 saniye ve 1 dakikalık agresif trade
    - Sabit 10 USDT işlem
    - 15x kaldıraç
    - Dakikada 1-2 işlem hedefi
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
    
    # --- ⚡ Hızlı Scalping Parametreleri ---
    TIMEFRAME: str = "1m"         # 1 dakika
    EMA_FAST_PERIOD: int = 5      # Hızlı EMA
    EMA_SLOW_PERIOD: int = 13     # Yavaş EMA
    
    # --- 💰 Pozisyon Ayarları ---
    POSITION_SIZE_USDT: float = 10.0  # Sabit 10 USDT
    LEVERAGE: int = 15                 # 15x kaldıraç
    MIN_BALANCE_USDT: float = 10
    
    # --- 🎯 TP/SL Ayarları (Çok Sıkı) ---
    TAKE_PROFIT_PERCENT: float = 0.004  # %0.4 kar al
    STOP_LOSS_PERCENT: float = 0.002    # %0.2 zarar durdur
    
    # --- 🚀 API Rate Limiting ---
    API_CALL_DELAY: float = 0.1
    MAX_REQUESTS_PER_SECOND: int = 10
    
    # --- 🌐 WebSocket Ayarları ---
    WEBSOCKET_PING_INTERVAL: int = 30
    WEBSOCKET_PING_TIMEOUT: int = 15
    WEBSOCKET_CLOSE_TIMEOUT: int = 10
    
    # --- 💾 Memory Management ---
    MAX_KLINES_PER_SYMBOL: int = 100
    STATUS_UPDATE_INTERVAL: int = 30
    
    # --- 🔍 Debug ---
    DEBUG_MODE: bool = True
    TEST_MODE: bool = False
    VERBOSE_LOGGING: bool = True
    
    @classmethod
    def validate_settings(cls):
        """Ayar doğrulama"""
        errors = []
        
        if not cls.API_KEY or not cls.API_SECRET:
            errors.append("❌ BINANCE_API_KEY veya BINANCE_API_SECRET eksik!")
        
        if cls.POSITION_SIZE_USDT < 10:
            errors.append("❌ Pozisyon boyutu minimum 10 USDT olmalı")
        
        for error in errors:
            print(error)
        
        return len(errors) == 0
    
    @classmethod
    def print_settings(cls):
        """Ayarları göster"""
        print("=" * 70)
        print("⚡ HIZLI SCALPING STRATEJİSİ")
        print("=" * 70)
        print(f"🌐 Ortam: {cls.ENVIRONMENT}")
        print(f"🧪 Test Modu: {'AÇIK' if cls.TEST_MODE else 'KAPALI (CANLI)'}")
        print(f"📊 EMA: {cls.EMA_FAST_PERIOD}/{cls.EMA_SLOW_PERIOD}")
        print(f"⏰ Timeframe: {cls.TIMEFRAME}")
        print(f"💰 Pozisyon: {cls.POSITION_SIZE_USDT} USDT")
        print(f"💰 Kaldıraç: {cls.LEVERAGE}x")
        print(f"🎯 TP: %{cls.TAKE_PROFIT_PERCENT*100:.2f}")
        print(f"🛑 SL: %{cls.STOP_LOSS_PERCENT*100:.2f}")
        print("=" * 70)
        print("⚡ SÜREKLI TRADE - FİLTRE YOK!")
        print("=" * 70)

# Global settings instance
settings = FastScalpingSettings()

if __name__ == "__main__":
    if settings.validate_settings():
        settings.print_settings()
