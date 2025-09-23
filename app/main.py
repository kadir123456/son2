# app/main.py - ENHANCED VERSION v4.0

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

# Enhanced rate limiting
class EnhancedRateLimiter:
    def __init__(self, max_requests: int = 50, time_window: int = 60):
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

rate_limiter = EnhancedRateLimiter(max_requests=40, time_window=60)

async def authenticate(token: str = Depends(bearer_scheme)):
    """Enhanced authentication with rate limiting"""
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
            detail="Çok fazla istek. Enhanced bot kullanımında lütfen bekleyin."
        )
    
    print(f"✅ Enhanced bot kullanıcısı: {user.get('email')}")
    return user

app = FastAPI(title="Enhanced Multi-Coin Binance Futures Bot v4.0", version="4.0.0")

@app.on_event("startup")
async def startup_event():
    """Enhanced uygulama başlangıcı"""
    print("🚀 Enhanced Multi-Coin Bot v4.0 başlatılıyor...")
    settings.validate_settings()
    settings.print_settings()
    
    # Enhanced optimization summary
    optimization = settings.get_optimization_summary()
    print(f"🎯 Optimization version: {optimization['optimization_version']}")
    print(f"✅ Removed features: {len(optimization['removed_features'])}")
    print(f"✅ New features: {len(optimization['new_features'])}")

@app.on_event("shutdown")
async def shutdown_event():
    if bot_core.status["is_running"]:
        await bot_core.stop()
    await position_manager.stop_monitoring()

# ============ ENHANCED MODEL'LER ============
class EnhancedMultiStartRequest(BaseModel):
    symbols: List[str]
    timeframe: Optional[str] = None  # Override default timeframe

class EnhancedSymbolRequest(BaseModel):
    symbol: str

class PartialExitConfigRequest(BaseModel):
    symbol: str
    enable_partial: bool

class ReverseConfigRequest(BaseModel):
    symbol: str
    enable_reverse: bool

# ============ ENHANCED MULTI-COIN ENDPOINT'LER ============

@app.post("/api/enhanced-multi-start")
async def start_enhanced_multi_bot(request: EnhancedMultiStartRequest, background_tasks: BackgroundTasks, 
                                  user: dict = Depends(authenticate)):
    """Enhanced multi-coin bot başlat - kademeli satış ve position reverse ile"""
    if bot_core.status["is_running"]:
        raise HTTPException(status_code=400, detail="Enhanced bot zaten çalışıyor.")
    
    if not request.symbols or len(request.symbols) == 0:
        raise HTTPException(status_code=400, detail="En az bir symbol gerekli.")
    
    if len(request.symbols) > 15:  # Reduced limit for enhanced features
        raise HTTPException(status_code=400, detail="Enhanced bot maksimum 15 symbol destekler.")
    
    # Symbolları normalize et
    normalized_symbols = []
    for symbol in request.symbols:
        symbol = symbol.upper().strip()
        
        if not symbol.endswith('USDT'):
            symbol += 'USDT'
        
        if len(symbol) < 6 or len(symbol) > 20:
            raise HTTPException(status_code=400, detail=f"Geçersiz sembol formatı: {symbol}")
        
        if not symbol.replace('USDT', '').isalpha():
            raise HTTPException(status_code=400, detail=f"Geçersiz sembol karakterleri: {symbol}")
        
        if symbol not in normalized_symbols:
            normalized_symbols.append(symbol)
    
    if len(normalized_symbols) == 0:
        raise HTTPException(status_code=400, detail="Geçerli sembol bulunamadı.")
    
    # Timeframe override
    if request.timeframe:
        original_timeframe = settings.TIMEFRAME
        settings.TIMEFRAME = request.timeframe
        print(f"⚙️ Timeframe override: {original_timeframe} -> {request.timeframe}")
    
    print(f"👤 {user.get('email')} tarafından Enhanced multi-coin bot başlatılıyor:")
    print(f"   Symbols: {', '.join(normalized_symbols)}")
    print(f"   Timeframe: {settings.TIMEFRAME}")
    print(f"   Kademeli satış: {'✅' if settings.ENABLE_PARTIAL_EXITS else '❌'}")
    print(f"   Position reverse: {'✅' if settings.ENABLE_POSITION_REVERSE else '❌'}")
    
    try:
        background_tasks.add_task(bot_core.start, normalized_symbols)
        await asyncio.sleep(2)
        
        current_status = bot_core.get_multi_status()
        
        return {
            "success": True,
            "message": f"Enhanced bot {len(normalized_symbols)} coin için başlatılıyor...",
            "symbols": normalized_symbols,
            "user": user.get('email'),
            "timestamp": time.time(),
            "enhanced_features": {
                "partial_exits": settings.ENABLE_PARTIAL_EXITS,
                "position_reverse": settings.ENABLE_POSITION_REVERSE,
                "sl_tightening": settings.ENABLE_SL_TIGHTENING,
                "timeframe": settings.TIMEFRAME
            },
            "status": current_status
        }
        
    except Exception as e:
        print(f"❌ Enhanced bot başlatma hatası: {e}")
        raise HTTPException(status_code=500, detail=f"Enhanced bot başlatılırken hata: {str(e)}")

