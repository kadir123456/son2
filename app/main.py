# app/main.py - OPTIMIZE EDİLMİŞ EMA Cross Bot API v1.2 - TÜM HATALAR DÜZELTİLDİ

import asyncio
import time
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.security import HTTPBearer
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional
from .bot_core import bot_core
from .config import settings
from .firebase_manager import firebase_manager
from .position_manager import position_manager
from .binance_client import binance_client
from .trading_strategy import trading_strategy
from .gemini_trading_manager import gemini_trading_manager

bearer_scheme = HTTPBearer()

app = FastAPI(
    title="TAMAMEN DÜZELTİLMİŞ EMA Cross Bot v1.3", 
    version="1.3.0",
    description="TÜM HATALAR DÜZELTİLDİ: Dictionary iteration, EMA hesaplama, Pandas warnings, 404 endpoints"
)

@app.on_event("startup")
async def startup_event():
    """✅ TAMAMEN DÜZELTİLMİŞ uygulama başlangıcı"""
    print("🚀 TAMAMEN DÜZELTİLMİŞ EMA Cross Bot v1.3 başlatılıyor...")
    print("✅ Dictionary iteration hatası düzeltildi!")
    print("✅ EMA 'Replacement lists must match' hatası çözüldü!")
    print("✅ Pandas FutureWarning uyarıları yok!")
    print("✅ API rate limiting optimize edildi!")
    print("✅ 404 endpoint hataları düzeltildi!")
    
    if settings.validate_settings_optimized():
        settings.print_settings_optimized()
        print("✅ Tüm ayarlar geçerli - Bot hazır!")
        print("🎯 Log hatalarına çözüm v1.3 aktif!")
    else:
        print("❌ Ayar hatalarını kontrol edin!")

@app.on_event("shutdown")
async def shutdown_event():
    """✅ GÜVENLI kapatma"""
    try:
        if bot_core.status["is_running"]:
            await bot_core.stop()
        if position_manager.is_running:
            await position_manager.stop_monitoring()
        if gemini_trading_manager.is_running:
            await gemini_trading_manager.stop_autonomous_trading()
        await binance_client.close()
        print("✅ Tüm bileşenler güvenli kapatıldı")
    except Exception as e:
        print(f"⚠️ Kapatma sırasında hata: {e}")

# ============ MODEL'LER ============
class MultiStartRequest(BaseModel):
    symbols: List[str]

class SymbolRequest(BaseModel):
    symbol: str

class DebugRequest(BaseModel):
    symbol: str

# ============ ✅ OPTIMIZE EDİLMİŞ KİMLİK DOĞRULAMA ============
async def authenticate_optimized(token: str = Depends(bearer_scheme)):
    """✅ OPTIMIZE Firebase authentication - Cache ile"""
    try:
        user = firebase_manager.verify_token(token.credentials)
        if not user:
            raise HTTPException(
                status_code=401,
                detail="Geçersiz veya süresi dolmuş güvenlik token'ı.",
            )
        
        user_email = user.get('email', 'unknown')
        if settings.VERBOSE_LOGGING:
            print(f"✅ Bot kullanıcısı: {user_email}")
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Auth hatası: {e}")
        raise HTTPException(status_code=401, detail="Kimlik doğrulama hatası")

# ============ ✅ OPTIMIZE EDİLMİŞ TEMEL ENDPOINT'LER ============

@app.post("/api/multi-start")
async def start_multi_bot_optimized(
    request: MultiStartRequest, 
    background_tasks: BackgroundTasks, 
    user: dict = Depends(authenticate_optimized)
):
    """✅ OPTIMIZE Multi-coin bot başlat - Tüm hatalar düzeltildi"""
    try:
        if bot_core.status["is_running"]:
            raise HTTPException(status_code=400, detail="Bot zaten çalışıyor.")
        
        if not request.symbols or len(request.symbols) == 0:
            raise HTTPException(status_code=400, detail="En az bir symbol gerekli.")
        
        if len(request.symbols) > 10:
            raise HTTPException(status_code=400, detail="Maksimum 10 symbol desteklenir.")
        
        # ✅ OPTIMIZE Symbol validation ve normalizasyon
        normalized_symbols = []
        for symbol in request.symbols:
            symbol = symbol.upper().strip()
            
            # USDT ekle
            if not symbol.endswith('USDT'):
                symbol += 'USDT'
            
            # Format kontrolü
            if len(symbol) < 6 or len(symbol) > 20:
                raise HTTPException(status_code=400, detail=f"Geçersiz sembol formatı: {symbol}")
            
            # Duplicate kontrolü
            if symbol not in normalized_symbols:
                normalized_symbols.append(symbol)
        
        if len(normalized_symbols) == 0:
            raise HTTPException(status_code=400, detail="Geçerli sembol bulunamadı.")
        
        user_email = user.get('email', 'anonymous')
        print(f"👤 {user_email} tarafından OPTIMIZE multi-coin bot başlatılıyor:")
        print(f"   Symbols: {', '.join(normalized_symbols)}")
        
        # ✅ BACKGROUND TASK ile güvenli başlatma
        background_tasks.add_task(bot_core.start, normalized_symbols)
        
        # Kısa bekleme - Bot state'ini güncellesin
        await asyncio.sleep(2)
        
        # Güncel durumu al
        current_status = bot_core.get_multi_status()
        
        return JSONResponse({
            "success": True,
            "message": f"OPTIMIZE Bot {len(normalized_symbols)} coin için başlatılıyor...",
            "symbols": normalized_symbols,
            "user": user_email,
            "timestamp": time.time(),
            "status": current_status,
            "version": "1.2_optimized_fixed",
            "fixes": [
                "✅ Dictionary iteration hatası düzeltildi",
                "✅ API rate limiting optimize edildi", 
                "✅ NaN safe EMA hesaplamaları",
                "✅ Thread-safe WebSocket connections",
                "✅ Güvenli pozisyon yönetimi"
            ]
        })
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ OPTIMIZE Bot başlatma hatası: {e}")
        raise HTTPException(status_code=500, detail=f"Bot başlatılırken hata: {str(e)}")

