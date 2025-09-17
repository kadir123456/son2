# BNC
BTT
# 🚀 Multi-Coin Binance Futures Bot v3.0

## ✨ Özellikler

- 🔄 **Multi-Coin Desteği**: Aynı anda 20'ye kadar coin izleme
- 🛡️ **Gelişmiş Sahte Sinyal Koruması**: 7 farklı filtre sistemi
- 🎯 **Otomatik TP/SL**: Pozisyon açıldığında otomatik kar al/zarar durdur
- 💰 **Dinamik Pozisyon Boyutlandırma**: Bakiyenin %90'ını kullanım
- 🧹 **Yetim Emir Koruması**: Açık emirlerin otomatik temizlenmesi
- 📊 **Gerçek Zamanlı İzleme**: WebSocket ile canlı veri
- 🔒 **Firebase Authentication**: Güvenli kullanıcı doğrulama
- 📱 **Responsive UI**: Mobil uyumlu modern arayüz

## 🛠️ Kurulum

### 1. Gereksinimleri Yükleyin

```bash
pip install -r requirements.txt
```

### 2. Çevre Değişkenlerini Ayarlayın

`.env` dosyası oluşturun:

```bash
# Binance API Bilgileri
BINANCE_API_KEY=your_binance_api_key_here
BINANCE_API_SECRET=your_binance_api_secret_here

# Ortam (LIVE veya TEST)
ENVIRONMENT=LIVE

# Firebase Bilgileri (JSON formatında)
FIREBASE_CREDENTIALS_JSON={"type": "service_account", "project_id": "..."}
FIREBASE_DATABASE_URL=https://your-project.firebaseio.com

# Bot Kimlik Bilgileri (isteğe bağlı)
BOT_USERNAME=admin
BOT_PASSWORD=changeme123
```

### 3. Firebase Kurulumu

