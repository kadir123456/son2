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
    
    // Mobile optimizations
    let touchStartY = 0;
    let touchStartTime = 0;
    let isScrolling = false;

    // === MOBILE DETECTION & OPTIMIZATION ===
    function isMobileDevice() {
        return (
            /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) ||
            ('ontouchstart' in window) ||
            (navigator.maxTouchPoints > 0) ||
            (window.matchMedia('(max-width: 768px)').matches)
        );
    }

    // Initialize mobile optimizations
    if (isMobileDevice()) {
        console.log('📱 Mobile device detected - applying optimizations');
        document.body.classList.add('mobile-device');
        
        // Optimize touch interactions
        document.addEventListener('touchstart', function() {}, { passive: true });
        document.addEventListener('touchmove', function() {}, { passive: true });
        
        // Prevent zoom on input focus (iOS Safari fix)
        const inputs = document.querySelectorAll('input, select, textarea');
        inputs.forEach(input => {
            input.addEventListener('focus', () => {
                if (input.getAttribute('readonly') === null) {
                    input.style.fontSize = '16px';
                }
            });
        });
        
        // Prevent pull-to-refresh on iOS
        let preventRefresh = false;
        document.body.addEventListener('touchstart', (e) => {
            if (e.touches.length === 1 && window.pageYOffset === 0) {
                preventRefresh = true;
                touchStartY = e.touches[0].clientY;
                touchStartTime = Date.now();
            }
        }, { passive: false });
        
        document.body.addEventListener('touchmove', (e) => {
            if (preventRefresh && e.touches.length === 1) {
                const touchY = e.touches[0].clientY;
                const touchTime = Date.now();
                
                // If scrolling down from top, prevent default
                if (touchY > touchStartY && window.pageYOffset === 0 && touchTime - touchStartTime < 500) {
                    e.preventDefault();
                }
            }
        }, { passive: false });
        
        document.body.addEventListener('touchend', () => {
            preventRefresh = false;
        }, { passive: true });
    }

    // === TOAST NOTIFICATION SİSTEMİ ===
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
        
        // Trigger animation
        setTimeout(() => {
            notification.classList.add('notification-show');
        }, 100);
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            if (notification.parentElement) {
                notification.classList.remove('notification-show');
                setTimeout(() => {
                    if (notification.parentElement) {
                        notification.remove();
                    }
                }, 300);
            }
        }, 5000);
        
        // Add haptic feedback on mobile
        if (isMobileDevice() && 'vibrate' in navigator) {
            const vibrationPatterns = {
                'success': [50],
                'error': [100, 50, 100],
                'warning': [100],
                'info': [50]
            };
            navigator.vibrate(vibrationPatterns[type] || [50]);
        }
    }
    
    function createNotificationContainer() {
        const container = document.createElement('div');
        container.id = 'notification-container';
        container.className = 'notification-container';
        document.body.appendChild(container);
        return container;
    }

    // === KİMLİK DOĞRULAMA ===
    loginButton.addEventListener('click', (e) => {
        e.preventDefault();
        loginError.textContent = "";
        
        // Mobile loading state
        loginButton.disabled = true;
        loginButton.textContent = "Giriş yapılıyor...";
        
        auth.signInWithEmailAndPassword(emailInput.value, passwordInput.value)
            .then(() => {
                showNotification('Giriş başarılı! 🎉', 'success');
            })
            .catch(error => { 
                loginError.textContent = "Hatalı e-posta veya şifre.";
                showNotification('Giriş başarısız: ' + error.message, 'error');
            })
            .finally(() => {
                loginButton.disabled = false;
                loginButton.textContent = "Giriş Yap";
            });
    });

    // Enter key support for mobile keyboards
    emailInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            passwordInput.focus();
        }
    });

    passwordInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            loginButton.click();
        }
    });

    logoutButton.addEventListener('click', (e) => {
        e.preventDefault();
        auth.signOut();
        showNotification('Güvenli çıkış yapıldı 👋', 'info');
    });

    auth.onAuthStateChanged(user => {
        if (user) {
            loginContainer.style.display = 'none';
            appContainer.style.display = 'flex';
            showNotification(`Hoş geldiniz ${user.email} 👋`, 'success');
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

    // === API İSTEKLERİ ===
    async function fetchApi(endpoint, options = {}) {
        const user = auth.currentUser;
        if (!user) { 
            showNotification('Oturum süresi doldu, yeniden giriş yapın', 'warning');
            return null; 
        }
        
        // Show loading state for mobile
        if (isMobileDevice() && options.showLoading !== false) {
            document.body.style.cursor = 'wait';
        }
        
        try {
            const idToken = await user.getIdToken(true);
            const headers = { 
                ...options.headers, 
                'Authorization': `Bearer ${idToken}`,
                'Content-Type': 'application/json'
            };
            
            const response = await fetch(endpoint, { 
                ...options, 
                headers,
                // Add timeout for mobile connections
                signal: AbortSignal.timeout(isMobileDevice() ? 15000 : 10000)
            });
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: response.statusText }));
                console.error("API Hatası:", errorData.detail);
                
                // Mobile-friendly error messages
                if (response.status === 429) {
                    showNotification('Çok fazla istek, lütfen bekleyin ⏳', 'warning');
                } else if (response.status >= 500) {
                    showNotification('Sunucu hatası, tekrar deneyin 🔄', 'error');
                } else {
                    showNotification(errorData.detail || 'Bir hata oluştu', 'error');
                }
                return null;
            }
            
            return response.json();
        } catch (error) { 
            console.error("API isteği hatası:", error);
            
            if (error.name === 'AbortError') {
                showNotification("İstek zaman aşımına uğradı, tekrar deneyin ⏱️", 'warning');
            } else if (!navigator.onLine) {
                showNotification("İnternet bağlantınızı kontrol edin 📶", 'error');
            } else {
                showNotification("Bağlantı hatası: " + (error.message || 'Bilinmeyen hata'), 'error');
            }
            return null; 
        } finally {
            if (isMobileDevice()) {
                document.body.style.cursor = 'default';
            }
        }
    }

    // === ZAMAN DİLİMİ YÖNETİMİ ===
    async function loadTimeframeInfo() {
        try {
            const data = await fetchApi('/api/timeframe-info', { showLoading: false });
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
            tfCooldown.textContent = `${settings.cooldown_minutes}dk`;
            
            // Mobile-optimized color coding
            const rr = settings.risk_reward;
            if (rr >= 2.0) {
                timeframeInfo.className = 'info-panel excellent';
            } else if (rr >= 1.5) {
                timeframeInfo.className = 'info-panel good';
            } else {
                timeframeInfo.className = 'info-panel warning';
            }
            
            // Add haptic feedback for good settings
            if (isMobileDevice() && 'vibrate' in navigator && rr >= 1.5) {
                navigator.vibrate(25);
            }
        }
    }
    
    function loadTimeframeComparison(comparisonData) {
        if (!comparisonTableBody) return;
        
        comparisonTableBody.innerHTML = '';
        
        const timeframes = ['1m', '3m', '5m', '15m', '30m', '1h'];
        const recommendations = {
            '1m': 'Scalping',
            '3m': 'Kısa Vade',
            '5m': 'Hızlı',
            '15m': 'Optimal',
            '30m': 'Orta Vade',
            '1h': 'Swing'
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
        
        if (comparisonCard) {
            comparisonCard.style.display = 'block';
        }
    }

    timeframeSelect.addEventListener('change', () => {
        updateTimeframeDisplay();
        
        // Mobile haptic feedback
        if (isMobileDevice() && 'vibrate' in navigator) {
            navigator.vibrate(25);
        }
    });
    
    // === GELİŞMİŞ UI GÜNCELLEMESI ===
    const updateEnhancedUI = (data) => {
        if (!data) return;
        
        // Status message with mobile-friendly truncation
        const statusMsg = data.status_message || 'Bilinmiyor';
        statusMessageSpan.textContent = isMobileDevice() && statusMsg.length > 50 ? 
            statusMsg.substring(0, 47) + '...' : statusMsg;
        statusMessageSpan.className = data.is_running ? 'status-running' : 'status-stopped';
        
        // İzlenen coinler - mobile-optimized display
        if (data.symbols && data.symbols.length > 0) {
            const symbolText = isMobileDevice() ? 
                `${data.symbols.length} coin` : 
                `${data.symbols.length} coin (${data.symbols.slice(0, 3).join(', ')}${data.symbols.length > 3 ? '...' : ''})`;
            
            monitoredSymbolsSpan.textContent = symbolText;
            monitoredSymbolsSpan.className = 'status-monitoring';
            
            // Show symbols card
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
        
        // Aktif pozisyon
        if (data.active_symbol && data.position_side) {
            const posText = isMobileDevice() ? 
                `${data.position_side}` : 
                `${data.position_side} @ ${data.active_symbol}`;
            activePositionSpan.textContent = posText;
            activePositionSpan.className = 'status-in-position';
            
            // Add mobile title attribute for full info
            if (isMobileDevice()) {
                activePositionSpan.title = `${data.position_side} @ ${data.active_symbol}`;
            }
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
        if (websocketCountSpan) {
            websocketCountSpan.textContent = data.websocket_connections || 0;
        }
        
        // Risk yönetimi bilgileri
        updateRiskManagementUI(data);
        
        // Bot kontrolleri - mobile-optimized states
        const isRunning = data.is_running;
        
        enhancedStartButton.disabled = isRunning;
        enhancedStartButton.textContent = isRunning ? '🔄 Çalışıyor...' : '🚀 Bot Başlat';
        
        if (legacyStartButton) {
            legacyStartButton.disabled = isRunning;
            legacyStartButton.textContent = isRunning ? '🔄 Çalışıyor...' : '▶️ Tek Coin Başlat';
        }
        
        stopButton.disabled = !isRunning;
        stopButton.textContent = isRunning ? '🛑 Durdur' : '⏹️ Durduruldu';
        
        multiSymbolsInput.disabled = isRunning;
        if (legacySymbolInput) legacySymbolInput.disabled = isRunning;
        timeframeSelect.disabled = isRunning;
        
        // Coin yönetimi visibility
        if (coinManagement && coinButtons) {
            coinManagement.style.display = isRunning ? 'block' : 'none';
            coinButtons.style.display = isRunning ? 'flex' : 'none';
        }
        if (filtersCard) {
            filtersCard.style.display = isRunning ? 'block' : 'none';
        }
        
        // Finansal veriler - mobile-optimized formatting
        updateFinancialData(data);
    };
    
    function updateFinancialData(data) {
        const formatMobileValue = (value, suffix = ' USDT') => {
            if (!isMobileDevice() || Math.abs(value) < 1000) {
                return value.toFixed(2) + suffix;
            }
            
            // Mobile: Show abbreviated values for large numbers
            if (Math.abs(value) >= 1000000) {
                return (value / 1000000).toFixed(1) + 'M' + suffix;
            } else if (Math.abs(value) >= 1000) {
                return (value / 1000).toFixed(1) + 'K' + suffix;
            }
            return value.toFixed(2) + suffix;
        };
        
        if (data.is_running && data.account_balance !== undefined) {
            statsMainBalance.textContent = formatMobileValue(data.account_balance);
            statsMainBalance.className = 'stats-value';
        } else {
            statsMainBalance.textContent = 'N/A';
            statsMainBalance.className = 'stats-value';
        }

        if (data.is_running && data.position_pnl !== undefined) {
            formatPnl(statsPositionPnl, data.position_pnl, false, true);
        } else {
            statsPositionPnl.textContent = 'N/A';
            statsPositionPnl.className = 'stats-value';
        }

        if (data.is_running && data.daily_pnl !== undefined) {
            formatPnl(statsDailyPnl, data.daily_pnl, false, true);
        } else {
            statsDailyPnl.textContent = 'N/A';
            statsDailyPnl.className = 'stats-value';
        }

        if (data.is_running && data.order_size !== undefined) {
            statsOrderSize.textContent = formatMobileValue(data.order_size);
            statsOrderSize.className = 'stats-value';
        } else {
            statsOrderSize.textContent = 'N/A';
            statsOrderSize.className = 'stats-value';
        }
    }
    
    function updateRiskManagementUI(data) {
        // Günlük pozisyon bilgisi
        const dailyPositions = data.daily_positions || 0;
        const maxDailyPositions = data.risk_management?.max_daily_positions || 8;
        
        if (dailyPositionsSpan) dailyPositionsSpan.textContent = dailyPositions;
        if (maxDailyPositionsSpan) maxDailyPositionsSpan.textContent = maxDailyPositions;
        
        // Progress bar güncelle
        const progressPercent = (dailyPositions / maxDailyPositions) * 100;
        if (dailyPositionsProgress) {
            dailyPositionsProgress.style.width = `${Math.min(progressPercent, 100)}%`;
            dailyPositionsProgress.className = 'progress-fill';
            
            if (progressPercent >= 90) {
                dailyPositionsProgress.classList.add('progress-danger');
            } else if (progressPercent >= 70) {
                dailyPositionsProgress.classList.add('progress-warning');
            } else {
                dailyPositionsProgress.classList.add('progress-success');
            }
        }
        
        // Filtrelenen sinyaller
        if (filteredSignalsCount) {
            filteredSignalsCount.textContent = data.filtered_signals_count || 0;
        }
        
        // Risk koruması durumu
        const riskActive = data.risk_management_active !== false;
        if (riskProtectionStatus) {
            riskProtectionStatus.textContent = riskActive ? 'Aktif' : 'Pasif';
            riskProtectionStatus.className = riskActive ? 'status-active' : 'status-inactive';
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
            
            // Mobile-optimized symbol display
            const displaySymbol = isMobileDevice() && symbol.length > 8 ? 
                symbol.substring(0, 8) + '...' : symbol;
            
            symbolDiv.innerHTML = `
                <div class="symbol-name" title="${symbol}">${displaySymbol}</div>
                <div class="symbol-signal ${signalClass}">${signal}</div>
            `;
            
            // Add touch feedback
            if (isMobileDevice()) {
                symbolDiv.addEventListener('touchstart', () => {
                    symbolDiv.style.transform = 'scale(0.98)';
                }, { passive: true });
                
                symbolDiv.addEventListener('touchend', () => {
                    symbolDiv.style.transform = 'scale(1)';
                }, { passive: true });
            }
            
            symbolsList.appendChild(symbolDiv);
        });
    }

    const getEnhancedStatus = async () => {
        const data = await fetchApi('/api/enhanced-status', { showLoading: false });
        updateEnhancedUI(data);
    };

    // === GELİŞMİŞ MULTI-COIN EVENT LISTENERS ===
    enhancedStartButton.addEventListener('click', async (e) => {
        e.preventDefault();
        
        const symbolsInput = multiSymbolsInput.value.trim();
        const selectedTimeframe = timeframeSelect.value;
        
        if (!symbolsInput) {
            showNotification('Lütfen en az bir coin sembolü girin 📝', 'error');
            multiSymbolsInput.focus();
            return;
        }
        
        // Parse and validate symbols
        const symbols = symbolsInput.split(',')
            .map(s => s.trim().toUpperCase())
            .filter(s => s.length > 0);
        
        if (symbols.length === 0) {
            showNotification('Geçerli coin sembolleri girin 💱', 'error');
            return;
        }
        
        if (symbols.length > 20) {
            showNotification('Maksimum 20 coin desteklenir 📊', 'error');
            return;
        }
        
        // Validate symbol format
        const invalidSymbols = symbols.filter(s => s.length < 3 || s.length > 12);
        if (invalidSymbols.length > 0) {
            showNotification(`Geçersiz semboller: ${invalidSymbols.join(', ')} ❌`, 'error');
            return;
        }
        
        console.log('Gelişmiş multi-coin bot başlatılıyor:', symbols, selectedTimeframe);
        
        // Mobile loading state
        enhancedStartButton.disabled = true;
        enhancedStartButton.textContent = '🔄 Başlatılıyor...';
        
        showNotification(`${symbols.length} coin için bot başlatılıyor... (${selectedTimeframe.toUpperCase()}) ⚡`, 'info');
        
        const result = await fetchApi('/api/enhanced-multi-start', { 
            method: 'POST', 
            body: JSON.stringify({ symbols, timeframe: selectedTimeframe }) 
        });
        
        if (result) {
            updateEnhancedUI(result);
            showNotification(`✅ ${symbols.length} coin için bot başlatıldı! 🚀`, 'success');
            
            // Mobile: Clear input and scroll to status
            multiSymbolsInput.value = '';
            if (isMobileDevice()) {
                document.querySelector('.status-card')?.scrollIntoView({ 
                    behavior: 'smooth', 
                    block: 'center' 
                });
            }
        } else {
            enhancedStartButton.disabled = false;
            enhancedStartButton.textContent = '🚀 Bot Başlat';
        }
    });

    stopButton.addEventListener('click', async (e) => {
        e.preventDefault();
        
        // Mobile confirmation
        if (isMobileDevice()) {
            const confirm = await showMobileConfirm('Bot\'u durdurmak istediğinizden emin misiniz?');
            if (!confirm) return;
        }
        
        stopButton.disabled = true;
        stopButton.textContent = '🔄 Durduruluyor...';
        
        const result = await fetchApi('/api/stop', { method: 'POST' });
        if (result) {
            updateEnhancedUI(result);
            showNotification('Bot durduruldu 🛑', 'info');
        }
        
        stopButton.disabled = false;
        stopButton.textContent = '🛑 Durdur';
    });

    // Mobile confirmation dialog
    async function showMobileConfirm(message) {
        return new Promise((resolve) => {
            const overlay = document.createElement('div');
            overlay.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0,0,0,0.5);
                z-index: 10000;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            `;
            
            const dialog = document.createElement('div');
            dialog.style.cssText = `
                background: var(--card-bg-color);
                border-radius: 12px;
                padding: 20px;
                max-width: 300px;
                width: 100%;
                text-align: center;
                box-shadow: 0 10px 40px rgba(0,0,0,0.3);
            `;
            
            dialog.innerHTML = `
                <p style="margin-bottom: 20px; color: var(--text-color); font-size: 16px;">${message}</p>
                <div style="display: flex; gap: 10px; justify-content: center;">
                    <button id="confirm-yes" style="
                        background: var(--danger-color);
                        color: white;
                        border: none;
                        padding: 12px 20px;
                        border-radius: 8px;
                        font-weight: 600;
                        cursor: pointer;
                        flex: 1;
                    ">Evet</button>
                    <button id="confirm-no" style="
                        background: var(--secondary-color);
                        color: white;
                        border: none;
                        padding: 12px 20px;
                        border-radius: 8px;
                        font-weight: 600;
                        cursor: pointer;
                        flex: 1;
                    ">Hayır</button>
                </div>
            `;
            
            overlay.appendChild(dialog);
            document.body.appendChild(overlay);
            
            const yesBtn = dialog.querySelector('#confirm-yes');
            const noBtn = dialog.querySelector('#confirm-no');
            
            const cleanup = () => {
                document.body.removeChild(overlay);
            };
            
            yesBtn.addEventListener('click', () => {
                cleanup();
                resolve(true);
            });
            
            noBtn.addEventListener('click', () => {
                cleanup();
                resolve(false);
            });
            
            overlay.addEventListener('click', (e) => {
                if (e.target === overlay) {
                    cleanup();
                    resolve(false);
                }
            });
        });
    }

    // Symbol management functions
    addSymbolButton?.addEventListener('click', async (e) => {
        e.preventDefault();
        
        const symbol = singleSymbolInput.value.trim().toUpperCase();
        if (!symbol) {
            showNotification('Lütfen bir coin sembolü girin 📝', 'error');
            singleSymbolInput.focus();
            return;
        }
        
        if (symbol.length < 3 || symbol.length > 12) {
            showNotification('Geçersiz sembol formatı ❌', 'error');
            return;
        }
        
        addSymbolButton.disabled = true;
        addSymbolButton.textContent = '⏳ Ekleniyor...';
        
        const result = await fetchApi('/api/add-symbol', { 
            method: 'POST', 
            body: JSON.stringify({ symbol }) 
        });
        
        addSymbolButton.disabled = false;
        addSymbolButton.textContent = '➕ Ekle';
        
        if (result && result.success) {
            singleSymbolInput.value = '';
            showNotification(result.message + ' ✅', 'success');
            getEnhancedStatus();
        }
    });

    removeSymbolButton?.addEventListener('click', async (e) => {
        e.preventDefault();
        
        const symbol = singleSymbolInput.value.trim().toUpperCase();
        if (!symbol) {
            showNotification('Lütfen çıkarılacak coin sembolünü girin 📝', 'error');
            singleSymbolInput.focus();
            return;
        }
        
        // Mobile confirmation for removal
        if (isMobileDevice()) {
            const confirm = await showMobileConfirm(`${symbol} coin'ini çıkarmak istediğinizden emin misiniz?`);
            if (!confirm) return;
        }
        
        removeSymbolButton.disabled = true;
        removeSymbolButton.textContent = '⏳ Çıkarılıyor...';
        
        const result = await fetchApi('/api/remove-symbol', { 
            method: 'POST', 
            body: JSON.stringify({ symbol }) 
        });
        
        removeSymbolButton.disabled = false;
        removeSymbolButton.textContent = '➖ Çıkar';
        
        if (result && result.success) {
            singleSymbolInput.value = '';
            showNotification(result.message + ' ✅', 'success');
            getEnhancedStatus();
        }
    });

    // === POZİSYON YÖNETİMİ EVENT LISTENERS ===
    scanAllButton?.addEventListener('click', async (e) => {
        e.preventDefault();
        
        scanAllButton.disabled = true;
        scanAllButton.textContent = '🔍 Taranıyor...';
        
        const result = await fetchApi('/api/scan-all-positions', { method: 'POST' });
        
        scanAllButton.disabled = false;
        scanAllButton.textContent = '🔍 Tümünü Tara';
        
        if (result && result.success) {
            showNotification(result.message + ' ✅', 'success');
        }
    });

    monitorToggleButton?.addEventListener('click', async (e) => {
        e.preventDefault();
        
        const originalText = monitorToggleButton.textContent;
        monitorToggleButton.disabled = true;
        monitorToggleButton.textContent = '⏳ İşlem yapılıyor...';
        
        if (isMonitorRunning) {
            const result = await fetchApi('/api/stop-position-monitor', { method: 'POST' });
            if (result && result.success) {
                showNotification(result.message + ' ⏹️', 'info');
                updateMonitorButton();
            }
        } else {
            const result = await fetchApi('/api/start-position-monitor', { method: 'POST' });
            if (result && result.success) {
                showNotification(result.message + ' ✅', 'success');
                updateMonitorButton();
            }
        }
        
        monitorToggleButton.disabled = false;
        if (!monitorToggleButton.textContent.includes('Monitor')) {
            monitorToggleButton.textContent = originalText;
        }
    });

    scanSymbolButton?.addEventListener('click', async (e) => {
        e.preventDefault();
        
        const symbol = scanSymbolInput.value.trim().toUpperCase();
        if (!symbol) {
            showNotification('Lütfen bir coin sembolü girin 📝', 'error');
            scanSymbolInput.focus();
            return;
        }
        
        scanSymbolButton.disabled = true;
        scanSymbolButton.textContent = '🎯 Kontrol ediliyor...';
        
        const result = await fetchApi('/api/scan-symbol', { 
            method: 'POST', 
            body: JSON.stringify({ symbol }) 
        });
        
        scanSymbolButton.disabled = false;
        scanSymbolButton.textContent = '🎯 Kontrol Et';
        
        if (result && result.success) {
            scanSymbolInput.value = '';
            showNotification(result.message + ' ✅', 'success');
        }
    });

    async function updateMonitorButton() {
        const status = await fetchApi('/api/position-monitor-status', { showLoading: false });
        if (status && status.monitor_status) {
            isMonitorRunning = status.monitor_status.is_running;
            if (monitorToggleButton) {
                monitorToggleButton.textContent = isMonitorRunning ? '⏹️ Monitor Durdur' : '▶️ Monitor Başlat';
                monitorToggleButton.className = isMonitorRunning ? 'btn btn-warning' : 'btn btn-secondary';
            }
        }
    }

    // === GERİYE UYUMLULUK EVENT LISTENERS ===
    legacyStartButton?.addEventListener('click', async (e) => {
        e.preventDefault();
        
        const symbol = legacySymbolInput.value.trim().toUpperCase();
        const selectedTimeframe = timeframeSelect.value;
        
        if (!symbol) {
            showNotification('Lütfen bir coin sembolü girin 📝', 'error');
            legacySymbolInput.focus();
            return;
        }
        
        if (symbol.length < 3 || symbol.length > 12) {
            showNotification('Geçersiz sembol formatı ❌', 'error');
            return;
        }
        
        console.log('Legacy tek coin bot başlatılıyor:', symbol, selectedTimeframe);
        
        legacyStartButton.disabled = true;
        legacyStartButton.textContent = '🔄 Başlatılıyor...';
        
        showNotification(`Tek coin modu: ${symbol} başlatılıyor... (${selectedTimeframe.toUpperCase()}) ⚡`, 'info');
        
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
            showNotification(`✅ Tek coin modu: ${symbol} başlatıldı! 🚀`, 'success');
            
            // Clear input
            legacySymbolInput.value = '';
        }
        
        legacyStartButton.disabled = false;
        legacyStartButton.textContent = '▶️ Tek Coin Başlat';
    });

    // === FİLTRE İSTATİSTİKLERİ ===
    async function loadFilterStatistics() {
        try {
            const data = await fetchApi('/api/filter-statistics', { showLoading: false });
            if (data) {
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

    // === İSTATİSTİK HESAPLAMA ===
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

        // Update stats with mobile-friendly formatting
        if (statsTotal) statsTotal.textContent = totalTrades;
        
        const winRate = totalTrades > 0 ? ((winningTrades / totalTrades) * 100).toFixed(1) : 0;
        const loseRate = totalTrades > 0 ? ((losingTrades / totalTrades) * 100).toFixed(1) : 0;
        
        if (statsWinning) {
            const winText = isMobileDevice() ? `${winningTrades} (${winRate}%)` : `${winningTrades} (%${winRate})`;
            statsWinning.textContent = winText;
        }
        
        if (statsLosing) {
            const loseText = isMobileDevice() ? `${losingTrades} (${loseRate}%)` : `${losingTrades} (%${loseRate})`;
            statsLosing.textContent = loseText;
        }

        if (statsTotalProfit) formatPnl(statsTotalProfit, totalProfit, false, true);
        if (statsTotalLoss) formatPnl(statsTotalLoss, totalLoss, false, true);
        if (statsNetPnl) formatPnl(statsNetPnl, netPnl, false, true);
    }

    function formatPnl(element, value, isBalance = false, isMobile = false) {
        const formatValue = (val, suffix = ' USDT') => {
            if (!isMobile || Math.abs(val) < 1000) {
                return val.toFixed(2) + suffix;
            }
            
            // Mobile: Show abbreviated values
            if (Math.abs(val) >= 1000000) {
                return (val / 1000000).toFixed(1) + 'M' + suffix;
            } else if (Math.abs(val) >= 1000) {
                return (val / 1000).toFixed(1) + 'K' + suffix;
            }
            return val.toFixed(2) + suffix;
        };
        
        element.textContent = formatValue(value);
        
        if (isBalance) {
            element.className = 'stats-value';
        } else {
            element.className = value > 0 ? 'stats-value pnl-positive' : 
                               (value < 0 ? 'stats-value pnl-negative' : 'stats-value');
        }
    }

    // === KLAVYE KISAYOLLARI - Mobile Optimized ===
    const setupKeyboardShortcuts = () => {
        multiSymbolsInput?.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                enhancedStartButton.click();
            }
        });

        singleSymbolInput?.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                addSymbolButton?.click();
            }
        });

        scanSymbolInput?.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                scanSymbolButton?.click();
            }
        });

        legacySymbolInput?.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                legacyStartButton?.click();
            }
        });
        
        // Mobile: Add 'Go' button functionality to keyboards
        const inputs = [multiSymbolsInput, singleSymbolInput, scanSymbolInput, legacySymbolInput];
        inputs.forEach(input => {
            if (input && isMobileDevice()) {
                input.setAttribute('enterkeyhint', 'go');
            }
        });
    };

    // === OTOMATIK YENİLEME ===
    const setupAutoRefresh = () => {
        setInterval(() => {
            if (auth.currentUser && document.visibilityState === 'visible') {
                loadFilterStatistics();
            }
        }, 30000); // 30 saniyede bir
        
        // Page visibility handling for mobile battery optimization
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'visible') {
                console.log('📱 Page visible - resuming updates');
                if (auth.currentUser) {
                    getEnhancedStatus();
                }
            } else {
                console.log('📱 Page hidden - pausing updates');
            }
        });
    };

    // === PWA SUPPORT ===
    // Service Worker Registration
    if ('serviceWorker' in navigator) {
        window.addEventListener('load', async () => {
            try {
                const registration = await navigator.serviceWorker.register('/static/sw.js');
                console.log('✅ PWA: Service Worker registered:', registration.scope);
                
                // Handle service worker updates
                registration.addEventListener('updatefound', () => {
                    const newWorker = registration.installing;
                    console.log('🔄 PWA: New service worker found');
                    
                    newWorker.addEventListener('statechange', () => {
                        if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                            console.log('📱 PWA: New version available');
                            showUpdateNotification();
                        }
                    });
                });
                
                // Listen for controlling service worker change
                navigator.serviceWorker.addEventListener('controllerchange', () => {
                    console.log('🔄 PWA: Controller changed, reloading...');
                    window.location.reload();
                });
                
            } catch (error) {
                console.error('❌ PWA: Service Worker registration failed:', error);
            }
        });
    }

    // App Update Notification
    function showUpdateNotification() {
        const updateBanner = document.createElement('div');
        updateBanner.innerHTML = `
            <div style="
                position: fixed;
                top: ${isMobileDevice() ? 'calc(var(--header-height) + var(--safe-area-top) + 10px)' : '10px'};
                left: 50%;
                transform: translateX(-50%);
                background: linear-gradient(135deg, #1f6feb, #7c3aed);
                color: white;
                padding: 12px 20px;
                border-radius: 8px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.3);
                z-index: 10001;
                font-size: 14px;
                display: flex;
                align-items: center;
                gap: 12px;
                max-width: calc(100vw - 20px);
            ">
                <span>🆕 Yeni güncelleme mevcut!</span>
                <button onclick="updateApp()" style="
                    background: rgba(255,255,255,0.2);
                    border: none;
                    color: white;
                    padding: 6px 12px;
                    border-radius: 4px;
                    cursor: pointer;
                    font-size: 12px;
                    font-weight: 600;
                ">Güncelle</button>
                <button onclick="this.parentElement.parentElement.remove()" style="
                    background: none;
                    border: none;
                    color: white;
                    cursor: pointer;
                    font-size: 16px;
                    padding: 4px;
                ">×</button>
            </div>
        `;
        document.body.appendChild(updateBanner);
        
        // Auto remove after 10 seconds
        setTimeout(() => {
            if (updateBanner.parentElement) {
                updateBanner.remove();
            }
        }, 10000);
    }

    // Update app function
    window.updateApp = async () => {
        try {
            const registration = await navigator.serviceWorker.getRegistration();
            if (registration && registration.waiting) {
                registration.waiting.postMessage({ type: 'SKIP_WAITING' });
            }
        } catch (error) {
            console.error('❌ PWA: Update failed:', error);
            window.location.reload();
        }
    };

    // Install prompt handling
    let deferredPrompt = null;

    window.addEventListener('beforeinstallprompt', (event) => {
        console.log('📱 PWA: Install prompt available');
        event.preventDefault();
        deferredPrompt = event;
        showInstallButton();
    });

    // Show install button
    function showInstallButton() {
        // Don't show install button if already installed
        if (window.matchMedia('(display-mode: standalone)').matches) {
            return;
        }
        
        const installButton = document.createElement('button');
        installButton.innerHTML = '📱 Ana Ekrana Ekle';
        installButton.className = 'btn btn-info';
        installButton.style.cssText = `
            position: fixed;
            bottom: ${isMobileDevice() ? 'calc(20px + var(--safe-area-bottom))' : '20px'};
            right: 20px;
            z-index: 10000;
            animation: pulse 2s infinite;
            font-size: 12px;
            padding: 8px 12px;
        `;
        
        installButton.addEventListener('click', async () => {
            if (deferredPrompt) {
                deferredPrompt.prompt();
                const result = await deferredPrompt.userChoice;
                
                if (result.outcome === 'accepted') {
                    console.log('✅ PWA: User accepted install prompt');
                    showNotification('Uygulama ana ekrana eklendi! 📱', 'success');
                } else {
                    console.log('❌ PWA: User dismissed install prompt');
                }
                
                deferredPrompt = null;
                installButton.remove();
            }
        });
        
        document.body.appendChild(installButton);
        
        // Auto remove after 30 seconds
        setTimeout(() => {
            if (installButton.parentElement) {
                installButton.remove();
            }
        }, 30000);
    }

    // Handle app installation
    window.addEventListener('appinstalled', (event) => {
        console.log('✅ PWA: App installed successfully');
        showNotification('Uygulama başarıyla yüklendi! 🎉', 'success');
        deferredPrompt = null;
    });

    // Handle online/offline status
    window.addEventListener('online', () => {
        console.log('🌐 PWA: Back online');
        showNotification('İnternet bağlantısı geri geldi 🌐', 'success');
        document.body.classList.remove('offline');
        
        // Refresh data when back online
        if (auth.currentUser) {
            getEnhancedStatus();
        }
    });

    window.addEventListener('offline', () => {
        console.log('📴 PWA: Gone offline');
        showNotification('Çevrimdışı mod - Bazı özellikler sınırlı 📴', 'warning');
        document.body.classList.add('offline');
    });

    // Add offline indicator styles
    const offlineStyles = `
        .offline {
            filter: grayscale(0.3);
        }
        
        .offline::before {
            content: '📴 Çevrimdışı';
            position: fixed;
            top: calc(var(--header-height) + var(--safe-area-top) + 5px);
            left: 50%;
            transform: translateX(-50%);
            background: #f85149;
            color: white;
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 11px;
            z-index: 10000;
            font-weight: 600;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
        }
        
        @media (max-width: 768px) {
            .offline::before {
                font-size: 10px;
                padding: 4px 8px;
            }
        }
    `;

    // Add offline styles to head
    const styleSheet = document.createElement('style');
    styleSheet.textContent = offlineStyles;
    document.head.appendChild(styleSheet);

    // === INITIALIZATION ===
    setupKeyboardShortcuts();
    setupAutoRefresh();
    
    // PWA install prompt after user interaction
    setTimeout(() => {
        if (deferredPrompt && !window.matchMedia('(display-mode: standalone)').matches) {
            showInstallButton();
        }
    }, 5000);
    
    // Add loading states for mobile
    const addLoadingState = (button, originalText) => {
        button.disabled = true;
        button.textContent = '⏳ Yükleniyor...';
        
        setTimeout(() => {
            if (button.disabled) {
                button.disabled = false;
                button.textContent = originalText;
            }
        }, 10000); // Fallback timeout
    };

    // Enhanced mobile input handling
    const mobileInputs = document.querySelectorAll('input[type="text"], input[type="email"], select');
    mobileInputs.forEach(input => {
        if (isMobileDevice()) {
            // Prevent zoom on focus for iOS
            input.style.fontSize = '16px';
            
            // Add mobile-friendly attributes
            if (input.type === 'text' && input.id.toLowerCase().includes('symbol')) {
                input.setAttribute('autocapitalize', 'characters');
                input.setAttribute('autocorrect', 'off');
                input.setAttribute('spellcheck', 'false');
                input.setAttribute('inputmode', 'text');
            }
            
            if (input.type === 'email') {
                input.setAttribute('inputmode', 'email');
            }
        }
    });

    console.log('✅ Mobile-optimized script initialized');
    console.log('📱 Mobile device:', isMobileDevice());
    console.log('🔧 PWA support:', 'serviceWorker' in navigator);
    console.log('📳 Vibration support:', 'vibrate' in navigator);
    console.log('🌐 Online status:', navigator.onLine);
});
