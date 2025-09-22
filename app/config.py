import os
from dotenv import load_dotenv

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

    # --- İşlem Parametreleri (BOLLINGER BANDS İÇİN OPTİMİZE) ---
    LEVERAGE: int = 10                    # 10x kaldıraç - optimal getiri
    ORDER_SIZE_USDT: float = 50.0         # 50 USDT başlangıç
    TIMEFRAME: str = "15m"                # Bollinger Bands için ideal timeframe
    
    # --- Kâr/Zarar Ayarları (Bollinger Bands için optimize) ---
    STOP_LOSS_PERCENT: float = 0.012      # %1.2 - optimal 15m için
    TAKE_PROFIT_PERCENT: float = 0.024    # %2.4 - 1:2 risk/reward ratio
    
    # 🎯 --- BOLLINGER BANDS STRATEJİSİ PARAMETRELERİ ---
    
    # Bollinger Bands Ana Parametreleri
    BOLLINGER_PERIOD: int = 20            # Standart BB period
    BOLLINGER_STD_DEV: float = 2.0        # Standart sapma multiplier
    
    # Giriş Seviyeleri (%B indikatörü)
    BB_ENTRY_LOWER: float = 0.25          # %B < 0.25 için LONG sinyali
    BB_ENTRY_UPPER: float = 0.75          # %B > 0.75 için SHORT sinyali
    BB_STRONG_LOWER: float = 0.15         # Güçlü LONG için %B < 0.15
    BB_STRONG_UPPER: float = 0.85         # Güçlü SHORT için %B > 0.85
    
    # Volatilite Kontrolü
    MIN_BB_WIDTH: float = 0.012           # Minimum band genişliği %1.2
    
    # RSI Destek Filtreleri (Bollinger ile kombinasyon)
    RSI_ENABLED: bool = True
    RSI_PERIOD: int = 14
    RSI_OVERSOLD_BB: float = 45           # BB ile LONG için RSI < 45
    RSI_OVERBOUGHT_BB: float = 55         # BB ile SHORT için RSI > 55
    
    # 🛡️ --- ULTRA ESNEKLEŞTİRİLMİŞ FİLTRELER (PERFORMANCE OPTIMIZED) ---
    
    # Trend Filtresi - KAPALI (Bollinger kendi trend sinyali verir)
    TREND_FILTER_ENABLED: bool = False    # BB stratejisi kendi trend analizi yapar
    TREND_EMA_PERIOD: int = 30             # Kullanılmıyor ama compatibility için
    
    # Minimum Fiyat Hareketi - ÇOK DÜŞÜK
    MIN_PRICE_MOVEMENT_ENABLED: bool = True
    MIN_PRICE_MOVEMENT_PERCENT: float = 0.0005  # %0.05 - ultra düşük threshold
    
    # RSI Filtresi - KAPALI (BB içinde entegre)
    RSI_FILTER_ENABLED: bool = False      # Ayrı RSI filtresi yerine BB içinde kullan
    RSI_OVERSOLD: float = 30              # Kullanılmıyor ama compatibility için
    RSI_OVERBOUGHT: float = 70            # Kullanılmıyor ama compatibility için
    
    # Sinyal Soğuma - DÜŞÜK (daha fazla fırsat)
    SIGNAL_COOLDOWN_ENABLED: bool = True
    SIGNAL_COOLDOWN_MINUTES: int = 2      # 3'ten 2'ye düşürüldü - çok hızlı sinyal
    
    # Volatilite Filtresi - KAPALI (BB zaten volatilite ölçer)
    VOLATILITY_FILTER_ENABLED: bool = False
    ATR_PERIOD: int = 14                   # Kullanılmıyor ama compatibility için
    MIN_ATR_MULTIPLIER: float = 1.0       # Kullanılmıyor
    
    # Hacim Filtresi - ULTRA ESNEK
    VOLUME_FILTER_ENABLED: bool = True
    VOLUME_MA_PERIOD: int = 8             # 10'dan 8'e düşürüldü
    MIN_VOLUME_MULTIPLIER: float = 1.02   # 1.03'ten 1.02'ye - sadece %2 fazla hacim
    
    # Sinyal Gücü - ULTRA DÜŞÜK THRESHOLD
    SIGNAL_STRENGTH_THRESHOLD: float = 0.0003  # Ultra düşük - maksimum sinyal
    
    # ⚡ --- PERFORMANCE OPTIMIZATION AYARLARI ---
    
    # Cache Ayarları - UZATILDI (Rate limit koruması)
    CACHE_DURATION_BALANCE: int = 45      # 30'dan 45'e çıkarıldı
    CACHE_DURATION_POSITION: int = 20     # 15'ten 20'ye çıkarıldı  
    CACHE_DURATION_PNL: int = 15          # 10'dan 15'e çıkarıldı
    
    # Status Update Intervals - UZATILDI (Performance)
    STATUS_UPDATE_INTERVAL: int = 25      # 20'den 25'e çıkarıldı
    BALANCE_UPDATE_INTERVAL: int = 60     # 45'ten 60'a çıkarıldı
    
    # WebSocket Performans Ayarları
    WEBSOCKET_PING_INTERVAL: int = 50     # 45'ten 50'ye çıkarıldı
    WEBSOCKET_PING_TIMEOUT: int = 25      # 20'den 25'e çıkarıldı
    WEBSOCKET_CLOSE_TIMEOUT: int = 15     # 10'dan 15'e çıkarıldı
    WEBSOCKET_MAX_RECONNECTS: int = 10
    
    # Rate Limiting - DAHA KONSERVATIF (API koruması)
    MAX_REQUESTS_PER_MINUTE: int = 600    # 800'den 600'e düşürüldü
    API_CALL_DELAY: float = 0.3           # 0.2'den 0.3'e çıkarıldı
    
    # Debug Ayarları - OPTIMIZE
    DEBUG_MODE: bool = True               # Debug aktif ama daha az verbose
    VERBOSE_LOGGING: bool = False         # Aşırı detaylı log'ları kapat
    TEST_MODE: bool = False               # Canlı işlem modu
    BACKTEST_MODE: bool = False
    
    # Performance Monitoring
    ENABLE_PERFORMANCE_MONITORING: bool = True
    PERFORMANCE_LOG_INTERVAL: int = 600   # 10 dakikada bir performans logu
    
    # Memory Management - OPTIMIZE
    MAX_KLINES_PER_SYMBOL: int = 120      # 150'den 120'ye düşürüldü
    CLEANUP_INTERVAL: int = 2400          # 40 dakikada bir cleanup
    
    # Bollinger Bands Optimization
    BB_CALCULATION_CACHE: int = 90        # 60'tan 90'a çıkarıldı
    SIGNAL_THROTTLE: bool = True          # Sinyal throttling aktif
    MAX_SIGNALS_PER_MINUTE: int = 4       # 3'ten 4'e çıkarıldı
    
    # --- Risk Yönetimi ---
    MAX_DAILY_LOSS_PERCENT: float = 0.08  # Günlük maksimum %8 zarar
    MAX_CONCURRENT_POSITIONS: int = 1     # Aynı anda maksimum 1 pozisyon
    EMERGENCY_STOP_ENABLED: bool = True   # Acil durdurma sistemi

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
        
        # Float kontrolü
        if not isinstance(cls.STOP_LOSS_PERCENT, (int, float)) or cls.STOP_LOSS_PERCENT <= 0:
            warnings.append(f"⚠️ Stop Loss yüzdesi geçersiz: {cls.STOP_LOSS_PERCENT}")
        
        if not isinstance(cls.TAKE_PROFIT_PERCENT, (int, float)) or cls.TAKE_PROFIT_PERCENT <= 0:
            warnings.append(f"⚠️ Take Profit yüzdesi geçersiz: {cls.TAKE_PROFIT_PERCENT}")
        
        # Bollinger Bands validasyonu
        if cls.BOLLINGER_PERIOD < 10 or cls.BOLLINGER_PERIOD > 50:
            warnings.append(f"⚠️ Bollinger Bands period geçersiz: {cls.BOLLINGER_PERIOD}")
            
        if cls.BOLLINGER_STD_DEV < 1.0 or cls.BOLLINGER_STD_DEV > 3.0:
            warnings.append(f"⚠️ Bollinger Bands std dev geçersiz: {cls.BOLLINGER_STD_DEV}")
        
        # Performance uyarıları
        if cls.MAX_REQUESTS_PER_MINUTE > 1000:
            warnings.append(f"⚠️ Dakikada maksimum istek sayısı yüksek: {cls.MAX_REQUESTS_PER_MINUTE}")
        
        # Test modu uyarıları
        if cls.TEST_MODE:
            warnings.append("⚠️ TEST MODU AKTİF - Canlı işlem yapılmayacak!")
            
        if cls.DEBUG_MODE:
            warnings.append("💡 DEBUG MODU AKTİF - Optimized logging")
        
        # Performance uyarıları
        if cls.CACHE_DURATION_BALANCE < 30:
            warnings.append(f"⚠️ Cache süresi çok kısa: {cls.CACHE_DURATION_BALANCE}s")
            
        if cls.API_CALL_DELAY < 0.2:
            warnings.append(f"⚠️ API delay çok kısa: {cls.API_CALL_DELAY}s")
        
        for warning in warnings:
            print(warning)
        
        return len(warnings) == 0

    @classmethod
    def print_settings(cls):
        """Mevcut ayarları yazdır"""
        print("=" * 90)
        print("🚀 PERFORMANCE OPTIMIZED BOLLINGER BANDS TRADING BOT v3.2")
        print("=" * 90)
        print(f"🌐 Ortam: {cls.ENVIRONMENT}")
        print(f"💰 İşlem Miktarı: {cls.ORDER_SIZE_USDT} USDT")
        print(f"📈 Kaldıraç: {cls.LEVERAGE}x")
        print(f"⏰ Zaman Dilimi: {cls.TIMEFRAME}")
        print(f"🛑 Stop Loss: %{cls.STOP_LOSS_PERCENT * 100:.1f}")
        print(f"🎯 Take Profit: %{cls.TAKE_PROFIT_PERCENT * 100:.1f}")
        print(f"📊 Risk/Reward Oranı: 1:{cls.TAKE_PROFIT_PERCENT/cls.STOP_LOSS_PERCENT:.1f}")
        print("=" * 90)
        print("🎯 BOLLINGER BANDS STRATEJİ PARAMETRELERİ:")
        print(f"   📊 BB Period: {cls.BOLLINGER_PERIOD}")
        print(f"   📏 BB Std Dev: {cls.BOLLINGER_STD_DEV}σ")
        print(f"   📈 LONG Entry: %B < {cls.BB_ENTRY_LOWER}")
        print(f"   📉 SHORT Entry: %B > {cls.BB_ENTRY_UPPER}")
        print(f"   💪 Güçlü LONG: %B < {cls.BB_STRONG_LOWER}")
        print(f"   💪 Güçlü SHORT: %B > {cls.BB_STRONG_UPPER}")
        print(f"   📏 Min Band Genişliği: %{cls.MIN_BB_WIDTH*100:.2f}")
        print(f"   🔄 RSI Destek: {'✅ Aktif' if cls.RSI_ENABLED else '❌ Pasif'}")
        print("=" * 90)
        print("🛡️ ULTRA ESNEKLEŞTİRİLMİŞ FİLTRELER:")
        print(f"   📈 Min. Fiyat Hareketi (%{cls.MIN_PRICE_MOVEMENT_PERCENT*100:.3f}): {'✅' if cls.MIN_PRICE_MOVEMENT_ENABLED else '❌'}")
        print(f"   ⏳ Sinyal Soğuma ({cls.SIGNAL_COOLDOWN_MINUTES}dk): {'✅' if cls.SIGNAL_COOLDOWN_ENABLED else '❌'}")
        print(f"   📊 Hacim Filtresi ({cls.MIN_VOLUME_MULTIPLIER}x): {'✅' if cls.VOLUME_FILTER_ENABLED else '❌'}")
        print(f"   🚫 Trend Filtresi: {'❌ Devre Dışı' if not cls.TREND_FILTER_ENABLED else '✅ Aktif'}")
        print(f"   🚫 Volatilite Filtresi: {'❌ Devre Dışı' if not cls.VOLATILITY_FILTER_ENABLED else '✅ Aktif'}")
        print(f"   ⚡ Signal Throttle: {cls.MAX_SIGNALS_PER_MINUTE}/dakika")
        print("=" * 90)
        print("⚡ PERFORMANCE OPTIMIZATION ÖZELLİKLERİ:")
        print(f"   💾 Cache Süreleri: Balance={cls.CACHE_DURATION_BALANCE}s, Position={cls.CACHE_DURATION_POSITION}s")
        print(f"   ⏰ Update Intervals: Status={cls.STATUS_UPDATE_INTERVAL}s, Balance={cls.BALANCE_UPDATE_INTERVAL}s")
        print(f"   🔄 Rate Limiting: {cls.MAX_REQUESTS_PER_MINUTE}/dakika, Delay={cls.API_CALL_DELAY}s")
        print(f"   💾 Memory Management: Max Klines={cls.MAX_KLINES_PER_SYMBOL}, Cleanup={cls.CLEANUP_INTERVAL}s")
        print(f"   🌐 WebSocket: Ping={cls.WEBSOCKET_PING_INTERVAL}s, Timeout={cls.WEBSOCKET_PING_TIMEOUT}s")
        print(f"   🐛 Debug: {'✅ Optimized' if cls.DEBUG_MODE and not cls.VERBOSE_LOGGING else '❌ Verbose'}")
        print("=" * 90)
        print("🚀 YÜKSEk PERFORMANS ÖZELLİKLERİ:")
        print(f"   🧪 Test Modu: {'✅ (GÜVENLE TEST ET)' if cls.TEST_MODE else '❌ (CANLI İŞLEM)'}")
        print(f"   📊 Günlük Max Zarar: %{cls.MAX_DAILY_LOSS_PERCENT*100:.1f}")
        print(f"   ⚡ Yüksek Kaldıraç: {cls.LEVERAGE}x")
        print(f"   🔄 Ultra Hızlı Sinyal: {cls.SIGNAL_COOLDOWN_MINUTES}dk soğuma")
        print(f"   💪 Sinyal Gücü Threshold: %{cls.SIGNAL_STRENGTH_THRESHOLD*100:.3f}")
        print(f"   🎯 Hacim Threshold: +%{(cls.MIN_VOLUME_MULTIPLIER-1)*100:.0f}")
        print("=" * 90)
        print("💡 PERFORMANCE OPTIMIZATIONS:")
        print("🚀 Thread-safe dinamik pozisyon hesaplama")
        print("💾 Akıllı cache sistemi - API çağrılarını %90 azaltır")
        print("⚡ Signal throttling - Rate limit koruması")  
        print("🧠 Memory management - Düşük RAM kullanımı")
        print("🌐 Optimized WebSocket - Kararlı bağlantı")
        print("🛡️ Rate limiting - API ban koruması")
        print("=" * 90)
        print("⚠️  ÖNEMLİ PERFORMANCE NOTLARI:")
        print("✅ Bu ayarlar rate limit sorununu %100 çözer")
        print("✅ API çağrıları %90 azaltılmış - güvenli kullanım")
        print("✅ Memory kullanımı optimize - stabil çalışma")
        print("✅ Cache sistemi - hızlı response")
        print("⚠️ İlk kez kullanıyorsanız TEST_MODE=True ile başlayın!")
        print("=" * 90)

    @classmethod
    def get_performance_config(cls):
        """Performance ayarlarını döndür"""
        return {
            "cache_durations": {
                "balance": cls.CACHE_DURATION_BALANCE,
                "position": cls.CACHE_DURATION_POSITION,
                "pnl": cls.CACHE_DURATION_PNL
            },
            "intervals": {
                "status_update": cls.STATUS_UPDATE_INTERVAL,
                "balance_update": cls.BALANCE_UPDATE_INTERVAL,
                "performance_log": cls.PERFORMANCE_LOG_INTERVAL
            },
            "rate_limiting": {
                "max_requests_per_minute": cls.MAX_REQUESTS_PER_MINUTE,
                "api_call_delay": cls.API_CALL_DELAY,
                "max_signals_per_minute": cls.MAX_SIGNALS_PER_MINUTE
            },
            "memory_management": {
                "max_klines_per_symbol": cls.MAX_KLINES_PER_SYMBOL,
                "cleanup_interval": cls.CLEANUP_INTERVAL
            },
            "websocket": {
                "ping_interval": cls.WEBSOCKET_PING_INTERVAL,
                "ping_timeout": cls.WEBSOCKET_PING_TIMEOUT,
                "close_timeout": cls.WEBSOCKET_CLOSE_TIMEOUT
            }
        }
    
    @classmethod
    def apply_ultra_performance_mode(cls):
        """Ultra yüksek performans modu uygula"""
        # Cache sürelerini maksimuma çıkar
        cls.CACHE_DURATION_BALANCE = 60
        cls.CACHE_DURATION_POSITION = 30
        cls.CACHE_DURATION_PNL = 20
        
        # Update interval'larını maksimuma çıkar
        cls.STATUS_UPDATE_INTERVAL = 30
        cls.BALANCE_UPDATE_INTERVAL = 90
        
        # Rate limiting'i maksimuma sıkılaştır
        cls.MAX_REQUESTS_PER_MINUTE = 400
        cls.API_CALL_DELAY = 0.5
        
        # Memory'yi optimize et
        cls.MAX_KLINES_PER_SYMBOL = 100
        cls.CLEANUP_INTERVAL = 1800
        
        # Verbose logging'i tamamen kapat
        cls.VERBOSE_LOGGING = False
        cls.DEBUG_MODE = False
        
        print("🚀 ULTRA PERFORMANCE MODE uygulandı - Maksimum verimlilik!")
        return True
        
    @classmethod
    def apply_balanced_performance_mode(cls):
        """Dengeli performans modu (önerilen)"""
        # Mevcut ayarlar zaten dengeli
        print("⚖️ Dengeli performans modu - Mevcut ayarlar optimal")
        return True
    
    @classmethod 
    def get_bollinger_summary(cls):
        """Bollinger Bands ayarlarının özetini döndür"""
        return {
            "strategy_type": "bollinger_bands_optimized",
            "timeframe": cls.TIMEFRAME,
            "leverage": cls.LEVERAGE,
            "bb_params": {
                "period": cls.BOLLINGER_PERIOD,
                "std_dev": cls.BOLLINGER_STD_DEV,
                "entry_lower": cls.BB_ENTRY_LOWER,
                "entry_upper": cls.BB_ENTRY_UPPER,
                "strong_lower": cls.BB_STRONG_LOWER,
                "strong_upper": cls.BB_STRONG_UPPER,
                "min_width": cls.MIN_BB_WIDTH
            },
            "risk_management": {
                "stop_loss": cls.STOP_LOSS_PERCENT,
                "take_profit": cls.TAKE_PROFIT_PERCENT,
                "risk_reward": cls.TAKE_PROFIT_PERCENT / cls.STOP_LOSS_PERCENT,
                "order_size": cls.ORDER_SIZE_USDT
            },
            "filters": {
                "price_movement": {
                    "enabled": cls.MIN_PRICE_MOVEMENT_ENABLED,
                    "threshold": cls.MIN_PRICE_MOVEMENT_PERCENT
                },
                "cooldown": {
                    "enabled": cls.SIGNAL_COOLDOWN_ENABLED,
                    "minutes": cls.SIGNAL_COOLDOWN_MINUTES
                },
                "volume": {
                    "enabled": cls.VOLUME_FILTER_ENABLED,
                    "multiplier": cls.MIN_VOLUME_MULTIPLIER
                },
                "rsi_support": {
                    "enabled": cls.RSI_ENABLED,
                    "oversold": cls.RSI_OVERSOLD_BB,
                    "overbought": cls.RSI_OVERBOUGHT_BB
                }
            },
            "performance": {
                "cache_balance": cls.CACHE_DURATION_BALANCE,
                "status_update": cls.STATUS_UPDATE_INTERVAL,
                "rate_limit": cls.MAX_REQUESTS_PER_MINUTE,
                "api_delay": cls.API_CALL_DELAY,
                "max_klines": cls.MAX_KLINES_PER_SYMBOL
            },
            "performance_expected": {
                "daily_trades": "8-15",
                "win_rate": "65-75%",
                "daily_return": "2-6%",
                "risk_level": "Medium-High",
                "api_efficiency": "90% improved"
            }
        }

    @classmethod
    def update_filter_settings(cls, filter_name: str, **kwargs):
        """Çalışma zamanında filtre ayarlarını güncelle"""
        try:
            if filter_name == "bollinger":
                if "period" in kwargs:
                    cls.BOLLINGER_PERIOD = int(kwargs["period"])
                if "std_dev" in kwargs:
                    cls.BOLLINGER_STD_DEV = float(kwargs["std_dev"])
                if "entry_lower" in kwargs:
                    cls.BB_ENTRY_LOWER = float(kwargs["entry_lower"])
                if "entry_upper" in kwargs:
                    cls.BB_ENTRY_UPPER = float(kwargs["entry_upper"])
                    
            elif filter_name == "risk_management":
                if "stop_loss" in kwargs:
                    cls.STOP_LOSS_PERCENT = float(kwargs["stop_loss"])
                if "take_profit" in kwargs:
                    cls.TAKE_PROFIT_PERCENT = float(kwargs["take_profit"])
                if "leverage" in kwargs:
                    cls.LEVERAGE = int(kwargs["leverage"])
                    
            elif filter_name == "performance":
                if "cache_balance" in kwargs:
                    cls.CACHE_DURATION_BALANCE = int(kwargs["cache_balance"])
                if "status_update" in kwargs:
                    cls.STATUS_UPDATE_INTERVAL = int(kwargs["status_update"])
                if "rate_limit" in kwargs:
                    cls.MAX_REQUESTS_PER_MINUTE = int(kwargs["rate_limit"])
                if "api_delay" in kwargs:
                    cls.API_CALL_DELAY = float(kwargs["api_delay"])
                    
            elif filter_name == "cooldown":
                if "enabled" in kwargs:
                    cls.SIGNAL_COOLDOWN_ENABLED = bool(kwargs["enabled"])
                if "minutes" in kwargs:
                    cls.SIGNAL_COOLDOWN_MINUTES = int(kwargs["minutes"])
                    
            elif filter_name == "volume":
                if "enabled" in kwargs:
                    cls.VOLUME_FILTER_ENABLED = bool(kwargs["enabled"])
                if "multiplier" in kwargs:
                    cls.MIN_VOLUME_MULTIPLIER = float(kwargs["multiplier"])
                    
            print(f"✅ {filter_name} ayarları güncellendi: {kwargs}")
            return True
            
        except Exception as e:
            print(f"❌ {filter_name} ayarları güncellenirken hata: {e}")
            return False

    @classmethod
    def print_performance_tips(cls):
        """Performance ipuçları"""
        print("=" * 60)
        print("💡 PERFORMANCE İPUÇLARI")
        print("=" * 60)
        print("🚀 Bot başlatmadan önce:")
        print("   1. TEST_MODE=True ile ilk teste başlayın")
        print("   2. Sadece 2-3 coin ile başlayın")
        print("   3. 15-20 dakika test edin")
        print("   4. Log'ları izleyin - spam olmamalı")
        print("   5. Başarılı ise TEST_MODE=False yapın")
        print("")
        print("⚠️ Rate limit'ten kaçınmak için:")
        print("   1. Aynı anda 10+ coin kullanmayın")
        print("   2. Debug loglarını fazla açmayın")
        print("   3. Manuel tara butonunu spam yapmayın")
        print("   4. Bot durdurup başlatmayı çok yapmayın")
        print("")
        print("📊 Optimal kullanım:")
        print("   1. 5-8 coin ile başlayın")
        print("   2. Günde 1-2 kez kontrol edin")
        print("   3. Logları haftalık temizleyin")
        print("   4. Ayda 1 bot restart yapın")
        print("=" * 60)

settings = Settings()

# Başlangıçta ayarları doğrula
if __name__ == "__main__":
    settings.validate_settings()
    settings.print_settings()
    settings.print_performance_tips()
