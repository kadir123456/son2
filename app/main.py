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
    print(f"Doğrulanan kullanıcı: {user.get('email')}")
    return user

app = FastAPI(title="Binance Futures Bot", version="3.0.0") # Versiyon güncellendi

@app.on_event("shutdown")
async def shutdown_event():
    """Uygulama kapanırken botu durdurur."""
    if bot_core.status["is_running"]:
        print("Uygulama kapanıyor, bot durduruluyor...")
        await bot_core.stop()

class StartRequest(BaseModel):
    symbol: str | None = None # Sembol artık opsiyonel

@app.post("/api/start")
async def start_bot(request: StartRequest, background_tasks: BackgroundTasks, user: dict = Depends(authenticate)):
    """Botu başlatma isteğini işler."""
    if bot_core.status["is_running"]:
        raise HTTPException(status_code=400, detail="Bot zaten çalışıyor.")
    
    # Eğer sembol belirtilirse, sadece o sembol ile başlar (ve listede o yoksa ekler).
    # Belirtilmezse, config'deki SYMBOLS_TO_TRADE listesinden başlar.
    background_tasks.add_task(bot_core.start, request.symbol)
    
    # Botun durumunun hemen güncellenmesi için kısa bir bekleme
    await asyncio.sleep(1) 
    return bot_core.status

@app.post("/api/stop")
async def stop_bot(user: dict = Depends(authenticate)):
    """Botu durdurma isteğini işler."""
    if not bot_core.status["is_running"]:
        raise HTTPException(status_code=400, detail="Bot zaten durdurulmuş.")
    await bot_core.stop()
    return bot_core.status

@app.get("/api/status")
async def get_status(user: dict = Depends(authenticate)):
    """Botun anlık durumunu döndürür."""
    return bot_core.status

# Statik dosyaları sunmak için
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_index():
    """Ana HTML sayfasını sunar."""
    return FileResponse('static/index.html')