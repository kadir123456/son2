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
    LEVERAGE: int = int(os.getenv("LEVERAGE", "5"))
    ORDER_SIZE_USDT: float = float(os.getenv("ORDER_SIZE_USDT", "35.0"))  # Sabit işlem miktarı
    TIMEFRAME: str = os.getenv("TIMEFRAME", "15m")
    
    # --- Kâr/Zarar Ayarları (Stop Loss ve Take Profit) ---
    STOP_LOSS_PERCENT: float = float(os.getenv("STOP_LOSS_PERCENT", "0.008"))  # %0.8 Zarar Durdur
    TAKE_PROFIT_PERCENT: float = float(os.getenv("TAKE_PROFIT_PERCENT", "0.010"))  # %1.0 Kar Al
    
    # --- Rate Limiting ve Performance Ayarları ---
    MAX_REQUESTS_PER_MINUTE: int = int(os.getenv("MAX_REQUESTS_PER_MINUTE", "1200"))  # Binance limit: 2400
    CACHE_DURATION_BALANCE: int = int(os.getenv("CACHE_DURATION_BALANCE", "10"))  # Bakiye cache süresi (saniye)
    CACHE_DURATION_POSITION: int = int(os.getenv("CACHE_DURATION_POSITION", "5"))  # Pozisyon cache süresi (saniye)
    CACHE_DURATION_PNL: int = int(os.getenv("CACHE_DURATION_PNL", "3"))  # PnL cache süresi (saniye)
    
    # --- WebSocket Ayarları ---
    WEBSOCKET_PING_INTERVAL: int = int(os.getenv("WEBSOCKET_PING_INTERVAL", "30"))
    WEBSOCKET_PING_TIMEOUT: int = int(os.getenv("WEBSOCKET_PING_TIMEOUT", "15"))
    WEBSOCKET_CLOSE_TIMEOUT: int = int(os.getenv("WEBSOCKET_CLOSE_TIMEOUT", "10"))
    WEBSOCKET_MAX_RECONNECTS: int = int(os.getenv("WEBSOCKET_MAX_RECONNECTS", "10"))
    
    # --- Status Update Intervals ---
    STATUS_UPDATE_INTERVAL: int = int(os.getenv("STATUS_UPDATE_INTERVAL", "10"))  # Ana durum güncelleme aralığı (saniye)
    BALANCE_UPDATE_INTERVAL: int = int(os.getenv("BALANCE_UPDATE_INTERVAL", "30"))  # Bakiye güncelleme aralığı (saniye)

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
        
        if cls.STOP_LOSS_PERCENT <= 0 or cls.STOP_LOSS_PERCENT >= 1:
            warnings.append(f"⚠️ Stop Loss yüzdesi geçersiz: {cls.STOP_LOSS_PERCENT}. 0-1 arası olmalı.")
        
        if cls.TAKE_PROFIT_PERCENT <= 0 or cls.TAKE_PROFIT_PERCENT >= 1:
            warnings.append(f"⚠️ Take Profit yüzdesi geçersiz: {cls.TAKE_PROFIT_PERCENT}. 0-1 arası olmalı.")
        
        # Rate limit kontrolü
        if cls.MAX_REQUESTS_PER_MINUTE > 2000:
            warnings.append(f"⚠️ Dakikada maksimum istek sayısı yüksek: {cls.MAX_REQUESTS_PER_MINUTE}. Rate limit riski!")
        
        for warning in warnings:
            print(warning)
        
        return len(warnings) == 0

    @classmethod
    def print_settings(cls):
        """Mevcut ayarları yazdır"""
        print("=" * 50)
        print("📊 BOT AYARLARI")
        print("=" * 50)
        print(f"🌐 Ortam: {cls.ENVIRONMENT}")
        print(f"💰 İşlem Miktarı: {cls.ORDER_SIZE_USDT} USDT")
        print(f"📈 Kaldıraç: {cls.LEVERAGE}x")
        print(f"⏰ Zaman Dilimi: {cls.TIMEFRAME}")
        print(f"🛑 Stop Loss: %{cls.STOP_LOSS_PERCENT * 100:.1f}")
        print(f"🎯 Take Profit: %{cls.TAKE_PROFIT_PERCENT * 100:.1f}")
        print(f"🔄 Maks. İstek/Dakika: {cls.MAX_REQUESTS_PER_MINUTE}")
        print(f"💾 Cache Süreleri: Bakiye={cls.CACHE_DURATION_BALANCE}s, Pozisyon={cls.CACHE_DURATION_POSITION}s")
        print(f"🌐 WebSocket: Ping={cls.WEBSOCKET_PING_INTERVAL}s, Timeout={cls.WEBSOCKET_PING_TIMEOUT}s")
        print("=" * 50)

settings = Settings()

# Başlangıçta ayarları doğrula
if __name__ == "__main__":
    settings.validate_settings()
    settings.print_settings()
