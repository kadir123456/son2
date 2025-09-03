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
    INITIAL_ORDER_SIZE_USDT: float = 50.0  # Varsayılan işlem boyutu
    
    # Ana işlem zaman dilimi - EMA kesişim stratejisi için
    TIMEFRAME: str = "5m"  # 5 dakikalık mumlar (daha hızlı sinyaller için)
    
    # --- Kâr/Zarar Ayarları ---
    STOP_LOSS_PERCENT: float = 0.02  # %2 Zarar Durdur
    TAKE_PROFIT_PERCENT: float = 0.03 # %3 Kar Al

    # --- Çoklu Coin Ayarları ---
    # Maksimum aynı anda açık olabilecek pozisyon sayısı
    MAX_CONCURRENT_POSITIONS: int = 5
    
    # Her coin için minimum işlem boyutu (USDT)
    MIN_ORDER_SIZE_USDT: float = 10.0
    
    # Bot'un kullanabileceği maksimum bakiye yüzdesi (güvenlik için)
    MAX_BALANCE_USAGE_PERCENT: float = 0.8  # %80

    # --- Strateji Ayarları ---
    # EMA periyotları
    SHORT_EMA_PERIOD: int = 9
    LONG_EMA_PERIOD: int = 21
    
    # Sinyal filtreleme - aynı yönde art arda kaç sinyal gelmeli
    SIGNAL_CONFIRMATION_COUNT: int = 1  # 1 = Doğrudan işlem aç
    
    # Pozisyon değiştirme gecikme süresi (saniye) - çok sık işlem yapmamak için
    POSITION_CHANGE_DELAY: float = 30.0
    
    # --- Ek Onay Ayarları (İsteğe Bağlı) ---
    # Bu özellik şu an devre dışı bırakıldı
    USE_ADDITIONAL_CONFIRMATION: bool = False
    CONFIRMATION_TIMEFRAME: str = "15m"

    # --- Risk Yönetimi ---
    # Günlük maksimum zarar limiti (USDT)
    DAILY_LOSS_LIMIT: float = 200.0
    
    # Günlük maksimum işlem sayısı (spam önleme)
    DAILY_TRADE_LIMIT: int = 50
    
    # Pozisyon boyutu risk çarpanı (volatil coinler için küçük pozisyon)
    POSITION_SIZE_MULTIPLIER: float = 1.0

settings = Settings()
