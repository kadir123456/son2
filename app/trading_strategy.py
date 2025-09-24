// ============ EMA DEBUG TEST - script.js'e ekleyin ============
    
    const debugSymbolInput = document.getElementById('debug-symbol-input');
    const debugEmaButton = document.getElementById('debug-ema-button');
    const debugResults = document.getElementById('debug-results');
    const debugOutput = document.getElementById('debug-output');

    if (debugEmaButton) {
        debugEmaButton.addEventListener('click', async () => {
            const symbol = debugSymbolInput ? debugSymbolInput.value.trim().toUpperCase() : '';
            if (!symbol) {
                showError('Lütfen debug için bir symbol girin.');
                return;
            }
            
            debugEmaButton.disabled = true;
            debugEmaButton.textContent = '🔍 Analiz ediliyor...';
            debugResults.style.display = 'none';
            
            try {
                const result = await fetchApi('/api/debug-ema', { 
                    method: 'POST', 
                    body: JSON.stringify({ symbol }) 
                });
                
                if (result && result.success) {
                    // Debug sonuçlarını güzel formatta göster
                    const debugInfo = result.debug_info;
                    const strategyStatus = result.strategy_status;
                    
                    let output = `🎯 ${result.symbol} EMA Debug Raporu\n`;
                    output += `⏰ Timeframe: ${result.timeframe}\n`;
                    output += `🚨 Mevcut Sinyal: ${result.current_signal}\n`;
                    output += `=======================================\n\n`;
                    
                    if (debugInfo.error) {
                        output += `❌ Hata: ${debugInfo.error}\n`;
                    } else {
                        output += `📊 Toplam Mum: ${debugInfo.total_candles}\n`;
                        output += `💰 Mevcut Fiyat: ${debugInfo.current_price}\n`;
                        output += `📈 EMA9: ${debugInfo.current_ema9.toFixed(6)}\n`;
                        output += `📊 EMA21: ${debugInfo.current_ema21.toFixed(6)}\n`;
                        output += `⚖️  EMA9 > EMA21: ${debugInfo.ema9_above}\n`;
                        output += `🚀 Bullish Cross: ${debugInfo.bullish_cross}\n`;
                        output += `📉 Bearish Cross: ${debugInfo.bearish_cross}\n\n`;
                        
                        output += `🔍 Son 5 Mum Detayı:\n`;
                        output += `=======================================\n`;
                        
                        if (debugInfo.last_5_candles) {
                            debugInfo.last_5_candles.forEach((candle, index) => {
                                const num = debugInfo.last_5_candles.length - index;
                                output += `${num}. Close: ${candle.close?.toFixed(4)} | `;
                                output += `EMA9: ${candle.ema9?.toFixed(4)} | `;
                                output += `EMA21: ${candle.ema21?.toFixed(4)} | `;
                                output += `Above: ${candle.ema9_above_ema21} | `;
                                output += `Bull: ${candle.bullish_cross} | `;
                                output += `Bear: ${candle.bearish_cross}\n`;
                            });
                        }
                    }
                    
                    output += `\n📋 Strateji Bilgisi:\n`;
                    output += `=======================================\n`;
                    output += `Versiyon: ${strategyStatus.strategy_version}\n`;
                    output += `EMA Hızlı: ${strategyStatus.ema_fast}\n`;
                    output += `EMA Yavaş: ${strategyStatus.ema_slow}\n`;
                    
                    if (strategyStatus.fix_notes) {
                        output += `\n🔧 Düzeltmeler:\n`;
                        strategyStatus.fix_notes.forEach(note => {
                            output += `${note}\n`;
                        });
                    }
                    
                    debugOutput.textContent = output;
                    debugResults.style.display = 'block';
                    
                    showSuccess(`${symbol} EMA analizi tamamlandı`);
                } else {
                    showError(result?.error || 'Debug analizi başarısız');
                }
                
            } catch (error) {
                showError('Debug isteği hatası: ' + error.message);
            } finally {
                debugEmaButton.disabled = false;
                debugEmaButton.textContent = '🐛 EMA Sinyali Test Et';
            }
        });
    }

    // Debug için Enter tuşu desteği
    if (debugSymbolInput) {
        debugSymbolInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && debugEmaButton && !debugEmaButton.disabled) {
                debugEmaButton.click();
            }
        });
    }
