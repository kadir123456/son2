# app/config.py - BOLLİNGER BANDS STRATEJİSİ

import os
from dotenv import load_dotenv

load_dotenv()

class SimpleEMACrossSettings:  # İsim aynı kaldı - uyumluluk için
    """
    📊 Bollinger Bands 1 Dakikalık Strateji
    - Her dakika 1 LONG + 1 SHORT pozisyon
    - Sabit 10 USDT işlem boyutu
    - Bantlar arası al-sat
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

    # --- 📊 Bollinger Bands Parametreleri ---
    BB_PERIOD: int = 20           # Bollinger period
    BB_STD_DEV: float = 2.0       # Standart sapma çarpanı
    TIMEFRAME: str = "1m"         # Sabit 1 dakika
    
    # Eski EMA parametreleri - geriye uyumluluk (kullanılmıyor)
    EMA_FAST_PERIOD: int = 9
    EMA_SLOW_PERIOD: int = 21
    
    # --- 💰 Pozisyon Ayarları ---
    POSITION_SIZE_USDT: float = 10.0  # Sabit 10 USDT
    LEVERAGE: int = 10                 # 10x kaldıraç
    MAX_POSITION_SIZE_PERCENT: float = 0.90  # Kullanılmıyor artık
    MIN_BALANCE_USDT: float = 5
    
    # --- 🎯 TP/SL Ayarları (Dinamik - Bollinger genişliğine göre) ---
    TP_MULTIPLIER: float = 0.5    # TP = Bollinger genişliği * 0.5
    SL_MULTIPLIER: float = 0.3    # SL = Bollinger genişliği * 0.3
    
    # Minimum TP/SL (güvenlik için)
    MIN_TP_PERCENT: float = 0.003  # %0.3
    MIN_SL_PERCENT: float = 0.002  # %0.2
    
    # Maksimum TP/SL (aşırı geniş bantlarda)
    MAX_TP_PERCENT: float = 0.015  # %1.5
    MAX_SL_PERCENT: float = 0.010  # %1.0
    
    # Eski TP/SL - geriye uyumluluk (kullanılmıyor)
    STOP_LOSS_PERCENT: float = 0.008
    TAKE_PROFIT_PERCENT: float = 0.015
    
    # --- 🚀 API Rate Limiting ---
    API_CALL_DELAY: float = 0.1  # 100ms
    MAX_REQUESTS_PER_SECOND: int = 10
    
    # --- 🌐 WebSocket Ayarları ---
    WEBSOCKET_PING_INTERVAL: int = 30
    WEBSOCKET_PING_TIMEOUT: int = 15
    WEBSOCKET_CLOSE_TIMEOUT: int = 10
    
    # --- 📊 Multi-Coin Tarama (kullanılmıyor artık) ---
    MAX_COINS: int = 1
    MAX_CONCURRENT_POSITIONS: int = 1
    
    # --- 💾 Memory Management ---
    MAX_KLINES_PER_SYMBOL: int = 30  # Sadece 30 mum yeterli
    STATUS_UPDATE_INTERVAL: int = 30
    
    # --- 🔍 Debug ---
    DEBUG_MODE: bool = True
    TEST_MODE: bool = False
    VERBOSE_LOGGING: bool = True
    
    # --- Geriye uyumluluk metodları ---
    @classmethod
    def get_tp_sl(cls, timeframe: str = None):
        """Eski format için uyumluluk"""
        return {
            "tp_percent": cls.TAKE_PROFIT_PERCENT,
            "sl_percent": cls.STOP_LOSS_PERCENT
        }
    
    @classmethod
    def validate_settings(cls):
        """Ayar doğrulama"""
        errors = []
        
        if not cls.API_KEY or not cls.API_SECRET:
            errors.append("❌ BINANCE_API_KEY veya BINANCE_API_SECRET eksik!")
        
        if cls.POSITION_SIZE_USDT < 10:
            errors.append("❌ Pozisyon boyutu minimum 10 USDT olmalı")
        
        if cls.BB_PERIOD < 10:
            errors.append("❌ Bollinger period minimum 10 olmalı")
        
        for error in errors:
            print(error)
        
        return len(errors) == 0
    
    @classmethod
    def print_settings(cls):
        """Ayarları göster"""
        print("=" * 70)
        print("📊 BOLLİNGER BANDS AL-SAT STRATEJİSİ")
        print("=" * 70)
        print(f"🌐 Ortam: {cls.ENVIRONMENT}")
        print(f"🧪 Test Modu: {'AÇIK' if cls.TEST_MODE else 'KAPALI (CANLI)'}")
        print(f"📊 Bollinger Period: {cls.BB_PERIOD}")
        print(f"📈 Std Dev: {cls.BB_STD_DEV}")
        print(f"⏰ Timeframe: {cls.TIMEFRAME} (SABİT)")
        print(f"💰 Pozisyon Boyutu: {cls.POSITION_SIZE_USDT} USDT (SABİT)")
        print(f"💰 Kaldıraç: {cls.LEVERAGE}x")
        print(f"🎯 TP Multiplier: {cls.TP_MULTIPLIER}")
        print(f"🛑 SL Multiplier: {cls.SL_MULTIPLIER}")
        print("=" * 70)
        print("✅ HER DAKİKA 1 LONG + 1 SHORT POZİSYON")
        print("=" * 70)
    
    @classmethod
    def validate_settings_optimized(cls):
        """Geriye uyumluluk"""
        return cls.validate_settings()
    
    @classmethod
    def print_settings_optimized(cls):
        """Geriye uyumluluk"""
        return cls.print_settings()
    
    @classmethod
    def get_trading_config(cls):
        """Trading config"""
        return {
            "strategy": "bollinger_bands",
            "timeframe": cls.TIMEFRAME,
            "bb_period": cls.BB_PERIOD,
            "bb_std": cls.BB_STD_DEV,
            "position_size": cls.POSITION_SIZE_USDT,
            "leverage": cls.LEVERAGE
        }
    
    @classmethod
    def get_api_rate_config(cls):
        """API config"""
        return {
            "delay": cls.API_CALL_DELAY,
            "max_per_second": cls.MAX_REQUESTS_PER_SECOND
        }

# Global settings instance
settings = SimpleEMACrossSettings()

if __name__ == "__main__":
    if settings.validate_settings():
        settings.print_settings()
