document.addEventListener('DOMContentLoaded', () => {
    // Firebase yapılandırması
    const firebaseConfig = {
        apiKey: "AIzaSyDkJch-8B46dpZSB-pMSR4q1uvzadCVekE",
        authDomain: "aviator-90c8b.firebaseapp.com",
        databaseURL: "https://aviator-90c8b-default-rtdb.firebaseio.com",
        projectId: "aviator-90c8b",
        storageBucket: "aviator-90c8b.appspot.com",
        messagingSenderId: "823763988442",
        appId: "1:823763988442:web:16a797275675a219c3dae3"
    };

    firebase.initializeApp(firebaseConfig);
    const auth = firebase.auth();
    const database = firebase.database();

    // HTML elementleri - Login
    const loginContainer = document.getElementById('login-container');
    const appContainer = document.getElementById('app-container');
    const loginButton = document.getElementById('login-button');
    const logoutButton = document.getElementById('logout-button');
    const emailInput = document.getElementById('email');
    const passwordInput = document.getElementById('password');
    const loginError = document.getElementById('login-error');
    
    // HTML elementleri - Bot kontrolleri
    const multiSymbolsInput = document.getElementById('multi-symbols-input');
    const multiStartButton = document.getElementById('multi-start-button');
    const stopButton = document.getElementById('stop-button');
    const refreshButton = document.getElementById('refresh-button');
    const singleSymbolInput = document.getElementById('single-symbol-input');
    const singleStartButton = document.getElementById('single-start-button');
    
    // HTML elementleri - Status
    const statusMessageSpan = document.getElementById('status-message');
    const monitoredSymbolsSpan = document.getElementById('monitored-symbols');
    const activePositionSpan = document.getElementById('active-position');
    const websocketCountSpan = document.getElementById('websocket-count');
    const lastUpdateSpan = document.getElementById('last-update');
    const symbolsCard = document.getElementById('symbols-card');
    const symbolsList = document.getElementById('symbols-list');
    
    // HTML elementleri - Pozisyon yönetimi
    const scanAllButton = document.getElementById('scan-all-button');
    const monitorToggleButton = document.getElementById('monitor-toggle-button');
    const scanSymbolInput = document.getElementById('scan-symbol-input');
    const scanSymbolButton = document.getElementById('scan-symbol-button');
    
    // HTML elementleri - İstatistikler
    const statsMainBalance = document.getElementById('stats-main-balance');
    const statsPositionPnl = document.getElementById('stats-position-pnl');
    const statsOrderSize = document.getElementById('stats-order-size');
    const statsTotal = document.getElementById('stats-total-trades');
    const statsWinning = document.getElementById('stats-winning-trades');
    const statsLosing = document.getElementById('stats-losing-trades');
    const statsWinRate = document.getElementById('stats-win-rate');
    
    // Global değişkenler
    let statusInterval;
    let isMonitorRunning = false;
    let lastRefresh = 0; // Manuel refresh rate limiting için

    // ⚡ API RATE SORUNU DÜZELTİLDİ
    // Eski: Her 8 saniyede bir istek (çok fazla!)
    // Yeni: Bot çalışırken 45 saniye, durmuşken 60 saniye
    const STATUS_UPDATE_INTERVALS = {
        BOT_RUNNING: 45000,      // Bot çalışırken 45 saniyede bir
        BOT_STOPPED: 60000       // Bot durakken 60 saniyede bir
    };

    // ============ KİMLİK DOĞRULAMA ============
    
    loginButton.addEventListener('click', () => {
        loginError.textContent = "";
        auth.signInWithEmailAndPassword(emailInput.value, passwordInput.value)
            .catch(error => { 
                loginError.textContent = "Hatalı e-posta veya şifre."; 
            });
    });

    logoutButton.addEventListener('click', () => { 
        auth.signOut(); 
    });

    auth.onAuthStateChanged(user => {
        if (user) {
            loginContainer.style.display = 'none';
            appContainer.style.display = 'flex';
            console.log('✅ Kullanıcı giriş yaptı:', user.email);
            
            // İlk status kontrolü
            getStatus();
            
            // ✅ DÜZELTİLDİ: Optimize edilmiş status güncellemeleri
            startOptimizedStatusUpdates();
            
            // Diğer başlangıç işlemleri
            listenForTradeUpdates();
            updateMonitorButton();
        } else {
            loginContainer.style.display = 'flex';
            appContainer.style.display = 'none';
            
            // Status güncellemelerini durdur
            stopStatusUpdates();
            console.log('👤 Kullanıcı çıkış yaptı');
        }
    });

    // ============ OPTIMIZE EDİLMİŞ STATUS GÜNCELLEMELERİ ============
    
    function startOptimizedStatusUpdates() {
        console.log('🚀 Optimize edilmiş status güncellemeleri başlatılıyor...');
        
        // Mevcut interval'ları temizle
        stopStatusUpdates();
        
        const updateStatus = async () => {
            try {
                console.log('📡 Status güncelleniyor...');
                await getStatus();
                
                // Bot durumuna göre dinamik interval
                const currentStatus = await getCurrentBotStatus();
                const interval = currentStatus.is_running ? 
                    STATUS_UPDATE_INTERVALS.BOT_RUNNING : 
                    STATUS_UPDATE_INTERVALS.BOT_STOPPED;
                
                const intervalText = interval === STATUS_UPDATE_INTERVALS.BOT_RUNNING ? '45s' : '60s';
                console.log(`⏰ Sonraki güncelleme: ${intervalText} sonra (Bot: ${currentStatus.is_running ? 'ÇALIŞIYOR' : 'DURMUŞ'})`);
                
                // Sonraki güncellemeyi zamanla
                statusInterval = setTimeout(updateStatus, interval);
                
            } catch (error) {
                console.error('❌ Status güncelleme hatası:', error);
                
                // Hata durumunda 30 saniye sonra tekrar dene
                statusInterval = setTimeout(updateStatus, 30000);
            }
        };
        
        updateStatus(); // İlk çalıştırma
    }

    function stopStatusUpdates() {
        if (statusInterval) {
            clearInterval(statusInterval);
            clearTimeout(statusInterval);
            statusInterval = null;
            console.log('🛑 Status güncellemeleri durduruldu');
        }
    }

    async function getCurrentBotStatus() {
        try {
            // Mevcut UI state'inden bot durumunu kontrol et
            const statusMessage = statusMessageSpan ? statusMessageSpan.textContent.toLowerCase() : '';
            const isRunning = statusMessage.includes('izleniyor') || 
                             statusMessage.includes('başlatılıyor') ||
                             statusMessage.includes('çalışıyor') ||
                             statusMessage.includes('coin') ||
                             statusMessage.includes('ema');
            
            return { is_running: isRunning };
            
        } catch (e) {
            console.log('⚠️ Bot durumu belirlenemedi, varsayılan: DURMUŞ');
            return { is_running: false };
        }
    }

    // ============ API İSTEKLERİ ============
    
    async function fetchApi(endpoint, options = {}) {
        const user = auth.currentUser;
        if (!user) {
            console.error('❌ Kullanıcı oturumu bulunamadı');
            return null;
        }
        
        try {
            const idToken = await user.getIdToken(true);
            const headers = { 
                ...options.headers, 
                'Authorization': `Bearer ${idToken}` 
            };
            
            if (options.body) {
                headers['Content-Type'] = 'application/json';
            }
            
            const response = await fetch(endpoint, { 
                ...options, 
                headers 
            });
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ 
                    detail: response.statusText 
                }));
                console.error("API Hatası:", errorData.detail);
                showError(errorData.detail);
                return null;
            }
            
            return response.json();
            
        } catch (error) { 
            console.error("API isteği hatası:", error); 
            showError("Bağlantı hatası: " + error.message);
            return null; 
        }
    }

    function showError(message) {
        console.error("🔴 HATA:", message);
        // TODO: Toast notification eklenebilir
    }

    function showSuccess(message) {
        console.log("🟢 BAŞARILI:", message);
        // TODO: Toast notification eklenebilir
    }

    // ============ UI GÜNCELLEME FONKSİYONLARI ============
    
    function updateLastUpdateTime() {
        if (lastUpdateSpan) {
            const now = new Date();
            lastUpdateSpan.textContent = now.toLocaleTimeString('tr-TR');
        }
    }
    
    const updateUI = (data) => {
        if (!data) {
            console.warn('⚠️ UI güncellemesi için veri yok');
            return;
        }
        
        updateLastUpdateTime();
        
        // Durum mesajı
        if (statusMessageSpan) {
            statusMessageSpan.textContent = data.status_message || 'Bilinmiyor';
            statusMessageSpan.className = data.is_running ? 'status-running' : 'status-stopped';
        }
        
        // İzlenen coinler
        if (monitoredSymbolsSpan) {
            if (data.symbols && data.symbols.length > 0) {
                monitoredSymbolsSpan.textContent = `${data.symbols.length} coin (${data.symbols.join(', ')})`;
                monitoredSymbolsSpan.className = 'status-monitoring';
                
                // Symbols card'ı göster ve güncelle
                if (symbolsCard) {
                    symbolsCard.style.display = 'block';
                    updateSymbolsList(data.symbols, data.last_signals, data.active_symbol);
                }
            } else {
                monitoredSymbolsSpan.textContent = 'Hayır';
                monitoredSymbolsSpan.className = '';
                if (symbolsCard) {
                    symbolsCard.style.display = 'none';
                }
            }
        }
        
        // Aktif pozisyon
        if (activePositionSpan) {
            if (data.active_symbol && data.position_side) {
                activePositionSpan.textContent = `${data.position_side} @ ${data.active_symbol}`;
                activePositionSpan.className = 'status-in-position';
            } else {
                activePositionSpan.textContent = 'Hayır';
                activePositionSpan.className = '';
            }
        }
        
        // WebSocket bağlantıları
        if (websocketCountSpan) {
            websocketCountSpan.textContent = data.websocket_connections || 0;
        }
        
        // Bot kontrolleri
        updateBotControls(data.is_running);
        
        // Finansal veriler
        updateFinancialData(data);
    };

    function updateBotControls(isRunning) {
        if (multiStartButton) multiStartButton.disabled = isRunning;
        if (singleStartButton) singleStartButton.disabled = isRunning;
        if (stopButton) stopButton.disabled = !isRunning;
        if (multiSymbolsInput) multiSymbolsInput.disabled = isRunning;
        if (singleSymbolInput) singleSymbolInput.disabled = false;
    }

    function updateFinancialData(data) {
        // Ana bakiye
        if (statsMainBalance) {
            if (data.is_running && data.account_balance !== undefined) {
                formatPnl(statsMainBalance, data.account_balance, true);
            } else {
                statsMainBalance.textContent = 'N/A';
                statsMainBalance.className = 'stats-value';
            }
        }

        // Pozisyon P&L
        if (statsPositionPnl) {
            if (data.is_running && data.position_pnl !== undefined) {
                formatPnl(statsPositionPnl, data.position_pnl);
            } else {
                statsPositionPnl.textContent = 'N/A';
                statsPositionPnl.className = 'stats-value';
            }
        }

        // Order size
        if (statsOrderSize) {
            if (data.is_running && data.order_size !== undefined) {
                statsOrderSize.textContent = `${data.order_size.toFixed(2)} USDT`;
                statsOrderSize.className = 'stats-value';
            } else {
                statsOrderSize.textContent = 'N/A';
                statsOrderSize.className = 'stats-value';
            }
        }
    }

    function updateSymbolsList(symbols, lastSignals, activeSymbol) {
        if (!symbolsList) return;
        
        symbolsList.innerHTML = '';
        
        symbols.forEach(symbol => {
            const symbolDiv = document.createElement('div');
            symbolDiv.className = 'symbol-item';
            if (symbol === activeSymbol) {
                symbolDiv.classList.add('active-symbol');
            }
            
            const signal = lastSignals ? lastSignals[symbol] || 'HOLD' : 'HOLD';
            const signalClass = signal === 'LONG' ? 'signal-long' : 
                               signal === 'SHORT' ? 'signal-short' : 'signal-hold';
            
            symbolDiv.innerHTML = `
                <div class="symbol-name">${symbol}</div>
                <div class="symbol-signal ${signalClass}">${signal}</div>
            `;
            
            symbolsList.appendChild(symbolDiv);
        });
    }

    function formatPnl(element, value, isBalance = false) {
        if (!element) return;
        
        element.textContent = `${value.toFixed(2)} USDT`;
        if (isBalance) {
            element.className = 'stats-value';
        } else {
            element.className = value > 0 ? 'stats-value pnl-positive' : 
                             (value < 0 ? 'stats-value pnl-negative' : 'stats-value');
        }
    }

    // ============ API ÇAĞRILARI ============
    
    const getStatus = () => fetchApi('/api/multi-status').then(updateUI);

    // ============ EVENT LISTENERS ============
    
    // Manuel refresh butonu - Rate limit korumalı
    if (refreshButton) {
        refreshButton.addEventListener('click', async () => {
            const now = Date.now();
            if (now - lastRefresh < 5000) { // 5 saniye cooldown
                showError('⏳ Çok sık yenileme, 5 saniye bekleyin');
                return;
            }
            lastRefresh = now;
            
            refreshButton.disabled = true;
            refreshButton.textContent = 'Yenileniyor...';
            
            await getStatus();
            
            setTimeout(() => {
                refreshButton.disabled = false;
                refreshButton.textContent = '🔄 Manuel Yenile';
                showSuccess('Durum yenilendi');
            }, 1000);
        });
    }

    // Multi-coin bot başlatma
    if (multiStartButton) {
        multiStartButton.addEventListener('click', async () => {
            const symbolsInput = multiSymbolsInput ? multiSymbolsInput.value.trim() : '';
            if (!symbolsInput) {
                showError('Lütfen en az bir coin sembolü girin.');
                return;
            }
            
            const symbols = symbolsInput.split(',')
                .map(s => s.trim().toUpperCase())
                .filter(s => s.length > 0);
            
            if (symbols.length === 0) {
                showError('Geçerli coin sembolleri girin.');
                return;
            }
            
            if (symbols.length > 10) {
                showError('Maksimum 10 coin desteklenir.');
                return;
            }
            
            console.log('🚀 Multi-coin bot başlatılıyor:', symbols);
            const result = await fetchApi('/api/multi-start', { 
                method: 'POST', 
                body: JSON.stringify({ symbols }) 
            });
            
            if (result && result.status) {
                updateUI(result.status);
                showSuccess(`${symbols.length} coin için bot başlatıldı`);
                
                // Bot başlatıldığında status güncellemesini yeniden başlat
                startOptimizedStatusUpdates();
            }
        });
    }

    // Tek coin bot başlatma
    if (singleStartButton) {
        singleStartButton.addEventListener('click', async () => {
            const symbol = singleSymbolInput ? singleSymbolInput.value.trim().toUpperCase() : '';
            if (!symbol) {
                showError('Lütfen bir coin sembolü girin.');
                return;
            }
            
            console.log('🔄 Tek coin bot başlatılıyor:', symbol);
            const result = await fetchApi('/api/start', { 
                method: 'POST', 
                body: JSON.stringify({ symbol }) 
            });
            
            if (result) {
                // Legacy response'u multi format'a çevir
                const multiResult = {
                    is_running: result.is_running,
                    symbols: result.symbol ? [result.symbol] : [],
                    active_symbol: result.symbol,
                    position_side: result.position_side,
                    status_message: result.status_message,
                    account_balance: result.account_balance,
                    position_pnl: result.position_pnl,
                    order_size: result.order_size,
                    last_signals: {},
                    websocket_connections: 1
                };
                updateUI(multiResult);
                showSuccess(`Tek coin modu: ${symbol} başlatıldı`);
                startOptimizedStatusUpdates();
            }
        });
    }

    // Bot durdurma
    if (stopButton) {
        stopButton.addEventListener('click', async () => {
            const result = await fetchApi('/api/stop', { method: 'POST' });
            if (result) {
                updateUI(result);
                showSuccess('Bot durduruldu');
                
                // Bot durdurulduğunda güncelleme sıklığını ayarla
                startOptimizedStatusUpdates();
            }
        });
    }

    // ============ POZİSYON YÖNETİMİ EVENT LISTENERS ============
    
    if (scanAllButton) {
        scanAllButton.addEventListener('click', async () => {
            scanAllButton.disabled = true;
            scanAllButton.textContent = 'Taranıyor...';
            
            const result = await fetchApi('/api/scan-all-positions', { method: 'POST' });
            
            scanAllButton.disabled = false;
            scanAllButton.textContent = '🔍 Tüm Pozisyonları Tara';
            
            if (result && result.success) {
                showSuccess(result.message);
            }
        });
    }

    if (monitorToggleButton) {
        monitorToggleButton.addEventListener('click', async () => {
            if (isMonitorRunning) {
                const result = await fetchApi('/api/stop-position-monitor', { method: 'POST' });
                if (result && result.success) {
                    showSuccess(result.message);
                    updateMonitorButton();
                }
            } else {
                const result = await fetchApi('/api/start-position-monitor', { method: 'POST' });
                if (result && result.success) {
                    showSuccess(result.message);
                    updateMonitorButton();
                }
            }
        });
    }

    if (scanSymbolButton) {
        scanSymbolButton.addEventListener('click', async () => {
            const symbol = scanSymbolInput ? scanSymbolInput.value.trim().toUpperCase() : '';
            if (!symbol) {
                showError('Lütfen bir coin sembolü girin.');
                return;
            }
            
            scanSymbolButton.disabled = true;
            scanSymbolButton.textContent = 'Kontrol Ediliyor...';
            
            const result = await fetchApi('/api/scan-symbol', { 
                method: 'POST', 
                body: JSON.stringify({ symbol }) 
            });
            
            scanSymbolButton.disabled = false;
            scanSymbolButton.textContent = '🎯 Coin Kontrol Et';
            
            if (result && result.success) {
                if (scanSymbolInput) scanSymbolInput.value = '';
                showSuccess(result.message);
            }
        });
    }

    async function updateMonitorButton() {
        const status = await fetchApi('/api/position-monitor-status');
        if (status && status.monitor_status && monitorToggleButton) {
            isMonitorRunning = status.monitor_status.is_running;
            monitorToggleButton.textContent = isMonitorRunning ? 'Monitor Durdur' : 'Monitor Başlat';
            monitorToggleButton.className = isMonitorRunning ? 'btn btn-warning' : 'btn btn-secondary';
        }
    }

    // ============ İSTATİSTİK YÖNETİMİ ============
    
    function listenForTradeUpdates() {
        const tradesRef = database.ref('trades');
        tradesRef.on('value', (snapshot) => {
            const trades = snapshot.val() ? Object.values(snapshot.val()) : [];
            calculateAndDisplayStats(trades);
        });
    }

    function calculateAndDisplayStats(trades) {
        let totalTrades = trades.length;
        let winningTrades = 0, losingTrades = 0;

        trades.forEach(trade => {
            const pnl = parseFloat(trade.pnl) || 0;
            if (pnl > 0) {
                winningTrades++;
            } else {
                losingTrades++;
            }
        });

        // İstatistikleri güncelle
        if (statsTotal) statsTotal.textContent = totalTrades;
        if (statsWinning) statsWinning.textContent = winningTrades;
        if (statsLosing) statsLosing.textContent = losingTrades;
        
        if (statsWinRate) {
            const winRate = totalTrades > 0 ? ((winningTrades / totalTrades) * 100).toFixed(1) : 0;
            statsWinRate.textContent = `%${winRate}`;
        }
    }

    // ============ BAŞLANGIÇ MESAJI ============
    
    console.log('🎯 Basit EMA Cross Bot v1.0 yüklendi');
    console.log('⚡ API Rate Limit sorunu düzeltildi: 45s/60s interval');
    console.log('🚀 Bot hazır!');
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
     // ============ 🤖 GEMİNİ AI FONKSİYONLARI - MEVCUT script.js'in SONUNA EKLEYİN ============

