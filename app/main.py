# app/main.py - GÜNCELLENMIŞ HALİ

import asyncio
import time
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.security import HTTPBearer
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from .bot_core import bot_core
from .config import settings
from .firebase_manager import firebase_manager
from .position_manager import position_manager  # YENİ IMPORT

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

rate_limiter = RateLimiter(max_requests=30, time_window=60)

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

app = FastAPI(title="Binance Futures Bot", version="2.2.0")

@app.on_event("startup")
async def startup_event():
    """Uygulama başlangıcında ayarları doğrula"""
    print("🚀 Bot başlatılıyor...")
    settings.validate_settings()
    settings.print_settings()

@app.on_event("shutdown")
async def shutdown_event():
    if bot_core.status["is_running"]:
        await bot_core.stop()
    await position_manager.stop_monitoring()

class StartRequest(BaseModel):
    symbol: str

class SymbolRequest(BaseModel):
    symbol: str

# ============ MEVCUT ENDPOINT'LER ============

@app.post("/api/start")
async def start_bot(request: StartRequest, background_tasks: BackgroundTasks, user: dict = Depends(authenticate)):
    if bot_core.status["is_running"]:
        raise HTTPException(status_code=400, detail="Bot zaten çalışıyor.")
    
    symbol = request.symbol.upper().strip()
    
    if not symbol.endswith('USDT'):
        symbol += 'USDT'
    
    if len(symbol) < 6 or len(symbol) > 20:
        raise HTTPException(status_code=400, detail="Geçersiz sembol formatı.")
    
    print(f"👤 {user.get('email')} tarafından bot başlatılıyor: {symbol}")
    
    background_tasks.add_task(bot_core.start, symbol)
    await asyncio.sleep(1.5)
    return bot_core.status

@app.post("/api/stop")
async def stop_bot(user: dict = Depends(authenticate)):
    if not bot_core.status["is_running"]:
        raise HTTPException(status_code=400, detail="Bot zaten durdurulmuş.")
    
    print(f"👤 {user.get('email')} tarafından bot durduruluyor")
    await bot_core.stop()
    return bot_core.status

@app.get("/api/status")
async def get_status(user: dict = Depends(authenticate)):
    # Durum bilgisine position manager durumunu da ekle
    status = bot_core.status.copy()
    status["position_manager"] = position_manager.get_status()
    return status

@app.get("/api/health")
async def health_check():
    """Sağlık kontrolü - authentication gerektirmez"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "bot_running": bot_core.status["is_running"],
        "position_monitor_running": position_manager.is_running,
        "version": "2.2.0"
    }

# ============ YENİ ENDPOINT'LER - POZISYON YÖNETİMİ ============

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
            "monitor_status": result.get("monitor_status")
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
            "timestamp": time.time()
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

# ============ STATIC FILES ============

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_index():
    return FileResponse('static/index.html')
