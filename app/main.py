# app/main.py - GELIŞMIŞ MULTI-COIN VE ZAMAN DİLİMİ SEÇİMİ DESTEKLİ VERSİYON

import asyncio
import time
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.security import HTTPBearer
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
from .bot_core import bot_core
from .config import settings
from .firebase_manager import firebase_manager
from .position_manager import position_manager

bearer_scheme = HTTPBearer()

# Rate limiting için basit bir sistem
class RateLimiter:
    def __init__(self, max_requests: int = 60, time_window: int = 60):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = {}
    
    def is_allowed(self, client_id: str) -> bool:
        current_time = time.time()
        if client_id not in self.requests:
            self.requests[client_id] = []
        
        # Eski istekleri temizle
        self.requests[client_id] = [
            req_time for req_time in self.requests[client_id] 
            if current_time - req_time < self.time_window
        ]
        
        if len(self.requests[client_id]) >= self.max_requests:
            return False
        
        self.requests[client_id].append(current_time)
        return True

rate_limiter = RateLimiter(max_requests=40, time_window=60)  # Biraz daha yüksek limit

async def authenticate(token: str = Depends(bearer_scheme)):
    """Gelen Firebase ID Token'ını doğrular ve rate limiting uygular."""
    user = firebase_manager.verify_token(token.credentials)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Geçersiz veya süresi dolmuş güvenlik token'ı.",
        )
    
    # Rate limiting kontrolü
    user_id = user.get('uid', 'unknown')
    if not rate_limiter.is_allowed(user_id):
        raise HTTPException(
            status_code=429,
            detail="Çok fazla istek. Lütfen bekleyin."
        )
    
    print(f"Doğrulanan kullanıcı: {user.get('email')}")
    return user

app = FastAPI(title="Enhanced Multi-Coin Binance Futures Bot", version="4.0.0")

@app.on_event("startup")
async def startup_event():
    """Uygulama başlangıcında ayarları doğrula"""
    print("🚀 Gelişmiş Multi-Coin Bot başlatılıyor...")
    settings.validate_settings()
    settings.print_settings()

@app.on_event("shutdown")
async def shutdown_event():
    if bot_core.status["is_running"]:
        await bot_core.stop()
    await position_manager.stop_monitoring()

# ============ YENİ MODEL'LER - GELİŞMİŞ ÖZELLİKLER ============
class EnhancedMultiStartRequest(BaseModel):
    symbols: List[str]  # Birden fazla symbol
    timeframe: Optional[str] = "15m"  # YENİ: Zaman dilimi seçimi

class TimeframeChangeRequest(BaseModel):
    timeframe: str

class AddSymbolRequest(BaseModel):
    symbol: str

class RemoveSymbolRequest(BaseModel):
    symbol: str

class SymbolRequest(BaseModel):
    symbol: str

class RiskSettingsRequest(BaseModel):
    max_daily_positions: Optional[int] = None
    max_daily_loss_percent: Optional[float] = None
    max_consecutive_losses: Optional[int] = None

# ============ GELİŞMİŞ MULTI-COIN ENDPOINT'LER ============

@app.post("/api/enhanced-multi-start")
async def start_enhanced_multi_bot(request: EnhancedMultiStartRequest, background_tasks: BackgroundTasks, user: dict = Depends(authenticate)):
    """Gelişmiş özelliklerle birden fazla coin ve zaman dilimi ile bot başlat"""
    if bot_core.status["is_running"]:
        raise HTTPException(status_code=400, detail="Bot zaten çalışıyor.")
    
    if not request.symbols or len(request.symbols) == 0:
        raise HTTPException(status_code=400, detail="En az bir symbol gerekli.")
    
    if len(request.symbols) > 20:
        raise HTTPException(status_code=400, detail="Maksimum 20 symbol desteklenir.")
    
    # Zaman dilimini kontrol et
    available_timeframes = bot_core.get_available_timeframes()
    if request.timeframe not in available_timeframes:
        raise HTTPException(
            status_code=400, 
            detail=f"Geçersiz zaman dilimi: {request.timeframe}. Desteklenenler: {', '.join(available_timeframes)}"
        )
    
    # Symbolları normalize et
    normalized_symbols = []
    for symbol in request.symbols:
        symbol = symbol.upper().strip()
        if not symbol.endswith('USDT'):
            symbol += 'USDT'
        
        if len(symbol) < 6 or len(symbol) > 20:
            raise HTTPException(status_code=400, detail=f"Geçersiz sembol formatı: {symbol}")
        
        if symbol not in normalized_symbols:  # Duplicate kontrolü
            normalized_symbols.append(symbol)
    
    print(f"👤 {user.get('email')} tarafından gelişmiş multi-coin bot başlatılıyor:")
    print(f"   📊 Coinler: {', '.join(normalized_symbols)}")
    print(f"   🕐 Zaman dilimi: {request.timeframe}")
    
    background_tasks.add_task(bot_core.start, normalized_symbols, request.timeframe)
    await asyncio.sleep(2)
    return bot_core.get_multi_status()

