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
    LEVERAGE: int = 10                    # 10x kaldıraç
    ORDER_SIZE_USDT: float = 50.0         # 50 USDT pozisyon boyutu
    TIMEFRAME: str = "15m"                # 15m timeframe
    
    # --- TP/SL Ayarları ---
    STOP_LOSS_PERCENT: float = 0.008      # %0.8 stop loss
    TAKE_PROFIT_PERCENT: float = 0.015    # %1.5 take profit
    
    # --- EMA Parametreleri ---
    EMA_FAST_PERIOD: int = 9              # Hızlı EMA
    EMA_SLOW_PERIOD: int = 21             # Yavaş EMA
    
    # --- Cache ve Performance ---
    CACHE_DURATION_BALANCE: int = 30      # 30 saniye
    CACHE_DURATION_POSITION: int = 15     # 15 saniye
    
    # Status Update Intervals
    STATUS_UPDATE_INTERVAL: int = 15      # 15 saniye
    BALANCE_UPDATE_INTERVAL: int = 45     # 45 saniye
    
    # WebSocket Ayarları
    WEBSOCKET_PING_INTERVAL: int = 30     
    WEBSOCKET_PING_TIMEOUT: int = 15     
    WEBSOCKET_CLOSE_TIMEOUT: int = 10    
    
    # Rate Limiting
    API_CALL_DELAY: float = 0.2           # 200ms delay
    
    # Debug Ayarları
    DEBUG_MODE: bool = True               
    TEST_MODE: bool = False               # Canlı işlem için False
    
    # Memory Management
    MAX_KLINES_PER_SYMBOL: int = 100      # 100 mum yeterli
    
    # Risk Yönetimi
    MAX_CONCURRENT_POSITIONS: int = 1     # Sadece 1 pozisyon

    @classmethod
    def validate_settings(cls):
        """Ayarları doğrula"""
        warnings = []
        
        if not cls.API_KEY or not cls.API_SECRET:
            warnings.append("⚠️ BINANCE_API_KEY veya BINANCE_API_SECRET ayarlanmamış!")
        
        if cls.LEVERAGE < 1 or cls.LEVERAGE > 20:
            warnings.append(f"⚠️ Kaldıraç değeri güvenli aralığın dışında: {cls.LEVERAGE}")
        
        # EMA validasyonu
        if cls.EMA_FAST_PERIOD >= cls.EMA_SLOW_PERIOD:
            warnings.append(f"⚠️ Hızlı EMA yavaş EMA'dan küçük olmalı: {cls.EMA_FAST_PERIOD} >= {cls.EMA_SLOW_PERIOD}")
        
        # TP/SL validasyonu
        if cls.STOP_LOSS_PERCENT > 0.02:  # %2'den fazla
            warnings.append(f"⚠️ Stop loss çok geniş: %{cls.STOP_LOSS_PERCENT*100:.1f}")
            
        for warning in warnings:
            print(warning)
        
        return len(warnings) == 0

    @classmethod
    def print_settings(cls):
        """Ayarları yazdır"""
        print("=" * 60)
        print("🎯 BASİT EMA CROSS TRADING BOT v1.0")
        print("=" * 60)
        print(f"🌐 Ortam: {cls.ENVIRONMENT}")
        print(f"💰 İşlem Miktarı: {cls.ORDER_SIZE_USDT} USDT")
        print(f"📈 Kaldıraç: {cls.LEVERAGE}x")
        print(f"⏰ Zaman Dilimi: {cls.TIMEFRAME}")
        print("=" * 60)
        print("🎯 EMA STRATEJİSİ:")
        print(f"   📈 Hızlı EMA: {cls.EMA_FAST_PERIOD}")
        print(f"   📊 Yavaş EMA: {cls.EMA_SLOW_PERIOD}")
        print(f"   🎯 Strateji: Sadece EMA kesişimi")
        print("=" * 60)
        print("💰 TP/SL AYARLARI:")
        print(f"   📉 Stop Loss: %{cls.STOP_LOSS_PERCENT*100:.1f}")
        print(f"   📈 Take Profit: %{cls.TAKE_PROFIT_PERCENT*100:.1f}")
        print("=" * 60)
        print("✅ ÖZELLİKLER:")
        print("   ✅ Basit ve güvenilir")
        print("   ✅ Sadece EMA 9/21 kesişimi")
        print("   ✅ Otomatik TP/SL")
        print("   ✅ Multi-coin desteği")
        print("=" * 60)

# Settings instance
settings = Settings()

# Başlangıçta ayarları doğrula
if __name__ == "__main__":
    settings.validate_settings()
    settings.print_settings()
