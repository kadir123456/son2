# app/main.py - Basit EMA Cross Bot API

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

app = FastAPI(title="Basit EMA Cross Bot v1.0", version="1.0.0")

@app.on_event("startup")
async def startup_event():
    """Uygulama başlangıcı"""
    print("🚀 Basit EMA Cross Bot v1.0 başlatılıyor...")
    settings.validate_settings()
    settings.print_settings()

@app.on_event("shutdown")
async def shutdown_event():
    if bot_core.status["is_running"]:
        await bot_core.stop()
    await position_manager.stop_monitoring()

# ============ MODEL'LER ============
class MultiStartRequest(BaseModel):
    symbols: List[str]

class SymbolRequest(BaseModel):
    symbol: str

# ============ KİMLİK DOĞRULAMA ============
async def authenticate(token: str = Depends(bearer_scheme)):
    """Firebase authentication"""
    user = firebase_manager.verify_token(token.credentials)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Geçersiz veya süresi dolmuş güvenlik token'ı.",
        )
    print(f"✅ Bot kullanıcısı: {user.get('email')}")
    return user

# ============ TEMEL ENDPOINT'LER ============

@app.post("/api/multi-start")
async def start_multi_bot(request: MultiStartRequest, background_tasks: BackgroundTasks, 
                         user: dict = Depends(authenticate)):
    """Multi-coin bot başlat"""
    if bot_core.status["is_running"]:
        raise HTTPException(status_code=400, detail="Bot zaten çalışıyor.")
    
    if not request.symbols or len(request.symbols) == 0:
        raise HTTPException(status_code=400, detail="En az bir symbol gerekli.")
    
    if len(request.symbols) > 10:
        raise HTTPException(status_code=400, detail="Maksimum 10 symbol desteklenir.")
    
    # Symbolları normalize et
    normalized_symbols = []
    for symbol in request.symbols:
        symbol = symbol.upper().strip()
        
        if not symbol.endswith('USDT'):
            symbol += 'USDT'
        
        if len(symbol) < 6 or len(symbol) > 20:
            raise HTTPException(status_code=400, detail=f"Geçersiz sembol formatı: {symbol}")
        
        if symbol not in normalized_symbols:
            normalized_symbols.append(symbol)
    
    if len(normalized_symbols) == 0:
        raise HTTPException(status_code=400, detail="Geçerli sembol bulunamadı.")
    
    print(f"👤 {user.get('email')} tarafından multi-coin bot başlatılıyor:")
    print(f"   Symbols: {', '.join(normalized_symbols)}")
    
    try:
        background_tasks.add_task(bot_core.start, normalized_symbols)
        await asyncio.sleep(2)
        
        current_status = bot_core.get_multi_status()
        
        return {
            "success": True,
            "message": f"Bot {len(normalized_symbols)} coin için başlatılıyor...",
            "symbols": normalized_symbols,
            "user": user.get('email'),
            "timestamp": time.time(),
            "status": current_status
        }
        
    except Exception as e:
        print(f"❌ Bot başlatma hatası: {e}")
        raise HTTPException(status_code=500, detail=f"Bot başlatılırken hata: {str(e)}")

@app.get("/api/multi-status")
async def get_multi_status(user: dict = Depends(authenticate)):
    """Bot durumunu döndür"""
    return bot_core.get_multi_status()

@app.post("/api/stop")
async def stop_bot(user: dict = Depends(authenticate)):
    """Bot durdur"""
    if not bot_core.status["is_running"]:
        raise HTTPException(status_code=400, detail="Bot zaten durdurulmuş.")
    
    print(f"👤 {user.get('email')} tarafından bot durduruluyor")
    await bot_core.stop()
    return bot_core.get_multi_status()

@app.get("/api/status")
async def get_status_legacy(user: dict = Depends(authenticate)):
    """Eski format status"""
    status = bot_core.get_multi_status()
    return {
        "is_running": status.get("is_running", False),
        "symbol": status.get("active_symbol"),
        "position_side": status.get("position_side"),
        "status_message": status.get("status_message", ""),
        "account_balance": status.get("account_balance", 0),
        "position_pnl": status.get("position_pnl", 0),
        "order_size": status.get("order_size", 0)
    }