@app.post("/api/change-timeframe")
async def change_timeframe(request: TimeframeChangeRequest, user: dict = Depends(authenticate)):
    """Zaman dilimini değiştir (bot durdurulmuşken)"""
    result = await bot_core.change_timeframe(request.timeframe)
    if result["success"]:
        return {
            "success": True,
            "message": result["message"],
            "new_settings": result["new_settings"],
            "user": user.get('email'),
            "timestamp": time.time()
        }
    else:
        raise HTTPException(status_code=400, detail=result["message"])

@app.get("/api/timeframe-info")
async def get_timeframe_info(user: dict = Depends(authenticate)):
    """Zaman dilimi bilgilerini döndür"""
    current_timeframe = settings.TIMEFRAME
    current_settings = settings.get_current_settings()
    
    return {
        "current_timeframe": current_timeframe,
        "available_timeframes": bot_core.get_available_timeframes(),
        "current_settings": {
            "stop_loss_percent": current_settings["stop_loss_percent"] * 100,
            "take_profit_percent": current_settings["take_profit_percent"] * 100,
            "risk_reward_ratio": settings.get_risk_reward_ratio(),
            "cooldown_minutes": current_settings["cooldown_minutes"],
            "min_price_movement": current_settings["min_price_movement"] * 100,
            "signal_strength": current_settings["signal_strength"],
            "atr_multiplier": current_settings["atr_multiplier"]
        },
        "timeframe_comparison": {
            tf: {
                "stop_loss": settings.TIMEFRAME_SETTINGS[tf]["stop_loss_percent"] * 100,
                "take_profit": settings.TIMEFRAME_SETTINGS[tf]["take_profit_percent"] * 100,
                "risk_reward": settings.TIMEFRAME_SETTINGS[tf]["take_profit_percent"] / settings.TIMEFRAME_SETTINGS[tf]["stop_loss_percent"],
                "cooldown_minutes": settings.TIMEFRAME_SETTINGS[tf]["cooldown_minutes"]
            }
            for tf in settings.TIMEFRAME_SETTINGS.keys()
        }
    }

@app.post("/api/add-symbol")
async def add_symbol_to_bot(request: AddSymbolRequest, user: dict = Depends(authenticate)):
    """Çalışan bot'a yeni symbol ekle"""
    if not bot_core.status["is_running"]:
        raise HTTPException(status_code=400, detail="Bot çalışmıyor.")
    
    symbol = request.symbol.upper().strip()
    if not symbol.endswith('USDT'):
        symbol += 'USDT'
    
    if len(symbol) < 6 or len(symbol) > 20:
        raise HTTPException(status_code=400, detail="Geçersiz sembol formatı.")
    
    if len(bot_core.status["symbols"]) >= 20:
        raise HTTPException(status_code=400, detail="Maksimum 20 symbol desteklenir.")
    
    print(f"👤 {user.get('email')} tarafından symbol ekleniyor: {symbol}")
    
    result = await bot_core.add_symbol(symbol)
    if result["success"]:
        return {
            "success": True,
            "message": result["message"],
            "current_symbols": bot_core.status["symbols"],
            "current_timeframe": bot_core.status["current_timeframe"],
            "user": user.get('email'),
            "timestamp": time.time()
        }
    else:
        raise HTTPException(status_code=400, detail=result["message"])

