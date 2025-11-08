from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.security import HTTPBearer
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import time

from .bollinger_bot_core import bollinger_bot
from .config import settings
from .firebase_manager import firebase_manager
from .binance_client import binance_client

bearer_scheme = HTTPBearer()

app = FastAPI(
    title="Bollinger Bands Al-Sat Bot",
    version="1.0.0",
    description="Her dakika 1 LONG + 1 SHORT - Bollinger Bantları Stratejisi"
)


# ===================== STARTUP =====================
@app.on_event("startup")
async def startup_event():
    """✅ Bollinger Bands Bot başlangıcı"""
    print("🚀 Bollinger Bands Al-Sat Bot başlatılıyor...")
    print("=" * 70)
    print("📊 STRATEJİ: Her dakika 1 LONG + 1 SHORT")
    print("💰 POZİSYON: Sabit 10 USDT")
    print("📈 BOLLINGER: 20 period, 2.0 std dev")
    print("⏰ TIMEFRAME: 1 dakika")
    print("=" * 70)

    if settings.validate_settings():
        settings.print_settings()
        print("✅ Tüm ayarlar geçerli - Bot hazır!")
    else:
        print("❌ Ayar hatalarını kontrol edin!")


# ===================== SHUTDOWN =====================
@app.on_event("shutdown")
async def shutdown_event():
    """Kapatma"""
    try:
        if bollinger_bot.status["is_running"]:
            await bollinger_bot.stop()
        await binance_client.close()
        print("✅ Bot güvenli kapatıldı")
    except Exception as e:
        print(f"⚠️ Kapatma hatası: {e}")


# ===================== MODELLER =====================
class StartRequest(BaseModel):
    symbol: str


# ===================== KİMLİK DOĞRULAMA =====================
async def authenticate(token: str = Depends(bearer_scheme)):
    """Firebase authentication"""
    try:
        user = firebase_manager.verify_token(token.credentials)
        if not user:
            raise HTTPException(status_code=401, detail="Geçersiz token")
        return user
    except:
        raise HTTPException(status_code=401, detail="Kimlik doğrulama hatası")


# ===================== BOT ENDPOINTLERİ =====================
@app.post("/api/start")
async def start_bot(
    request: StartRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(authenticate)
):
    """📊 Bollinger Bot başlatma"""
    try:
        if bollinger_bot.status["is_running"]:
            raise HTTPException(status_code=400, detail="Bot zaten çalışıyor")

        symbol = request.symbol.upper().strip()
        if not symbol:
            raise HTTPException(status_code=400, detail="Symbol gerekli")

        user_email = user.get('email', 'anonymous')
        print(f"👤 {user_email} botu başlatıyor: {symbol}")

        # Background task ile başlat
        background_tasks.add_task(bollinger_bot.start, symbol)

        return JSONResponse({
            "success": True,
            "message": f"Bollinger Bot {symbol} için başlatılıyor...",
            "symbol": symbol,
            "user": user_email,
            "strategy": "Bollinger Bands Dual Position",
            "info": {
                "position_size": f"{settings.POSITION_SIZE_USDT} USDT",
                "leverage": f"{settings.LEVERAGE}x",
                "timeframe": settings.TIMEFRAME,
                "bb_period": settings.BB_PERIOD
            }
        })

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/stop")
async def stop_bot(user: dict = Depends(authenticate)):
    """🛑 Bot durdurma"""
    try:
        if not bollinger_bot.status["is_running"]:
            raise HTTPException(status_code=400, detail="Bot zaten durdurulmuş")

        await bollinger_bot.stop()

        return JSONResponse({
            "success": True,
            "message": "Bot durduruldu",
            "user": user.get('email', 'anonymous')
        })

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/status")
async def get_status(user: dict = Depends(authenticate)):
    """📊 Bot durumu"""
    try:
        status = bollinger_bot.get_status()
        return JSONResponse(status)
    except Exception as e:
        return JSONResponse({
            "is_running": False,
            "status_message": f"Status hatası: {str(e)}",
            "timestamp": time.time()
        })


@app.get("/api/health")
async def health_check():
    """🏥 Sağlık kontrolü"""
    try:
        status = bollinger_bot.get_status()
        return JSONResponse({
            "status": "healthy",
            "bot_running": status["is_running"],
            "strategy": "Bollinger Bands Dual Position",
            "version": "1.0.0",
            "timestamp": time.time(),
            "config": {
                "environment": settings.ENVIRONMENT,
                "timeframe": settings.TIMEFRAME,
                "position_size": f"{settings.POSITION_SIZE_USDT} USDT",
                "leverage": f"{settings.LEVERAGE}x"
            }
        })
    except Exception as e:
        return JSONResponse({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": time.time()
        }, status_code=503)


# ===================== HESAP BİLGİLERİ =====================
@app.get("/api/account-info")
async def get_account_info(user: dict = Depends(authenticate)):
    """💰 Hesap bilgileri"""
    try:
        if not binance_client.client:
            await binance_client.initialize()

        balance = await binance_client.get_account_balance()

        await binance_client._rate_limit_delay()
        all_positions = await binance_client.client.futures_position_information()
        open_positions = [p for p in all_positions if float(p['positionAmt']) != 0]

        position_summary = []
        total_pnl = 0.0

        for pos in open_positions:
            pnl = float(pos['unRealizedProfit'])
            total_pnl += pnl

            position_summary.append({
                "symbol": pos['symbol'],
                "side": "LONG" if float(pos['positionAmt']) > 0 else "SHORT",
                "size": abs(float(pos['positionAmt'])),
                "entry_price": float(pos['entryPrice']),
                "mark_price": float(pos['markPrice']),
                "pnl": pnl
            })

        return JSONResponse({
            "account_balance": balance,
            "total_pnl": total_pnl,
            "open_positions_count": len(open_positions),
            "positions": position_summary,
            "user": user.get('email', 'anonymous'),
            "timestamp": time.time()
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===================== STATIC FILES =====================
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_index():
    """Ana sayfa"""
    return FileResponse('static/index.html')


# ===================== GLOBAL ERROR HANDLER =====================
@app.exception_handler(Exception)
async def exception_handler(request, exc):
    """Global hata yakalama"""
    error_msg = str(exc)
    print(f"❌ Global hata: {error_msg}")

    return JSONResponse({
        "error": "Bot hatası",
        "detail": error_msg,
        "timestamp": time.time()
    }, status_code=500)


print("✅ Bollinger Bands Bot API yüklendi!")
print("📊 Strateji: Her dakika 1 LONG + 1 SHORT pozisyon")