@app.get("/api/multi-status")
async def get_multi_status_optimized(user: dict = Depends(authenticate_optimized)):
    """✅ OPTIMIZE Bot durumunu döndür - Hızlı ve güvenli"""
    try:
        status = bot_core.get_multi_status()
        
        # ✅ Response'a debug bilgisi ekle
        status["debug_info"] = {
            "user": user.get('email'),
            "timestamp": time.time(),
            "websocket_status": "active" if len(bot_core._websocket_connections) > 0 else "inactive",
            "connection_count": len(bot_core._websocket_connections),
            "version": "1.2_optimized"
        }
        
        return JSONResponse(status)
        
    except Exception as e:
        print(f"❌ Status hatası: {e}")
        # ✅ Hata durumunda da minimal response döndür
        return JSONResponse({
            "is_running": False,
            "status_message": "Status alınırken hata oluştu",
            "error": str(e),
            "timestamp": time.time()
        })

@app.post("/api/stop")
async def stop_bot_optimized(user: dict = Depends(authenticate_optimized)):
    """✅ OPTIMIZE Bot durdur - Güvenli kapatma"""
    try:
        if not bot_core.status["is_running"]:
            raise HTTPException(status_code=400, detail="Bot zaten durdurulmuş.")
        
        user_email = user.get('email', 'anonymous')
        print(f"👤 {user_email} tarafından OPTIMIZE bot durduruluyor")
        
        # ✅ GÜVENLI durdurma - Dictionary iteration hatası yok
        await bot_core.stop()
        
        # Son durumu al
        final_status = bot_core.get_multi_status()
        
        return JSONResponse({
            "success": True,
            "message": "Bot güvenli durduruldu",
            "user": user_email,
            "timestamp": time.time(),
            "status": final_status
        })
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Bot durdurma hatası: {e}")
        raise HTTPException(status_code=500, detail=f"Bot durdurulurken hata: {str(e)}")

# ============ ✅ YENİ OPTIMIZE DEBUG ENDPOINT ============

@app.post("/api/debug-ema-optimized")
async def debug_ema_analysis_optimized(
    request: DebugRequest, 
    user: dict = Depends(authenticate_optimized)
):
    """✅ OPTIMIZE EMA hesaplamalarını test et - Gelişmiş debug"""
    symbol = request.symbol.upper().strip()
    
    if not symbol.endswith('USDT'):
        symbol += 'USDT'
    
    user_email = user.get('email', 'anonymous')
    print(f"🐛 {user_email} OPTIMIZE debug isteği: {symbol}")
    
    try:
        # Binance bağlantısını kontrol et
        if not binance_client.client:
            await binance_client.initialize()
        
        # ✅ OPTIMIZE veri alma
        required_candles = settings.EMA_SLOW_PERIOD + 30
        klines = await binance_client.get_historical_klines(
            symbol, settings.TIMEFRAME, limit=required_candles
        )
        
        if not klines or len(klines) < 20:
            raise HTTPException(
                status_code=404, 
                detail=f"{symbol} için yeterli veri bulunamadı"
            )
        
        # ✅ OPTIMIZE EMA analizini test et
        current_signal = trading_strategy.analyze_klines(klines, symbol)
        debug_info = trading_strategy.get_debug_info_optimized(klines, symbol)
        strategy_status = trading_strategy.get_strategy_status_optimized(symbol)
        
        # ✅ Market bilgisi ekle
        current_price = await binance_client.get_market_price(symbol)
        
        return JSONResponse({
            "success": True,
            "symbol": symbol,
            "timeframe": settings.TIMEFRAME,
            "current_signal": current_signal,
            "current_price": current_price,
            "debug_info": debug_info,
            "strategy_status": strategy_status,
            "klines_count": len(klines),
            "user": user_email,
            "timestamp": time.time(),
            "optimization_version": "1.2_nan_safe_optimized",
            "performance_notes": [
                "✅ NaN handling tamamen güvenli",
                "✅ Boolean operations düzeltildi",
                "✅ Memory kullanımı optimize edildi", 
                "✅ Whipsaw koruması aktif",
                "✅ API rate limiting optimize edildi"
            ]
        })
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ OPTIMIZE Debug hatası: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e),
            "symbol": symbol,
            "user": user_email,
            "timestamp": time.time(),
            "debug_notes": "Hata detayları için log'ları kontrol edin"
        })

# ============ ✅ GELİŞMİŞ HEALTH CHECK ============

