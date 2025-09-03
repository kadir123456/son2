// Multi-Coin Trading Bot - Clean JavaScript
// Firebase configuration will be fetched from backend

console.log('🚀 Multi-Coin Trading Bot başlatılıyor...');

// Global variables
let auth, database, statusInterval;

// DOM Elements
const elements = {
    // Login elements
    loginScreen: document.getElementById('login-screen'),
    appLayout: document.getElementById('app-layout'),
    loginForm: document.getElementById('login-form'),
    loginBtn: document.getElementById('login-btn'),
    loginText: document.getElementById('login-text'),
    loginLoading: document.getElementById('login-loading'),
    loginError: document.getElementById('login-error'),
    emailInput: document.getElementById('email'),
    passwordInput: document.getElementById('password'),
    createTestUserBtn: document.getElementById('create-test-user-btn'),
    testConnectionBtn: document.getElementById('test-connection-btn'),
    
    // Header elements
    logoutBtn: document.getElementById('logout-btn'),
    userEmail: document.getElementById('user-email'),
    
    // Bot control elements
    startMonitoringBtn: document.getElementById('start-monitoring-btn'),
    stopAllBtn: document.getElementById('stop-all-btn'),
    addCoinBtn: document.getElementById('add-coin-btn'),
    symbolInput: document.getElementById('symbol-input'),
    orderSizeInput: document.getElementById('order-size-input'),
    
    // Status elements
    botStatus: document.getElementById('bot-status'),
    totalBalance: document.getElementById('total-balance'),
    activeCoinsCount: document.getElementById('active-coins-count'),
    totalPositions: document.getElementById('total-positions'),
    statusMessage: document.getElementById('status-message'),
    coinsContainer: document.getElementById('coins-container'),
    
    // Stats elements
    statsTotal: document.getElementById('stats-total-trades'),
    statsWinning: document.getElementById('stats-winning-trades'),
    statsLosing: document.getElementById('stats-losing-trades'),
    statsNetPnl: document.getElementById('stats-net-pnl')
};

// Initialize Firebase from backend config
async function initializeFirebase() {
    try {
        console.log('Firebase konfigürasyonu alınıyor...');
        
        // Firebase config'i backend'den al
        const response = await fetch('/api/firebase-config');
        if (!response.ok) {
            throw new Error('Firebase config alınamadı');
        }
        
        const firebaseConfig = await response.json();
        console.log('Firebase config alındı');
        
        // Firebase'i başlat
        firebase.initializeApp(firebaseConfig);
        auth = firebase.auth();
        database = firebase.database();
        
        console.log('✅ Firebase başarıyla başlatıldı');
        
        // Auth state listener'ı ekle
        setupAuthListener();
        
        // Event listener'ları ekle
        setupEventListeners();
        
        return true;
    } catch (error) {
        console.error('❌ Firebase başlatma hatası:', error);
        showError('Firebase bağlantısı kurulamadı. Sayfa yenileyin.');
        return false;
    }
}

// Authentication state listener
function setupAuthListener() {
    auth.onAuthStateChanged(user => {
        console.log('🔐 Auth durumu değişti:', user ? user.email : 'Kullanıcı yok');
        
        if (user) {
            showApp(user);
        } else {
            showLogin();
        }
    });
}

// Show app interface
function showApp(user) {
    hideElement(elements.loginScreen);
    showElement(elements.appLayout);
    
    if (elements.userEmail) {
        elements.userEmail.textContent = user.email;
    }
    
    // Start status polling
    getStatus();
    statusInterval = setInterval(getStatus, 3000);
    
    // Listen for Firebase trade updates
    listenForTradeUpdates();
}

// Show login interface
function showLogin() {
    showElement(elements.loginScreen);
    hideElement(elements.appLayout);
    setLoading(false);
    hideError();
    
    if (statusInterval) {
        clearInterval(statusInterval);
    }
}

