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

    # --- İşlem Parametreleri ---
    LEVERAGE: int = 5
    ORDER_SIZE_USDT: float = 35.0
    TIMEFRAME: str = "15m"
    
    # --- Kâr/Zarar Ayarları (Stop Loss ve Take Profit) ---
    STOP_LOSS_PERCENT: float = 0.007   # %0.9 Zarar Durdur
    TAKE_PROFIT_PERCENT: float = 0.01 # %1.0 Kar Al
    
    # 🛡️ --- DÜZELTME: DAHA ESNEK SAHTE SİNYAL KORUMASI AYARLARI ---
    
    # Trend Filtresi - DAHA ESNEK
    TREND_FILTER_ENABLED: bool = True
    TREND_EMA_PERIOD: int = 30          # 50'den 30'a düşürüldü - daha hızlı trend tespiti
    
    # Minimum Fiyat Hareketi Filtresi - DAHA ESNEK  
    MIN_PRICE_MOVEMENT_ENABLED: bool = True
    MIN_PRICE_MOVEMENT_PERCENT: float = 0.0015  # %0.3'ten %0.15'e düşürüldü
    
    # RSI Filtresi - DAHA ESNEK (Aşırı alım/satım koruması)
    RSI_FILTER_ENABLED: bool = True
    RSI_PERIOD: int = 14
    RSI_OVERSOLD: float = 25.0         # 30'dan 25'e düşürüldü - daha az katı
    RSI_OVERBOUGHT: float = 75.0       # 70'ten 75'e çıkarıldı - daha az katı
    
    # Sinyal Soğuma Süresi - DAHA ESNEK (Whipsaw koruması)
    SIGNAL_COOLDOWN_ENABLED: bool = True
    SIGNAL_COOLDOWN_MINUTES: int = 8   # 15'ten 8'e düşürüldü - daha sık sinyal
    
    # Volatilite Filtresi - DAHA ESNEK
    VOLATILITY_FILTER_ENABLED: bool = True
    ATR_PERIOD: int = 14
    MIN_ATR_MULTIPLIER: float = 1.0     # 1.5'ten 1.0'a düşürüldü - daha az volatilite gerekli
    
    # Hacim Filtresi - DAHA ESNEK
    VOLUME_FILTER_ENABLED: bool = True
    VOLUME_MA_PERIOD: int = 15          # 20'den 15'e düşürüldü
    MIN_VOLUME_MULTIPLIER: float = 1.1  # 1.2'den 1.1'e düşürüldü - %10 fazla hacim yeterli
    
    # Sinyal Gücü Threshold - DAHA ESNEK
    SIGNAL_STRENGTH_THRESHOLD: float = 0.0001  # %0.02'den %0.01'e düşürüldü
    
    # --- DÜZELTME: Debugging ve Test Ayarları ---
    DEBUG_MODE: bool = True  # Detaylı loglar için
    TEST_MODE: bool = False  # Test modu (canlı işlem yapmaz)
    BACKTEST_MODE: bool = False  # Backtest modu
    
    # --- DÜZELTME: Gelişmiş Risk Yönetimi ---
    MAX_DAILY_LOSS_PERCENT: float = 0.05  # Günlük maksimum %5 zarar
    MAX_CONCURRENT_POSITIONS: int = 1      # Aynı anda maksimum pozisyon sayısı
    EMERGENCY_STOP_ENABLED: bool = True    # Acil durdurma sistemi
    
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
    def validate_settings(cls):
        """Ayarları doğrula ve gerekirse uyar"""
        warnings = []
        
        if not cls.API_KEY or not cls.API_SECRET:
            warnings.append("⚠️ BINANCE_API_KEY veya BINANCE_API_SECRET ayarlanmamış!")
        
        if cls.LEVERAGE < 1 or cls.LEVERAGE > 125:
            warnings.append(f"⚠️ Kaldıraç değeri geçersiz: {cls.LEVERAGE}. 1-125 arası olmalı.")
        
        if cls.ORDER_SIZE_USDT < 5:
            warnings.append(f"⚠️ İşlem miktarı çok düşük: {cls.ORDER_SIZE_USDT}. Minimum 5 USDT önerilir.")
        
        # Float kontrolü ekle
        if not isinstance(cls.STOP_LOSS_PERCENT, (int, float)) or cls.STOP_LOSS_PERCENT <= 0 or cls.STOP_LOSS_PERCENT >= 1:
            warnings.append(f"⚠️ Stop Loss yüzdesi geçersiz: {cls.STOP_LOSS_PERCENT}. 0-1 arası float olmalı.")
        
        if not isinstance(cls.TAKE_PROFIT_PERCENT, (int, float)) or cls.TAKE_PROFIT_PERCENT <= 0 or cls.TAKE_PROFIT_PERCENT >= 1:
            warnings.append(f"⚠️ Take Profit yüzdesi geçersiz: {cls.TAKE_PROFIT_PERCENT}. 0-1 arası float olmalı.")
        
        # Rate limit kontrolü
        if cls.MAX_REQUESTS_PER_MINUTE > 2000:
            warnings.append(f"⚠️ Dakikada maksimum istek sayısı yüksek: {cls.MAX_REQUESTS_PER_MINUTE}. Rate limit riski!")
        
        # DÜZELTME: Sahte sinyal koruması validasyonu - daha esnek
        if cls.MIN_PRICE_MOVEMENT_PERCENT > 0.005:  # %0.5'ten fazla ise uyar
            warnings.append(f"⚠️ Minimum fiyat hareketi yüksek olabilir: %{cls.MIN_PRICE_MOVEMENT_PERCENT*100}")
        
        if cls.SIGNAL_COOLDOWN_MINUTES > 30:  # 30 dakikadan fazla ise uyar
            warnings.append(f"⚠️ Sinyal soğuma süresi uzun olabilir: {cls.SIGNAL_COOLDOWN_MINUTES} dakika")
        
        if cls.MIN_VOLUME_MULTIPLIER > 1.5:
            warnings.append(f"⚠️ Hacim filtresi çok katı olabilir: {cls.MIN_VOLUME_MULTIPLIER}x")
            
        if cls.MIN_ATR_MULTIPLIER > 2.0:
            warnings.append(f"⚠️ Volatilite filtresi çok katı olabilir: {cls.MIN_ATR_MULTIPLIER}x")
        
        # DÜZELTME: Test modu uyarıları
        if cls.TEST_MODE:
            warnings.append("⚠️ TEST MODU AKTİF - Canlı işlem yapılmayacak!")
            
        if cls.DEBUG_MODE:
            warnings.append("💡 DEBUG MODU AKTİF - Detaylı loglar yazılacak")
        
        for warning in warnings:
            print(warning)
        
        return len(warnings) == 0

    @classmethod
    def print_settings(cls):
        """Mevcut ayarları yazdır"""
        print("=" * 70)
        print("🚀 GELİŞMİŞ SAHTE SİNYAL KORUMASLI BOT AYARLARI v2.0")
        print("=" * 70)
        print(f"🌐 Ortam: {cls.ENVIRONMENT}")
        print(f"💰 İşlem Miktarı: {cls.ORDER_SIZE_USDT} USDT")
        print(f"📈 Kaldıraç: {cls.LEVERAGE}x")
        print(f"⏰ Zaman Dilimi: {cls.TIMEFRAME}")
        print(f"🛑 Stop Loss: %{cls.STOP_LOSS_PERCENT * 100:.1f}")
        print(f"🎯 Take Profit: %{cls.TAKE_PROFIT_PERCENT * 100:.1f}")
        print("=" * 70)
        print("🛡️ GELİŞMİŞ SAHTE SİNYAL KORUMALARI (ESNEKLEŞTİRİLMİŞ):")
        print(f"   📊 Trend Filtresi (EMA{cls.TREND_EMA_PERIOD}): {'✅' if cls.TREND_FILTER_ENABLED else '❌'}")
        print(f"   📈 Min. Fiyat Hareketi (%{cls.MIN_PRICE_MOVEMENT_PERCENT*100:.2f}): {'✅' if cls.MIN_PRICE_MOVEMENT_ENABLED else '❌'}")
        print(f"   🔄 RSI Filtresi ({cls.RSI_OVERSOLD}-{cls.RSI_OVERBOUGHT}): {'✅' if cls.RSI_FILTER_ENABLED else '❌'}")
        print(f"   ⏳ Sinyal Soğuma ({cls.SIGNAL_COOLDOWN_MINUTES}dk): {'✅' if cls.SIGNAL_COOLDOWN_ENABLED else '❌'}")
        print(f"   🌊 Volatilite Filtresi (ATR{cls.ATR_PERIOD}x{cls.MIN_ATR_MULTIPLIER}): {'✅' if cls.VOLATILITY_FILTER_ENABLED else '❌'}")
        print(f"   📊 Hacim Filtresi ({cls.MIN_VOLUME_MULTIPLIER}x): {'✅' if cls.VOLUME_FILTER_ENABLED else '❌'}")
        print(f"   💪 Sinyal Gücü (%{cls.SIGNAL_STRENGTH_THRESHOLD*100:.2f}): Aktif")
        print("=" * 70)
        print("🔧 GELİŞMİŞ ÖZELLİKLER:")
        print(f"   🐛 Debug Modu: {'✅' if cls.DEBUG_MODE else '❌'}")
        print(f"   🧪 Test Modu: {'✅' if cls.TEST_MODE else '❌'}")
        print(f"   🚨 Acil Durdurma: {'✅' if cls.EMERGENCY_STOP_ENABLED else '❌'}")
        print(f"   📊 Günlük Max Zarar: %{cls.MAX_DAILY_LOSS_PERCENT*100:.1f}")
        print(f"   🎯 Max Pozisyon: {cls.MAX_CONCURRENT_POSITIONS}")
        print("=" * 70)
        print("💡 Bu korumalar DAHA ESNEK ayarlanmış - yatay piyasalarda sahte sinyalleri engeller")
        print("🎯 Whipsaw (testere) hareketlerinden korunma aktif")
        print("📊 Piyasa koşullarına göre dinamik sinyal filtreleme")
        print("⚡ Daha hızlı sinyal yakalama ile daha fazla fırsat")
        print("=" * 70)

    @classmethod
    def get_filter_summary(cls):
        """Filtre ayarlarının özetini döndür"""
        return {
            "trend_filter": {
                "enabled": cls.TREND_FILTER_ENABLED,
                "period": cls.TREND_EMA_PERIOD,
                "description": f"EMA{cls.TREND_EMA_PERIOD} trend takibi"
            },
            "price_movement_filter": {
                "enabled": cls.MIN_PRICE_MOVEMENT_ENABLED,
                "threshold": cls.MIN_PRICE_MOVEMENT_PERCENT,
                "description": f"Min %{cls.MIN_PRICE_MOVEMENT_PERCENT*100:.2f} fiyat hareketi"
            },
            "rsi_filter": {
                "enabled": cls.RSI_FILTER_ENABLED,
                "oversold": cls.RSI_OVERSOLD,
                "overbought": cls.RSI_OVERBOUGHT,
                "description": f"RSI {cls.RSI_OVERSOLD}-{cls.RSI_OVERBOUGHT} arası"
            },
            "cooldown_filter": {
                "enabled": cls.SIGNAL_COOLDOWN_ENABLED,
                "minutes": cls.SIGNAL_COOLDOWN_MINUTES,
                "description": f"{cls.SIGNAL_COOLDOWN_MINUTES}dk sinyal soğuma"
            },
            "volatility_filter": {
                "enabled": cls.VOLATILITY_FILTER_ENABLED,
                "multiplier": cls.MIN_ATR_MULTIPLIER,
                "description": f"ATR x{cls.MIN_ATR_MULTIPLIER} volatilite"
            },
            "volume_filter": {
                "enabled": cls.VOLUME_FILTER_ENABLED,
                "multiplier": cls.MIN_VOLUME_MULTIPLIER,
                "description": f"{cls.MIN_VOLUME_MULTIPLIER}x ortalama hacim"
            },
            "signal_strength": {
                "enabled": True,
                "threshold": cls.SIGNAL_STRENGTH_THRESHOLD,
                "description": f"Min %{cls.SIGNAL_STRENGTH_THRESHOLD*100:.2f} EMA farkı"
            }
        }

    @classmethod
    def update_filter_settings(cls, filter_name: str, **kwargs):
        """Çalışma zamanında filtre ayarlarını güncelle"""
        try:
            if filter_name == "trend":
                if "enabled" in kwargs:
                    cls.TREND_FILTER_ENABLED = bool(kwargs["enabled"])
                if "period" in kwargs:
                    cls.TREND_EMA_PERIOD = int(kwargs["period"])
                    
            elif filter_name == "price_movement":
                if "enabled" in kwargs:
                    cls.MIN_PRICE_MOVEMENT_ENABLED = bool(kwargs["enabled"])
                if "threshold" in kwargs:
                    cls.MIN_PRICE_MOVEMENT_PERCENT = float(kwargs["threshold"])
                    
            elif filter_name == "rsi":
                if "enabled" in kwargs:
                    cls.RSI_FILTER_ENABLED = bool(kwargs["enabled"])
                if "oversold" in kwargs:
                    cls.RSI_OVERSOLD = float(kwargs["oversold"])
                if "overbought" in kwargs:
                    cls.RSI_OVERBOUGHT = float(kwargs["overbought"])
                    
            elif filter_name == "cooldown":
                if "enabled" in kwargs:
                    cls.SIGNAL_COOLDOWN_ENABLED = bool(kwargs["enabled"])
                if "minutes" in kwargs:
                    cls.SIGNAL_COOLDOWN_MINUTES = int(kwargs["minutes"])
                    
            elif filter_name == "volatility":
                if "enabled" in kwargs:
                    cls.VOLATILITY_FILTER_ENABLED = bool(kwargs["enabled"])
                if "multiplier" in kwargs:
                    cls.MIN_ATR_MULTIPLIER = float(kwargs["multiplier"])
                    
            elif filter_name == "volume":
                if "enabled" in kwargs:
                    cls.VOLUME_FILTER_ENABLED = bool(kwargs["enabled"])
                if "multiplier" in kwargs:
                    cls.MIN_VOLUME_MULTIPLIER = float(kwargs["multiplier"])
                    
            print(f"✅ {filter_name} filtresi güncellendi: {kwargs}")
            return True
            
        except Exception as e:
            print(f"❌ {filter_name} filtresi güncellenirken hata: {e}")
            return False

settings = Settings()

# Başlangıçta ayarları doğrula
if __name__ == "__main__":
    settings.validate_settings()
    settings.print_settings()