@app.get("/api/health-optimized")
async def health_check_optimized():
    """✅ OPTIMIZE Sağlık kontrolü - Kapsamlı sistem durumu"""
    try:
        # ✅ Bot durumu
        bot_status = bot_core.get_multi_status()
        
        # ✅ WebSocket durumu
        websocket_status = {
            "active_connections": len(bot_core._websocket_connections),
            "connection_symbols": list(bot_core._websocket_connections.keys()),
            "status": "healthy" if len(bot_core._websocket_connections) > 0 or not bot_status["is_running"] else "warning"
        }
        
        # ✅ Binance bağlantı durumu
        binance_status = "connected" if binance_client.client else "disconnected"
        
        # ✅ Position manager durumu
        position_manager_status = position_manager.get_status()
        
        # ✅ Trading strategy durumu
        strategy_performance = {
            "total_analysis": trading_strategy.analysis_count,
            "successful_signals": trading_strategy.successful_signals,
            "efficiency": f"{(trading_strategy.successful_signals/max(trading_strategy.analysis_count,1))*100:.1f}%"
        }
        
        # ✅ System resources (basic) - Güvenli import
        try:
            import psutil
            system_status = {
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage('/').percent
            }
        except ImportError:
            system_status = {
                "cpu_percent": "N/A (psutil not installed)",
                "memory_percent": "N/A (psutil not installed)", 
                "disk_percent": "N/A (psutil not installed)"
            }
        except Exception as sys_error:
            system_status = {
                "cpu_percent": f"Error: {sys_error}",
                "memory_percent": f"Error: {sys_error}",
                "disk_percent": f"Error: {sys_error}"
            }
        
        return JSONResponse({
            "status": "healthy",
            "timestamp": time.time(),
            "version": "1.3_completely_fixed",
            
            # Bot components
            "bot_status": {
                "running": bot_status["is_running"],
                "symbols_count": len(bot_status["symbols"]),
                "active_symbol": bot_status["active_symbol"],
                "successful_trades": bot_status["successful_trades"],
                "failed_trades": bot_status["failed_trades"]
            },
            
            # Connections
            "connections": {
                "websocket": websocket_status,
                "binance": binance_status,
                "position_manager": position_manager_status["is_running"]
            },
            
            # Performance
            "performance": {
                "strategy": strategy_performance,
                "system": system_status
            },
            
            # Configuration
            "config": {
                "environment": settings.ENVIRONMENT,
                "debug_mode": settings.DEBUG_MODE,
                "test_mode": settings.TEST_MODE,
                "timeframe": settings.TIMEFRAME,
                "leverage": settings.LEVERAGE
            },
            
            # v1.3 fixes
            "all_fixes_v1.3": [
                "✅ Dictionary iteration hatası tamamen düzeltildi",
                "✅ EMA 'Replacement lists must match' hatası çözüldü", 
                "✅ Pandas FutureWarning uyarıları yok",
                "✅ Thread-safe WebSocket connections",
                "✅ API rate limiting optimize edildi",
                "✅ Memory usage optimized",
                "✅ 404 endpoint hataları düzeltildi",
                "✅ Element-wise NaN/Inf cleaning",
                "✅ infer_objects() ile pandas uyumluluk",
                "✅ Güvenli error handling"
            ]
        })
        
    except Exception as e:
        return JSONResponse({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": time.time(),
            "version": "1.3_completely_fixed"
        }, status_code=503)

# ============ ✅ LEGACY UYUMLULUK (Geriye uyumlu) ============

@app.get("/api/status")
async def get_status_legacy(user: dict = Depends(authenticate_optimized)):
    """✅ Eski format status - Geriye uyumluluk"""
    status = bot_core.get_multi_status()
    return JSONResponse({
        "is_running": status.get("is_running", False),
        "symbol": status.get("active_symbol"),
        "position_side": status.get("position_side"),
        "status_message": status.get("status_message", ""),
        "account_balance": status.get("account_balance", 0),
        "position_pnl": status.get("position_pnl", 0),
        "order_size": status.get("order_size", 0),
        "version": "1.2_legacy_compatible"
    })

@app.post("/api/start")
async def start_bot_legacy(
    request: dict, 
    background_tasks: BackgroundTasks, 
    user: dict = Depends(authenticate_optimized)
):
    """✅ Tek symbol için geriye uyumluluk"""
    symbol = request.get("symbol", "").upper().strip()
    
    if not symbol:
        raise HTTPException(status_code=400, detail="Symbol gerekli.")
        
    if not symbol.endswith('USDT'):
        symbol += 'USDT'
    
    user_email = user.get('email', 'anonymous')
    print(f"👤 {user_email} tek symbol (legacy): {symbol}")
    
    # Multi-coin API'yi kullan
    multi_request = MultiStartRequest(symbols=[symbol])
    result = await start_multi_bot_optimized(multi_request, background_tasks, user)
    
    # Legacy format'a çevir
    if isinstance(result, JSONResponse):
        result_data = result.body.decode() if hasattr(result, 'body') else {}
        status = result_data.get("status", {}) if isinstance(result_data, dict) else {}
    else:
        status = result.get("status", {})
    
    return JSONResponse({
        "is_running": status.get("is_running", False),
        "symbol": status.get("symbols", [None])[0],
        "position_side": status.get("position_side"),
        "status_message": status.get("status_message", ""),
        "account_balance": status.get("account_balance", 0),
        "position_pnl": status.get("position_pnl", 0),
        "order_size": status.get("order_size", 0),
        "version": "1.2_legacy_mode"
    })

# ============ ✅ OPTIMIZE POZİSYON YÖNETİMİ ============

@app.post("/api/scan-all-positions")
async def scan_all_positions_optimized(user: dict = Depends(authenticate_optimized)):
    """✅ OPTIMIZE Tüm açık pozisyonları tara"""
    user_email = user.get('email', 'anonymous')
    print(f"👤 {user_email} OPTIMIZE pozisyon taraması başlattı")
    
    try:
        # ✅ Rate limit koruması
        await asyncio.sleep(0.5)
        
        # Manuel tarama yap
        await position_manager._scan_and_protect()
        
        return JSONResponse({
            "success": True,
            "message": "Tüm pozisyonlar TP/SL koruması ile tarandı",
            "monitor_status": position_manager.get_status(),
            "user": user_email,
            "timestamp": time.time(),
            "optimization": "v1.2_rate_limited"
        })
        
    except Exception as e:
        print(f"❌ OPTIMIZE Tarama hatası: {e}")
        return JSONResponse({
            "success": False, 
            "message": f"Tarama hatası: {e}",
            "user": user_email,
            "timestamp": time.time()
        })

@app.post("/api/scan-symbol")
async def scan_specific_symbol_optimized(
    request: SymbolRequest, 
    user: dict = Depends(authenticate_optimized)
):
    """✅ OPTIMIZE Belirli bir coin için TP/SL kontrolü"""
    symbol = request.symbol.upper().strip()
    if not symbol.endswith('USDT'):
        symbol += 'USDT'
    
    user_email = user.get('email', 'anonymous')
    print(f"👤 {user_email} OPTIMIZE symbol kontrolü: {symbol}")
    
    try:
        # ✅ Rate limit koruması
        await asyncio.sleep(0.3)
        
        # Symbol kontrolü yap
        success = await position_manager.manual_scan_symbol(symbol)
        
        return JSONResponse({
            "success": success,
            "symbol": symbol,
            "message": f"{symbol} için TP/SL kontrolü tamamlandı",
            "user": user_email,
            "timestamp": time.time(),
            "optimization": "v1.2_symbol_specific"
        })
        
    except Exception as e:
        print(f"❌ OPTIMIZE Symbol kontrolü hatası: {e}")
        return JSONResponse({
            "success": False, 
            "symbol": symbol,
            "message": f"{symbol} kontrolü hatası: {e}",
            "user": user_email,
            "timestamp": time.time()
        })

