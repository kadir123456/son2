async def _update_status_info(self):
    """Durum bilgilerini günceller - OPTIMIZE EDİLMİŞ"""
    try:
        if self.status["is_running"]:
            # Cache kullanarak sorgu sayısını azalt
            self.status["account_balance"] = await binance_client.get_account_balance(use_cache=True)
            if self.status["position_side"]:
                self.status["position_pnl"] = await binance_client.get_position_pnl(
                    self.status["symbol"], use_cache=True
                )
            else:
                self.status["position_pnl"] = 0.0
            
            # SADECE POZİSYON KAPANDIĞINDA VEYA İLK BAŞLADIĞINDA DİNAMİK SİZING HESAPLA
            # Her status update'de değil!
            if not hasattr(self, '_last_sizing_update'):
                self._last_sizing_update = 0
            
            current_time = time.time()
            # 60 saniyede bir sizing güncelle (çok daha az)
            if current_time - self._last_sizing_update > 60:
                await self._calculate_dynamic_order_size()
                self._last_sizing_update = current_time
                
    except Exception as e:
        print(f"Durum güncelleme hatası: {e}")

async def _flip_position(self, new_signal: str):
    symbol = self.status["symbol"]
    
    try:
        # Mevcut pozisyonu kapat
        open_positions = await binance_client.get_open_positions(symbol, use_cache=False)
        if open_positions:
            position = open_positions[0]
            position_amt = float(position['positionAmt'])
            side_to_close = 'SELL' if position_amt > 0 else 'BUY'
            print(f"--> Ters sinyal geldi. Mevcut {self.status['position_side']} pozisyonu kapatılıyor...")
            
            pnl = await binance_client.get_last_trade_pnl(symbol)
            firebase_manager.log_trade({
                "symbol": symbol, 
                "pnl": pnl, 
                "status": "CLOSED_BY_FLIP", 
                "timestamp": datetime.now(timezone.utc)
            })

            await binance_client.close_position(symbol, position_amt, side_to_close)
            await asyncio.sleep(2)  # Pozisyon kapanması için biraz daha bekle

        # BURDA DİNAMİK ORDER SIZE HESAPLA (pozisyon değiştiğinde)
        print(f"--> Yeni {new_signal} pozisyonu için dinamik boyut hesaplanıyor...")
        dynamic_order_size = await self._calculate_dynamic_order_size()
        
        # Yeni pozisyon aç
        print(f"--> Yeni {new_signal} pozisyonu açılıyor... (Tutar: {dynamic_order_size} USDT)")
        side = "BUY" if new_signal == "LONG" else "SELL"
        price = await binance_client.get_market_price(symbol)
        if not price:
            print("❌ Yeni pozisyon için fiyat alınamadı.")
            return
            
        quantity = self._format_quantity((dynamic_order_size * settings.LEVERAGE) / price)
        if quantity <= 0:
            print("❌ Hesaplanan miktar çok düşük.")
            return

        print(f"📊 İşlem detayları:")
        print(f"   Fiyat: {price}")
        print(f"   Miktar: {quantity}")
        print(f"   Toplam: {dynamic_order_size * settings.LEVERAGE} USDT değerinde pozisyon")

        order = await binance_client.create_market_order_with_sl_tp(
            symbol, side, quantity, price, self.price_precision
        )
        
        if order:
            self.status["position_side"] = new_signal
            self.status["status_message"] = f"Yeni {new_signal} pozisyonu {price} fiyattan açıldı. (Tutar: {dynamic_order_size:.2f} USDT)"
            print(f"✅ {self.status['status_message']}")
            
            # Cache temizle
            try:
                if hasattr(binance_client, '_cached_positions'):
                    binance_client._cached_positions.clear()
                if hasattr(binance_client, '_last_position_check'):
                    binance_client._last_position_check.clear()
            except Exception as cache_error:
                print(f"Cache temizleme hatası: {cache_error}")
        else:
            self.status["position_side"] = None
            self.status["status_message"] = "Yeni pozisyon açılamadı."
            print(f"❌ {self.status['status_message']}")
            
    except Exception as e:
        print(f"Pozisyon değiştirme hatası: {e}")
        print(f"Full traceback: {traceback.format_exc()}")
        self.status["position_side"] = None
