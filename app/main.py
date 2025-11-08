# app/main.py - HIZLI SCALPING BOT API

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.security import HTTPBearer
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import time

from .config import settings
from .firebase_manager import firebase_manager
from .binance_client import create_binance_client
from .fast_scalping_strategy import FastScalpingStrategy
from .professional_scalping_strategy import ProfessionalScalpingStrategy
from .fast_scalping_bot import create_bot

bearer_scheme = HTTPBearer()

app = FastAPI(
    title="Professional Scalping Bot",
    version="2.0.0",
    description="Ultra Professional Scalping - Pullback + Volume + Trend"
)

# Instance'ları global olarak oluştur
binance_client = create_binance_client(settings)

# Strateji seçimi - config'e göre
if settings.USE_PROFESSIONAL_STRATEGY:
    strategy = ProfessionalScalpingStrategy()
    print("✅ PROFESSIONAL SCALPING STRATEGY aktif!")
else:
    strategy = FastScalpingStrategy()
    print("✅ Fast Scalping Strategy aktif")

fast_scalping_bot = create_bot(settings, binance_client, strategy, firebase_manager)


# ===================== STARTUP =====================
@app.on_event("startup")
async def startup_event():
    """✅ Professional Scalping Bot başlangıcı"""
    print("🚀 Professional Scalping Bot başlatılıyor...")
    print("=" * 70)
    
    if settings.USE_PROFESSIONAL_STRATEGY:
        print("🔥 STRATEJİ: PROFESSIONAL SCALPING")
        print("   📊 Pullback Detection + Volume Spike + Trend")
        print(f"   🎯 TP: %{settings.PRO_TP_PERCENT*100:.2f} | SL: %{settings.PRO_SL_PERCENT*100:.2f}")
        print(f"   ✨ Min Confidence: {settings.PRO_MIN_CONFIDENCE}%")
        print(f"   📈 Min Trend: %{settings.PRO_MIN_TREND*100:.3f}")
    else:
        print("⚡ STRATEJİ: Optimized Scalping (Eski)")
        print(f"   🎯 TP: %{settings.TAKE_PROFIT_PERCENT*100:.2f} | SL: %{settings.STOP_LOSS_PERCENT*100:.2f}")
    
    print(f"💰 POZİSYON: %{settings.BALANCE_USAGE_PERCENT*100:.0f} bakiye")
    print(f"📈 KALDIRAÇ: {settings.LEVERAGE}x")
    print("⏰ TIMEFRAME: 1 dakika")
    print(f"⏳ COOLDOWN: {settings.TRADE_COOLDOWN_SECONDS}s")
    print(f"🔢 GÜNLÜK LİMİT: {settings.MAX_DAILY_TRADES} trade")
    print("=" * 70)
    print("🎯 HEDEF: Günlük %5-10, Win Rate %75+")
    print("=" * 70)
    
    if settings.validate_settings():
        print("✅ Tüm ayarlar geçerli - Bot hazır!")
    else:
        print("❌ Ayar hatalarını kontrol edin!")


# ===================== SHUTDOWN =====================
@app.on_event("shutdown")
async def shutdown_event():
    """Kapatma"""
    try:
        if fast_scalping_bot and fast_scalping_bot.status["is_running"]:
            await fast_scalping_bot.stop()
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
    """⚡ Hızlı Scalping Bot başlatma"""
    try:
        if fast_scalping_bot.status["is_running"]:
            raise HTTPException(status_code=400, detail="Bot zaten çalışıyor")
        
        symbol = request.symbol.upper().strip()
        if not symbol:
            raise HTTPException(status_code=400, detail="Symbol gerekli")
        
        user_email = user.get('email', 'anonymous')
        print(f"👤 {user_email} botu başlatıyor: {symbol}")
        
        # Background task ile başlat
        background_tasks.add_task(fast_scalping_bot.start, symbol)
        
        return JSONResponse({
            "success": True,
            "message": f"Professional Scalping Bot {symbol} için başlatılıyor...",
            "symbol": symbol,
            "user": user_email,
            "strategy": "Professional Pullback Scalping v2.0" if settings.USE_PROFESSIONAL_STRATEGY else "Fast Scalping v1.0",
            "info": {
                "position_size": f"%{settings.BALANCE_USAGE_PERCENT*100:.0f} bakiye",
                "leverage": f"{settings.LEVERAGE}x",
                "timeframe": "1m",
                "tp": f"%{settings.PRO_TP_PERCENT*100:.2f}" if settings.USE_PROFESSIONAL_STRATEGY else f"%{settings.TAKE_PROFIT_PERCENT*100:.2f}",
                "sl": f"%{settings.PRO_SL_PERCENT*100:.2f}" if settings.USE_PROFESSIONAL_STRATEGY else f"%{settings.STOP_LOSS_PERCENT*100:.2f}",
                "cooldown": f"{settings.TRADE_COOLDOWN_SECONDS}s",
                "daily_limit": settings.MAX_DAILY_TRADES,
                "min_confidence": f"{settings.PRO_MIN_CONFIDENCE}%" if settings.USE_PROFESSIONAL_STRATEGY else "N/A"
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
        if not fast_scalping_bot.status["is_running"]:
            raise HTTPException(status_code=400, detail="Bot zaten durdurulmuş")
        
        await fast_scalping_bot.stop()
        
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
        status = fast_scalping_bot.get_status()
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
        status = fast_scalping_bot.get_status()
        return JSONResponse({
            "status": "healthy",
            "bot_running": status["is_running"],
            "strategy": "Optimized Scalping v2.0",
            "version": "2.0.0",
            "timestamp": time.time(),
            "config": {
                "environment": settings.ENVIRONMENT,
                "timeframe": "1m",
                "position_size": f"%{settings.BALANCE_USAGE_PERCENT*100:.0f} bakiye",
                "leverage": f"{settings.LEVERAGE}x",
                "tp": f"%{settings.TAKE_PROFIT_PERCENT*100:.2f}",
                "sl": f"%{settings.STOP_LOSS_PERCENT*100:.2f}",
                "cooldown": f"{settings.TRADE_COOLDOWN_SECONDS}s",
                "daily_limit": settings.MAX_DAILY_TRADES,
                "min_momentum": f"%{settings.MIN_MOMENTUM_PERCENT*100:.3f}"
            }
        })
    except Exception as e:
        return JSONResponse({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": time.time()
        }, status_code=503)


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
                "pnl": pnl,
                "leverage": int(pos['leverage'])
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


print("✅ Optimized Scalping Bot API yüklendi!")
print("⚡ Strateji: Dinamik pozisyon + Cooldown + Günlük limit!")