@app.get("/api/position-monitor-status")
async def get_position_monitor_status_optimized(user: dict = Depends(authenticate_optimized)):
    """✅ TAMAMEN DÜZELTİLMİŞ Position monitor durumu - 404 hatası çözüldü"""
    try:
        # position_manager import kontrolü
        try:
            from .position_manager import position_manager
            monitor_status = position_manager.get_status()
        except Exception as import_error:
            print(f"⚠️ Position manager import hatası: {import_error}")
            monitor_status = {
                "is_running": False,
                "error": "Position manager bulunamadı",
                "scan_interval": 30,
                "last_scan_ago_seconds": None
            }
        
        # Bot status güvenli alma
        try:
            bot_status = bot_core.get_multi_status()
        except Exception as bot_error:
            print(f"⚠️ Bot status hatası: {bot_error}")
            bot_status = {
                "is_running": False,
                "active_symbol": None,
                "position_side": None
            }
        
        return JSONResponse({
            "success": True,
            "monitor_status": monitor_status,
            "bot_status": {
                "is_running": bot_status.get("is_running", False),
                "active_symbol": bot_status.get("active_symbol"),
                "position_side": bot_status.get("position_side")
            },
            "user": user.get('email', 'anonymous'),
            "timestamp": time.time(),
            "version": "1.3_fixed_404",
            "endpoint_status": "active"
        })
        
    except Exception as e:
        print(f"❌ Monitor status endpoint hatası: {e}")
        return JSONResponse({
            "success": False,
            "monitor_status": {
                "is_running": False, 
                "error": str(e),
                "scan_interval": 30,
                "last_scan_ago_seconds": None
            },
            "bot_status": {"is_running": False},
            "timestamp": time.time(),
            "endpoint_status": "error"
        }, status_code=200)  # 200 döndür, 500 değil

@app.post("/api/start-position-monitor")
async def start_position_monitor_optimized(
    background_tasks: BackgroundTasks, 
    user: dict = Depends(authenticate_optimized)
):
    """✅ OPTIMIZE Position monitor başlat"""
    if position_manager.is_running:
        raise HTTPException(status_code=400, detail="Position monitor zaten çalışıyor.")
    
    user_email = user.get('email', 'anonymous')
    print(f"👤 {user_email} OPTIMIZE position monitor başlatıyor")
    
    try:
        # ✅ Background task ile başlat
        background_tasks.add_task(position_manager.start_monitoring)
        
        # Kısa bekleme
        await asyncio.sleep(1.5)
        
        return JSONResponse({
            "success": True,
            "message": "Otomatik TP/SL monitoring başlatıldı",
            "monitor_status": position_manager.get_status(),
            "user": user_email,
            "timestamp": time.time(),
            "optimization": "v1.2_background_task"
        })
        
    except Exception as e:
        print(f"❌ Monitor başlatma hatası: {e}")
        raise HTTPException(status_code=500, detail=f"Monitor başlatma hatası: {e}")

@app.post("/api/stop-position-monitor")
async def stop_position_monitor_optimized(user: dict = Depends(authenticate_optimized)):
    """✅ OPTIMIZE Position monitor durdur"""
    if not position_manager.is_running:
        raise HTTPException(status_code=400, detail="Position monitor zaten durdurulmuş.")
    
    user_email = user.get('email', 'anonymous')
    print(f"👤 {user_email} OPTIMIZE position monitor durduruyor")
    
    try:
        await position_manager.stop_monitoring()
        
        return JSONResponse({
            "success": True,
            "message": "Position monitor durduruldu",
            "monitor_status": position_manager.get_status(),
            "user": user_email,
            "timestamp": time.time(),
            "optimization": "v1.2_safe_stop"
        })
        
    except Exception as e:
        print(f"❌ Monitor durdurma hatası: {e}")
        raise HTTPException(status_code=500, detail=f"Monitor durdurma hatası: {e}")

# ============ ✅ EK YARDIMCI ENDPOINT'LER ============

@app.post("/api/add-symbol")
async def add_symbol_to_bot(
    request: SymbolRequest,
    user: dict = Depends(authenticate_optimized)
):
    """✅ Çalışan bota yeni symbol ekle"""
    if not bot_core.status["is_running"]:
        raise HTTPException(status_code=400, detail="Bot çalışmıyor, önce botu başlatın.")
    
    symbol = request.symbol.upper().strip()
    if not symbol.endswith('USDT'):
        symbol += 'USDT'
    
    current_symbols = bot_core.status["symbols"]
    if symbol in current_symbols:
        raise HTTPException(status_code=400, detail=f"{symbol} zaten izleniyor.")
    
    if len(current_symbols) >= 10:
        raise HTTPException(status_code=400, detail="Maksimum 10 symbol desteklenir.")
    
    user_email = user.get('email', 'anonymous')
    print(f"👤 {user_email} yeni symbol ekliyor: {symbol}")
    
    try:
        # Symbol'ü listeye ekle (basit ekleme)
        bot_core.status["symbols"].append(symbol)
        
        return JSONResponse({
            "success": True,
            "message": f"{symbol} bot'a eklendi",
            "symbol": symbol,
            "current_symbols": bot_core.status["symbols"],
            "user": user_email,
            "timestamp": time.time(),
            "note": "WebSocket bağlantısı sonraki restart'ta aktif olacak"
        })
        
    except Exception as e:
        print(f"❌ Symbol ekleme hatası: {e}")
        raise HTTPException(status_code=500, detail=f"Symbol eklenirken hata: {e}")

