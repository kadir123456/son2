# app/config.py - OPTIMIZE EDİLMİŞ ve GÜVENLİ Configuration

import os
from dotenv import load_dotenv

load_dotenv()

class OptimizedSettings:
    """
    ✅ OPTIMIZE EDİLMİŞ Trading Bot Ayarları v1.2
    - API Rate Limiting optimize edildi
    - Güvenli işlem parametreleri  
    - Memory optimize edildi
    - Whipsaw koruması eklendi
    """
    
    # --- Temel Ayarlar ---
    API_KEY: str = os.getenv("BINANCE_API_KEY")
    API_SECRET: str = os.getenv("BINANCE_API_SECRET")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "LIVE")
    BOT_USERNAME: str = os.getenv("BOT_USERNAME", "admin")
    BOT_PASSWORD: str = os.getenv("BOT_PASSWORD", "changeme123")
    BASE_URL = "https://fapi.binance.com" if os.getenv("ENVIRONMENT", "TEST") == "LIVE" else "https://testnet.binancefuture.com"
    WEBSOCKET_URL = "wss://fstream.binance.com" if os.getenv("ENVIRONMENT", "TEST") == "LIVE" else "wss://stream.binancefuture.com"

    # --- OPTIMIZE EDİLMİŞ İşlem Parametreleri ---
    LEVERAGE: int = 10                      # ✅ Güvenli 10x kaldıraç
    ORDER_SIZE_USDT: float = 50.0          # ✅ 50 USDT başlangıç boyutu
    TIMEFRAME: str = "15m"                 # ✅ 15m optimal timeframe
    
    # --- GÜVENLI TP/SL Ayarları ---
    STOP_LOSS_PERCENT: float = 0.008       # ✅ %0.8 stop loss (güvenli)
    TAKE_PROFIT_PERCENT: float = 0.015     # ✅ %1.5 take profit (optimize)
    
    # --- OPTIMIZE EMA Parametreleri ---
    EMA_FAST_PERIOD: int = 9               # ✅ Hızlı EMA
    EMA_SLOW_PERIOD: int = 21              # ✅ Yavaş EMA
    
    # --- ✅ YENİ: WHIPSAW KORUMA AYARLARI ---
    SIGNAL_COOLDOWN_MINUTES: int = 5       # 5 dakika sinyal soğuma
    MIN_EMA_SPREAD_PERCENT: float = 0.001  # Min %0.1 EMA farkı
    CONFIRM_PRICE_ABOVE_EMA: bool = True   # Fiyat EMA üzerinde olmalı
    
    # --- ✅ OPTIMIZE EDİLMİŞ API RATE LIMITING ---
    API_CALL_DELAY: float = 0.3             # ✅ 300ms güvenli delay
    RATE_LIMIT_BUFFER: float = 0.2          # ✅ 200ms buffer
    MAX_API_CALLS_PER_MINUTE: int = 50      # ✅ Dakika başına max 50 istek
    
    # --- ✅ OPTIMIZE Cache ve Performance ---
    CACHE_DURATION_BALANCE: int = 45        # ✅ 45 saniye bakiye cache
    CACHE_DURATION_POSITION: int = 30       # ✅ 30 saniye pozisyon cache
    CACHE_DURATION_PRICE: int = 10          # ✅ 10 saniye fiyat cache
    
    # --- ✅ OPTIMIZE Status Update Intervals ---
    STATUS_UPDATE_INTERVAL: int = 20        # ✅ 20 saniye status update
    BALANCE_UPDATE_INTERVAL: int = 45       # ✅ 45 saniye bakiye update
    POSITION_UPDATE_INTERVAL: int = 30      # ✅ 30 saniye pozisyon update
    
    # --- ✅ OPTIMIZE WebSocket Ayarları ---
    WEBSOCKET_PING_INTERVAL: int = 30       # ✅ 30s ping
    WEBSOCKET_PING_TIMEOUT: int = 15        # ✅ 15s timeout
    WEBSOCKET_CLOSE_TIMEOUT: int = 10       # ✅ 10s close timeout
    WEBSOCKET_RECONNECT_DELAY: int = 5      # ✅ 5s reconnect delay
    
    # --- ✅ GÜVENLI Debug Ayarları ---
    DEBUG_MODE: bool = True                 # ✅ Debug aktif
    TEST_MODE: bool = False                 # ✅ Canlı işlem (False = LIVE)
    VERBOSE_LOGGING: bool = False           # ✅ Az log (performance için)
    
    # --- ✅ OPTIMIZE Memory Management ---
    MAX_KLINES_PER_SYMBOL: int = 100        # ✅ 100 mum yeterli EMA için
    MAX_CACHED_SYMBOLS: int = 20            # ✅ Max 20 symbol cache
    CLEANUP_INTERVAL: int = 300             # ✅ 5 dakikada bir cache cleanup
    
    # --- ✅ GÜVENLI Risk Yönetimi ---
    MAX_CONCURRENT_POSITIONS: int = 1       # ✅ Sadece 1 pozisyon
    MAX_DAILY_TRADES: int = 10              # ✅ Günde max 10 işlem
    MIN_BALANCE_USDT: float = 10.0          # ✅ Min 10 USDT bakiye
    MAX_POSITION_SIZE_PERCENT: float = 0.85 # ✅ Bakiyenin max %85'i
    
    # --- ✅ YENİ: SINYAL KALİTE FİLTRELERİ ---
    ENABLE_QUALITY_FILTERS: bool = True     # Kalite filtreleri aktif
    MIN_VOLUME_MULTIPLIER: float = 1.2      # Min %120 hacim artışı
    MIN_CANDLE_BODY_PERCENT: float = 0.3    # Min %0.3 candle body
    TREND_CONFIRMATION_REQUIRED: bool = True # Trend teyidi gerekli
    
    # --- ✅ OPTIMIZE CONNECTION SETTINGS ---
    CONNECTION_TIMEOUT: int = 30            # 30s connection timeout
    READ_TIMEOUT: int = 60                  # 60s read timeout
    MAX_RETRIES: int = 3                    # Max 3 retry
    BACKOFF_FACTOR: float = 0.5             # Exponential backoff
    
    @classmethod
    def validate_settings_optimized(cls):
        """✅ OPTIMIZE EDİLMİŞ ayar doğrulama"""
        warnings = []
        errors = []
        
        # Kritik ayar kontrolleri
        if not cls.API_KEY or not cls.API_SECRET:
            errors.append("❌ KRİTİK: BINANCE_API_KEY veya BINANCE_API_SECRET ayarlanmamış!")
        
        # Güvenlik kontrolleri
        if cls.LEVERAGE < 1 or cls.LEVERAGE > 20:
            warnings.append(f"⚠️ UYARI: Kaldıraç değeri güvenli aralığın dışında: {cls.LEVERAGE}")
        
        if cls.LEVERAGE > 15:
            warnings.append(f"⚠️ RİSK: {cls.LEVERAGE}x kaldıraç yüksek risk taşır!")
        
        # EMA validasyonu
        if cls.EMA_FAST_PERIOD >= cls.EMA_SLOW_PERIOD:
            errors.append(f"❌ HATA: Hızlı EMA yavaş EMA'dan küçük olmalı: {cls.EMA_FAST_PERIOD} >= {cls.EMA_SLOW_PERIOD}")
        
        # TP/SL validasyonu
        if cls.STOP_LOSS_PERCENT > 0.02:  # %2'den fazla
            warnings.append(f"⚠️ UYARI: Stop loss çok geniş: %{cls.STOP_LOSS_PERCENT*100:.1f}")
            
        if cls.TAKE_PROFIT_PERCENT < cls.STOP_LOSS_PERCENT:
            warnings.append(f"⚠️ UYARI: Take profit stop loss'dan küçük!")
            
        # Risk yönetimi kontrolleri
        if cls.MAX_POSITION_SIZE_PERCENT > 0.9:
            warnings.append(f"⚠️ RİSK: Pozisyon boyutu çok yüksek: %{cls.MAX_POSITION_SIZE_PERCENT*100}")
            
        # API rate limit kontrolleri
        if cls.API_CALL_DELAY < 0.2:
            warnings.append(f"⚠️ RİSK: API delay çok düşük: {cls.API_CALL_DELAY}s")
            
        if cls.MAX_API_CALLS_PER_MINUTE > 60:
            warnings.append(f"⚠️ RİSK: Dakika başına çok fazla API çağrısı: {cls.MAX_API_CALLS_PER_MINUTE}")
        
        # Sonuçları yazdır
        for error in errors:
            print(error)
        for warning in warnings:
            print(warning)
        
        if errors:
            print("❌ KRİTİK HATALAR VAR! Bot çalışmayabilir.")
            return False
        
        if warnings:
            print("⚠️ UYARILAR mevcut, dikkatli kullanın.")
            
        print("✅ Ayar doğrulama tamamlandı.")
        return True

    @classmethod
    def print_settings_optimized(cls):
        """✅ OPTIMIZE EDİLMİŞ ayar görüntüleme"""
        print("=" * 65)
        print("🎯 OPTIMIZE EDİLMİŞ EMA CROSS TRADING BOT v1.2")
        print("=" * 65)
        print(f"🌐 Ortam: {cls.ENVIRONMENT}")
        print(f"🧪 Test Modu: {'AÇIK' if cls.TEST_MODE else 'KAPALI (CANLI İŞLEM)'}")
        print(f"💰 İşlem Miktarı: {cls.ORDER_SIZE_USDT} USDT")
        print(f"📈 Kaldıraç: {cls.LEVERAGE}x")
        print(f"⏰ Zaman Dilimi: {cls.TIMEFRAME}")
        print("=" * 65)
        print("🎯 OPTIMIZE EMA STRATEJİSİ:")
        print(f"   📈 Hızlı EMA: {cls.EMA_FAST_PERIOD}")
        print(f"   📊 Yavaş EMA: {cls.EMA_SLOW_PERIOD}")
        print(f"   🛡️ Sinyal Soğuma: {cls.SIGNAL_COOLDOWN_MINUTES} dakika")
        print(f"   📏 Min EMA Farkı: %{cls.MIN_EMA_SPREAD_PERCENT*100}")
        print("=" * 65)
        print("💰 GÜVENLI TP/SL AYARLARI:")
        print(f"   📉 Stop Loss: %{cls.STOP_LOSS_PERCENT*100:.1f}")
        print(f"   📈 Take Profit: %{cls.TAKE_PROFIT_PERCENT*100:.1f}")
        print(f"   🎯 Risk/Reward: 1:{cls.TAKE_PROFIT_PERCENT/cls.STOP_LOSS_PERCENT:.1f}")
        print("=" * 65)
        print("⚡ OPTIMIZE PERFORMANS AYARLARI:")
        print(f"   🔄 API Delay: {cls.API_CALL_DELAY}s")
        print(f"   📊 Status Update: {cls.STATUS_UPDATE_INTERVAL}s")
        print(f"   💾 Bakiye Cache: {cls.CACHE_DURATION_BALANCE}s")
        print(f"   📈 Max Klines: {cls.MAX_KLINES_PER_SYMBOL}")
        print("=" * 65)
        print("✅ YENİ ÖZELLİKLER:")
        print("   ✅ NaN safe EMA hesaplamaları")
        print("   ✅ Dictionary iteration hatası düzeltildi")
        print("   ✅ Whipsaw koruması aktif")
        print("   ✅ API rate limiting optimize edildi") 
        print("   ✅ Memory kullanımı optimize edildi")
        print("   ✅ Güvenli pozisyon yönetimi")
        print("   ✅ Kaliteli sinyal filtreleme")
        print("=" * 65)
        print("🛡️ RİSK YÖNETİMİ:")
        print(f"   🎯 Max Pozisyon: {cls.MAX_CONCURRENT_POSITIONS}")
        print(f"   📊 Max Günlük İşlem: {cls.MAX_DAILY_TRADES}")
        print(f"   💰 Max Pozisyon Boyutu: %{cls.MAX_POSITION_SIZE_PERCENT*100}")
        print(f"   🚨 Min Bakiye: {cls.MIN_BALANCE_USDT} USDT")
        print("=" * 65)
        
        # Risk seviyesi belirleme
        risk_score = 0
        if cls.LEVERAGE > 15: risk_score += 2
        if cls.STOP_LOSS_PERCENT > 0.015: risk_score += 1  
        if cls.MAX_POSITION_SIZE_PERCENT > 0.9: risk_score += 1
        
        risk_level = "DÜŞÜk" if risk_score == 0 else "ORTA" if risk_score <= 2 else "YÜKSEK"
        risk_color = "🟢" if risk_score == 0 else "🟡" if risk_score <= 2 else "🔴"
        
        print(f"📊 GENEL RİSK SEVİYESİ: {risk_color} {risk_level}")
        print("=" * 65)
        
    @classmethod  
    def get_api_rate_config(cls) -> dict:
        """✅ API rate limiting konfigürasyonu"""
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
        """✅ Trading konfigürasyonu"""
        return {
            "ema_fast": cls.EMA_FAST_PERIOD,
            "ema_slow": cls.EMA_SLOW_PERIOD,
            "timeframe": cls.TIMEFRAME,
            "leverage": cls.LEVERAGE,
            "stop_loss_percent": cls.STOP_LOSS_PERCENT,
            "take_profit_percent": cls.TAKE_PROFIT_PERCENT,
            "signal_cooldown_minutes": cls.SIGNAL_COOLDOWN_MINUTES,
            "min_ema_spread": cls.MIN_EMA_SPREAD_PERCENT,
            "enable_quality_filters": cls.ENABLE_QUALITY_FILTERS
        }

# Optimized settings instance
settings = OptimizedSettings()

# Başlangıçta ayarları doğrula ve göster
if __name__ == "__main__":
    if settings.validate_settings_optimized():
        settings.print_settings_optimized()
    else:
        print("❌ Ayar hatalarını düzeltin!")