// Setup all event listeners
function setupEventListeners() {
    // Login form
    if (elements.loginForm) {
        elements.loginForm.addEventListener('submit', handleLogin);
    }
    
    // Logout button
    if (elements.logoutBtn) {
        elements.logoutBtn.addEventListener('click', () => auth.signOut());
    }
    
    // Test buttons
    if (elements.createTestUserBtn) {
        elements.createTestUserBtn.addEventListener('click', createTestUser);
    }
    
    if (elements.testConnectionBtn) {
        elements.testConnectionBtn.addEventListener('click', testFirebaseConnection);
    }
    
    // Bot control buttons
    if (elements.startMonitoringBtn) {
        elements.startMonitoringBtn.addEventListener('click', startMonitoring);
    }
    
    if (elements.stopAllBtn) {
        elements.stopAllBtn.addEventListener('click', stopAll);
    }
    
    if (elements.addCoinBtn) {
        elements.addCoinBtn.addEventListener('click', addCoin);
    }
    
    // Symbol input auto-uppercase and enter key
    if (elements.symbolInput) {
        elements.symbolInput.addEventListener('input', (e) => {
            e.target.value = e.target.value.toUpperCase();
        });
        
        elements.symbolInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                if (elements.addCoinBtn) elements.addCoinBtn.click();
            }
        });
    }
}

// Handle login form submission
async function handleLogin(e) {
    e.preventDefault();
    
    const email = elements.emailInput?.value?.trim();
    const password = elements.passwordInput?.value?.trim();
    
    console.log('Giriş denemesi:', { email, password: password ? '***' : 'boş' });
    
    if (!email || !password) {
        showError('E-posta ve şifre alanları boş olamaz!');
        return;
    }

    setLoading(true);
    hideError();

    try {
        console.log('Firebase giriş deneniyor...');
        const userCredential = await auth.signInWithEmailAndPassword(email, password);
        console.log('✅ Giriş başarılı:', userCredential.user.email);
    } catch (error) {
        console.error('❌ Giriş hatası:', error);
        
        let errorMessage = 'Giriş yapılırken bir hata oluştu!';
        
        switch (error.code) {
            case 'auth/user-not-found':
                errorMessage = 'Bu e-posta adresi ile kayıtlı kullanıcı bulunamadı!';
                break;
            case 'auth/wrong-password':
                errorMessage = 'Şifre yanlış!';
                break;
            case 'auth/invalid-email':
                errorMessage = 'Geçersiz e-posta formatı!';
                break;
            case 'auth/invalid-credential':
                errorMessage = 'E-posta veya şifre hatalı!';
                break;
            case 'auth/too-many-requests':
                errorMessage = 'Çok fazla başarısız deneme. Lütfen daha sonra tekrar deneyin.';
                break;
            default:
                errorMessage = `Hata: ${error.message}`;
        }
        
        showError(errorMessage);
        setLoading(false);
    }
}

// Create test user
async function createTestUser() {
    try {
        const email = "test@example.com";
        const password = "test123456";
        
        console.log('Test kullanıcısı oluşturuluyor...');
        const userCredential = await auth.createUserWithEmailAndPassword(email, password);
        console.log('✅ Test kullanıcı oluşturuldu:', userCredential.user.email);
        alert(`✅ Test kullanıcısı oluşturuldu!\nE-posta: ${email}\nŞifre: ${password}`);
    } catch (error) {
        console.error('❌ Test kullanıcı hatası:', error);
        
        if (error.code === 'auth/email-already-in-use') {
            alert(`ℹ️ Test kullanıcısı zaten mevcut!\nE-posta: test@example.com\nŞifre: test123456`);
        } else {
            alert('❌ Test kullanıcısı oluşturulamadı: ' + error.message);
        }
    }
}

// Test Firebase connection
async function testFirebaseConnection() {
    try {
        console.log('Firebase bağlantısı test ediliyor...');
        
        // Auth test
        const currentUser = auth.currentUser;
        console.log('Mevcut kullanıcı:', currentUser?.email || 'Yok');
        
        // Database test
        const testRef = database.ref('test');
        await testRef.set({ timestamp: Date.now(), message: 'Test bağlantısı' });
        console.log('✅ Database yazma testi başarılı');
        
        const snapshot = await testRef.once('value');
        console.log('✅ Database okuma testi başarılı:', snapshot.val());
        
        alert('✅ Firebase bağlantısı başarılı!');
        
    } catch (error) {
        console.error('❌ Firebase bağlantı testi başarısız:', error);
        alert('❌ Firebase bağlantı testi başarısız: ' + error.message);
    }
}

// Bot control functions
async function startMonitoring() {
    console.log('Bot başlatılıyor...');
    const result = await fetchApi('/api/start-monitoring', { method: 'POST' });
    if (result) {
        updateStatusMessage('✅ Bot monitoring başlatıldı!', 'success');
        updateUI(result.status);
    }
}