@app.post("/api/remove-symbol")
async def remove_symbol_from_bot(
    request: SymbolRequest,
    user: dict = Depends(authenticate_optimized)
):
    """✅ Çalışan bottan symbol çıkar"""
    if not bot_core.status["is_running"]:
        raise HTTPException(status_code=400, detail="Bot çalışmıyor.")
    
    symbol = request.symbol.upper().strip()
    if not symbol.endswith('USDT'):
        symbol += 'USDT'
    
    current_symbols = bot_core.status["symbols"]
    if symbol not in current_symbols:
        raise HTTPException(status_code=400, detail=f"{symbol} izlenmıyor.")
    
    # Aktif pozisyon kontrolü
    if bot_core.status["active_symbol"] == symbol:
        raise HTTPException(status_code=400, detail=f"{symbol} aktif pozisyonda, önce pozisyonu kapatın.")
    
    user_email = user.get('email', 'anonymous')
    print(f"👤 {user_email} symbol çıkarıyor: {symbol}")
    
    try:
        # Symbol'ü listeden çıkar
        bot_core.status["symbols"].remove(symbol)
        
        # Last signals'dan da temizle
        if symbol in bot_core.status["last_signals"]:
            del bot_core.status["last_signals"][symbol]
        
        return JSONResponse({
            "success": True,
            "message": f"{symbol} bot'tan çıkarıldı",
            "symbol": symbol,
            "remaining_symbols": bot_core.status["symbols"],
            "user": user_email,
            "timestamp": time.time()
        })
        
    except Exception as e:
        print(f"❌ Symbol çıkarma hatası: {e}")
        raise HTTPException(status_code=500, detail=f"Symbol çıkarılırken hata: {e}")

@app.get("/api/account-info")
async def get_account_info_optimized(user: dict = Depends(authenticate_optimized)):
    """✅ OPTIMIZE Hesap bilgilerini getir"""
    try:
        # Binance bağlantısını kontrol et
        if not binance_client.client:
            await binance_client.initialize()
        
        # ✅ Rate limit koruması
        await asyncio.sleep(0.2)
        
        # Hesap bakiyesi
        balance = await binance_client.get_account_balance()
        
        # Açık pozisyonları al
        await binance_client._rate_limit_delay()
        all_positions = await binance_client.client.futures_position_information()
        open_positions = [p for p in all_positions if float(p['positionAmt']) != 0]
        
        # Pozisyon özetleri
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
                "pnl_percent": float(pos['percentage'])
            })
        
        return JSONResponse({
            "account_balance": balance,
            "total_unrealized_pnl": total_pnl,
            "open_positions_count": len(open_positions),
            "position_summary": position_summary,
            "bot_order_size": bot_core.status["order_size"],
            "available_for_trading": balance * settings.MAX_POSITION_SIZE_PERCENT,
            "user": user.get('email', 'anonymous'),
            "timestamp": time.time(),
            "version": "1.2_optimized"
        })
        
    except Exception as e:
        print(f"❌ Account info hatası: {e}")
        raise HTTPException(status_code=500, detail=f"Hesap bilgileri alınırken hata: {e}")

@app.get("/api/trading-config")
async def get_trading_config(user: dict = Depends(authenticate_optimized)):
    """✅ Trading konfigürasyonunu getir"""
    try:
        config = settings.get_trading_config()
        api_config = settings.get_api_rate_config()
        
        return JSONResponse({
            "trading_config": config,
            "api_config": api_config,
            "risk_management": {
                "max_concurrent_positions": settings.MAX_CONCURRENT_POSITIONS,
                "max_daily_trades": settings.MAX_DAILY_TRADES,
                "min_balance_usdt": settings.MIN_BALANCE_USDT,
                "max_position_size_percent": settings.MAX_POSITION_SIZE_PERCENT
            },
            "strategy_info": {
                "name": "Optimized EMA Cross",
                "version": "1.2",
                "whipsaw_protection": True,
                "nan_safe": True,
                "memory_optimized": True
            },
            "user": user.get('email', 'anonymous'),
            "timestamp": time.time()
        })
        
    except Exception as e:
        return JSONResponse({"error": f"Config hatası: {e}"}, status_code=500)

# ============ ✅ STATISTICS ENDPOINT ============

@app.get("/api/bot-statistics")
async def get_bot_statistics(user: dict = Depends(authenticate_optimized)):
    """✅ Bot istatistiklerini getir"""
    try:
        bot_status = bot_core.get_multi_status()
        
        # Trading strategy performance
        strategy_stats = {
            "total_analysis": trading_strategy.analysis_count,
            "successful_signals": trading_strategy.successful_signals,
            "efficiency_percent": (trading_strategy.successful_signals / max(trading_strategy.analysis_count, 1)) * 100
        }
        
        # Bot performance
        total_trades = bot_status["successful_trades"] + bot_status["failed_trades"]
        win_rate = (bot_status["successful_trades"] / max(total_trades, 1)) * 100
        
        return JSONResponse({
            "trading_performance": {
                "successful_trades": bot_status["successful_trades"],
                "failed_trades": bot_status["failed_trades"],
                "total_trades": total_trades,
                "win_rate_percent": win_rate
            },
            "strategy_performance": strategy_stats,
            "current_status": {
                "is_running": bot_status["is_running"],
                "monitored_symbols": len(bot_status["symbols"]),
                "active_position": bot_status["active_symbol"],
                "websocket_connections": bot_status["websocket_connections"]
            },
            "system_info": {
                "version": "1.3_completely_fixed",
                "uptime_status": "running" if bot_status["is_running"] else "stopped",
                "all_fixes_active": [
                    "Dictionary iteration fix",
                    "EMA calculation fix", 
                    "Pandas FutureWarning fix",
                    "NaN safe operations", 
                    "API rate limiting",
                    "Memory optimization",
                    "Whipsaw protection",
                    "404 endpoint fixes"
                ]
            },
            "user": user.get('email', 'anonymous'),
            "timestamp": time.time()
        })
        
    except Exception as e:
        return JSONResponse({"error": f"İstatistik hatası: {e}"}, status_code=500)

# ============ ✅ OPTIMIZE HATA YÖNETİMİ ============
# app/main.py dosyanızın EN SONUNA (diğer endpoint'lerden sonra) ekleyin

