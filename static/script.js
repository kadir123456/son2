document.addEventListener('DOMContentLoaded', () => {
    // ÇOK ÖNEMLİ: BU BİLGİLERİ KENDİ FIREBASE PROJENİZDEN ALIP DOLDURUN
    const firebaseConfig = {
        apiKey: "AIzaSyDkJch-8B46dpZSB-pMSR4q1uvzadCVekE",
        authDomain: "aviator-90c8b.firebaseapp.com",
        databaseURL: "https://aviator-90c8b-default-rtdb.firebaseio.com",
        projectId: "aviator-90c8b",
        storageBucket: "aviator-90c8b.appspot.com",
        messagingSenderId: "823763988442",
        appId: "1:823763988442:web:16a797275675a219c3dae3"
    };
    // -----------------------------------------------------------------

    firebase.initializeApp(firebaseConfig);
    const auth = firebase.auth();
    const database = firebase.database();

    // HTML elementleri - Mevcut
    const loginContainer = document.getElementById('login-container');
    const appContainer = document.getElementById('app-container');
    const loginButton = document.getElementById('login-button');
    const logoutButton = document.getElementById('logout-button');
    const emailInput = document.getElementById('email');
    const passwordInput = document.getElementById('password');
    const loginError = document.getElementById('login-error');
    
    // HTML elementleri - Multi-Coin Yeni
    const multiSymbolsInput = document.getElementById('multi-symbols-input');
    const multiStartButton = document.getElementById('multi-start-button');
    const stopButton = document.getElementById('stop-button');
    const singleSymbolInput = document.getElementById('single-symbol-input');
    const addSymbolButton = document.getElementById('add-symbol-button');
    const removeSymbolButton = document.getElementById('remove-symbol-button');
    const coinManagement = document.getElementById('coin-management');
    const coinButtons = document.getElementById('coin-buttons');
    const symbolsCard = document.getElementById('symbols-card');
    const symbolsList = document.getElementById('symbols-list');
    
    // HTML elementleri - Durum
    const statusMessageSpan = document.getElementById('status-message');
    const monitoredSymbolsSpan = document.getElementById('monitored-symbols');
    const activePositionSpan = document.getElementById('active-position');
    const websocketCountSpan = document.getElementById('websocket-count');
    
    // HTML elementleri - Pozisyon Yönetimi
    const scanAllButton = document.getElementById('scan-all-button');
    const monitorToggleButton = document.getElementById('monitor-toggle-button');
    const scanSymbolInput = document.getElementById('scan-symbol-input');
    const scanSymbolButton = document.getElementById('scan-symbol-button');
    
    // HTML elementleri - Geriye Uyumluluk
    const legacySymbolInput = document.getElementById('legacy-symbol-input');
    const legacyStartButton = document.getElementById('legacy-start-button');
    
    // HTML elementleri - İstatistikler
    const statsMainBalance = document.getElementById('stats-main-balance');
    const statsPositionPnl = document.getElementById('stats-position-pnl');
    const statsOrderSize = document.getElementById('stats-order-size');
    const statsTotal = document.getElementById('stats-total-trades');
    const statsWinning = document.getElementById('stats-winning-trades');
    const statsLosing = document.getElementById('stats-losing-trades');
    const statsTotalProfit = document.getElementById('stats-total-profit');
    const statsTotalLoss = document.getElementById('stats-total-loss');
    const statsNetPnl = document.getElementById('stats-net-pnl');
    
    let statusInterval;
    let isMonitorRunning = false;

    // --- KİMLİK DOĞRULAMA ---
    loginButton.addEventListener('click', () => {
        loginError.textContent = "";
        auth.signInWithEmailAndPassword(emailInput.value, passwordInput.value)
            .catch(error => { loginError.textContent = "Hatalı e-posta veya şifre."; });
    });

    logoutButton.addEventListener('click', () => { auth.signOut(); });

    auth.onAuthStateChanged(user => {
        if (user) {
            loginContainer.style.display = 'none';
            appContainer.style.display = 'flex';
            getMultiStatus();
            statusInterval = setInterval(getMultiStatus, 8000);
            listenForTradeUpdates();
            updateMonitorButton();
        } else {
            loginContainer.style.display = 'flex';
            appContainer.style.display = 'none';
            if (statusInterval) clearInterval(statusInterval);
        }
    });

    // --- API İSTEKLERİ ---
    async function fetchApi(endpoint, options = {}) {
        const user = auth.currentUser;
        if (!user) { return null; }
        const idToken = await user.getIdToken(true);
        const headers = { ...options.headers, 'Authorization': `Bearer ${idToken}` };
        if (options.body) headers['Content-Type'] = 'application/json';
        try {
            const response = await fetch(endpoint, { ...options, headers });
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: response.statusText }));
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
        // Basit error notification
        console.error("HATA:", message);
        // Gelecekte toast notification eklenebilir
    }

    function showSuccess(message) {
        console.log("BAŞARILI:", message);
        // Gelecekte toast notification eklenebilir
    }
    
    // --- MULTI-COIN UI GÜNCELLEMESI ---
    const updateMultiUI = (data) => {
        if (!data) return;
        
        // Durum mesajı
        statusMessageSpan.textContent = data.status_message || 'Bilinmiyor';
        statusMessageSpan.className = data.is_running ? 'status-running' : 'status-stopped';
        
        // İzlenen coinler
        if (data.symbols && data.symbols.length > 0) {
            monitoredSymbolsSpan.textContent = `${data.symbols.length} coin (${data.symbols.join(', ')})`;
            monitoredSymbolsSpan.className = 'status-monitoring';
            
            // Symbols card'ı göster ve güncelle
            symbolsCard.style.display = 'block';
            updateSymbolsList(data.symbols, data.last_signals, data.active_symbol);
        } else {
            monitoredSymbolsSpan.textContent = 'Hayır';
            monitoredSymbolsSpan.className = '';
            symbolsCard.style.display = 'none';
        }
        
        // Aktif pozisyon
        if (data.active_symbol && data.position_side) {
            activePositionSpan.textContent = `${data.position_side} @ ${data.active_symbol}`;
            activePositionSpan.className = 'status-in-position';
        } else {
            activePositionSpan.textContent = 'Hayır';
            activePositionSpan.className = '';
        }
        
        // WebSocket bağlantıları
        websocketCountSpan.textContent = data.websocket_connections || 0;
        
        // Bot kontrolleri
        if (data.is_running) {
            multiStartButton.disabled = true;
            legacyStartButton.disabled = true;
            stopButton.disabled = false;
            multiSymbolsInput.disabled = true;
            legacySymbolInput.disabled = true;
            
            // Coin yönetimi göster
            coinManagement.style.display = 'block';
            coinButtons.style.display = 'flex';
        } else {
            multiStartButton.disabled = false;
            legacyStartButton.disabled = false;
            stopButton.disabled = true;
            multiSymbolsInput.disabled = false;
            legacySymbolInput.disabled = false;
            
            // Coin yönetimi gizle
            coinManagement.style.display = 'none';
            coinButtons.style.display = 'none';
        }
        
        // Finansal veriler
        if (data.is_running && data.account_balance !== undefined) {
            formatPnl(statsMainBalance, data.account_balance, true);
        } else {
            statsMainBalance.textContent = 'N/A';
            statsMainBalance.className = 'stats-value';
        }

        if (data.is_running && data.position_pnl !== undefined) {
            formatPnl(statsPositionPnl, data.position_pnl);
        } else {
            statsPositionPnl.textContent = 'N/A';
            statsPositionPnl.className = 'stats-value';
        }

        if (data.is_running && data.order_size !== undefined) {
            statsOrderSize.textContent = `${data.order_size.toFixed(2)} USDT`;
            statsOrderSize.className = 'stats-value';
        } else {
            statsOrderSize.textContent = 'N/A';
            statsOrderSize.className = 'stats-value';
        }
    };

    function updateSymbolsList(symbols, lastSignals, activeSymbol) {
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

    const getMultiStatus = async () => updateMultiUI(await fetchApi('/api/multi-status'));

    // --- MULTI-COIN EVENT LISTENERS ---
    multiStartButton.addEventListener('click', async () => {
        const symbolsInput = multiSymbolsInput.value.trim();
        if (!symbolsInput) {
            showError('Lütfen en az bir coin sembolü girin.');
            return;
        }
        
        // Coinleri parse et
        const symbols = symbolsInput.split(',')
            .map(s => s.trim().toUpperCase())
            .filter(s => s.length > 0);
        
        if (symbols.length === 0) {
            showError('Geçerli coin sembolleri girin.');
            return;
        }
        
        if (symbols.length > 20) {
            showError('Maksimum 20 coin desteklenir.');
            return;
        }
        
        console.log('Multi-coin bot başlatılıyor:', symbols);
        const result = await fetchApi('/api/multi-start', { 
            method: 'POST', 
            body: JSON.stringify({ symbols }) 
        });
        
        if (result) {
            updateMultiUI(result);
            showSuccess(`${symbols.length} coin için bot başlatıldı`);
        }
    });

    stopButton.addEventListener('click', async () => {
        const result = await fetchApi('/api/stop', { method: 'POST' });
        if (result) {
            updateMultiUI(result);
            showSuccess('Bot durduruldu');
        }
    });

    addSymbolButton.addEventListener('click', async () => {
        const symbol = singleSymbolInput.value.trim().toUpperCase();
        if (!symbol) {
            showError('Lütfen bir coin sembolü girin.');
            return;
        }
        
        const result = await fetchApi('/api/add-symbol', { 
            method: 'POST', 
            body: JSON.stringify({ symbol }) 
        });
        
        if (result && result.success) {
            singleSymbolInput.value = '';
            showSuccess(result.message);
            getMultiStatus(); // Refresh status
        }
    });

    removeSymbolButton.addEventListener('click', async () => {
        const symbol = singleSymbolInput.value.trim().toUpperCase();
        if (!symbol) {
            showError('Lütfen çıkarılacak coin sembolünü girin.');
            return;
        }
        
        const result = await fetchApi('/api/remove-symbol', { 
            method: 'POST', 
            body: JSON.stringify({ symbol }) 
        });
        
        if (result && result.success) {
            singleSymbolInput.value = '';
            showSuccess(result.message);
            getMultiStatus(); // Refresh status
        }
    });

    // --- POZİSYON YÖNETİMİ EVENT LISTENERS ---
    scanAllButton.addEventListener('click', async () => {
        scanAllButton.disabled = true;
        scanAllButton.textContent = 'Taranıyor...';
        
        const result = await fetchApi('/api/scan-all-positions', { method: 'POST' });
        
        scanAllButton.disabled = false;
        scanAllButton.textContent = 'Tüm Pozisyonları Tara';
        
        if (result && result.success) {
            showSuccess(result.message);
        }
    });

    monitorToggleButton.addEventListener('click', async () => {
        if (isMonitorRunning) {
            // Durdur
            const result = await fetchApi('/api/stop-position-monitor', { method: 'POST' });
            if (result && result.success) {
                showSuccess(result.message);
                updateMonitorButton();
            }
        } else {
            // Başlat
            const result = await fetchApi('/api/start-position-monitor', { method: 'POST' });
            if (result && result.success) {
                showSuccess(result.message);
                updateMonitorButton();
            }
        }
    });

    scanSymbolButton.addEventListener('click', async () => {
        const symbol = scanSymbolInput.value.trim().toUpperCase();
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
        scanSymbolButton.textContent = 'Coin Kontrol Et';
        
        if (result && result.success) {
            scanSymbolInput.value = '';
            showSuccess(result.message);
        }
    });

    async function updateMonitorButton() {
        const status = await fetchApi('/api/position-monitor-status');
        if (status && status.monitor_status) {
            isMonitorRunning = status.monitor_status.is_running;
            monitorToggleButton.textContent = isMonitorRunning ? 'Monitor Durdur' : 'Monitor Başlat';
            monitorToggleButton.className = isMonitorRunning ? 'btn btn-warning' : 'btn btn-secondary';
        }
    }

    // --- GERİYE UYUMLULUK EVENT LISTENERS ---
    legacyStartButton.addEventListener('click', async () => {
        const symbol = legacySymbolInput.value.trim().toUpperCase();
        if (!symbol) {
            showError('Lütfen bir coin sembolü girin.');
            return;
        }
        
        console.log('Legacy tek coin bot başlatılıyor:', symbol);
        const result = await fetchApi('/api/start', { 
            method: 'POST', 
            body: JSON.stringify({ symbol }) 
        });
        
        if (result) {
            // Legacy response'u multi-UI'ye uyarla
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
            updateMultiUI(multiResult);
            showSuccess(`Tek coin modu: ${symbol} başlatıldı`);
        }
    });

    // --- İSTATİSTİK HESAPLAMA ---
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
        let totalProfit = 0, totalLoss = 0;

        trades.forEach(trade => {
            const pnl = parseFloat(trade.pnl) || 0;
            if (pnl > 0) {
                winningTrades++;
                totalProfit += pnl;
            } else {
                losingTrades++;
                totalLoss += pnl;
            }
        });
        
        const netPnl = totalProfit + totalLoss;

        statsTotal.textContent = totalTrades;
        const winRate = totalTrades > 0 ? ((winningTrades / totalTrades) * 100).toFixed(1) : 0;
        const loseRate = totalTrades > 0 ? ((losingTrades / totalTrades) * 100).toFixed(1) : 0;
        statsWinning.textContent = `${winningTrades} (%${winRate})`;
        statsLosing.textContent = `${losingTrades} (%${loseRate})`;

        formatPnl(statsTotalProfit, totalProfit);
        formatPnl(statsTotalLoss, totalLoss);
        formatPnl(statsNetPnl, netPnl);
    }

    function formatPnl(element, value, isBalance = false) {
        element.textContent = `${value.toFixed(2)} USDT`;
        if (isBalance) {
            element.className = 'stats-value';
        } else {
            element.className = value > 0 ? 'stats-value pnl-positive' : (value < 0 ? 'stats-value pnl-negative' : 'stats-value');
        }
    }

    // --- KLAVYE KISAYOLLARI ---
    multiSymbolsInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') multiStartButton.click();
    });

    singleSymbolInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') addSymbolButton.click();
    });

    scanSymbolInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') scanSymbolButton.click();
    });

    legacySymbolInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') legacyStartButton.click();
    });
});