async function stopAll() {
    if (!confirm('Tüm işlemleri durdurmak istediğinizden emin misiniz?')) return;
    
    console.log('Bot durduruluyor...');
    const result = await fetchApi('/api/stop-all', { method: 'POST' });
    if (result) {
        updateStatusMessage('✅ Tüm işlemler durduruldu!', 'success');
        updateUI(result.status);
    }
}

async function addCoin() {
    const symbol = elements.symbolInput?.value?.trim()?.toUpperCase();
    const orderSize = parseFloat(elements.orderSizeInput?.value);

    if (!symbol) {
        updateStatusMessage('❌ Coin sembolü boş olamaz!', 'danger');
        return;
    }

    if (!orderSize || orderSize < 10) {
        updateStatusMessage('❌ İşlem boyutu minimum 10 USDT olmalı!', 'danger');
        return;
    }

    console.log('Coin ekleniyor:', symbol, orderSize);
    const result = await fetchApi('/api/add-coin', {
        method: 'POST',
        body: JSON.stringify({
            symbol: symbol,
            order_size_usdt: orderSize
        })
    });

    if (result) {
        updateStatusMessage(`✅ ${symbol} başarıyla eklendi!`, 'success');
        if (elements.symbolInput) elements.symbolInput.value = '';
        if (elements.orderSizeInput) elements.orderSizeInput.value = '50';
        updateUI(result.status);
    }
}

// Remove coin function (globally accessible)
window.removeCoin = async function(symbol) {
    if (!confirm(`${symbol} coin'ini kaldırmak istediğinizden emin misiniz?\nAçık pozisyon varsa kapatılacaktır!`)) {
        return;
    }

    console.log('Coin kaldırılıyor:', symbol);
    const result = await fetchApi('/api/remove-coin', {
        method: 'POST',
        body: JSON.stringify({ symbol: symbol })
    });

    if (result) {
        updateStatusMessage(`✅ ${symbol} başarıyla kaldırıldı!`, 'success');
        updateUI(result.status);
    }
};

// API request function
async function fetchApi(endpoint, options = {}) {
    const user = auth?.currentUser;
    if (!user) {
        console.warn('Kullanıcı giriş yapmamış');
        return null;
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
            headers
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({
                detail: response.statusText
            }));
            throw new Error(errorData.detail);
        }

        return response.json();
    } catch (error) {
        console.error('API Hatası:', error);
        updateStatusMessage(`❌ ${error.message}`, 'danger');
        return null;
    }
}

// UI update functions
function updateUI(data) {
    if (!data) return;

    console.log('UI güncelleniyor:', data);

    // Bot Status
    if (elements.botStatus) {
        elements.botStatus.innerHTML = data.is_running ? 
            '<span class="badge badge-success">🟢 Çalışıyor</span>' : 
            '<span class="badge badge-danger">🔴 Durdurulmuş</span>';
    }

    // Balance and Counts
    if (elements.totalBalance) {
        elements.totalBalance.textContent = `${(data.total_balance || 0).toFixed(2)} USDT`;
    }
    if (elements.activeCoinsCount) {
        elements.activeCoinsCount.textContent = Object.keys(data.active_coins || {}).length;
    }
    if (elements.totalPositions) {
        elements.totalPositions.textContent = data.total_positions || 0;
    }

    // Button States
    if (elements.startMonitoringBtn) elements.startMonitoringBtn.disabled = data.is_running;
    if (elements.stopAllBtn) elements.stopAllBtn.disabled = !data.is_running;
    if (elements.addCoinBtn) elements.addCoinBtn.disabled = !data.is_running;

    // Update Coins Display
    updateCoinsDisplay(data.coin_details || {});
}