// Gemini HTML elementleri
const geminiTestSymbol = document.getElementById('gemini-test-symbol');
const geminiTestButton = document.getElementById('gemini-test-button');
const geminiStatusButton = document.getElementById('gemini-status-button');
const geminiClearCacheButton = document.getElementById('gemini-clear-cache-button');
const geminiResults = document.getElementById('gemini-results');
const geminiOutput = document.getElementById('gemini-output');
const geminiStatusText = document.getElementById('gemini-status-text');
const geminiProvider = document.getElementById('gemini-provider');
const geminiCacheSize = document.getElementById('gemini-cache-size');

// Gemini AI Test
if (geminiTestButton) {
    geminiTestButton.addEventListener('click', async () => {
        const symbol = geminiTestSymbol.value.trim().toUpperCase();
        if (!symbol) {
            showError('Lütfen bir coin sembolü girin.');
            return;
        }
        
        geminiTestButton.disabled = true;
        geminiTestButton.textContent = '🤖 AI analiz ediyor...';
        geminiResults.style.display = 'none';
        
        try {
            const result = await fetchApi('/api/test-gemini', {
                method: 'POST',
                body: JSON.stringify({ symbol })
            });
            
            if (result && result.success) {
                const analysis = result.ai_analysis;
                
                let output = `🤖 ${result.symbol} GEMINI AI ANALİZİ\n`;
                output += `💰 Fiyat: $${result.current_price.toFixed(2)}\n`;
                output += `═══════════════════════════════════\n\n`;
                
                output += `🚦 SİNYAL: ${analysis.signal}\n`;
                output += `📊 İŞLEM ÖNERİSİ: ${analysis.should_trade ? '✅ EVET' : '❌ HAYIR'}\n`;
                output += `🎯 GÜVEN SKORU: %${analysis.confidence.toFixed(1)}\n`;
                output += `⚠️ RİSK SKORU: ${analysis.risk_score}/10\n\n`;
                
                output += `📝 AI AÇIKLAMASI:\n${analysis.reasoning}\n\n`;
                
                if (analysis.should_trade) {
                    output += `💹 ÖNERİLEN POZİSYON:\n`;
                    output += `   🎯 Take Profit: %${analysis.take_profit_percent.toFixed(2)}\n`;
                    output += `   🛑 Stop Loss: %${analysis.stop_loss_percent.toFixed(2)}\n\n`;
                }
                
                output += `📊 VERİ İSTATİSTİKLERİ:\n`;
                output += `   1m mumlar: ${result.data_info.klines_1m_count}\n`;
                output += `   5m mumlar: ${result.data_info.klines_5m_count}\n`;
                output += `   Timeframe: ${result.data_info.timeframe_primary} + ${result.data_info.timeframe_secondary}\n`;
                
                geminiOutput.textContent = output;
                geminiResults.style.display = 'block';
                
                showSuccess(result.message);
            } else if (result && !result.ai_enabled) {
                let errorMsg = result.message || 'Gemini AI aktif değil';
                if (result.help) {
                    errorMsg += '\n\n' + result.help;
                }
                showError(errorMsg);
                geminiOutput.textContent = `❌ ${errorMsg}`;
                geminiResults.style.display = 'block';
            }
            
        } catch (error) {
            showError('Gemini AI test hatası: ' + error.message);
        } finally {
            geminiTestButton.disabled = false;
            geminiTestButton.textContent = '🤖 Gemini AI Test';
        }
    });
}

