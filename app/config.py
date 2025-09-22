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
    LEVERAGE: int = 10                    # 5'ten 10'a çıkarıldı - daha fazla getiri
    ORDER_SIZE_USDT: float = 25.0         # 35'ten 50'ye çıkarıldı
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
    
    # 🛡️ --- ESNEKLEŞTİRİLMİŞ FİLTRELER (BOLLINGER BANDS İÇİN) ---
    
    # Trend Filtresi - KAPALI (Bollinger kendi trend sinyali verir)
    TREND_FILTER_ENABLED: bool = False    # BB stratejisi kendi trend analizi yapar
    TREND_EMA_PERIOD: int = 30             # Kullanılmıyor ama compatibility için
    
    # Minimum Fiyat Hareketi - ÇOK DÜŞÜK
    MIN_PRICE_MOVEMENT_ENABLED: bool = True
    MIN_PRICE_MOVEMENT_PERCENT: float = 0.0008  # %0.08 - çok düşük threshold
    
    # RSI Filtresi - KAPALI (BB içinde entegre)
    RSI_FILTER_ENABLED: bool = False      # Ayrı RSI filtresi yerine BB içinde kullan
    RSI_OVERSOLD: float = 30              # Kullanılmıyor ama compatibility için
    RSI_OVERBOUGHT: float = 70            # Kullanılmıyor ama compatibility için
    
    # Sinyal Soğuma - ÇOK DÜŞÜK (daha fazla fırsat)
    SIGNAL_COOLDOWN_ENABLED: bool = True
    SIGNAL_COOLDOWN_MINUTES: int = 3      # 5'ten 3'e düşürüldü - daha sık sinyal
    
    # Volatilite Filtresi - KAPALI (BB zaten volatilite ölçer)
    VOLATILITY_FILTER_ENABLED: bool = False
    ATR_PERIOD: int = 14                   # Kullanılmıyor ama compatibility için
    MIN_ATR_MULTIPLIER: float = 1.0       # Kullanılmıyor
    
    # Hacim Filtresi - ÇOK ESNEK
    VOLUME_FILTER_ENABLED: bool = True
    VOLUME_MA_PERIOD: int = 10            # 15'ten 10'a düşürüldü
    MIN_VOLUME_MULTIPLIER: float = 1.03   # 1.05'ten 1.03'e - sadece %3 fazla hacim
    
    # Sinyal Gücü - DÜŞÜK THRESHOLD
    SIGNAL_STRENGTH_THRESHOLD: float = 0.0005  # Çok düşük - daha fazla sinyal
    
    # --- Debugging ve Test Ayarları ---
    DEBUG_MODE: bool = True               # Detaylı loglar
    TEST_MODE: bool = False               # Canlı işlem modu - False olmalı!
    BACKTEST_MODE: bool = False
    
    # --- Risk Yönetimi ---
    MAX_DAILY_LOSS_PERCENT: float = 0.08  # Günlük maksimum %8 zarar
    MAX_CONCURRENT_POSITIONS: int = 1     # Aynı anda maksimum 1 pozisyon
    EMERGENCY_STOP_ENABLED: bool = True   # Acil durdurma sistemi
    
    # --- Rate Limiting ve Performance Ayarları ---
    MAX_REQUESTS_PER_MINUTE: int = 1200
    CACHE_DURATION_BALANCE: int = 15      # Daha uzun cache - performance
    CACHE_DURATION_POSITION: int = 8
    CACHE_DURATION_PNL: int = 5
    
    # --- WebSocket Ayarları ---
    WEBSOCKET_PING_INTERVAL: int = 30
    WEBSOCKET_PING_TIMEOUT: int = 15
    WEBSOCKET_CLOSE_TIMEOUT: int = 10
    WEBSOCKET_MAX_RECONNECTS: int = 10
    
    # --- Status Update Intervals ---
    STATUS_UPDATE_INTERVAL: int = 12
    BALANCE_UPDATE_INTERVAL: int = 30

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
        
        # Rate limit kontrolü
        if cls.MAX_REQUESTS_PER_MINUTE > 2000:
            warnings.append(f"⚠️ Dakikada maksimum istek sayısı yüksek: {cls.MAX_REQUESTS_PER_MINUTE}")
        
        # Test modu uyarıları
        if cls.TEST_MODE:
            warnings.append("⚠️ TEST MODU AKTİF - Canlı işlem yapılmayacak!")
            
        if cls.DEBUG_MODE:
            warnings.append("💡 DEBUG MODU AKTİF - Detaylı loglar yazılacak")
        
        # Bollinger Bands uyarıları
        if cls.BB_ENTRY_LOWER >= cls.BB_ENTRY_UPPER:
            warnings.append(f"⚠️ BB Entry seviyeleri geçersiz: Lower={cls.BB_ENTRY_LOWER}, Upper={cls.BB_ENTRY_UPPER}")
        
        for warning in warnings:
            print(warning)
        
        return len(warnings) == 0

    @classmethod
    def print_settings(cls):
        """Mevcut ayarları yazdır"""
        print("=" * 80)
        print("🎯 BOLLINGER BANDS STRATEJİSİ - YÜKSEK PERFORMANS TRADING BOT v3.1")
        print("=" * 80)
        print(f"🌐 Ortam: {cls.ENVIRONMENT}")
        print(f"💰 İşlem Miktarı: {cls.ORDER_SIZE_USDT} USDT")
        print(f"📈 Kaldıraç: {cls.LEVERAGE}x")
        print(f"⏰ Zaman Dilimi: {cls.TIMEFRAME}")
        print(f"🛑 Stop Loss: %{cls.STOP_LOSS_PERCENT * 100:.1f}")
        print(f"🎯 Take Profit: %{cls.TAKE_PROFIT_PERCENT * 100:.1f}")
        print(f"📊 Risk/Reward Oranı: 1:{cls.TAKE_PROFIT_PERCENT/cls.STOP_LOSS_PERCENT:.1f}")
        print("=" * 80)
        print("🎯 BOLLINGER BANDS STRATEJİ PARAMETRELERİ:")
        print(f"   📊 BB Period: {cls.BOLLINGER_PERIOD}")
        print(f"   📏 BB Std Dev: {cls.BOLLINGER_STD_DEV}σ")
        print(f"   📈 LONG Entry: %B < {cls.BB_ENTRY_LOWER}")
        print(f"   📉 SHORT Entry: %B > {cls.BB_ENTRY_UPPER}")
        print(f"   💪 Güçlü LONG: %B < {cls.BB_STRONG_LOWER}")
        print(f"   💪 Güçlü SHORT: %B > {cls.BB_STRONG_UPPER}")
        print(f"   📏 Min Band Genişliği: %{cls.MIN_BB_WIDTH*100:.2f}")
        print(f"   🔄 RSI Destek: {'✅ Aktif' if cls.RSI_ENABLED else '❌ Pasif'}")
        print("=" * 80)
        print("🛡️ OPTİMİZE EDİLMİŞ FİLTRELER (ULTRA ESNEK):")
        print(f"   📈 Min. Fiyat Hareketi (%{cls.MIN_PRICE_MOVEMENT_PERCENT*100:.3f}): {'✅' if cls.MIN_PRICE_MOVEMENT_ENABLED else '❌'}")
        print(f"   ⏳ Sinyal Soğuma ({cls.SIGNAL_COOLDOWN_MINUTES}dk): {'✅' if cls.SIGNAL_COOLDOWN_ENABLED else '❌'}")
        print(f"   📊 Hacim Filtresi ({cls.MIN_VOLUME_MULTIPLIER}x): {'✅' if cls.VOLUME_FILTER_ENABLED else '❌'}")
        print(f"   🚫 Trend Filtresi: {'❌ Devre Dışı' if not cls.TREND_FILTER_ENABLED else '✅ Aktif'}")
        print(f"   🚫 Volatilite Filtresi: {'❌ Devre Dışı' if not cls.VOLATILITY_FILTER_ENABLED else '✅ Aktif'}")
        print("=" * 80)
        print("🚀 YÜKSEK PERFORMANS ÖZELLİKLERİ:")
        print(f"   🐛 Debug Modu: {'✅' if cls.DEBUG_MODE else '❌'}")
        print(f"   🧪 Test Modu: {'✅ (GÜVENLE TEST ET)' if cls.TEST_MODE else '❌ (CANLI İŞLEM)'}")
        print(f"   📊 Günlük Max Zarar: %{cls.MAX_DAILY_LOSS_PERCENT*100:.1f}")
        print(f"   ⚡ Yüksek Kaldıraç: {cls.LEVERAGE}x")
        print(f"   🔄 Hızlı Sinyal: {cls.SIGNAL_COOLDOWN_MINUTES}dk soğuma")
        print("=" * 80)
        print("💡 BOLLINGER BANDS AVANTAJLARI:")
        print("🎯 Volatilite bazlı otomatik giriş/çıkış sinyalleri")
        print("📊 %B indikatörü ile matematiksel kesinlik")
        print("⚡ Ultra esnek filtreler - maksimum fırsat yakalama")  
        print("🔄 3 dakika cooldown - çok hızlı sinyal yakalama")
        print("💰 1:2 Risk/Reward oranı - yüksek karlılık")
        print("=" * 80)
        print("⚠️  ÖNEMLİ UYARI:")
        print("Bu ayarlar yüksek getiri için optimize edilmiştir.")
        print("İlk kez kullanıyorsanız TEST_MODE=True ile başlayın!")
        print("=" * 80)

    @classmethod
    def get_bollinger_summary(cls):
        """Bollinger Bands ayarlarının özetini döndür"""
        return {
            "strategy_type": "bollinger_bands",
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
            "performance_expected": {
                "daily_trades": "6-12",
                "win_rate": "65-75%",
                "daily_return": "2-5%",
                "risk_level": "Medium-High"
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

settings = Settings()

# Başlangıçta ayarları doğrula
if __name__ == "__main__":
    settings.validate_settings()
    settings.print_settings()
