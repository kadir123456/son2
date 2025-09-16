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
    LEVERAGE: int = 3
    ORDER_SIZE_USDT: float = 35.0
    TIMEFRAME: str = "3m"
    
    # --- Kâr/Zarar Ayarları (Stop Loss ve Take Profit) ---
    STOP_LOSS_PERCENT: float = 0.009   # %0.9 Zarar Durdur
    TAKE_PROFIT_PERCENT: float = 0.004 # %0.4 Kar Al
    
    # 🛡️ --- SAHTE SİNYAL KORUMASI AYARLARI ---
    
    # Trend Filtresi
    TREND_FILTER_ENABLED: bool = True
    TREND_EMA_PERIOD: int = 50          # Ana trend için EMA(50)
    
    # Minimum Fiyat Hareketi Filtresi  
    MIN_PRICE_MOVEMENT_ENABLED: bool = True
    MIN_PRICE_MOVEMENT_PERCENT: float = 0.003  # %0.3 minimum hareket
    
    # RSI Filtresi (Aşırı alım/satım koruması)
    RSI_FILTER_ENABLED: bool = True
    RSI_PERIOD: int = 14
    RSI_OVERSOLD: float = 30.0         # RSI < 30 = aşırı satım
    RSI_OVERBOUGHT: float = 70.0       # RSI > 70 = aşırı alım
    
    # Sinyal Soğuma Süresi (Whipsaw koruması)
    SIGNAL_COOLDOWN_ENABLED: bool = True
    SIGNAL_COOLDOWN_MINUTES: int = 15   # 15 dakika soğuma
    
    # Volatilite Filtresi
    VOLATILITY_FILTER_ENABLED: bool = True
    ATR_PERIOD: int = 14
    MIN_ATR_MULTIPLIER: float = 1.5     # ATR * 1.5 minimum volatilite
    
    # Hacim Filtresi
    VOLUME_FILTER_ENABLED: bool = True
    VOLUME_MA_PERIOD: int = 20
    MIN_VOLUME_MULTIPLIER: float = 1.2  # Ortalama hacmin 1.2x'i
    
    # Sinyal Gücü Threshold
    SIGNAL_STRENGTH_THRESHOLD: float = 0.0002  # EMA farkı minimum %0.02
    
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
        
        # Sahte sinyal koruması validasyonu
        if cls.MIN_PRICE_MOVEMENT_PERCENT > 0.01:
            warnings.append(f"⚠️ Minimum fiyat hareketi çok yüksek: %{cls.MIN_PRICE_MOVEMENT_PERCENT*100}")
        
        if cls.SIGNAL_COOLDOWN_MINUTES > 60:
            warnings.append(f"⚠️ Sinyal soğuma süresi çok uzun: {cls.SIGNAL_COOLDOWN_MINUTES} dakika")
        
        for warning in warnings:
            print(warning)
        
        return len(warnings) == 0

    @classmethod
    def print_settings(cls):
        """Mevcut ayarları yazdır"""
        print("=" * 70)
        print("🚀 SAHTE SİNYAL KORUMASLI BOT AYARLARI")
        print("=" * 70)
        print(f"🌐 Ortam: {cls.ENVIRONMENT}")
        print(f"💰 İşlem Miktarı: {cls.ORDER_SIZE_USDT} USDT")
        print(f"📈 Kaldıraç: {cls.LEVERAGE}x")
        print(f"⏰ Zaman Dilimi: {cls.TIMEFRAME}")
        print(f"🛑 Stop Loss: %{cls.STOP_LOSS_PERCENT * 100:.1f}")
        print(f"🎯 Take Profit: %{cls.TAKE_PROFIT_PERCENT * 100:.1f}")
        print("=" * 70)
        print("🛡️ SAHTE SİNYAL KORUMALARI:")
        print(f"   📊 Trend Filtresi (EMA{cls.TREND_EMA_PERIOD}): {'✅' if cls.TREND_FILTER_ENABLED else '❌'}")
        print(f"   📈 Min. Fiyat Hareketi (%{cls.MIN_PRICE_MOVEMENT_PERCENT*100:.1f}): {'✅' if cls.MIN_PRICE_MOVEMENT_ENABLED else '❌'}")
        print(f"   🔄 RSI Filtresi ({cls.RSI_OVERSOLD}-{cls.RSI_OVERBOUGHT}): {'✅' if cls.RSI_FILTER_ENABLED else '❌'}")
        print(f"   ⏳ Sinyal Soğuma ({cls.SIGNAL_COOLDOWN_MINUTES}dk): {'✅' if cls.SIGNAL_COOLDOWN_ENABLED else '❌'}")
        print(f"   🌊 Volatilite Filtresi (ATR{cls.ATR_PERIOD}): {'✅' if cls.VOLATILITY_FILTER_ENABLED else '❌'}")
        print(f"   📊 Hacim Filtresi ({cls.MIN_VOLUME_MULTIPLIER}x): {'✅' if cls.VOLUME_FILTER_ENABLED else '❌'}")
        print("=" * 70)
        print("💡 Bu korumalar yatay piyasalarda sahte sinyalleri engeller")
        print("🎯 Whipsaw (testere) hareketlerinden korunma aktif")
        print("=" * 70)

settings = Settings()

# Başlangıçta ayarları doğrula
if __name__ == "__main__":
    settings.validate_settings()
    settings.print_settings()
