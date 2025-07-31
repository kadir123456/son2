document.addEventListener('DOMContentLoaded', () => {
    // ÇOK ÖNEMLİ: BU BİLGİLERİ KENDİ FIREBASE PROJENİZDEN ALIP DOLDURUN
    const firebaseConfig = {
        apiKey: "AIzaSyDkJch-8B46dpZSB-pMSR4q1uvzadCVekE", // Kendi Firebase API Key'iniz
        authDomain: "aviator-90c8b.firebaseapp.com", // Kendi Firebase Auth Domain'iniz
        databaseURL: "https://aviator-90c8b-default-rtdb.firebaseio.com", // Kendi Firebase Database URL'iniz
        projectId: "aviator-90c8b", // Kendi Firebase Project ID'niz
        storageBucket: "aviator-90c8b.appspot.com", // Kendi Firebase Storage Bucket'ınız
        messagingSenderId: "823763988442", // Kendi Firebase Messaging Sender ID'niz
        appId: "1:823763988442:web:16a797275675a219c3dae3" // Kendi Firebase App ID'niz
    };
    // -----------------------------------------------------------------

    firebase.initializeApp(firebaseConfig);
    const auth = firebase.auth();
    const database = firebase.database();

    // HTML elementleri
    const loginContainer = document.getElementById('login-container');
    const appContainer = document.getElementById('app-container');
    const loginButton = document.getElementById('login-button');
    const logoutButton = document.getElementById('logout-button');
    const emailInput = document.getElementById('email');
    const passwordInput = document.getElementById('password');
    const loginError = document.getElementById('login-error');
    const symbolInput = document.getElementById('symbol-input');
    const startButton = document.getElementById('start-button');
    const stopButton = document.getElementById('stop-button');

    // Yeni ve güncellenmiş durum alanları
    const statusMessageSpan = document.getElementById('status-message');
    const currentSymbolSpan = document.getElementById('current-symbol');
    const positionStatusSpan = document.getElementById('position-status');
    const positionSideSpan = document.getElementById('position-side'); // Yeni
    const lastSignalSpan = document.getElementById('last-signal');
    const currentBalanceSpan = document.getElementById('current-balance'); // Yeni

    // İstatistik elementleri
    const statsTotal = document.getElementById('stats-total-trades');
    const statsWinning = document.getElementById('stats-winning-trades');
    const statsLosing = document.getElementById('stats-losing-trades');
    const statsTotalProfit = document.getElementById('stats-total-profit');
    const statsTotalLoss = document.getElementById('stats-total-loss');
    const statsNetPnl = document.getElementById('stats-net-pnl');
    
    let statusInterval;

    // --- KİMLİK DOĞRULAMA ---
    loginButton.addEventListener('click', () => {
        loginError.textContent = "";
        auth.signInWithEmailAndPassword(emailInput.value, passwordInput.value)
            .catch(error => { 
                console.error("Giriş hatası:", error);
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
            getStatus();
            statusInterval = setInterval(getStatus, 5000); // Durum sorgulama aralığı 5 saniyeye düşürüldü
            listenForTradeUpdates(); // Firebase Realtime DB dinlemesi
        } else {
            loginContainer.style.display = 'flex';
            appContainer.style.display = 'none';
            if (statusInterval) clearInterval(statusInterval);
        }
    });

    // --- API İSTEKLERİ ---
    async function fetchApi(endpoint, options = {}) {
        const user = auth.currentUser;
        if (!user) {
            console.warn("Kullanıcı giriş yapmamış, API isteği yapılamaz.");
            return null;
        }
        try {
            const idToken = await user.getIdToken(true); // Token'ı yenile
            const headers = { ...options.headers, 'Authorization': `Bearer ${idToken}` };
            if (options.body && !headers['Content-Type']) { // Content-Type'ı body varsa ayarla
                headers['Content-Type'] = 'application/json';
            }
            
            const response = await fetch(endpoint, { ...options, headers });
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: response.statusText }));
                console.error("API Hatası:", errorData.detail);
                // Kullanıcıya hata göstermek için bir mekanizma eklenebilir
                statusMessageSpan.textContent = `Hata: ${errorData.detail}`;
                statusMessageSpan.className = 'status-stopped'; // Hata durumunda kırmızı
                return null;
            }
            return response.json();
        } catch (error) { 
            console.error("API isteği hatası:", error); 
            statusMessageSpan.textContent = `Bağlantı Hatası: ${error.message}`;
            statusMessageSpan.className = 'status-stopped'; // Hata durumunda kırmızı
            return null;
        }
    }
    
    // --- ARAYÜZ GÜNCELLEME ---
    const updateUI = (data) => {
        if (!data) {
            // Veri gelmezse veya hata olursa botu durmuş gibi göster
            startButton.disabled = false; 
            stopButton.disabled = true; 
            symbolInput.disabled = false;
            statusMessageSpan.className = 'status-stopped';
            return;
        }

        statusMessageSpan.textContent = data.status_message;
        currentSymbolSpan.textContent = data.symbol || 'N/A';
        lastSignalSpan.textContent = data.last_signal || 'N/A';
        currentBalanceSpan.textContent = `${data.current_balance ? data.current_balance.toFixed(2) : '0.00'} USDT`; // Güncel bakiye
        
        // Botun çalışma durumuna göre butonları ayarla
        if (data.is_running) {
            startButton.disabled = true;
            stopButton.disabled = false;
            symbolInput.disabled = true; // Bot çalışırken sembol değiştirilemez
            statusMessageSpan.className = 'status-running'; // Yeşil
        } else {
            startButton.disabled = false;
            stopButton.disabled = true;
            symbolInput.disabled = false;
            statusMessageSpan.className = 'status-stopped'; // Kırmızı
        }
        
        // Pozisyon durumu ve yönü
        positionStatusSpan.textContent = data.in_position ? 'Evet' : 'Hayır';
        positionStatusSpan.className = data.in_position ? 'status-in-position' : ''; // Pozisyondaysa mavi
        positionSideSpan.textContent = data.position_side || 'N/A';
    };

    const getStatus = async () => updateUI(await fetchApi('/api/status'));

    startButton.addEventListener('click', async () => {
        const symbol = symbolInput.value.trim().toUpperCase();
        // Symbol boşsa bile isteği gönder, bot config'den alsın
        const dataToSend = symbol ? { symbol: symbol } : {};

        updateUI(await fetchApi('/api/start', { 
            method: 'POST', 
            body: JSON.stringify(dataToSend) 
        }));
    });

    stopButton.addEventListener('click', async () => {
        updateUI(await fetchApi('/api/stop', { method: 'POST' }));
    });

    // --- İSTATİSTİK HESAPLAMA ---
    function listenForTradeUpdates() {
        const tradesRef = database.ref('trades');
        // 'child_added' yerine 'value' kullanmak tüm veriyi alıp tekrar hesaplama için daha uygun.
        // Daha büyük veri setlerinde 'child_added' ve 'child_changed' daha performanslı olabilir.
        tradesRef.on('value', (snapshot) => {
            const trades = snapshot.val() ? Object.values(snapshot.val()) : [];
            calculateAndDisplayStats(trades);
        });
    }

    function calculateAndDisplayStats(trades) {
        let totalTrades = 0;
        let winningTrades = 0, losingTrades = 0;
        let totalProfit = 0, totalLoss = 0;

        trades.forEach(trade => {
            // Sadece kapanan pozisyonları say (OPEN statüsündeki işlemleri dahil etme)
            if (trade.status && trade.status !== "OPEN") {
                totalTrades++;
                const pnl = parseFloat(trade.pnl) || 0;
                if (pnl > 0) {
                    winningTrades++;
                    totalProfit += pnl;
                } else if (pnl < 0) {
                    losingTrades++;
                    totalLoss += pnl;
                }
            }
        });
        
        const netPnl = totalProfit + totalLoss; // totalLoss zaten negatif bir sayı olacak

        statsTotal.textContent = totalTrades;
        const winRate = totalTrades > 0 ? ((winningTrades / totalTrades) * 100).toFixed(1) : 0;
        const loseRate = totalTrades > 0 ? ((losingTrades / totalTrades) * 100).toFixed(1) : 0;
        statsWinning.textContent = `${winningTrades} (%${winRate})`;
        statsLosing.textContent = `${losingTrades} (%${loseRate})`;

        formatPnl(statsTotalProfit, totalProfit);
        formatPnl(statsTotalLoss, totalLoss);
        formatPnl(statsNetPnl, netPnl);
    }

    function formatPnl(element, value) {
        element.textContent = `${value.toFixed(2)} USDT`;
        element.className = value > 0 ? 'stats-value pnl-positive' : (value < 0 ? 'stats-value pnl-negative' : 'stats-value');
    }
});