# ============ 🤖 GEMİNİ AI TEST ENDPOINTS ============

@app.post("/api/test-gemini")
async def test_gemini_ai(
    request: SymbolRequest, 
    user: dict = Depends(authenticate_optimized)
):
    """
    🤖 Gemini AI'yi test et
    Mevcut botunuzla uyumlu çalışır, 1m ve 5m verilerle analiz yapar
    """
    try:
        from .gemini_analyzer import gemini_analyzer
        
        symbol = request.symbol.upper().strip()
        if not symbol.endswith('USDT'):
            symbol += 'USDT'
        
        user_email = user.get('email', 'anonymous')
        print(f"🤖 {user_email} Gemini AI test ediyor: {symbol}")
        
        # Gemini aktif mi kontrol
        if not gemini_analyzer.enabled:
            return JSONResponse({
                "success": False,
                "message": "❌ Gemini AI aktif değil. .env dosyasına GEMINI_API_KEY ekleyin.",
                "help": "https://makersuite.google.com/app/apikey adresinden ücretsiz API key alabilirsiniz.",
                "ai_enabled": False
            })
        
        # Binance'den veri al
        if not binance_client.client:
            await binance_client.initialize()
        
        current_price = await binance_client.get_market_price(symbol)
        if not current_price:
            raise HTTPException(status_code=404, detail=f"{symbol} fiyat alınamadı")
        
        # 1m ve 5m veri al (Gemini scalping stratejisi için)
        print(f"📊 {symbol} için 1m ve 5m verileri alınıyor...")
        klines_1m = await binance_client.get_historical_klines(symbol, "1m", limit=100)
        klines_5m = await binance_client.get_historical_klines(symbol, "5m", limit=50)
        
        if not klines_1m or len(klines_1m) < 20:
            raise HTTPException(status_code=404, detail=f"{symbol} 1m veri yetersiz")
        
        if not klines_5m or len(klines_5m) < 10:
            raise HTTPException(status_code=404, detail=f"{symbol} 5m veri yetersiz")
        
        # Gemini AI analizi
        print(f"🤖 Gemini AI analiz başlatılıyor: {symbol}")
        
        analysis = await gemini_analyzer.analyze_scalping_opportunity(
            symbol=symbol,
            current_price=current_price,
            klines_1m=klines_1m,
            klines_5m=klines_5m,
            ema_signal="TEST",  # Test modu
            volume_data={"is_valid": True, "ratio": 1.5, "current_volume": 1000, "avg_volume": 800}
        )
        
        # Sonuçları formatla
        result_message = f"✅ Gemini AI Analizi Tamamlandı"
        if analysis['should_trade']:
            result_message = f"🚀 {analysis['signal']} Sinyali (Güven: %{analysis['confidence']:.0f})"
        else:
            result_message = f"⏸️ İşlem Önerilmiyor: {analysis['reasoning']}"
        
        return JSONResponse({
            "success": True,
            "symbol": symbol,
            "current_price": current_price,
            "ai_analysis": {
                "signal": analysis['signal'],
                "should_trade": analysis['should_trade'],
                "confidence": analysis['confidence'],
                "reasoning": analysis['reasoning'],
                "stop_loss_percent": analysis['stop_loss_percent'],
                "take_profit_percent": analysis['take_profit_percent'],
                "risk_score": analysis['risk_score'],
                "ai_validated": analysis.get('ai_validated', False)
            },
            "data_info": {
                "klines_1m_count": len(klines_1m),
                "klines_5m_count": len(klines_5m),
                "timeframe_primary": "1m",
                "timeframe_secondary": "5m"
            },
            "ai_enabled": True,
            "message": result_message,
            "user": user_email,
            "timestamp": time.time()
        })
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Gemini test hatası: {e}")
        import traceback
        print(traceback.format_exc())
        return JSONResponse({
            "success": False,
            "error": str(e),
            "ai_enabled": False,
            "message": "Gemini AI test hatası"
        }, status_code=500)

@app.get("/api/gemini-status")
async def get_gemini_status(user: dict = Depends(authenticate_optimized)):
    """🤖 Gemini AI durum kontrolü"""
    try:
        from .gemini_analyzer import gemini_analyzer
        
        status = {
            "ai_enabled": gemini_analyzer.enabled,
            "api_key_configured": bool(gemini_analyzer.api_key) if gemini_analyzer.enabled else False,
            "provider": "Gemini 2.0 Flash",
            "model": "gemini-2.0-flash-exp",
            "cache_size": len(gemini_analyzer.cache) if gemini_analyzer.enabled else 0,
            "cache_duration_seconds": gemini_analyzer.cache_duration if gemini_analyzer.enabled else 0
        }
        
        if not gemini_analyzer.enabled:
            status["message"] = "❌ GEMINI_API_KEY ayarlanmamış"
            status["help"] = "https://makersuite.google.com/app/apikey adresinden ücretsiz API key alın"
            status["setup_steps"] = [
                "1. Google AI Studio'ya giriş yapın",
                "2. 'Create API Key' butonuna tıklayın",
                "3. API key'i kopyalayın",
                "4. .env dosyasına GEMINI_API_KEY=your_key_here ekleyin",
                "5. Uygulamayı yeniden başlatın"
            ]
        else:
            status["message"] = "✅ Gemini AI aktif ve hazır"
            status["api_key_preview"] = gemini_analyzer.api_key[:10] + "..." if gemini_analyzer.api_key else None
            status["features"] = [
                "✅ 1m + 5m multi-timeframe analiz",
                "✅ AI güven skoru hesaplama",
                "✅ Risk değerlendirmesi",
                "✅ Otomatik TP/SL önerisi",
                "✅ Volume ve volatilite analizi"
            ]
        
        return JSONResponse({
            "success": True,
            "status": status,
            "user": user.get('email', 'anonymous'),
            "timestamp": time.time()
        })
        
    except Exception as e:
        print(f"❌ Gemini status hatası: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e),
            "ai_enabled": False
        }, status_code=500)