function updateCoinsDisplay(coinDetails) {
    if (!elements.coinsContainer) return;

    if (Object.keys(coinDetails).length === 0) {
        elements.coinsContainer.innerHTML = '<div class="no-data">Henüz coin eklenmedi</div>';
        return;
    }

    const coinsHTML = Object.entries(coinDetails).map(([symbol, details]) => {
        const positionBadge = details.in_position ? 
            '<span class="badge badge-success">📍 Pozisyonda</span>' : 
            '<span class="badge badge-info">⏳ Beklemede</span>';

        const pnlClass = (details.pnl || 0) >= 0 ? 'positive' : 'negative';
        const signalBadge = getSignalBadge(details.last_signal);

        return `
            <div class="coin-item">
                <div class="coin-header">
                    <div class="coin-symbol">${symbol}</div>
                    <button onclick="removeCoin('${symbol}')" class="btn btn-danger btn-sm">
                        🗑️ Kaldır
                    </button>
                </div>
                <div class="coin-info">
                    <div class="info-item">
                        <div class="info-label">Durum</div>
                        <div class="info-value">${positionBadge}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Pozisyon Yönü</div>
                        <div class="info-value">${details.position_side || 'Yok'}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Son Sinyal</div>
                        <div class="info-value">${signalBadge}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">İşlem Boyutu</div>
                        <div class="info-value">${(details.order_size_usdt || 0).toFixed(2)} USDT</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">P&L</div>
                        <div class="info-value ${pnlClass}">${(details.pnl || 0).toFixed(2)} USDT</div>
                    </div>
                </div>
            </div>
        `;
    }).join('');

    elements.coinsContainer.innerHTML = coinsHTML;
}

function getSignalBadge(signal) {
    switch (signal) {
        case 'LONG':
            return '<span class="badge badge-success">📈 LONG</span>';
        case 'SHORT':
            return '<span class="badge badge-danger">📉 SHORT</span>';
        case 'HOLD':
            return '<span class="badge badge-warning">⏸️ BEKLE</span>';
        default:
            return '<span class="badge badge-info">📊 N/A</span>';
    }
}

function updateStatusMessage(message, type = 'info') {
    if (elements.statusMessage) {
        elements.statusMessage.textContent = message;
        if (elements.statusMessage.parentElement) {
            elements.statusMessage.parentElement.className = `alert alert-${type}`;
        }
    }
    console.log(`Status: ${message}`);
}

// Status polling
async function getStatus() {
    const data = await fetchApi('/api/status');
    if (data) updateUI(data);
}

// Firebase statistics listener
function listenForTradeUpdates() {
    try {
        const tradesRef = database.ref('trades');
        tradesRef.on('value', (snapshot) => {
            const trades = snapshot.val() ? Object.values(snapshot.val()) : [];
            calculateAndDisplayStats(trades);
        });
    } catch (error) {
        console.error('Firebase dinleme hatası:', error);
    }
}

function calculateAndDisplayStats(trades) {
    let totalTrades = 0;
    let winningTrades = 0;
    let losingTrades = 0;
    let totalProfit = 0;
    let totalLoss = 0;

    trades.forEach(trade => {
        if (trade.status && trade.status !== "OPEN") {
            totalTrades++;
            const pnl = parseFloat(trade.pnl) || 0;
            
            if (pnl > 0) {
                winningTrades++;
                totalProfit += pnl;
            } else if (pnl < 0) {
                losingTrades++;
                totalLoss += Math.abs(pnl);
            }
        }
    });

    const netPnl = totalProfit - totalLoss;
    const winRate = totalTrades > 0 ? ((winningTrades / totalTrades) * 100).toFixed(1) : 0;

    // Update Stats
    if (elements.statsTotal) elements.statsTotal.textContent = totalTrades;
    if (elements.statsWinning) {
        elements.statsWinning.textContent = `${winningTrades} (${winRate}%)`;
    }
    if (elements.statsLosing) {
        elements.statsLosing.textContent = `${losingTrades} (${(100 - winRate).toFixed(1)}%)`;
    }
    
    // Format Net P&L
    if (elements.statsNetPnl) {
        elements.statsNetPnl.textContent = netPnl.toFixed(2);
        elements.statsNetPnl.className = `stat-value ${netPnl >= 0 ? 'positive' : 'negative'}`;
    }
}

// Utility functions
function showElement(element) {
    if (element) element.classList.remove('hidden');
}

function hideElement(element) {
    if (element) element.classList.add('hidden');
}

function showError(message) {
    if (elements.loginError) {
        elements.loginError.textContent = message;
        showElement(elements.loginError);
    }
}

function hideError() {
    hideElement(elements.loginError);
}

function setLoading(loading) {
    if (loading) {
        if (elements.loginBtn) elements.loginBtn.disabled = true;
        hideElement(elements.loginText);
        showElement(elements.loginLoading);
    } else {
        if (elements.loginBtn) elements.loginBtn.disabled = false;
        showElement(elements.loginText);
        hideElement(elements.loginLoading);
    }
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', async () => {
    console.log('🚀 DOM yüklendi, Firebase başlatılıyor...');
    await initializeFirebase();
});