1. [Firebase Console](https://console.firebase.google.com/) üzerinden proje oluşturun
2. **Authentication** > **Sign-in method** > **Email/Password**'ü etkinleştirin
3. **Realtime Database** oluşturun
4. **Project Settings** > **Service accounts** > **Generate new private key**
5. İndirilen JSON dosyasını `FIREBASE_CREDENTIALS_JSON` değişkenine ekleyin

### 4. Binance API Kurulumu

1. [Binance](https://www.binance.com/) hesabınıza giriş yapın
2. **API Management** bölümünden yeni API key oluşturun
3. **Futures Trading** izinlerini verin
4. IP kısıtlaması ayarlayın (güvenlik için önerilen)

## 🚀 Çalıştırma

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Bot `http://localhost:8000` adresinde çalışacak.

## 📊 Strateji Ayarları

`app/config.py` dosyasından stratejiyi özelleştirebilirsiniz:

### Temel Parametreler
- **LEVERAGE**: Kaldıraç oranı (varsayılan: 20x)
- **TIMEFRAME**: Analiz zaman dilimi (varsayılan: 15m)
- **STOP_LOSS_PERCENT**: Zarar durdur yüzdesi (varsayılan: %0.9)
- **TAKE_PROFIT_PERCENT**: Kar al yüzdesi (varsayılan: %1.0)

### Sahte Sinyal Filtreleri (Esnek Ayarlar)
- **TREND_FILTER_ENABLED**: EMA50 trend filtresi
- **MIN_PRICE_MOVEMENT_PERCENT**: Min. %0.15 fiyat hareketi
- **RSI_FILTER_ENABLED**: RSI 25-75 arası filtre
- **SIGNAL_COOLDOWN_MINUTES**: 8 dakika sinyal soğuma
- **VOLATILITY_FILTER_ENABLED**: ATR volatilite filtresi
- **VOLUME_FILTER_ENABLED**: %110 hacim filtresi

## 🎯 Kullanım

### Multi-Coin Bot Başlatma

1. Web arayüzünde Firebase ile giriş yapın
2. "İzlenecek Coinler" alanına semboller girin: `BTC, ETH, ADA, SOL`
3. "Multi-Coin Bot Başlat" düğmesine tıklayın

### Pozisyon Yönetimi

- **Tüm Pozisyonları Tara**: Mevcut tüm pozisyonlara TP/SL ekler
- **Coin Kontrol Et**: Belirli bir coin için TP/SL kontrolü
- **TP/SL Monitor**: Otomatik izleme sistemi

### API Kullanımı

```javascript
// Bot başlatma
POST /api/multi-start
{
  "symbols": ["BTCUSDT", "ETHUSDT", "ADAUSDT"]
}

// Coin ekleme
POST /api/add-symbol
{
  "symbol": "SOLUSDT"
}

// Durum kontrolü
GET /api/multi-status
```

## 🛡️ Güvenlik Özellikleri

### Sahte Sinyal Koruması
- **Trend Filtresi**: Ana trend yönünde işlem
- **Fiyat Hareketi**: Minimum volatilite gereksinimi
- **RSI Kontrolü**: Aşırı alım/satım bölgelerini filtrele
- **Sinyal Soğuma**: Whipsaw koruması
- **Hacim Kontrolü**: Yeterli likidite gereksinimi

### Risk Yönetimi
- **Otomatik TP/SL**: Her pozisyon için otomatik koruma
- **Yetim Emir Temizliği**: Açık emirlerin otomatik iptali
- **Dinamik Pozisyon**: Bakiyeye göre otomatik boyutlandırma
- **Rate Limiting**: API limitlerini aşmama koruması

## 📱 Web Arayüzü

### Ana Özellikler
- **Gerçek Zamanlı Durum**: Canlı bot ve pozisyon bilgileri
- **Çoklu Coin İzleme**: Tüm coinlerin sinyalleri
- **Performans İstatistikleri**: Kar/zarar analizi
- **Mobil Uyumlu**: Tüm cihazlarda çalışır

### Durum İndikatörleri
- 🟢 **Yeşil**: Bot çalışıyor / Pozisyon karlı
- 🔴 **Kırmızı**: Bot durdu / Pozisyon zararlı
- 🟡 **Sarı**: Beklemede / Sinyal aranıyor
- 🔵 **Mavi**: İzleniyor / TP/SL aktif

## 🐛 Sorun Giderme

### Sık Karşılaşılan Sorunlar

**Bot pozisyon açmıyor:**
- Sahte sinyal filtrelerini kontrol edin
- Debug modu açın (`DEBUG_MODE = True`)
- Console loglarını inceleyin

**API hataları:**
- Binance API key izinlerini kontrol edin
- IP kısıtlamalarını kontrol edin
- Rate limit durumunu kontrol edin

**WebSocket bağlantı sorunları:**
- İnternet bağlantınızı kontrol edin
- Firewall ayarlarını kontrol edin
- Proxy kullanıyorsanız ayarları kontrol edin

### Debug Modu

`config.py` dosyasında `DEBUG_MODE = True` yaparak detaylı logları açabilirsiniz:

```python
DEBUG_MODE = True  # Detaylı loglar
TEST_MODE = False  # Canlı işlem yapma
```

## 📊 Log Örnekleri

### Başarılı Pozisyon Açma
```
🎯 BTCUSDT için yeni LONG pozisyonu açılıyor...
✅ Ana pozisyon başarılı: BTCUSDT BUY 0.001
✅ STOP LOSS başarılı: 43850.00
✅ TAKE PROFIT başarılı: 45150.00
✅ Pozisyon tam korumalı: Hem SL hem TP kuruldu.
```

### Sinyal Filtreleme
```
🔍 ETHUSDT Temel EMA Sinyali: LONG
🚫 ETHUSDT Trend filtresi: LONG sinyali ana trend ile uyumsuz
🛡️ ETHUSDT sinyal filtrelendi - toplam filtrelenen: 5
```

## 🔧 Özelleştirme

### Yeni Filtre Ekleme

```python
def _pass_custom_filter(self, row: pd.Series, signal: str) -> bool:
    """Özel filtre mantığınız"""
    # Kendi filtre kodunuzu buraya ekleyin
    return True
```

### Strateji Değiştirme

EMA parametrelerini değiştirmek için:

```python
trading_strategy = TradingStrategy(
    short_ema_period=9,  # Hızlı EMA
    long_ema_period=21   # Yavaş EMA
)
```

## 📄 Lisans

Bu proje MIT lisansı altında lisanslanmıştır.

## ⚠️ Uyarı

Bu bot kripto para işlemlerinde kullanılmak üzere tasarlanmıştır. Kripto para işlemleri yüksek risk içerir ve sermaye kaybına yol açabilir. Bot'u kullanmadan önce:

1. **Test ortamında** deneyin
2. **Küçük miktarlarla** başlayın  
3. **Risk yönetimi** kurallarına uyun
4. **Piyasa koşullarını** sürekli izleyin

**Finansal tavsiye değildir.** Kendi sorumluluğunuzda kullanın.

## 📞 Destek

Sorularınız için GitHub Issues bölümünü kullanabilirsiniz.