@app.post("/api/remove-symbol")
async def remove_symbol_from_bot(request: RemoveSymbolRequest, user: dict = Depends(authenticate)):
    """Çalışan bot'tan symbol çıkar"""
    if not bot_core.status["is_running"]:
        raise HTTPException(status_code=400, detail="Bot çalışmıyor.")
    
    symbol = request.symbol.upper().strip()
    if not symbol.endswith('USDT'):
        symbol += 'USDT'
    
    if len(bot_core.status["symbols"]) <= 1:
        raise HTTPException(status_code=400, detail="En az bir symbol bot'ta kalmalı.")
    
    print(f"👤 {user.get('email')} tarafından symbol çıkarılıyor: {symbol}")
    
    result = await bot_core.remove_symbol(symbol)
    if result["success"]:
        return {
            "success": True,
            "message": result["message"],
            "current_symbols": bot_core.status["symbols"],
            "current_timeframe": bot_core.status["current_timeframe"],
            "user": user.get('email'),
            "timestamp": time.time()
        }
    else:
        raise HTTPException(status_code=400, detail=result["message"])

@app.get("/api/enhanced-status")
async def get_enhanced_status(user: dict = Depends(authenticate)):
    """Gelişmiş multi-coin bot durumunu döndür"""
    return bot_core.get_multi_status()

@app.get("/api/risk-management-status")
async def get_risk_management_status(user: dict = Depends(authenticate)):
    """Risk yönetimi durumunu detaylı döndür"""
    from .trading_strategy import trading_strategy
    
    status = bot_core.get_multi_status()
    risk_info = {
        "current_settings": {
            "max_daily_positions": settings.MAX_DAILY_POSITIONS,
            "max_daily_loss_percent": settings.MAX_DAILY_LOSS_PERCENT * 100,
            "max_consecutive_losses": settings.MAX_CONSECUTIVE_LOSSES,
            "min_risk_reward_ratio": settings.MIN_RISK_REWARD_RATIO
        },
        "current_status": {
            "daily_positions": status.get("daily_positions", 0),
            "daily_pnl": status.get("daily_pnl", 0.0),
            "account_balance": status.get("account_balance", 0.0),
            "risk_management_active": status.get("risk_management_active", False)
        },
        "symbol_details": {}
    }
    
    # Her symbol için detay
    for symbol in status.get("symbols", []):
        filter_status = trading_strategy.get_filter_status(symbol)
        risk_info["symbol_details"][symbol] = filter_status
    
    return risk_info

# ============ UYUMLULUK - ESKİ ENDPOINT'LER ============

@app.post("/api/multi-start")
async def start_multi_bot(request: dict, background_tasks: BackgroundTasks, user: dict = Depends(authenticate)):
    """Eski multi-start endpoint'i - geriye uyumluluk"""
    symbols = request.get("symbols", [])
    timeframe = request.get("timeframe", "15m")
    
    enhanced_request = EnhancedMultiStartRequest(symbols=symbols, timeframe=timeframe)
    return await start_enhanced_multi_bot(enhanced_request, background_tasks, user)

@app.post("/api/start")
async def start_bot(request: dict, background_tasks: BackgroundTasks, user: dict = Depends(authenticate)):
    """Tek symbol için geriye uyumluluk - artık multi-coin olarak çalışır"""
    symbol = request.get("symbol", "").upper().strip()
    timeframe = request.get("timeframe", "15m")
    
    if not symbol.endswith('USDT'):
        symbol += 'USDT'
    
    print(f"👤 {user.get('email')} tarafından tek symbol bot başlatılıyor: {symbol} ({timeframe})")
    
    # Tek symbol'ü liste olarak gönder
    background_tasks.add_task(bot_core.start, [symbol], timeframe)
    await asyncio.sleep(2)
    
    # Eski format için uyumlu response
    status = bot_core.get_multi_status()
    return {
        "is_running": status["is_running"],
        "symbol": status["symbols"][0] if status["symbols"] else None,
        "position_side": status["position_side"],
        "status_message": status["status_message"],
        "account_balance": status["account_balance"],
        "position_pnl": status["position_pnl"],
        "order_size": status["order_size"],
        "position_monitor_active": status["position_monitor_active"],
        "current_timeframe": status["current_timeframe"]
    }

