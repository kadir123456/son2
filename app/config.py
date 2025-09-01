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
    LEVERAGE: int = 10
    INITIAL_ORDER_SIZE_USDT: float = 40.0  # Katlamalı sistem için başlangıç işlem boyutu
    
    # Bu değişken bot_core tarafından dinamik olarak güncellenecek.
    # Başlangıçta INITIAL_ORDER_SIZE_USDT değerini alır.
    ORDER_SIZE_USDT: float = INITIAL_ORDER_SIZE_USDT 
    
    TIMEFRAME: str = "15m"  # ANA İŞLEM ZAMAN DİLİMİ (5m yerine 3m önerisi)
    
    # Botun analiz edeceği coin sembolleri listesi
    # NOT: USDT pariteleri olmalıdır (örn: BTCUSDT, ETHUSDT)
    # Varsayılan olarak 10 adet coin eklendi. İstediğiniz coinleri buraya ekleyebilirsiniz.
    SYMBOLS_TO_TRADE: list[str] = [
        "SUIUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", 
        "XRPUSDT", "ADAUSDT", "DOGEUSDT", "SHIBUSDT", 
        "DOTUSDT", "AVAXUSDT"
    ]
    
    # --- Kâr/Zarar Ayarları ---
    STOP_LOSS_PERCENT: float = 0.02  # %2 Zarar Durdur
    TAKE_PROFIT_PERCENT: float = 0.05 # %3 Kar Al

    # --- Ek Onay Ayarları ---
    # EMA kesişimine ek bir onay kullanılsın mı?
    # Eğer True ise, CONFIRMATION_TIMEFRAME'deki strateji sinyali de aynı yönde olmalı.
    USE_ADDITIONAL_CONFIRMATION: bool = False # EK ONAY DEVRE DIŞI BIRAKILDI
    CONFIRMATION_TIMEFRAME: str = "15m" # Ek onay için zaman dilimi (Bu ayar artık USE_ADDITIONAL_CONFIRMATION False olduğu için etkisizdir)

settings = Settings()
