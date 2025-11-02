import os
import asyncio
import google.generativeai as genai
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

class GeminiAnalyzer:
    """
    🤖 Gemini 2.0 Flash AI Trading Analyzer
    - Dakikalık mum analizi
    - Risk değerlendirmesi
    - Sinyal güvenilirlik skoru
    - Market sentiment analizi
    """
    
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            print("⚠️ GEMINI_API_KEY bulunamadı. AI analizi devre dışı.")
            self.enabled = False
            return
            
        genai.configure(api_key=self.api_key)
        
        # Gemini 2.0 Flash model - en hızlı ve uygun maliyetli
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        self.enabled = True
        self.cache = {}  # Response cache
        self.cache_duration = 60  # 60 saniye cache
        
        print("🤖 Gemini 2.0 Flash AI Analyzer aktif")
    
    async def analyze_scalping_opportunity(
        self, 
        symbol: str,
        current_price: float,
        klines_1m: List,
        klines_5m: List,
        ema_signal: str,
        volume_data: Dict
    ) -> Dict:
        """
        🎯 Dakikalık scalping fırsatı analizi
        
        Returns:
        {
            "should_trade": bool,
            "confidence": float (0-100),
            "signal": "LONG" | "SHORT" | "HOLD",
            "stop_loss": float,
            "take_profit": float,
            "reasoning": str,
            "risk_score": float (0-10)
        }
        """
        
        if not self.enabled:
            return self._fallback_analysis(ema_signal)
        
        # Cache kontrolü
        cache_key = f"{symbol}_{int(datetime.now().timestamp() / 60)}"
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if (datetime.now() - cached['timestamp']).seconds < self.cache_duration:
                return cached['result']
        
        try:
            # Market verilerini hazırla
            market_context = self._prepare_market_context(
                symbol, current_price, klines_1m, klines_5m, 
                ema_signal, volume_data
            )
            
            # Gemini'ye sorgu gönder
            prompt = self._build_scalping_prompt(market_context)
            
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt,
                generation_config={
                    "temperature": 0.3,  # Düşük temperature = daha tutarlı
                    "top_p": 0.8,
                    "top_k": 40,
                    "max_output_tokens": 1024,
                }
            )
            
            # Response'u parse et
            analysis = self._parse_gemini_response(response.text)
            
            # Cache'e kaydet
            self.cache[cache_key] = {
                'timestamp': datetime.now(),
                'result': analysis
            }
            
            # Sonuçları logla
            if analysis['confidence'] > 70:
                print(f"🤖 {symbol} AI Sinyali: {analysis['signal']} "
                      f"(Güven: %{analysis['confidence']:.1f})")
                print(f"   📊 Risk Skoru: {analysis['risk_score']}/10")
                print(f"   💡 Neden: {analysis['reasoning'][:100]}...")
            
            return analysis
            
        except Exception as e:
            print(f"❌ Gemini analiz hatası: {e}")
            return self._fallback_analysis(ema_signal)
    
    def _prepare_market_context(
        self,
        symbol: str,
        current_price: float,
        klines_1m: List,
        klines_5m: List,
        ema_signal: str,
        volume_data: Dict
    ) -> Dict:
        """Market verilerini AI için hazırla"""
        
        # 1 dakikalık veriler
        latest_1m = klines_1m[-10:] if len(klines_1m) >= 10 else klines_1m
        
        # Son 10 mum için özet
        candles_1m = []
        for kline in latest_1m:
            candles_1m.append({
                'open': float(kline[1]),
                'high': float(kline[2]),
                'low': float(kline[3]),
                'close': float(kline[4]),
                'volume': float(kline[5])
            })
        
        # Fiyat momentum
        price_change_1m = 0
        if len(candles_1m) >= 2:
            price_change_1m = ((candles_1m[-1]['close'] - candles_1m[0]['open']) 
                              / candles_1m[0]['open'] * 100)
        
        # Volume momentum
        avg_volume = sum(c['volume'] for c in candles_1m) / len(candles_1m)
        current_volume = candles_1m[-1]['volume'] if candles_1m else 0
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
        
        # Volatilite (ATR benzeri)
        ranges = [c['high'] - c['low'] for c in candles_1m]
        avg_range = sum(ranges) / len(ranges) if ranges else 0
        volatility = (avg_range / current_price * 100) if current_price > 0 else 0
        
        return {
            'symbol': symbol,
            'current_price': current_price,
            'timeframe': '1m',
            'candles_count': len(candles_1m),
            'price_change_1m': price_change_1m,
            'volume_ratio': volume_ratio,
            'volatility_percent': volatility,
            'ema_signal': ema_signal,
            'latest_candles': candles_1m[-5:],  # Son 5 mum
            'trend_strength': abs(price_change_1m)
        }
    
    def _build_scalping_prompt(self, context: Dict) -> str:
        """AI için optimized prompt oluştur"""
        
        prompt = f"""
Siz bir profesyonel cryptocurrency scalping uzmanısınız. 1 dakikalık mum verilerini analiz edip hızlı alım-satım kararı veriyorsunuz.

## MARKET VERİLERİ
Symbol: {context['symbol']}
Güncel Fiyat: ${context['current_price']}
Son 1dk Değişim: %{context['price_change_1m']:.2f}
Volume Oranı: {context['volume_ratio']:.2f}x (1=normal, >1.5=yüksek)
Volatilite: %{context['volatility_percent']:.3f}
EMA Cross Sinyali: {context['ema_signal']}

## SON 5 MUM (1 Dakikalık)
"""
        for i, candle in enumerate(context['latest_candles'], 1):
            body_size = abs(candle['close'] - candle['open'])
            body_pct = (body_size / candle['open'] * 100) if candle['open'] > 0 else 0
            candle_type = "🟢 Bullish" if candle['close'] > candle['open'] else "🔴 Bearish"
            
            prompt += f"""
{i}. {candle_type} | O:{candle['open']:.2f} H:{candle['high']:.2f} L:{candle['low']:.2f} C:{candle['close']:.2f} | Body:%{body_pct:.2f}
"""

        prompt += f"""

## SCALPING KURALLARI
1. **Güvenli Giriş**: Trend net olmalı, volume yüksek olmalı
2. **Hızlı Çıkış**: TP: %0.3-0.5, SL: %0.2-0.3 (sıkı)
3. **Risk Yönetimi**: Risk/Reward minimum 1:1.5
4. **Volume Konfirmasyonu**: Volume ratio >1.3 olmalı
5. **Volatilite**: %0.1-0.3 arası ideal (çok düşük veya yüksek riskli)

## KARAR VERİN
Aşağıdaki JSON formatında yanıt verin (sadece JSON, açıklama yok):

{{
  "should_trade": true/false,
  "signal": "LONG" veya "SHORT" veya "HOLD",
  "confidence": 0-100 arası güven skoru,
  "stop_loss_percent": 0.2-0.5 arası,
  "take_profit_percent": 0.3-0.8 arası,
  "reasoning": "Kısa açıklama (max 100 karakter)",
  "risk_score": 0-10 arası (0=çok güvenli, 10=çok riskli)
}}

ÖNEMLİ: 
- Volume düşükse (ratio <1.2) HOLD deyin
- Volatilite çok yüksekse (>0.5%) HOLD deyin
- Trend belirsizse confidence <60 olmalı
- should_trade sadece confidence >75 ise true olmalı
"""
        return prompt
    
    def _parse_gemini_response(self, response_text: str) -> Dict:
        """Gemini yanıtını parse et"""
        try:
            # JSON'ı bul (markdown kod bloğu içinde olabilir)
            if '```json' in response_text:
                json_start = response_text.find('```json') + 7
                json_end = response_text.find('```', json_start)
                json_str = response_text[json_start:json_end].strip()
            elif '```' in response_text:
                json_start = response_text.find('```') + 3
                json_end = response_text.find('```', json_start)
                json_str = response_text[json_start:json_end].strip()
            else:
                json_str = response_text.strip()
            
            # JSON parse
            analysis = json.loads(json_str)
            
            # Validasyon
            required_keys = ['should_trade', 'signal', 'confidence', 
                           'stop_loss_percent', 'take_profit_percent',
                           'reasoning', 'risk_score']
            
            for key in required_keys:
                if key not in analysis:
                    raise ValueError(f"Missing key: {key}")
            
            # Değer kontrolü
            analysis['confidence'] = max(0, min(100, float(analysis['confidence'])))
            analysis['risk_score'] = max(0, min(10, float(analysis['risk_score'])))
            analysis['stop_loss_percent'] = max(0.1, min(1.0, float(analysis['stop_loss_percent'])))
            analysis['take_profit_percent'] = max(0.2, min(2.0, float(analysis['take_profit_percent'])))
            
            return analysis
            
        except Exception as e:
            print(f"❌ Gemini response parse hatası: {e}")
            print(f"Response: {response_text[:200]}")
            return {
                'should_trade': False,
                'signal': 'HOLD',
                'confidence': 0,
                'stop_loss_percent': 0.3,
                'take_profit_percent': 0.5,
                'reasoning': 'Parse error',
                'risk_score': 10
            }
    
    def _fallback_analysis(self, ema_signal: str) -> Dict:
        """AI olmadan basit analiz"""
        return {
            'should_trade': ema_signal in ['LONG', 'SHORT'],
            'signal': ema_signal,
            'confidence': 50,  # Orta güven
            'stop_loss_percent': 0.3,
            'take_profit_percent': 0.5,
            'reasoning': 'Fallback: EMA signal only',
            'risk_score': 5
        }
    
    def clear_cache(self):
        """Cache temizle"""
        self.cache.clear()
        print("🧹 Gemini cache temizlendi")

# Global instance
gemini_analyzer = GeminiAnalyzer()