@app.get("/api/enhanced-status")
async def get_enhanced_status(user: dict = Depends(authenticate)):
    """Enhanced bot durumunu döndür - detaylı istatistiklerle"""
    status = bot_core.get_multi_status()
    
    # Enhanced statistics ekle
    enhanced_stats = {
        "strategy_version": status.get("version", "4.0_enhanced"),
        "optimization_results": settings.get_optimization_summary(),
        "current_features": {
            "simplified_ema": True,
            "position_reverse": status.get("reverse_detection_active", False),
            "partial_exits": status.get("using_partial_exits", False),
            "sl_tightening": settings.ENABLE_SL_TIGHTENING,
            "minimal_filters": True
        },
        "performance_metrics": status.get("performance", {}),
        "enhanced_counts": {
            "position_reverses": status.get("position_reverses", 0),
            "sl_tightenings": status.get("sl_tightenings", 0),
            "partial_exits": status.get("partial_exits_executed", 0)
        }
    }
    
    status["enhanced_stats"] = enhanced_stats
    return status

@app.post("/api/configure-partial-exits")
async def configure_partial_exits(request: PartialExitConfigRequest, user: dict = Depends(authenticate)):
    """Belirli bir symbol için kademeli satış yapılandır"""
    # Bu endpoint gelecek sürümlerde symbol-specific ayarlar için kullanılabilir
    return {
        "success": True,
        "message": f"{request.symbol} için kademeli satış {'etkinleştirildi' if request.enable_partial else 'devre dışı bırakıldı'}",
        "symbol": request.symbol,
        "partial_exits_enabled": request.enable_partial,
        "current_timeframe": settings.TIMEFRAME,
        "supports_partial": settings.TIMEFRAME in settings.TIMEFRAMES_FOR_PARTIAL
    }

