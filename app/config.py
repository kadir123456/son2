# app/config.py - OPTİMİZE EDİLMİŞ SCALPING AYARLARI

import os
from dotenv import load_dotenv

load_dotenv()

class OptimizedScalpingSettings:
    """
    ⚡ OPTİMİZE EDİLMİŞ SCALPING AYARLARI
    
    DEĞİŞİKLİKLER:
    - Dinamik pozisyon boyutu (bakiyenin %15'i)
    - Daha güvenli kaldıraç (10x)
    - Gerçekçi TP/SL (%0.8/%0.4)
    - Minimum momentum filtresi
    - Trade cooldown (90 saniye)
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
    
    # --- ⚡ Scalping Parametreleri ---
    TIMEFRAME: str = "1m"          # 1 dakika
    EMA_FAST_PERIOD: int = 5       # Hızlı EMA
    EMA_SLOW_PERIOD: int = 13      # Yavaş EMA
    
    # --- 💰 Pozisyon Ayarları (DİNAMİK) ---
    BALANCE_USAGE_PERCENT: float = 0.15  # Bakiyenin %15'i
    LEVERAGE: int = 10                   # 10x kaldıraç (daha güvenli)
    MIN_BALANCE_USDT: float = 20         # Minimum 20 USDT
    MIN_POSITION_SIZE_USDT: float = 5.0  # Minimum 5 USDT pozisyon
    
    # --- 🎯 TP/SL Ayarları (GERÇEKÇİ) ---
    TAKE_PROFIT_PERCENT: float = 0.008   # %0.8 kar al
    STOP_LOSS_PERCENT: float = 0.004     # %0.4 zarar durdur
    
    # --- 🛡️ Risk Yönetimi ---
    MAX_DAILY_TRADES: int = 50           # Günlük max trade
    TRADE_COOLDOWN_SECONDS: int = 90     # 90 saniye trade aralığı
    MIN_MOMENTUM_PERCENT: float = 0.001  # Min %0.1 momentum
    
    # --- 🚀 API Rate Limiting ---
    API_CALL_DELAY: float = 0.2
    MAX_REQUESTS_PER_SECOND: int = 8
    
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
    def calculate_position_size(cls, balance: float) -> float:
        """Dinamik pozisyon boyutu hesapla"""
        if balance < cls.MIN_BALANCE_USDT:
            return 0.0
        
        position_size = balance * cls.BALANCE_USAGE_PERCENT
        
        if position_size < cls.MIN_POSITION_SIZE_USDT:
            return 0.0
        
        return round(position_size, 2)
    
    @classmethod
    def validate_settings(cls):
        """Ayar doğrulama"""
        errors = []
        
        if not cls.API_KEY or not cls.API_SECRET:
            errors.append("❌ BINANCE_API_KEY veya BINANCE_API_SECRET eksik!")
        
        if cls.MIN_BALANCE_USDT < 20:
            errors.append("❌ Minimum bakiye 20 USDT olmalı")
        
        if cls.TAKE_PROFIT_PERCENT <= cls.STOP_LOSS_PERCENT:
            errors.append("❌ TP, SL'den büyük olmalı")
        
        for error in errors:
            print(error)
        
        return len(errors) == 0
    
    @classmethod
    def print_settings(cls):
        """Ayarları göster"""
        print("=" * 70)
        print("⚡ OPTİMİZE EDİLMİŞ SCALPING STRATEJİSİ")
        print("=" * 70)
        print(f"🌐 Ortam: {cls.ENVIRONMENT}")
        print(f"🧪 Test Modu: {'AÇIK' if cls.TEST_MODE else 'KAPALI (CANLI)'}")
        print(f"📊 EMA: {cls.EMA_FAST_PERIOD}/{cls.EMA_SLOW_PERIOD}")
        print(f"⏰ Timeframe: {cls.TIMEFRAME}")
        print(f"💰 Pozisyon: Bakiyenin %{cls.BALANCE_USAGE_PERCENT*100:.0f}'i")
        print(f"📈 Kaldıraç: {cls.LEVERAGE}x")
        print(f"🎯 TP: %{cls.TAKE_PROFIT_PERCENT*100:.2f}")
        print(f"🛑 SL: %{cls.STOP_LOSS_PERCENT*100:.2f}")
        print(f"⏳ Trade Cooldown: {cls.TRADE_COOLDOWN_SECONDS}s")
        print(f"📉 Min Momentum: %{cls.MIN_MOMENTUM_PERCENT*100:.2f}")
        print(f"🔢 Günlük Max Trade: {cls.MAX_DAILY_TRADES}")
        print("=" * 70)
        print("✅ FİLTRELER AKTİF - Güvenli Trade")
        print("=" * 70)

# Global settings instance
settings = OptimizedScalpingSettings()

if __name__ == "__main__":
    if settings.validate_settings():
        settings.print_settings()
        
        # Test position size calculation
        print("\n💡 POZİSYON BOYUTU TESTİ:")
        test_balances = [15, 20, 50, 100, 200]
        for balance in test_balances:
            pos_size = settings.calculate_position_size(balance)
            if pos_size > 0:
                notional = pos_size * settings.LEVERAGE
                print(f"   Bakiye: ${balance} → Pozisyon: ${pos_size} → Notional: ${notional}")
            else:
                print(f"   Bakiye: ${balance} → YETERSİZ")