// Gemini Status Kontrol
if (geminiStatusButton) {
    geminiStatusButton.addEventListener('click', async () => {
        try {
            const result = await fetchApi('/api/gemini-status');
            
            if (result && result.success) {
                const status = result.status;
                
                // UI güncelle
                if (geminiStatusText) {
                    geminiStatusText.textContent = status.ai_enabled ? '✅ Aktif' : '❌ Devre Dışı';
                    geminiStatusText.className = status.ai_enabled ? 'status-running' : 'status-stopped';
                }
                
                if (geminiProvider) {
                    geminiProvider.textContent = status.provider || '-';
                }
                
                if (geminiCacheSize) {
                    geminiCacheSize.textContent = status.cache_size || 0;
                }
                
                // Mesaj göster
                showSuccess(status.message);
                
                // Eğer devre dışıysa yardım göster
                if (!status.ai_enabled) {
                    console.log('🤖 Gemini AI Kurulum Adımları:');
                    if (status.setup_steps) {
                        status.setup_steps.forEach(step => console.log(step));
                    }
                    if (status.help) {
                        console.log('ℹ️ API Key:', status.help);
                    }
                }
            }
            
        } catch (error) {
            showError('Status kontrol hatası: ' + error.message);
        }
    });
}

// Cache Temizle
if (geminiClearCacheButton) {
    geminiClearCacheButton.addEventListener('click', async () => {
        if (!confirm('Gemini AI cache temizlensin mi?')) {
            return;
        }
        
        try {
            const result = await fetchApi('/api/gemini-clear-cache', {
                method: 'POST'
            });
            
            if (result && result.success) {
                showSuccess(result.message);
                if (geminiCacheSize) {
                    geminiCacheSize.textContent = '0';
                }
            }
            
        } catch (error) {
            showError('Cache temizleme hatası: ' + error.message);
        }
    });
}

