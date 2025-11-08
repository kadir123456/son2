# app/config.py - OPTİMİZE EDİLMİŞ + PROFESSIONAL SCALPING AYARLARI

import os
from dotenv import load_dotenv

load_dotenv()

class OptimizedScalpingSettings:
    """
    ⚡ OPTİMİZE EDİLMİŞ + 🔥 PROFESSIONAL SCALPING AYARLARI
    
    İKİ STRATEJİ:
    1. Optimized Scalping (Eski) - EMA cross
    2. Professional Scalping (Yeni) - Pullback + Volume + Trend ✅
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
    LEVERAGE: int = 15                   # 15x kaldıraç (scalping için ideal)
    MIN_BALANCE_USDT: float = 20         # Minimum 20 USDT
    MIN_POSITION_SIZE_USDT: float = 5.0  # Minimum 5 USDT pozisyon
    
    # --- 🎯 TP/SL Ayarları (ESKI STRATEJİ) ---
    TAKE_PROFIT_PERCENT: float = 0.008   # %0.8 kar al
    STOP_LOSS_PERCENT: float = 0.004     # %0.4 zarar durdur
    
    # --- 🔥 PROFESSIONAL SCALPING (YENİ) ---
    USE_PROFESSIONAL_STRATEGY: bool = True  # True = Pro strateji ✅, False = Eski strateji
    
    # Professional scalping parametreleri
    PRO_TP_PERCENT: float = 0.006        # %0.6 kar (mikro scalping)
    PRO_SL_PERCENT: float = 0.003        # %0.3 zarar (sıkı stop)
    PRO_MIN_CONFIDENCE: int = 75         # Minimum %75 güven skoru
    PRO_VOLUME_MULTIPLIER: float = 1.5   # 1.5x volume spike gerekli
    PRO_MIN_TREND: float = 0.003         # %0.3 minimum trend gücü
    PRO_PULLBACK_MIN: float = 0.002      # Min %0.2 pullback
    PRO_PULLBACK_MAX: float = 0.008      # Max %0.8 pullback
    
    # --- 🛡️ Risk Yönetimi ---
    MAX_DAILY_TRADES: int = 40           # Günlük max trade (professional için 40)
    TRADE_COOLDOWN_SECONDS: int = 60     # 60 saniye trade aralığı
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
        if cls.USE_PROFESSIONAL_STRATEGY:
            print("🔥 PROFESSIONAL SCALPING STRATEGY 🔥")
        else:
            print("⚡ OPTIMIZED SCALPING STRATEGY")
        print("=" * 70)
        print(f"🌐 Ortam: {cls.ENVIRONMENT}")
        print(f"🧪 Test Modu: {'AÇIK' if cls.TEST_MODE else 'KAPALI (CANLI)'}")
        
        if cls.USE_PROFESSIONAL_STRATEGY:
            print(f"\n🔥 PROFESSIONAL SCALPING:")
            print(f"   📊 Strateji: Pullback + Volume + Trend")
            print(f"   🎯 TP: %{cls.PRO_TP_PERCENT*100:.2f}")
            print(f"   🛑 SL: %{cls.PRO_SL_PERCENT*100:.2f}")
            print(f"   ✨ Min Confidence: {cls.PRO_MIN_CONFIDENCE}%")
            print(f"   📈 Min Trend: %{cls.PRO_MIN_TREND*100:.2f}")
            print(f"   📊 Volume Spike: {cls.PRO_VOLUME_MULTIPLIER}x")
            print(f"   🔄 Pullback: %{cls.PRO_PULLBACK_MIN*100:.2f}-%{cls.PRO_PULLBACK_MAX*100:.2f}")
        else:
            print(f"\n⚡ OPTIMIZED SCALPING:")
            print(f"   📊 EMA: {cls.EMA_FAST_PERIOD}/{cls.EMA_SLOW_PERIOD}")
            print(f"   🎯 TP: %{cls.TAKE_PROFIT_PERCENT*100:.2f}")
            print(f"   🛑 SL: %{cls.STOP_LOSS_PERCENT*100:.2f}")
        
        print(f"\n💰 POZİSYON:")
        print(f"   Bakiye Kullanımı: %{cls.BALANCE_USAGE_PERCENT*100:.0f}")
        print(f"   Kaldıraç: {cls.LEVERAGE}x")
        print(f"   Min Bakiye: {cls.MIN_BALANCE_USDT} USDT")
        
        print(f"\n🛡️ RİSK YÖNETİMİ:")
        print(f"   ⏳ Trade Cooldown: {cls.TRADE_COOLDOWN_SECONDS}s")
        print(f"   🔢 Günlük Max Trade: {cls.MAX_DAILY_TRADES}")
        print(f"   ⏰ Timeframe: {cls.TIMEFRAME}")
        
        print("=" * 70)
        print("🎯 HEDEF: Günlük %5-10, Win Rate %75+")
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