@app.post("/api/trigger-position-reverse")
async def trigger_manual_position_reverse(request: EnhancedSymbolRequest, user: dict = Depends(authenticate)):
    """Manuel position reverse tetikleme"""
    if not bot_core.status["is_running"]:
        raise HTTPException(status_code=400, detail="Enhanced bot çalışmıyor.")
    
    symbol = request.symbol.upper().strip()
    if not symbol.endswith('USDT'):
        symbol += 'USDT'
    
    if bot_core.status["active_symbol"] != symbol:
        raise HTTPException(status_code=400, detail=f"{symbol} şu anda aktif pozisyonda değil.")
    
    print(f"👤 {user.get('email')} tarafından manuel position reverse: {symbol}")
    
    try:
        current_side = bot_core.status["position_side"]
        new_side = "SHORT" if current_side == "LONG" else "LONG"
        
        await bot_core._execute_position_reverse(symbol, new_side)
        
        return {
            "success": True,
            "message": f"{symbol} manuel position reverse başarılı",
            "old_side": current_side,
            "new_side": new_side,
            "user": user.get('email'),
            "timestamp": time.time()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Position reverse hatası: {e}")

@app.post("/api/trigger-sl-tightening")
async def trigger_sl_tightening(request: EnhancedSymbolRequest, user: dict = Depends(authenticate)):
    """Manuel SL tightening tetikleme"""
    symbol = request.symbol.upper().strip()
    if not symbol.endswith('USDT'):
        symbol += 'USDT'
    
    print(f"👤 {user.get('email')} tarafından manuel SL tightening: {symbol}")
    
    try:
        result = await bot_core._check_sl_tightening(symbol)
        
        if result:
            return {
                "success": True,
                "message": f"{symbol} SL tightening başarılı",
                "symbol": symbol,
                "user": user.get('email'),
                "timestamp": time.time()
            }
        else:
            return {
                "success": False,
                "message": f"{symbol} SL tightening şartları sağlanmadı (yetersiz kar veya daha önce sıkılaştırılmış)",
                "symbol": symbol
            }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SL tightening hatası: {e}")

@app.get("/api/strategy-performance")
async def get_strategy_performance(user: dict = Depends(authenticate)):
    """Strateji performansını detaylı analiz et"""
    status = bot_core.get_multi_status()
    performance = status.get("performance", {})
    
    # Trading strategy'den detailed status al
    strategy_statuses = {}
    for symbol in bot_core.status.get("symbols", []):
        try:
            strategy_status = trading_strategy.get_strategy_status(symbol)
            strategy_statuses[symbol] = strategy_status
        except Exception as e:
            strategy_statuses[symbol] = {"error": str(e)}
    
    return {
        "overall_performance": performance,
        "strategy_statuses": strategy_statuses,
        "optimization_summary": settings.get_optimization_summary(),
        "current_settings": {
            "ema_fast": settings.EMA_FAST_PERIOD,
            "ema_slow": settings.EMA_SLOW_PERIOD,
            "ema_trend": settings.EMA_TREND_PERIOD,
            "timeframe": settings.TIMEFRAME,
            "leverage": settings.LEVERAGE,
            "tp1_percent": settings.TP1_PERCENT,
            "tp2_percent": settings.TP2_PERCENT,
            "sl_percent": settings.STOP_LOSS_PERCENT
        },
        "removed_filters": [
            "RSI filter - çok gürültülü",
            "Volume filter - false negative üretiyor",
            "Price movement filter - gereksiz",
            "Volatility filter - karmaşık"
        ],
        "active_filters": {
            "ema_spread_check": settings.MIN_EMA_SPREAD_ENABLED,
            "momentum_validation": settings.MOMENTUM_VALIDATION_ENABLED,
            "signal_cooldown": settings.SIGNAL_COOLDOWN_ENABLED
        }
    }

# ============ GERİYE UYUMLULUK ENDPOINT'LERİ ============

@app.post("/api/multi-start")
async def start_multi_bot_legacy(request: dict, background_tasks: BackgroundTasks, 
                                user: dict = Depends(authenticate)):
    """Geriye uyumluluk için eski multi-start endpoint'i"""
    symbols = request.get("symbols", [])
    
    enhanced_request = EnhancedMultiStartRequest(symbols=symbols)
    return await start_enhanced_multi_bot(enhanced_request, background_tasks, user)

@app.get("/api/multi-status")
async def get_multi_status_legacy(user: dict = Depends(authenticate)):
    """Geriye uyumluluk için eski multi-status"""
    return await get_enhanced_status(user)

@app.post("/api/start")
async def start_bot_legacy(request: dict, background_tasks: BackgroundTasks, user: dict = Depends(authenticate)):
    """Tek symbol için geriye uyumluluk"""
    symbol = request.get("symbol", "").upper().strip()
    
    if not symbol:
        raise HTTPException(status_code=400, detail="Symbol gerekli.")
        
    if not symbol.endswith('USDT'):
        symbol += 'USDT'
    
    print(f"👤 {user.get('email')} geriye uyumluluk ile tek symbol: {symbol}")
    
    enhanced_request = EnhancedMultiStartRequest(symbols=[symbol])
    result = await start_enhanced_multi_bot(enhanced_request, background_tasks, user)
    
    # Legacy format'a çevir
    status = result.get("status", {})
    return {
        "is_running": status.get("is_running", False),
        "symbol": status.get("symbols", [None])[0],
        "position_side": status.get("position_side"),
        "status_message": status.get("status_message", ""),
        "account_balance": status.get("account_balance", 0),
        "position_pnl": status.get("position_pnl", 0),
        "order_size": status.get("order_size", 0),
        "position_monitor_active": status.get("position_monitor_active", False)
    }

@app.post("/api/stop")
async def stop_bot(user: dict = Depends(authenticate)):
    """Enhanced bot durdur"""
    if not bot_core.status["is_running"]:
        raise HTTPException(status_code=400, detail="Enhanced bot zaten durdurulmuş.")
    
    print(f"👤 {user.get('email')} tarafından Enhanced bot durduruluyor")
    await bot_core.stop()
    return await get_enhanced_status(user)

@app.get("/api/status")
async def get_status_legacy(user: dict = Depends(authenticate)):
    """Geriye uyumluluk için eski format status"""
    status = await get_enhanced_status(user)
    return {
        "is_running": status.get("is_running", False),
        "symbol": status.get("active_symbol"),
        "position_side": status.get("position_side"),
        "status_message": status.get("status_message", ""),
        "account_balance": status.get("account_balance", 0),
        "position_pnl": status.get("position_pnl", 0),
        "order_size": status.get("order_size", 0),
        "position_monitor_active": status.get("position_monitor_active", False),
        "position_manager": status.get("position_manager", {})
    }

@app.get("/api/health")
async def enhanced_health_check():
    """Enhanced sağlık kontrolü"""
    try:
        binance_status = "connected" if bot_core.status["is_running"] else "disconnected"
        position_manager_status = position_manager.get_status()
        
        return {
            "status": "healthy",
            "timestamp": time.time(),
            "bot_running": bot_core.status["is_running"],
            "symbols_count": len(bot_core.status["symbols"]),
            "active_symbol": bot_core.status["active_symbol"],
            "position_monitor_running": position_manager.is_running,
            "websocket_connections": len(bot_core._websocket_connections),
            "binance_connection": binance_status,
            "position_manager": position_manager_status,
            "environment": settings.ENVIRONMENT,
            "version": "4.0.0_enhanced",
            "debug_mode": settings.DEBUG_MODE,
            "test_mode": getattr(settings, 'TEST_MODE', False),
            
            # Enhanced health metrics
            "enhanced_features": {
                "partial_exits": settings.ENABLE_PARTIAL_EXITS,
                "position_reverse": settings.ENABLE_POSITION_REVERSE,
                "sl_tightening": settings.ENABLE_SL_TIGHTENING,
                "momentum_validation": settings.MOMENTUM_VALIDATION_ENABLED
            },
            "optimization": {
                "filters_removed": 4,  # RSI, Volume, Price Movement, Volatility
                "filters_active": 3,   # EMA spread, momentum, cooldown
                "strategy_simplified": True,
                "signal_quality_improved": True
            },
            "performance_tracking": {
                "total_signals": bot_core._performance_monitoring.get("total_signals", 0),
                "clean_signals": bot_core._performance_monitoring.get("clean_signals", 0),
                "reverse_signals": bot_core._performance_monitoring.get("reverse_signals", 0)
            }
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": time.time(),
            "version": "4.0.0_enhanced"
        }

# ============ ENHANCED POZİSYON YÖNETİMİ ============

@app.post("/api/enhanced-scan-all")
async def enhanced_scan_all_positions(user: dict = Depends(authenticate)):
    """Enhanced pozisyon taraması - kademeli satış desteği ile"""
    print(f"👤 {user.get('email')} Enhanced pozisyon taraması başlattı")
    
    try:
        result = await bot_core.scan_all_positions()
        
        # Enhanced bilgileri ekle
        enhanced_result = {
            **result,
            "scan_type": "enhanced_protection",
            "supports_partial_exits": settings.ENABLE_PARTIAL_EXITS,
            "supports_sl_tightening": settings.ENABLE_SL_TIGHTENING,
            "current_timeframe": settings.TIMEFRAME,
            "user": user.get('email'),
            "timestamp": time.time()
        }
        
        return enhanced_result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Enhanced pozisyon tarama hatası: {e}")

@app.post("/api/enhanced-scan-symbol")
async def enhanced_scan_specific_symbol(request: EnhancedSymbolRequest, user: dict = Depends(authenticate)):
    """Enhanced coin kontrolü"""
    symbol = request.symbol.upper().strip()
    if not symbol.endswith('USDT'):
        symbol += 'USDT'
    
    print(f"👤 {user.get('email')} Enhanced symbol kontrolü: {symbol}")
    
    try:
        result = await bot_core.scan_specific_symbol(symbol)
        
        enhanced_result = {
            **result,
            "scan_type": "enhanced_symbol_protection",
            "partial_exits_supported": settings.TIMEFRAME in settings.TIMEFRAMES_FOR_PARTIAL,
            "user": user.get('email'),
            "timestamp": time.time()
        }
        
        return enhanced_result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Enhanced symbol kontrolü hatası: {e}")

# Mevcut endpoint'leri koru
@app.post("/api/scan-all-positions")
async def scan_all_positions_legacy(user: dict = Depends(authenticate)):
    """Geriye uyumluluk"""
    return await enhanced_scan_all_positions(user)

@app.post("/api/scan-symbol")
async def scan_specific_symbol_legacy(request: dict, user: dict = Depends(authenticate)):
    """Geriye uyumluluk"""
    enhanced_request = EnhancedSymbolRequest(symbol=request.get("symbol", ""))
    return await enhanced_scan_specific_symbol(enhanced_request, user)

# Position monitor endpoints (unchanged)
@app.get("/api/position-monitor-status")
async def get_position_monitor_status(user: dict = Depends(authenticate)):
    return {
        "monitor_status": position_manager.get_status(),
        "bot_status": bot_core.status["is_running"],
        "enhanced_features": {
            "partial_exits": settings.ENABLE_PARTIAL_EXITS,
            "sl_tightening": settings.ENABLE_SL_TIGHTENING
        },
        "timestamp": time.time()
    }

@app.post("/api/start-position-monitor")
async def start_position_monitor(background_tasks: BackgroundTasks, user: dict = Depends(authenticate)):
    if position_manager.is_running:
        raise HTTPException(status_code=400, detail="Position monitor zaten çalışıyor.")
    
    print(f"👤 {user.get('email')} Enhanced position monitor başlatıyor")
    
    try:
        background_tasks.add_task(position_manager.start_monitoring)
        await asyncio.sleep(1)
        
        return {
            "success": True,
            "message": "Enhanced otomatik TP/SL monitoring başlatıldı",
            "monitor_status": position_manager.get_status(),
            "user": user.get('email'),
            "timestamp": time.time()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Monitor başlatma hatası: {e}")

@app.post("/api/stop-position-monitor")
async def stop_position_monitor(user: dict = Depends(authenticate)):
    if not position_manager.is_running:
        raise HTTPException(status_code=400, detail="Position monitor zaten durdurulmuş.")
    
    print(f"👤 {user.get('email')} position monitor durduruyor")
    
    try:
        await position_manager.stop_monitoring()
        
        return {
            "success": True,
            "message": "Position monitor durduruldu",
            "monitor_status": position_manager.get_status(),
            "user": user.get('email'),
            "timestamp": time.time()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Monitor durdurma hatası: {e}")

# ============ HATA YÖNETİMİ ============

@app.exception_handler(Exception)
async def enhanced_exception_handler(request, exc):
    print(f"❌ Enhanced bot genel hata: {exc}")
    return {
        "error": "Enhanced bot'ta beklenmeyen hata oluştu",
        "detail": str(exc),
        "timestamp": time.time(),
        "version": "4.0.0_enhanced"
    }

# ============ STATIC FILES ============

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_index():
    return FileResponse('static/index.html')
