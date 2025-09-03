# app/main.py

import asyncio
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.security import HTTPBearer
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from .bot_core import bot_core
from .config import settings
from .firebase_manager import firebase_manager

bearer_scheme = HTTPBearer()

async def authenticate(token: str = Depends(bearer_scheme)):
    """Gelen Firebase ID Token'ını doğrular."""
    user = firebase_manager.verify_token(token.credentials)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Geçersiz veya süresi dolmuş güvenlik token'ı.",
        )
    print(f"✅ Doğrulanan kullanıcı: {user.get('email')}")
    return user

app = FastAPI(title="Multi-Coin Futures Bot", version="4.0.0")

@app.on_event("shutdown")
async def shutdown_event():
    """Uygulama kapanırken botu durdurur."""
    if bot_core.status["is_running"]:
        print("🛑 Uygulama kapanıyor, bot durduruluyor...")
        await bot_core.stop_all()

class AddCoinRequest(BaseModel):
    symbol: str
    order_size_usdt: float = 50.0  # Varsayılan işlem boyutu

class RemoveCoinRequest(BaseModel):
    symbol: str

@app.post("/api/start-monitoring")
async def start_monitoring(user: dict = Depends(authenticate)):
    """Bot core'unu başlatır (coin eklenmesi için hazır hale getirir)"""
    await bot_core.start_monitoring()
    return {"message": "Bot monitoring başlatıldı", "status": bot_core.status}

@app.post("/api/add-coin")
async def add_coin(request: AddCoinRequest, background_tasks: BackgroundTasks, user: dict = Depends(authenticate)):
    """Yeni bir coin ekler ve işlem başlatır"""
    if request.order_size_usdt <= 0:
        raise HTTPException(status_code=400, detail="İşlem boyutu 0'dan büyük olmalı.")
    
    if request.order_size_usdt > bot_core.status["total_balance"]:
        raise HTTPException(status_code=400, detail="İşlem boyutu toplam bakiyeden büyük olamaz.")
    
    success = await bot_core.add_coin(request.symbol.upper(), request.order_size_usdt)
    
    if not success:
        raise HTTPException(status_code=400, detail=f"{request.symbol} eklenirken sorun oluştu.")
    
    return {
        "message": f"{request.symbol.upper()} başarıyla eklendi",
        "status": bot_core.get_detailed_status()
    }

@app.post("/api/remove-coin")
async def remove_coin(request: RemoveCoinRequest, user: dict = Depends(authenticate)):
    """Coin'i izlemekten çıkarır ve pozisyon varsa kapatır"""
    success = await bot_core.remove_coin(request.symbol.upper())
    
    if not success:
        raise HTTPException(status_code=400, detail=f"{request.symbol} bulunamadı veya çıkarılamadı.")
    
    return {
        "message": f"{request.symbol.upper()} başarıyla çıkarıldı",
        "status": bot_core.get_detailed_status()
    }

@app.post("/api/stop-all")
async def stop_all(user: dict = Depends(authenticate)):
    """Tüm coin'leri durdurur ve botu kapatır"""
    await bot_core.stop_all()
    return {"message": "Tüm işlemler durduruldu", "status": bot_core.status}

@app.get("/api/status")
async def get_status(user: dict = Depends(authenticate)):
    """Bot'un detaylı durumunu döndürür"""
    return bot_core.get_detailed_status()

@app.get("/api/active-coins")
async def get_active_coins(user: dict = Depends(authenticate)):
    """Aktif olarak izlenen coin'lerin listesini döndürür"""
    return {
        "active_coins": list(bot_core.status["active_coins"].keys()),
        "total_positions": bot_core.status["total_positions"],
        "total_balance": bot_core.status["total_balance"]
    }

# Eski API endpoint'leri için uyumluluk (mevcut frontend'i bozmamak için)
class LegacyStartRequest(BaseModel):
    symbol: str | None = None

@app.post("/api/start")
async def legacy_start_bot(request: LegacyStartRequest, background_tasks: BackgroundTasks, user: dict = Depends(authenticate)):
    """Eski API uyumluluğu - tek coin başlatma"""
    if not request.symbol:
        # Eğer sembol belirtilmemişse sadece monitoring'i başlat
        await bot_core.start_monitoring()
        return bot_core.status
    
    # Bot monitoring'i başlat
    await bot_core.start_monitoring()
    await asyncio.sleep(0.5)
    
    # Coin'i ekle
    success = await bot_core.add_coin(request.symbol.upper(), settings.INITIAL_ORDER_SIZE_USDT)
    
    if not success:
        raise HTTPException(status_code=400, detail=f"{request.symbol} başlatılamadı.")
    
    return bot_core.get_detailed_status()

@app.post("/api/stop")
async def legacy_stop_bot(user: dict = Depends(authenticate)):
    """Eski API uyumluluğu - tüm bot'u durdurma"""
    await bot_core.stop_all()
    return bot_core.status

# Statik dosyaları sunmak için
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_index():
    """Ana HTML sayfasını sunar."""
    return FileResponse('static/index.html')