@app.post("/api/stop")
async def stop_bot(user: dict = Depends(authenticate)):
    if not bot_core.status["is_running"]:
        raise HTTPException(status_code=400, detail="Bot zaten durdurulmuş.")
    
    print(f"👤 {user.get('email')} tarafından bot durduruluyor")
    await bot_core.stop()
    return bot_core.get_multi_status()

@app.get("/api/status")
async def get_status(user: dict = Depends(authenticate)):
    """Geriye uyumluluk için eski format status"""
    status = bot_core.get_multi_status()
    return {
        "is_running": status["is_running"],
        "symbol": status["active_symbol"],  # Aktif symbol'ü döndür
        "position_side": status["position_side"],
        "status_message": status["status_message"],
        "account_balance": status["account_balance"],
        "position_pnl": status["position_pnl"],
        "order_size": status["order_size"],
        "position_monitor_active": status["position_monitor_active"],
        "position_manager": status["position_manager"],
        "current_timeframe": status["current_timeframe"]
    }

@app.get("/api/multi-status")
async def get_multi_status(user: dict = Depends(authenticate)):
    """Multi-coin bot durumunu döndür - yönlendirme"""
    return await get_enhanced_status(user)

@app.get("/api/health")
async def health_check():
    """Sağlık kontrolü - authentication gerektirmez"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "bot_running": bot_core.status["is_running"],
        "symbols_count": len(bot_core.status["symbols"]),
        "active_symbol": bot_core.status["active_symbol"],
        "position_monitor_running": position_manager.is_running,
        "websocket_connections": len(bot_core._websocket_connections),
        "current_timeframe": bot_core.status.get("current_timeframe", "15m"),
        "version": "4.0.0"
    }

# ============ POZİSYON YÖNETİMİ ENDPOINT'LERİ ============

@app.post("/api/scan-all-positions")
async def scan_all_positions(user: dict = Depends(authenticate)):
    """
    Tüm açık pozisyonları tarayıp eksik TP/SL emirlerini ekler
    Manuel işlemler ve bot dışı coinler için kullanılır
    """
    print(f"👤 {user.get('email')} tarafından tam pozisyon taraması başlatıldı")
    
    try:
        result = await bot_core.scan_all_positions()
        return {
            "success": result["success"],
            "message": result["message"],
            "user": user.get('email'),
            "timestamp": time.time(),
            "monitor_status": result.get("monitor_status"),
            "current_timeframe": bot_core.status.get("current_timeframe")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pozisyon tarama hatası: {e}")

@app.post("/api/scan-symbol")
async def scan_specific_symbol(request: SymbolRequest, user: dict = Depends(authenticate)):
    """
    Belirli bir coin için TP/SL kontrolü yapar
    Manuel işlemler için kullanılır
    """
    symbol = request.symbol.upper().strip()
    if not symbol.endswith('USDT'):
        symbol += 'USDT'
    
    print(f"👤 {user.get('email')} tarafından {symbol} TP/SL kontrolü başlatıldı")
    
    try:
        result = await bot_core.scan_specific_symbol(symbol)
        return {
            "success": result["success"],
            "symbol": result["symbol"],
            "message": result["message"],
            "user": user.get('email'),
            "timestamp": time.time(),
            "current_timeframe": bot_core.status.get("current_timeframe")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{symbol} kontrolü hatası: {e}")

@app.get("/api/position-monitor-status")
async def get_position_monitor_status(user: dict = Depends(authenticate)):
    """
    Otomatik TP/SL monitoring sisteminin durumunu döndürür
    """
    return {
        "monitor_status": position_manager.get_status(),
        "bot_status": bot_core.status["is_running"],
        "current_timeframe": bot_core.status.get("current_timeframe"),
        "timestamp": time.time()
    }

@app.post("/api/start-position-monitor")
async def start_position_monitor(background_tasks: BackgroundTasks, user: dict = Depends(authenticate)):
    """
    Otomatik TP/SL monitoring'i bot olmadan başlatır
    Manuel işlemler için sürekli koruma sağlar
    """
    if position_manager.is_running:
        raise HTTPException(status_code=400, detail="Position monitor zaten çalışıyor.")
    
    print(f"👤 {user.get('email')} tarafından standalone position monitor başlatılıyor")
    
    try:
        background_tasks.add_task(position_manager.start_monitoring)
        await asyncio.sleep(1)
        
        return {
            "success": True,
            "message": "Otomatik TP/SL monitoring başlatıldı",
            "monitor_status": position_manager.get_status(),
            "user": user.get('email'),
            "current_timeframe": bot_core.status.get("current_timeframe"),
            "timestamp": time.time()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Monitor başlatma hatası: {e}")

@app.post("/api/stop-position-monitor")
async def stop_position_monitor(user: dict = Depends(authenticate)):
    """
    Otomatik TP/SL monitoring'i durdurur
    """
    if not position_manager.is_running:
        raise HTTPException(status_code=400, detail="Position monitor zaten durdurulmuş.")
    
    print(f"👤 {user.get('email')} tarafından position monitor durduruluyor")
    
    try:
        await position_manager.stop_monitoring()
        
        return {
            "success": True,
            "message": "Otomatik TP/SL monitoring durduruldu",
            "monitor_status": position_manager.get_status(),
            "user": user.get('email'),
            "timestamp": time.time()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Monitor durdurma hatası: {e}")

# ============ YENİ: GELİŞMİŞ ANALİZ ENDPOINT'LERİ ============

@app.get("/api/filter-statistics")
async def get_filter_statistics(user: dict = Depends(authenticate)):
    """Filtre istatistiklerini döndür"""
    from .trading_strategy import trading_strategy
    
    stats = {
        "total_filtered_signals": bot_core.status.get("filtered_signals_count", 0),
        "active_filters": {
            "trend_filter": settings.TREND_FILTER_ENABLED,
            "momentum_filter": settings.MOMENTUM_FILTER_ENABLED,
            "trend_strength_filter": settings.TREND_STRENGTH_FILTER_ENABLED,
            "price_movement_filter": settings.MIN_PRICE_MOVEMENT_ENABLED,
            "rsi_filter": settings.RSI_FILTER_ENABLED,
            "cooldown_filter": settings.SIGNAL_COOLDOWN_ENABLED,
            "volatility_filter": settings.VOLATILITY_FILTER_ENABLED,
            "volume_filter": settings.VOLUME_FILTER_ENABLED
        },
        "symbol_statistics": {}
    }
    
    # Her symbol için detaylı istatistik
    for symbol in bot_core.status.get("symbols", []):
        stats["symbol_statistics"][symbol] = trading_strategy.get_filter_status(symbol)
    
    return stats

@app.get("/api/performance-metrics")
async def get_performance_metrics(user: dict = Depends(authenticate)):
    """Performans metriklerini döndür"""
    return {
        "bot_status": {
            "is_running": bot_core.status["is_running"],
            "uptime_seconds": time.time() - (bot_core.status.get("start_time", time.time())),
            "current_timeframe": bot_core.status.get("current_timeframe"),
            "symbols_count": len(bot_core.status.get("symbols", [])),
            "websocket_connections": len(bot_core._websocket_connections)
        },
        "risk_metrics": {
            "daily_positions": bot_core.status.get("daily_positions", 0),
            "daily_pnl": bot_core.status.get("daily_pnl", 0.0),
            "current_balance": bot_core.status.get("account_balance", 0.0),
            "position_pnl": bot_core.status.get("position_pnl", 0.0)
        },
        "signal_metrics": {
            "filtered_signals": bot_core.status.get("filtered_signals_count", 0),
            "active_signals": len([s for s in bot_core.status.get("last_signals", {}).values() if s != "HOLD"])
        },
        "timestamp": time.time()
    }

# ============ STATIC FILES ============

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_index():
    return FileResponse('static/index.html')
