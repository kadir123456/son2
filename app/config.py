# config.py

import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # --- Temel Ayarlar ---
    API_KEY: str = os.getenv("BINANCE_API_KEY")
    API_SECRET: str = os.getenv("BINANCE_API_SECRET")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "LIVE") # "LIVE" veya "TEST"
    BOT_USERNAME: str = os.getenv("BOT_USERNAME", "admin")
    BOT_PASSWORD: str = os.getenv("BOT_PASSWORD", "changeme123")
    
    # Binance API URL'leri (Ortama göre otomatik ayarlanır)
    BASE_URL = "https://fapi.binance.com" if os.getenv("ENVIRONMENT", "TEST") == "LIVE" else "https://testnet.binancefuture.com"
    WEBSOCKET_URL = "wss://fstream.binance.com" if os.getenv("ENVIRONMENT", "TEST") == "LIVE" else "wss://stream.binancefuture.com"

    # --- İşlem Parametreleri ---
    LEVERAGE: int = 5
    INITIAL_ORDER_SIZE_USDT: float = 10.0  # Katlamalı sistem için başlangıç işlem boyutu
    
    # Bu değişken bot_core tarafından dinamik olarak güncellenecek.
    # Başlangıçta INITIAL_ORDER_SIZE_USDT değerini alır.
    ORDER_SIZE_USDT: float = INITIAL_ORDER_SIZE_USDT 
    
    TIMEFRAME: str = "5m"  # Ana işlem zaman dilimi (3m veya 5m olarak güncellendi)
    
    # Botun analiz edeceği coin sembolleri listesi
    # NOT: USDT pariteleri olmalıdır (örn: BTCUSDT, ETHUSDT)
    # Varsayılan olarak 10 adet coin eklendi. İstediğiniz coinleri buraya ekleyebilirsiniz.
    SYMBOLS_TO_TRADE: list[str] = [
        "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", 
        "XRPUSDT", "ADAUSDT", "DOGEUSDT", "SHIBUSDT", 
        "DOTUSDT", "AVAXUSDT"
    ]
    
    # --- Kâr/Zarar Ayarları ---
    STOP_LOSS_PERCENT: float = 0.02  # %2 Zarar Durdur
    TAKE_PROFIT_PERCENT: float = 0.03 # %3 Kar Al (Yeni Eklendi)

    # --- Ek Onay Ayarları ---
    # EMA kesişimine ek bir onay kullanılsın mı?
    # Eğer True ise, CONFIRMATION_TIMEFRAME'deki strateji sinyali de aynı yönde olmalı.
    USE_ADDITIONAL_CONFIRMATION: bool = True 
    CONFIRMATION_TIMEFRAME: str = "15m" # Ek onay için zaman dilimi (Örn: daha yüksek zaman dilimi)

settings = Settings()