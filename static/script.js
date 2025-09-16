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
    
    // HTML elementleri - Gelişmiş Özellikler
    const timeframeSelect = document.getElementById('timeframe-select');
    const enhancedStartButton = document.getElementById('enhanced-start-button');
    const multiSymbolsInput = document.getElementById('multi-symbols-input');
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
    const currentTimeframeSpan = document.getElementById('current-timeframe');
    const riskRewardRatioSpan = document.getElementById('risk-reward-ratio');
    const websocketCountSpan = document.getElementById('websocket-count');
    
    // HTML elementleri - Zaman Dilimi Bilgisi
    const timeframeInfo = document.getElementById('timeframe-info');
    const tfStopLoss = document.getElementById('tf-stop-loss');
    const tfTakeProfit = document.getElementById('tf-take-profit');
    const tfRiskReward = document.getElementById('tf-risk-reward');
    const tfCooldown = document.getElementById('tf-cooldown');
    
    // HTML elementleri - Risk Yönetimi
    const dailyPositionsSpan = document.getElementById('daily-positions');
    const maxDailyPositionsSpan = document.getElementById('max-daily-positions');
    const dailyPositionsProgress = document.getElementById('daily-positions-progress');
    const filteredSignalsCount = document.getElementById('filtered-signals-count');
    const riskProtectionStatus = document.getElementById('risk-protection-status');
    
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
    const statsDailyPnl = document.getElementById('stats-daily-pnl');
    const statsOrderSize = document.getElementById('stats-order-size');
    const statsTotal = document.getElementById('stats-total-trades');
    const statsWinning = document.getElementById('stats-winning-trades');
    const statsLosing = document.getElementById('stats-losing-trades');
    const statsTotalProfit = document.getElementById('stats-total-profit');
    const statsTotalLoss = document.getElementById('stats-total-loss');
    const statsNetPnl = document.getElementById('stats-net-pnl');
    
    // HTML elementleri - Gelişmiş Paneller
    const filtersCard = document.getElementById('filters-card');
    const comparisonCard = document.getElementById('comparison-card');
    const comparisonTableBody = document.getElementById('comparison-table-body');
    
    let statusInterval;
    let isMonitorRunning = false;
    let timeframeInfo_data = {};

    // --- TOAST NOTIFICATION SİSTEMİ ---
    function showNotification(message, type = 'info') {
        const container = document.getElementById('notification-container') || createNotificationContainer();
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        
        const icon = {
            'success': '✅',
            'error': '❌',
            'warning': '⚠️',
            'info': 'ℹ️'
        }[type] || 'ℹ️';
        
        notification.innerHTML = `
            <span class="notification-icon">${icon}</span>
            <span class="notification-message">${message}</span>
            <button class="notification-close" onclick="this.parentElement.remove()">×</button>
        `;
        
        container.appendChild(notification);
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 5000);
        
        // Animate in
        setTimeout(() => {
            notification.classList.add('notification-show');
        }, 100);
    }
    
    function createNotificationContainer() {
        const container = document.createElement('div');
        container.id = 'notification-container';
        container.className = 'notification-container';
        document.body.appendChild(container);
        return container;
    }

    // --- KİMLİK DOĞRULAMA ---
    loginButton.addEventListener('click', () => {
        loginError.textContent = "";
        auth.signInWithEmailAndPassword(emailInput.value, passwordInput.value)
            .catch(error => { 
                loginError.textContent = "Hatalı e-posta veya şifre."; 
                showNotification('Giriş başarısız', 'error');
            });
    });

    logoutButton.addEventListener('click', () => { 
        auth.signOut();
        showNotification('Çıkış yapıldı', 'info');
    });

    auth.onAuthStateChanged(user => {
        if (user) {
            loginContainer.style.display = 'none';
            appContainer.style.display = 'flex';
            showNotification(`Hoş geldiniz, ${user.email}`, 'success');
            getEnhancedStatus();
            loadTimeframeInfo();
            statusInterval = setInterval(getEnhancedStatus, 8000);
            listenForTradeUpdates();
            updateMonitorButton();
            loadFilterStatistics();
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
                showNotification(errorData.detail, 'error');
                return null;
            }
            return response.json();
        } catch (error) { 
            console.error("API isteği hatası:", error); 
            showNotification("Bağlantı hatası: " + error.message, 'error');
            return null; 
        }
    }

    // --- ZAMAN DİLİMİ YÖNETİMİ ---
    async function loadTimeframeInfo() {
        try {
            const data = await fetchApi('/api/timeframe-info');
            if (data) {
                timeframeInfo_data = data;
                updateTimeframeDisplay(data.current_timeframe);
                loadTimeframeComparison(data.timeframe_comparison);
            }
        } catch (error) {
            console.error("Zaman dilimi bilgisi yüklenemedi:", error);
        }
    }
    
    function updateTimeframeDisplay(selectedTimeframe = null) {
        const timeframe = selectedTimeframe || timeframeSelect.value;
        
        if (timeframeInfo_data.timeframe_comparison && timeframeInfo_data.timeframe_comparison[timeframe]) {
            const settings = timeframeInfo_data.timeframe_comparison[timeframe];
            
            tfStopLoss.textContent = `${settings.stop_loss.toFixed(2)}%`;
            tfTakeProfit.textContent = `${settings.take_profit.toFixed(2)}%`;
            tfRiskReward.textContent = `1:${settings.risk_reward.toFixed(1)}`;
            tfCooldown.textContent = `${settings.cooldown_minutes} dakika`;
            
            // Progress bar renkleri
            const rr = settings.risk_reward;
            if (rr >= 2.0) {
                timeframeInfo.className = 'info-panel excellent';
            } else if (rr >= 1.5) {
                timeframeInfo.className = 'info-panel good';
            } else {
                timeframeInfo.className = 'info-panel warning';
            }
        }
    }
    
    function loadTimeframeComparison(comparisonData) {
        comparisonTableBody.innerHTML = '';
        
        const timeframes = ['1m', '3m', '5m', '15m', '30m', '1h'];
        const recommendations = {
            '1m': 'Scalping (Riskli)',
            '3m': 'Kısa Vade',
            '5m': 'Hızlı İşlem',
            '15m': 'Optimal',
            '30m': 'Orta Vade',
            '1h': 'Swing Trading'
        };
        
        timeframes.forEach(tf => {
            if (comparisonData[tf]) {
                const data = comparisonData[tf];
                const row = document.createElement('tr');
                row.className = tf === timeframeInfo_data.current_timeframe ? 'current-timeframe' : '';
                
                row.innerHTML = `
                    <td><strong>${tf.toUpperCase()}</strong></td>
                    <td>${data.stop_loss.toFixed(2)}%</td>
                    <td>${data.take_profit.toFixed(2)}%</td>
                    <td>1:${data.risk_reward.toFixed(1)}</td>
                    <td>${data.cooldown_minutes}dk</td>
                    <td>${recommendations[tf]}</td>
                `;
                
                comparisonTableBody.appendChild(row);
            }
        });
        
        comparisonCard.style.display = 'block';
    }

    timeframeSelect.addEventListener('change', () => {
        updateTimeframeDisplay();
    });
    
    // --- GELİŞMİŞ UI GÜNCELLEMESI ---
    const updateEnhancedUI = (data) => {
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
        
        // Zaman dilimi bilgisi
        if (data.current_timeframe) {
            currentTimeframeSpan.textContent = data.current_timeframe.toUpperCase();
            currentTimeframeSpan.className = 'status-timeframe';
            timeframeSelect.value = data.current_timeframe;
        }
        
        // Risk/Reward oranı
        if (data.risk_management && data.risk_management.risk_reward_ratio) {
            const rr = data.risk_management.risk_reward_ratio;
            riskRewardRatioSpan.textContent = `1:${rr.toFixed(1)}`;
            riskRewardRatioSpan.className = rr >= 2.0 ? 'ratio-excellent' : rr >= 1.5 ? 'ratio-good' : 'ratio-warning';
        }
        
        // WebSocket bağlantıları
        websocketCountSpan.textContent = data.websocket_connections || 0;
        
        // Risk yönetimi bilgileri
        updateRiskManagementUI(data);
        
        // Bot kontrolleri
        if (data.is_running) {
            enhancedStartButton.disabled = true;
            legacyStartButton.disabled = true;
            stopButton.disabled = false;
            multiSymbolsInput.disabled = true;
            legacySymbolInput.disabled = true;
            timeframeSelect.disabled = true;
            
            // Coin yönetimi göster
            coinManagement.style.display = 'block';
            coinButtons.style.display = 'flex';
            filtersCard.style.display = 'block';
        } else {
            enhancedStartButton.disabled = false;
            legacyStartButton.disabled = false;
            stopButton.disabled = true;
            multiSymbolsInput.disabled = false;
            legacySymbolInput.disabled = false;
            timeframeSelect.disabled = false;
            
            // Coin yönetimi gizle
            coinManagement.style.display = 'none';
            coinButtons.style.display = 'none';
            filtersCard.style.display = 'none';
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

        if (data.is_running && data.daily_pnl !== undefined) {
            formatPnl(statsDailyPnl, data.daily_pnl);
        } else {
            statsDailyPnl.textContent = 'N/A';
            statsDailyPnl.className = 'stats-value';
        }

        if (data.is_running && data.order_size !== undefined) {
            statsOrderSize.textContent = `${data.order_size.toFixed(2)} USDT`;
            statsOrderSize.className = 'stats-value';
        } else {
            statsOrderSize.textContent = 'N/A';
            statsOrderSize.className = 'stats-value';
        }
    };
    
    function updateRiskManagementUI(data) {
        // Günlük pozisyon bilgisi
        const dailyPositions = data.daily_positions || 0;
        const maxDailyPositions = data.risk_management?.max_daily_positions || 8;
        
        dailyPositionsSpan.textContent = dailyPositions;
        maxDailyPositionsSpan.textContent = maxDailyPositions;
        
        // Progress bar güncelle
        const progressPercent = (dailyPositions / maxDailyPositions) * 100;
        dailyPositionsProgress.style.width = `${Math.min(progressPercent, 100)}%`;
        dailyPositionsProgress.className = 'progress-fill';
        
        if (progressPercent >= 90) {
            dailyPositionsProgress.classList.add('progress-danger');
        } else if (progressPercent >= 70) {
            dailyPositionsProgress.classList.add('progress-warning');
        } else {
            dailyPositionsProgress.classList.add('progress-success');
        }
        
        // Filtrelenen sinyaller
        filteredSignalsCount.textContent = data.filtered_signals_count || 0;
        
        // Risk koruması durumu
        const riskActive = data.risk_management_active !== false;
        riskProtectionStatus.textContent = riskActive ? 'Aktif' : 'Pasif';
        riskProtectionStatus.className = riskActive ? 'status-active' : 'status-inactive';
    }

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

    const getEnhancedStatus = async () => updateEnhancedUI(await fetchApi('/api/enhanced-status'));

    // --- GELİŞMİŞ MULTI-COIN EVENT LISTENERS ---
    enhancedStartButton.addEventListener('click', async () => {
        const symbolsInput = multiSymbolsInput.value.trim();
        const selectedTimeframe = timeframeSelect.value;
        
        if (!symbolsInput) {
            showNotification('Lütfen en az bir coin sembolü girin.', 'error');
            return;
        }
        
        // Coinleri parse et
        const symbols = symbolsInput.split(',')
            .map(s => s.trim().toUpperCase())
            .filter(s => s.length > 0);
        
        if (symbols.length === 0) {
            showNotification('Geçerli coin sembolleri girin.', 'error');
            return;
        }
        
        if (symbols.length > 20) {
            showNotification('Maksimum 20 coin desteklenir.', 'error');
            return;
        }
        
        console.log('Gelişmiş multi-coin bot başlatılıyor:', symbols, selectedTimeframe);
        showNotification(`${symbols.length} coin için bot başlatılıyor... (${selectedTimeframe.toUpperCase()})`, 'info');
        
        const result = await fetchApi('/api/enhanced-multi-start', { 
            method: 'POST', 
            body: JSON.stringify({ symbols, timeframe: selectedTimeframe }) 
        });
        
        if (result) {
            updateEnhancedUI(result);
            showNotification(`✅ ${symbols.length} coin için gelişmiş bot başlatıldı!`, 'success');
        }
    });

    stopButton.addEventListener('click', async () => {
        const result = await fetchApi('/api/stop', { method: 'POST' });
        if (result) {
            updateEnhancedUI(result);
            showNotification('Bot durduruldu', 'info');
        }
    });

    addSymbolButton.addEventListener('click', async () => {
        const symbol = singleSymbolInput.value.trim().toUpperCase();
        if (!symbol) {
            showNotification('Lütfen bir coin sembolü girin.', 'error');
            return;
        }
        
        const result = await fetchApi('/api/add-symbol', { 
            method: 'POST', 
            body: JSON.stringify({ symbol }) 
        });
        
        if (result && result.success) {
            singleSymbolInput.value = '';
            showNotification(result.message, 'success');
            getEnhancedStatus(); // Refresh status
        }
    });

    removeSymbolButton.addEventListener('click', async () => {
        const symbol = singleSymbolInput.value.trim().toUpperCase();
        if (!symbol) {
            showNotification('Lütfen çıkarılacak coin sembolünü girin.', 'error');
            return;
        }
        
        const result = await fetchApi('/api/remove-symbol', { 
            method: 'POST', 
            body: JSON.stringify({ symbol }) 
        });
        
        if (result && result.success) {
            singleSymbolInput.value = '';
            showNotification(result.message, 'success');
            getEnhancedStatus(); // Refresh status
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
            showNotification(result.message, 'success');
        }
    });

    monitorToggleButton.addEventListener('click', async () => {
        if (isMonitorRunning) {
            // Durdur
            const result = await fetchApi('/api/stop-position-monitor', { method: 'POST' });
            if (result && result.success) {
                showNotification(result.message, 'info');
                updateMonitorButton();
            }
        } else {
            // Başlat
            const result = await fetchApi('/api/start-position-monitor', { method: 'POST' });
            if (result && result.success) {
                showNotification(result.message, 'success');
                updateMonitorButton();
            }
        }
    });

    scanSymbolButton.addEventListener('click', async () => {
        const symbol = scanSymbolInput.value.trim().toUpperCase();
        if (!symbol) {
            showNotification('Lütfen bir coin sembolü girin.', 'error');
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
            showNotification(result.message, 'success');
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
        const selectedTimeframe = timeframeSelect.value;
        
        if (!symbol) {
            showNotification('Lütfen bir coin sembolü girin.', 'error');
            return;
        }
        
        console.log('Legacy tek coin bot başlatılıyor:', symbol, selectedTimeframe);
        showNotification(`Tek coin modu: ${symbol} başlatılıyor... (${selectedTimeframe.toUpperCase()})`, 'info');
        
        const result = await fetchApi('/api/start', { 
            method: 'POST', 
            body: JSON.stringify({ symbol, timeframe: selectedTimeframe }) 
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
                websocket_connections: 1,
                current_timeframe: result.current_timeframe || selectedTimeframe
            };
            updateEnhancedUI(multiResult);
            showNotification(`✅ Tek coin modu: ${symbol} başlatıldı!`, 'success');
        }
    });

    // --- FİLTRE İSTATİSTİKLERİ ---
    async function loadFilterStatistics() {
        try {
            const data = await fetchApi('/api/filter-statistics');
            if (data) {
                // Filtre durumlarını güncelle
                updateFilterDisplay(data.active_filters);
            }
        } catch (error) {
            console.error("Filtre istatistikleri yüklenemedi:", error);
        }
    }
    
    function updateFilterDisplay(activeFilters) {
        const filterItems = document.querySelectorAll('.filter-item .filter-status');
        const filterNames = {
            'trend_filter': 0,
            'momentum_filter': 1,
            'trend_strength_filter': 2,
            'rsi_filter': 3,
            'volume_filter': 4,
            'cooldown_filter': 5
        };
        
        Object.keys(activeFilters).forEach(filterName => {
            const index = filterNames[filterName];
            if (index !== undefined && filterItems[index]) {
                const isActive = activeFilters[filterName];
                filterItems[index].textContent = isActive ? '✅ Aktif' : '❌ Pasif';
                filterItems[index].className = isActive ? 'filter-status active' : 'filter-status inactive';
            }
        });
    }

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
        if (e.key === 'Enter') enhancedStartButton.click();
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
    
    // --- OTOMATIK YENİLEME ---
    setInterval(() => {
        if (auth.currentUser && document.visibilityState === 'visible') {
            loadFilterStatistics();
        }
    }, 30000); // 30 saniyede bir filtre istatistiklerini güncelle
});
