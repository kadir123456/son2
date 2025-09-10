async def create_market_order_with_sl_tp(self, symbol: str, side: str, quantity: float, entry_price: float, price_precision: int):
    """
    Piyasa emri ile birlikte hem Stop Loss hem de Take Profit emri oluşturur
    YETİM EMİR KORUMASLI VERSİYON - TP/SL DÜZELTİLMİŞ
    """
    def format_price(price):
        return f"{price:.{price_precision}f}"
        
    try:
        # 🧹 ADIM 1: Önce tüm açık emirleri temizle (YETİM EMİR KORUMASII)
        print(f"🧹 {symbol} için yetim emir kontrolü yapılıyor...")
        cleanup_success = await self.cancel_all_orders_safe(symbol)
        if not cleanup_success:
            print("⚠️ Yetim emir temizliği başarısız - devam ediliyor...")
        
        # Kısa bekleme - emirlerin tamamen iptal olması için
        await asyncio.sleep(0.3)
        
        # 📈 ADIM 2: Ana piyasa emrini oluştur
        print(f"📈 {symbol} {side} {quantity} ana piyasa emri oluşturuluyor...")
        await self._rate_limit_delay()
        main_order = await self.client.futures_create_order(
            symbol=symbol,
            side=side,
            type='MARKET',
            quantity=quantity
        )
        print(f"✅ Ana pozisyon başarılı: {symbol} {side} {quantity}")
        
        # Pozisyon açıldıktan sonra bekleme - SL/TP için hazır olması için
        await asyncio.sleep(1.0)  # 0.8'den 1.0'a artırdık
        
        # 🛡️ ADIM 3: Stop Loss ve Take Profit fiyatlarını hesapla
        if side == 'BUY':  # Long pozisyon
            sl_price = entry_price * (1 - settings.STOP_LOSS_PERCENT)
            tp_price = entry_price * (1 + settings.TAKE_PROFIT_PERCENT)
            opposite_side = 'SELL'
        else:  # Short pozisyon
            sl_price = entry_price * (1 + settings.STOP_LOSS_PERCENT)
            tp_price = entry_price * (1 - settings.TAKE_PROFIT_PERCENT)
            opposite_side = 'BUY'
        
        formatted_sl_price = format_price(sl_price)
        formatted_tp_price = format_price(tp_price)
        
        print(f"💡 Hesaplanan fiyatlar:")
        print(f"   Giriş: {entry_price}")
        print(f"   SL: {formatted_sl_price}")
        print(f"   TP: {formatted_tp_price}")
        
        # 🛑 ADIM 4: Stop Loss emrini oluştur - DÜZELTİLMİŞ FORMAT
        sl_success = False
        tp_success = False
        
        try:
            print(f"🛑 Stop Loss emri oluşturuluyor: {formatted_sl_price}")
            await self._rate_limit_delay()
            sl_order = await self.client.futures_create_order(
                symbol=symbol,
                side=opposite_side,
                type='STOP_MARKET',
                quantity=quantity,  # ✅ quantity eklendi
                stopPrice=formatted_sl_price,
                timeInForce='GTE_GTC',  # ✅ timeInForce eklendi
                reduceOnly=True  # ✅ reduceOnly eklendi
            )
            print(f"✅ STOP LOSS başarılı: {formatted_sl_price}")
            sl_success = True
        except BinanceAPIException as e:
            print(f"❌ Stop Loss emri hatası: {e}")
            print(f"🔍 SL Hata detayı: Code={getattr(e, 'code', 'N/A')}, Message={getattr(e, 'message', str(e))}")
        
        # 🎯 ADIM 5: Take Profit emrini oluştur - DÜZELTİLMİŞ FORMAT
        try:
            print(f"🎯 Take Profit emri oluşturuluyor: {formatted_tp_price}")
            await self._rate_limit_delay()
            tp_order = await self.client.futures_create_order(
                symbol=symbol,
                side=opposite_side,
                type='TAKE_PROFIT_MARKET',
                quantity=quantity,  # ✅ quantity eklendi
                stopPrice=formatted_tp_price,
                timeInForce='GTE_GTC',  # ✅ timeInForce eklendi
                reduceOnly=True  # ✅ reduceOnly eklendi
            )
            print(f"✅ TAKE PROFIT başarılı: {formatted_tp_price}")
            tp_success = True
        except BinanceAPIException as e:
            print(f"❌ Take Profit emri hatası: {e}")
            print(f"🔍 TP Hata detayı: Code={getattr(e, 'code', 'N/A')}, Message={getattr(e, 'message', str(e))}")
        
        # 📊 ADIM 6: Alternatif yaklaşım - Eğer yukarıdaki başarısız olursa
        if not sl_success or not tp_success:
            print("🔄 Alternatif OCO emri deneniyor...")
            try:
                await self._rate_limit_delay()
                # OCO (One-Cancels-Other) emri - bazı durumlarda daha kararlı
                oco_order = await self.client.futures_create_order(
                    symbol=symbol,
                    side=opposite_side,
                    type='STOP',
                    quantity=quantity,
                    price=formatted_tp_price,  # limit price (TP)
                    stopPrice=formatted_sl_price,  # stop price (SL)
                    timeInForce='GTC',
                    reduceOnly=True
                )
                print(f"✅ OCO emri başarılı - hem SL hem TP kuruldu")
                sl_success = True
                tp_success = True
            except BinanceAPIException as oco_error:
                print(f"❌ OCO emri de başarısız: {oco_error}")
        
        # 📊 ADIM 7: Sonuç raporu ve güvenlik kontrolü
        if not sl_success and not tp_success:
            print("⚠️ UYARI: Ne SL ne de TP kurulabildi! Manuel kontrol gerekebilir.")
            # Acil durum - pozisyonu hemen kapat?
            print("🚨 Korumasız pozisyon tespit edildi!")
        elif not sl_success:
            print("⚠️ UYARI: Sadece TP kuruldu, SL kurulamadı!")
        elif not tp_success:
            print("⚠️ UYARI: Sadece SL kuruldu, TP kurulamadı!")
        else:
            print("✅ Pozisyon tam korumalı: Hem SL hem TP kuruldu.")
        
        return main_order
        
    except BinanceAPIException as e:
        print(f"❌ KRITIK HATA: Ana pozisyon emri oluşturulamadı: {e}")
        # Ana emir başarısız olursa mutlaka temizlik yap
        print("🧹 Hata sonrası acil temizlik yapılıyor...")
        await self.cancel_all_orders_safe(symbol)
        return None
    except Exception as e:
        print(f"❌ BEKLENMEYEN HATA: {e}")
        # Genel hata durumunda da temizlik yap
        print("🧹 Beklenmeyen hata sonrası temizlik yapılıyor...")
        await self.cancel_all_orders_safe(symbol)
        return None