// Enter tuşu desteği - Gemini test
if (geminiTestSymbol) {
    geminiTestSymbol.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && geminiTestButton && !geminiTestButton.disabled) {
            geminiTestButton.click();
        }
    });
}

// Sayfa yüklendiğinde Gemini status otomatik kontrol
async function checkGeminiHealth() {
    try {
        const response = await fetch('/api/gemini-health');
        if (response.ok) {
            const health = await response.json();
            console.log('🤖 Gemini AI Health:', health.status);
            
            if (health.status === 'healthy' && geminiStatusText) {
                geminiStatusText.textContent = '✅ Aktif';
                geminiStatusText.className = 'status-running';
            } else if (health.status === 'disabled' && geminiStatusText) {
                geminiStatusText.textContent = '❌ Devre Dışı';
                geminiStatusText.className = 'status-stopped';
            }
            
            if (geminiProvider && health.provider) {
                geminiProvider.textContent = health.provider;
            }
            
            if (geminiCacheSize && health.cache_size !== undefined) {
                geminiCacheSize.textContent = health.cache_size;
            }
        }
    } catch (e) {
        console.warn('Gemini health check başarısız:', e);
    }
}

// Auth state değiştiğinde Gemini health kontrol et
auth.onAuthStateChanged(user => {
    if (user) {
        // ... mevcut kodlarınız ...
        
        // Gemini health check
        setTimeout(() => {
            checkGeminiHealth();
        }, 2000); // 2 saniye sonra kontrol et
    }
});

console.log('✅ Gemini AI UI fonksiyonları yüklendi!');
    // Debug için Enter tuşu desteği
    if (debugSymbolInput) {
        debugSymbolInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && debugEmaButton && !debugEmaButton.disabled) {
                debugEmaButton.click();
            }
        });
    }
});
