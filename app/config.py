# app/config.py - KAR ODAKLI AYARLAR v2.0

import os
from dotenv import load_dotenv

load_dotenv()

class ProfitOptimizedSettings:
    """
    💰 KAR ODAKLI Trading Bot Ayarları v2.0
    - Bakiyenin %90'ı kullanılır
    - 1 dakikalık timeframe (SIK İŞLEM)
    - Optimize TP/SL oranları
    - Whipsaw koruması KAPALI (daha fazla fırsat)
    - Hedef: Günlük %5-10 kar
    """
    
    # --- Temel Ayarlar ---
    API_KEY: str = os.getenv("BINANCE_API_KEY")
    API_SECRET: str = os.getenv("BINANCE_API_SECRET")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "LIVE")
    BOT_USERNAME: str = os.getenv("BOT_USERNAME", "admin")
    BOT_PASSWORD: str = os.getenv("BOT_PASSWORD", "changeme123")
    BASE_URL = "https://fapi.binance.com" if os.getenv("ENVIRONMENT", "TEST") == "LIVE" else "https://testnet.binancefuture.com"
    WEBSOCKET_URL = "wss://fstream.binance.com" if os.getenv("ENVIRONMENT", "TEST") == "LIVE" else "wss://stream.binancefuture.com"

    # --- 🤖 GEMİNİ AI AYARLARI ---
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY")
    GEMINI_ENABLED: bool = bool(os.getenv("GEMINI_API_KEY"))
    GEMINI_MIN_CONFIDENCE: int = 65  # ✅ Daha düşük (daha fazla işlem)
    GEMINI_TIMEOUT: int = 10

    # --- 💰 KAR ODAKLI İşlem Parametreleri ---
    LEVERAGE: int = 15                      # ✅ 15x kaldıraç (kar potansiyeli yüksek)
    ORDER_SIZE_USDT: float = 100.0          # ✅ Bu değer dinamik hesaplanacak
    TIMEFRAME: str = "1m"                   # ✅ 1 dakika (SIK İŞLEM)
    
    # --- 🎯 OPTIMIZE TP/SL Ayarları ---
    STOP_LOSS_PERCENT: float = 0.004        # ✅ %0.4 stop loss (sıkı)
    TAKE_PROFIT_PERCENT: float = 0.012      # ✅ %1.2 take profit (optimize R/R 1:3)
    
    # --- 📈 OPTIMIZE EMA Parametreleri ---
    EMA_FAST_PERIOD: int = 7                # ✅ Daha hızlı EMA (7)
    EMA_SLOW_PERIOD: int = 20               # ✅ Yavaş EMA (20)
    
    # --- ⚡ WHIPSAW KORUMA (KAPALI) ---
    SIGNAL_COOLDOWN_MINUTES: int = 1        # ✅ Sadece 1 dakika (daha fazla işlem)
    MIN_EMA_SPREAD_PERCENT: float = 0.0003  # ✅ Çok düşük (%0.03)
    CONFIRM_PRICE_ABOVE_EMA: bool = False   # ✅ KAPALI (daha fazla sinyal)
    
    # --- 🚀 API RATE LIMITING ---
    API_CALL_DELAY: float = 0.2             # ✅ 200ms (hızlı)
    RATE_LIMIT_BUFFER: float = 0.1
    MAX_API_CALLS_PER_MINUTE: int = 60
    
    # --- 💾 Cache ve Performance ---
    CACHE_DURATION_BALANCE: int = 30
    CACHE_DURATION_POSITION: int = 20
    CACHE_DURATION_PRICE: int = 5
    
    # --- 📊 Status Update Intervals ---
    STATUS_UPDATE_INTERVAL: int = 15
    BALANCE_UPDATE_INTERVAL: int = 30
    POSITION_UPDATE_INTERVAL: int = 20
    
    # --- 🌐 WebSocket Ayarları ---
    WEBSOCKET_PING_INTERVAL: int = 30
    WEBSOCKET_PING_TIMEOUT: int = 15
    WEBSOCKET_CLOSE_TIMEOUT: int = 10
    WEBSOCKET_RECONNECT_DELAY: int = 3
    
    # --- 🔍 Debug Ayarları ---
    DEBUG_MODE: bool = True
    TEST_MODE: bool = False                 # ✅ CANLI İŞLEM
    VERBOSE_LOGGING: bool = True            # ✅ Detaylı log
    
    # --- 💾 Memory Management ---
    MAX_KLINES_PER_SYMBOL: int = 50         # ✅ 50 mum yeterli
    MAX_CACHED_SYMBOLS: int = 5
    CLEANUP_INTERVAL: int = 180
    
    # --- 💰 Risk Yönetimi ---
    MAX_CONCURRENT_POSITIONS: int = 1
    MAX_DAILY_TRADES: int = 30              # ✅ Günde 30 işlem (1m için normal)
    MIN_BALANCE_USDT: float = 50.0
    MAX_POSITION_SIZE_PERCENT: float = 0.90 # ✅ %90 kullanım
    
    # --- 🎯 SİNYAL KALİTE FİLTRELERİ (KAPALI) ---
    ENABLE_QUALITY_FILTERS: bool = False    # ✅ KAPALI (daha fazla sinyal)
    MIN_VOLUME_MULTIPLIER: float = 1.0      # ✅ Volume kontrolü yok
    MIN_CANDLE_BODY_PERCENT: float = 0.1
    TREND_CONFIRMATION_REQUIRED: bool = False
    
    # --- 🔌 CONNECTION SETTINGS ---
    CONNECTION_TIMEOUT: int = 20
    READ_TIMEOUT: int = 40
    MAX_RETRIES: int = 3
    BACKOFF_FACTOR: float = 0.3
    
    @classmethod
    def validate_settings_optimized(cls):
        """✅ Ayar doğrulama"""
        warnings = []
        errors = []
        
        if not cls.API_KEY or not cls.API_SECRET:
            errors.append("❌ KRİTİK: BINANCE_API_KEY veya BINANCE_API_SECRET ayarlanmamış!")
        
        if not cls.GEMINI_API_KEY:
            warnings.append("⚠️ UYARI: GEMINI_API_KEY ayarlanmamış.")
            cls.GEMINI_ENABLED = False
        
        if cls.LEVERAGE > 20:
            warnings.append(f"⚠️ RİSK: {cls.LEVERAGE}x kaldıraç çok yüksek!")
        
        if cls.EMA_FAST_PERIOD >= cls.EMA_SLOW_PERIOD:
            errors.append(f"❌ HATA: Hızlı EMA yavaş EMA'dan küçük olmalı")
        
        for error in errors:
            print(error)
        for warning in warnings:
            print(warning)
        
        if errors:
            print("❌ KRİTİK HATALAR VAR!")
            return False
        
        print("✅ Ayar doğrulama tamamlandı.")
        return True

    @classmethod
    def print_settings_optimized(cls):
        """✅ Ayar görüntüleme"""
        print("=" * 70)
        print("💰 KAR ODAKLI EMA CROSS TRADING BOT v2.0")
        print("=" * 70)
        print(f"🌐 Ortam: {cls.ENVIRONMENT}")
        print(f"🧪 Test Modu: {'AÇIK' if cls.TEST_MODE else 'KAPALI (CANLI İŞLEM) ⚠️'}")
        print(f"💰 Pozisyon Boyutu: BAKİYENİN %{cls.MAX_POSITION_SIZE_PERCENT*100:.0f}'i")
        print(f"📈 Kaldıraç: {cls.LEVERAGE}x ⚡")
        print(f"⏰ Timeframe: {cls.TIMEFRAME} (SIK İŞLEM)")
        print("=" * 70)
        print("🎯 OPTIMIZE STRATEJI:")
        print(f"   📈 EMA Fast: {cls.EMA_FAST_PERIOD}")
        print(f"   📊 EMA Slow: {cls.EMA_SLOW_PERIOD}")
        print(f"   ⚡ Cooldown: {cls.SIGNAL_COOLDOWN_MINUTES} dakika (HIZLI)")
        print(f"   🔍 Kalite Filtreleri: {'AKTİF' if cls.ENABLE_QUALITY_FILTERS else 'KAPALI ⚠️'}")
        print("=" * 70)
        print("💰 TP/SL AYARLARI:")
        print(f"   📉 Stop Loss: %{cls.STOP_LOSS_PERCENT*100:.1f}")
        print(f"   📈 Take Profit: %{cls.TAKE_PROFIT_PERCENT*100:.1f}")
        print(f"   🎯 Risk/Reward: 1:{cls.TAKE_PROFIT_PERCENT/cls.STOP_LOSS_PERCENT:.1f}")
        print("=" * 70)
        print("🛡️ RİSK YÖNETİMİ:")
        print(f"   🎯 Max Pozisyon: {cls.MAX_CONCURRENT_POSITIONS}")
        print(f"   📊 Max Günlük İşlem: {cls.MAX_DAILY_TRADES}")
        print(f"   💰 Max Pozisyon: %{cls.MAX_POSITION_SIZE_PERCENT*100}")
        print(f"   🚨 Min Bakiye: {cls.MIN_BALANCE_USDT} USDT")
        print("=" * 70)
        print("📊 BEKLENEN PERFORMANS:")
        print("   📈 Günlük Kar Hedefi: %5-10")
        print("   🎯 İşlem Sıklığı: Yüksek (1m timeframe)")
        print("   ⚡ Sinyal Üretimi: Agresif")
        print("   🛡️ Risk Seviyesi: ORTA-YÜKSEK 🟡")
        print("=" * 70)
        print("⚠️ ÖNEMLİ UYARILAR:")
        print("   🔴 15x kaldıraç kullanılıyor - dikkatli olun!")
        print("   🔴 %90 bakiye kullanılıyor - yeterli bakiye gerekli!")
        print("   🔴 Kalite filtreleri KAPALI - daha fazla risk!")
        print("   🟢 R/R 1:3 optimize edildi - iyi kazanç potansiyeli")
        print("=" * 70)

    @classmethod  
    def get_api_rate_config(cls) -> dict:
        return {
            "api_call_delay": cls.API_CALL_DELAY,
            "rate_limit_buffer": cls.RATE_LIMIT_BUFFER, 
            "max_calls_per_minute": cls.MAX_API_CALLS_PER_MINUTE,
            "connection_timeout": cls.CONNECTION_TIMEOUT,
            "read_timeout": cls.READ_TIMEOUT,
            "max_retries": cls.MAX_RETRIES,
            "backoff_factor": cls.BACKOFF_FACTOR
        }
        
    @classmethod
    def get_trading_config(cls) -> dict:
        return {
            "ema_fast": cls.EMA_FAST_PERIOD,
            "ema_slow": cls.EMA_SLOW_PERIOD,
            "timeframe": cls.TIMEFRAME,
            "leverage": cls.LEVERAGE,
            "stop_loss_percent": cls.STOP_LOSS_PERCENT,
            "take_profit_percent": cls.TAKE_PROFIT_PERCENT,
            "signal_cooldown_minutes": cls.SIGNAL_COOLDOWN_MINUTES,
            "min_ema_spread": cls.MIN_EMA_SPREAD_PERCENT,
            "enable_quality_filters": cls.ENABLE_QUALITY_FILTERS,
            "gemini_ai_enabled": cls.GEMINI_ENABLED,
            "gemini_min_confidence": cls.GEMINI_MIN_CONFIDENCE
        }

# Optimized settings instance
settings = ProfitOptimizedSettings()

if __name__ == "__main__":
    if settings.validate_settings_optimized():
        settings.print_settings_optimized()
    else:
        print("❌ Ayar hatalarını düzeltin!")