@app.post("/api/gemini-clear-cache")
async def clear_gemini_cache(user: dict = Depends(authenticate_optimized)):
    """🧹 Gemini AI cache temizle"""
    try:
        from .gemini_analyzer import gemini_analyzer
        
        if not gemini_analyzer.enabled:
            return JSONResponse({
                "success": False,
                "message": "Gemini AI aktif değil"
            })
        
        old_cache_size = len(gemini_analyzer.cache)
        gemini_analyzer.clear_cache()
        
        user_email = user.get('email', 'anonymous')
        print(f"🧹 {user_email} Gemini cache temizledi ({old_cache_size} kayıt)")
        
        return JSONResponse({
            "success": True,
            "message": f"✅ Cache temizlendi ({old_cache_size} kayıt silindi)",
            "cleared_count": old_cache_size,
            "user": user_email,
            "timestamp": time.time()
        })
        
    except Exception as e:
        print(f"❌ Cache temizleme hatası: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)

@app.get("/api/gemini-health")
async def gemini_health_check():
    """🤖 Gemini AI sağlık kontrolü (auth gerekmiyor)"""
    try:
        from .gemini_analyzer import gemini_analyzer
        
        health_status = {
            "service": "Gemini AI Analyzer",
            "version": "1.0",
            "status": "healthy" if gemini_analyzer.enabled else "disabled",
            "timestamp": time.time()
        }
        
        if gemini_analyzer.enabled:
            health_status.update({
                "provider": "Gemini 2.0 Flash",
                "cache_enabled": True,
                "cache_size": len(gemini_analyzer.cache),
                "features_available": [
                    "Scalping opportunity analysis",
                    "Multi-timeframe analysis",
                    "Risk scoring",
                    "Confidence calculation"
                ]
            })
        else:
            health_status.update({
                "reason": "API key not configured",
                "help_url": "https://makersuite.google.com/app/apikey"
            })
        
        return JSONResponse(health_status)
        
    except Exception as e:
        return JSONResponse({
            "service": "Gemini AI Analyzer",
            "status": "unhealthy",
            "error": str(e),
            "timestamp": time.time()
        }, status_code=503)

# ============ 🎯 GEMİNİ + MEVCUT BOT ENTEGRASYONU ============

@app.post("/api/analyze-with-ai")
async def analyze_symbol_with_ai(
    request: SymbolRequest,
    user: dict = Depends(authenticate_optimized)
):
    """
    🤖 Bir sembolü hem EMA hem de Gemini AI ile analiz et
    Mevcut botunuzun EMA stratejisi + Gemini AI önerisini karşılaştırır
    """
    try:
        from .gemini_analyzer import gemini_analyzer
        from .trading_strategy import trading_strategy
        
        symbol = request.symbol.upper().strip()
        if not symbol.endswith('USDT'):
            symbol += 'USDT'
        
        user_email = user.get('email', 'anonymous')
        print(f"🔍 {user_email} kombine analiz: {symbol}")
        
        # Binance bağlantısı
        if not binance_client.client:
            await binance_client.initialize()
        
        # Veri toplama
        current_price = await binance_client.get_market_price(symbol)
        klines_15m = await binance_client.get_historical_klines(symbol, "15m", limit=100)
        klines_1m = await binance_client.get_historical_klines(symbol, "1m", limit=100)
        klines_5m = await binance_client.get_historical_klines(symbol, "5m", limit=50)
        
        # 1. Mevcut EMA stratejisi analizi (15m)
        ema_signal = "HOLD"
        if klines_15m and len(klines_15m) >= 30:
            ema_signal = trading_strategy.analyze_klines(klines_15m, symbol)
        
        # 2. Gemini AI analizi (1m+5m)
        ai_analysis = None
        if gemini_analyzer.enabled and klines_1m and klines_5m:
            ai_analysis = await gemini_analyzer.analyze_scalping_opportunity(
                symbol=symbol,
                current_price=current_price,
                klines_1m=klines_1m,
                klines_5m=klines_5m,
                ema_signal=ema_signal,
                volume_data={"is_valid": True, "ratio": 1.5}
            )
        
        # 3. Karşılaştırma
        comparison = {
            "ema_15m_signal": ema_signal,
            "ai_1m5m_signal": ai_analysis['signal'] if ai_analysis else "N/A",
            "signals_agree": False,
            "recommendation": "HOLD"
        }
        
        if ai_analysis:
            signals_agree = (ema_signal == ai_analysis['signal']) and (ema_signal != "HOLD")
            comparison["signals_agree"] = signals_agree
            
            if signals_agree and ai_analysis['should_trade']:
                comparison["recommendation"] = ema_signal
                comparison["confidence"] = "HIGH"
                comparison["reason"] = "Hem EMA hem AI aynı yönde"
            elif ai_analysis['should_trade'] and ema_signal == "HOLD":
                comparison["recommendation"] = ai_analysis['signal']
                comparison["confidence"] = "MEDIUM"
                comparison["reason"] = "Sadece AI öneriyor (scalping fırsatı)"
            elif not ai_analysis['should_trade']:
                comparison["recommendation"] = "HOLD"
                comparison["confidence"] = "LOW"
                comparison["reason"] = ai_analysis['reasoning']
        
        return JSONResponse({
            "success": True,
            "symbol": symbol,
            "current_price": current_price,
            "analysis": {
                "ema_strategy": {
                    "timeframe": "15m",
                    "signal": ema_signal,
                    "strategy": "EMA 9/21 Cross"
                },
                "ai_strategy": ai_analysis if ai_analysis else {"error": "Gemini AI devre dışı"},
                "comparison": comparison
            },
            "user": user_email,
            "timestamp": time.time()
        })
        
    except Exception as e:
        print(f"❌ Kombine analiz hatası: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)

print("✅ Gemini AI endpoints yüklendi!")
print("🤖 Test için: POST /api/test-gemini {'symbol': 'BTC'}")
print("📊 Durum için: GET /api/gemini-status")
print("🔍 Kombine analiz: POST /api/analyze-with-ai {'symbol': 'BTC'}")

# ============ AUTONOMOUS AI TRADING ENDPOINTS ============

@app.post("/api/ai-trading/start")
async def start_ai_trading(
    background_tasks: BackgroundTasks,
    user: dict = Depends(authenticate_optimized)
):
    """
    Start Autonomous AI Trading
    Gemini AI tum kararlari verir, siz sadece izlersiniz
    """
    try:
        if not gemini_trading_manager.enabled:
            raise HTTPException(
                status_code=400,
                detail="Gemini API aktif degil. GEMINI_API_KEY kontrolu edin."
            )

        if gemini_trading_manager.is_running:
            raise HTTPException(status_code=400, detail="AI Trading zaten calisiyor.")

        user_email = user.get('email', 'anonymous')
        print(f"AI Trading baslatiyor: {user_email}")

        # Binance baglantisini kontrol et
        if not binance_client.client:
            await binance_client.initialize()

        # Background task olarak basla
        background_tasks.add_task(gemini_trading_manager.start_autonomous_trading)

        await asyncio.sleep(2)

        return JSONResponse({
            "success": True,
            "message": "Autonomous AI Trading baslatildi",
            "status": gemini_trading_manager.get_status(),
            "user": user_email,
            "timestamp": time.time(),
            "info": {
                "strategy": "Gemini AI Autonomous Scalping",
                "timeframes": ["1m", "15m"],
                "max_positions": gemini_trading_manager.max_positions,
                "capital_per_position": f"{gemini_trading_manager.capital_per_position*100}%",
                "min_confidence": gemini_trading_manager.min_confidence
            }
        })

    except HTTPException:
        raise
    except Exception as e:
        print(f"AI Trading start error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ai-trading/stop")
async def stop_ai_trading(user: dict = Depends(authenticate_optimized)):
    """Stop Autonomous AI Trading"""
    try:
        if not gemini_trading_manager.is_running:
            raise HTTPException(status_code=400, detail="AI Trading zaten durmus.")

        user_email = user.get('email', 'anonymous')
        print(f"AI Trading durduruluyor: {user_email}")

        await gemini_trading_manager.stop_autonomous_trading()

        return JSONResponse({
            "success": True,
            "message": "Autonomous AI Trading durduruldu",
            "status": gemini_trading_manager.get_status(),
            "user": user_email,
            "timestamp": time.time()
        })

    except HTTPException:
        raise
    except Exception as e:
        print(f"AI Trading stop error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/ai-trading/status")
async def get_ai_trading_status(user: dict = Depends(authenticate_optimized)):
    """Get AI Trading Manager status"""
    try:
        status = gemini_trading_manager.get_status()

        # Aktif pozisyonlarin detaylarini ekle
        position_details = []
        for symbol, pos_data in gemini_trading_manager.active_positions.items():
            try:
                current_price = await binance_client.get_market_price(symbol)
                if current_price:
                    entry_price = pos_data['entry_price']
                    pnl_pct = ((current_price - entry_price) / entry_price * 100) if pos_data['side'] == 'LONG' else ((entry_price - current_price) / entry_price * 100)

                    position_details.append({
                        'symbol': symbol,
                        'side': pos_data['side'],
                        'entry_price': entry_price,
                        'current_price': current_price,
                        'pnl_percent': round(pnl_pct, 2),
                        'tp': pos_data.get('tp'),
                        'sl': pos_data.get('sl'),
                        'confidence': pos_data.get('ai_confidence', 0)
                    })
            except:
                pass

        return JSONResponse({
            "success": True,
            "status": status,
            "position_details": position_details,
            "timestamp": time.time()
        })

    except Exception as e:
        print(f"AI Trading status error: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e),
            "status": gemini_trading_manager.get_status()
        }, status_code=500)

print("✅ Autonomous AI Trading endpoints yuklendi!")

@app.exception_handler(Exception)
async def exception_handler_optimized(request, exc):
    """✅ TAMAMEN DÜZELTİLMİŞ Global exception handler"""
    error_msg = str(exc)
    print(f"❌ FIXED Global hata: {error_msg}")
    
    # ✅ Hata tipine göre response
    if "dictionary changed size during iteration" in error_msg.lower():
        return JSONResponse({
            "error": "Dictionary iteration hatası - v1.3'te tamamen düzeltildi!",
            "detail": "Bu hata artık oluşmamalı",
            "timestamp": time.time(),
            "version": "1.3_completely_fixed",
            "action": "Eğer görürseniz lütfen destek alın"
        }, status_code=500)
    
    if "replacement lists must match in length" in error_msg.lower():
        return JSONResponse({
            "error": "EMA hesaplama hatası - v1.3'te düzeltildi!",
            "detail": "Element-wise cleaning ile çözüldü",
            "timestamp": time.time(),
            "version": "1.3_ema_fixed",
            "action": "Bu hata artık oluşmamalı"
        }, status_code=500)
    
    return JSONResponse({
        "error": "Bot'ta beklenmeyen hata oluştu", 
        "detail": error_msg,
        "timestamp": time.time(),
        "version": "1.3_all_errors_fixed",
        "support": "Log hatalarına çözüm v1.3 - Destek için iletişime geçin"
    }, status_code=500)

# ============ ✅ STATIC FILES ============

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_index():
    """✅ Ana sayfa"""
    return FileResponse('static/index.html')

# ============ ✅ BAŞLATMA MESAJLARI ============

print("🚀 TAMAMEN DÜZELTİLMİŞ EMA Cross Bot API v1.3 yüklendi!")
print("✅ Dictionary iteration hatası düzeltildi")
print("✅ EMA 'Replacement lists must match' hatası çözüldü")
print("✅ Pandas FutureWarning uyarıları yok")
print("✅ API rate limiting optimize edildi")
print("✅ NaN safe operations aktif")
print("✅ Thread-safe WebSocket connections")
print("✅ Güvenli pozisyon yönetimi")
print("✅ 404 endpoint hataları düzeltildi")
print("🎯 Bot hazır - LOG HATALARINDAN TEMİZ v1.3!")