@app.post("/api/start")
async def start_bot_legacy(request: dict, background_tasks: BackgroundTasks, user: dict = Depends(authenticate)):
    """Tek symbol için geriye uyumluluk"""
    symbol = request.get("symbol", "").upper().strip()
    
    if not symbol:
        raise HTTPException(status_code=400, detail="Symbol gerekli.")
        
    if not symbol.endswith('USDT'):
        symbol += 'USDT'
    
    print(f"👤 {user.get('email')} tek symbol: {symbol}")
    
    multi_request = MultiStartRequest(symbols=[symbol])
    result = await start_multi_bot(multi_request, background_tasks, user)
    
    # Legacy format'a çevir
    status = result.get("status", {})
    return {
        "is_running": status.get("is_running", False),
        "symbol": status.get("symbols", [None])[0],
        "position_side": status.get("position_side"),
        "status_message": status.get("status_message", ""),
        "account_balance": status.get("account_balance", 0),
        "position_pnl": status.get("position_pnl", 0),
        "order_size": status.get("order_size", 0)
    }

@app.get("/api/health")
async def health_check():
    """Sağlık kontrolü"""
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
            "version": "1.0.0_simple",
            "strategy": "simple_ema_cross",
            "debug_mode": settings.DEBUG_MODE,
            "test_mode": settings.TEST_MODE
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": time.time(),
            "version": "1.0.0_simple"
        }

# ============ POZİSYON YÖNETİMİ ============

@app.post("/api/scan-all-positions")
async def scan_all_positions(user: dict = Depends(authenticate)):
    """Tüm açık pozisyonları tara"""
    print(f"👤 {user.get('email')} pozisyon taraması başlattı")
    
    try:
        # Manuel tarama yap
        await position_manager._scan_and_protect()
        
        return {
            "success": True,
            "message": "Tüm pozisyonlar TP/SL koruması ile tarandı",
            "monitor_status": position_manager.get_status(),
            "user": user.get('email'),
            "timestamp": time.time()
        }
        
    except Exception as e:
        return {"success": False, "message": f"Tarama hatası: {e}"}

@app.post("/api/scan-symbol")
async def scan_specific_symbol(request: dict, user: dict = Depends(authenticate)):
    """Belirli bir coin için kontrol"""
    symbol = request.get("symbol", "").upper().strip()
    if not symbol.endswith('USDT'):
        symbol += 'USDT'
    
    print(f"👤 {user.get('email')} symbol kontrolü: {symbol}")
    
    try:
        success = await position_manager.manual_scan_symbol(symbol)
        return {
            "success": success,
            "symbol": symbol,
            "message": f"{symbol} için TP/SL kontrolü tamamlandı"
        }
    except Exception as e:
        return {"success": False, "message": f"{symbol} kontrolü hatası: {e}"}

@app.get("/api/position-monitor-status")
async def get_position_monitor_status(user: dict = Depends(authenticate)):
    return {
        "monitor_status": position_manager.get_status(),
        "bot_status": bot_core.status["is_running"],
        "timestamp": time.time()
    }

@app.post("/api/start-position-monitor")
async def start_position_monitor(background_tasks: BackgroundTasks, user: dict = Depends(authenticate)):
    if position_manager.is_running:
        raise HTTPException(status_code=400, detail="Position monitor zaten çalışıyor.")
    
    print(f"👤 {user.get('email')} position monitor başlatıyor")
    
    try:
        background_tasks.add_task(position_manager.start_monitoring)
        await asyncio.sleep(1)
        
        return {
            "success": True,
            "message": "Otomatik TP/SL monitoring başlatıldı",
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
async def exception_handler(request, exc):
    print(f"❌ Bot genel hata: {exc}")
    return {
        "error": "Bot'ta beklenmeyen hata oluştu",
        "detail": str(exc),
        "timestamp": time.time(),
        "version": "1.0.0_simple"
    }

# ============ STATIC FILES ============

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_index():
    return FileResponse('static/index.html')
