// Service Worker for Crypto Trading Bot PWA
const CACHE_NAME = 'crypto-bot-v4.0.1';
const STATIC_CACHE = 'crypto-bot-static-v4.0.1';
const DYNAMIC_CACHE = 'crypto-bot-dynamic-v4.0.1';

// Files to cache for offline functionality
const STATIC_FILES = [
  '/',
  '/static/style.css',
  '/static/script.js',
  '/static/manifest.json',
  'https://www.gstatic.com/firebasejs/8.6.1/firebase-app.js',
  'https://www.gstatic.com/firebasejs/8.6.1/firebase-auth.js',
  'https://www.gstatic.com/firebasejs/8.6.1/firebase-database.js',
  'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700&display=swap'
];

// Network-first resources (always try network first)
const NETWORK_FIRST = [
  '/api/',
  'https://fapi.binance.com/',
  'https://testnet.binancefuture.com/',
  'https://fstream.binance.com/',
  'https://stream.binancefuture.com/'
];

// Install event - cache static files
self.addEventListener('install', (event) => {
  console.log('💾 Service Worker: Installing...');
  
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then((cache) => {
        console.log('💾 Service Worker: Caching static files...');
        return cache.addAll(STATIC_FILES);
      })
      .then(() => {
        console.log('✅ Service Worker: Installation completed');
        return self.skipWaiting(); // Activate immediately
      })
      .catch((error) => {
        console.error('❌ Service Worker: Installation failed', error);
      })
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  console.log('🔄 Service Worker: Activating...');
  
  event.waitUntil(
    caches.keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames.map((cacheName) => {
            // Delete old caches
            if (cacheName !== STATIC_CACHE && cacheName !== DYNAMIC_CACHE) {
              console.log('🗑️ Service Worker: Deleting old cache:', cacheName);
              return caches.delete(cacheName);
            }
          })
        );
      })
      .then(() => {
        console.log('✅ Service Worker: Activated');
        return self.clients.claim(); // Take control immediately
      })
  );
});

// Fetch event - handle requests
self.addEventListener('fetch', (event) => {
  const requestUrl = event.request.url;
  
  // Skip non-GET requests
  if (event.request.method !== 'GET') {
    return;
  }
  
  // Skip Chrome extensions
  if (requestUrl.startsWith('chrome-extension://')) {
    return;
  }
  
  // Network-first strategy for API calls and trading data
  if (NETWORK_FIRST.some(pattern => requestUrl.includes(pattern))) {
    event.respondWith(networkFirstStrategy(event.request));
    return;
  }
  
  // Cache-first strategy for static files
  if (STATIC_FILES.some(file => requestUrl.endsWith(file) || requestUrl.includes(file))) {
    event.respondWith(cacheFirstStrategy(event.request));
    return;
  }
  
  // Default: Network-first for everything else
  event.respondWith(networkFirstStrategy(event.request));
});

// Cache-first strategy (for static files)
async function cacheFirstStrategy(request) {
  try {
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      console.log('💾 Cache hit:', request.url);
      return cachedResponse;
    }
    
    console.log('🌐 Network fallback:', request.url);
    const networkResponse = await fetch(request);
    
    // Cache successful responses
    if (networkResponse.status === 200) {
      const cache = await caches.open(DYNAMIC_CACHE);
      cache.put(request, networkResponse.clone());
    }
    
    return networkResponse;
  } catch (error) {
    console.error('❌ Cache-first strategy failed:', error);
    
    // Return offline page or fallback
    if (request.destination === 'document') {
      return caches.match('/') || new Response('Offline - Please check your connection', {
        status: 503,
        statusText: 'Service Unavailable'
      });
    }
    
    throw error;
  }
}

// Network-first strategy (for API calls and real-time data)
async function networkFirstStrategy(request) {
  try {
    console.log('🌐 Network first:', request.url);
    const networkResponse = await fetch(request);
    
    // Cache successful responses (except API calls)
    if (networkResponse.status === 200 && !request.url.includes('/api/')) {
      const cache = await caches.open(DYNAMIC_CACHE);
      cache.put(request, networkResponse.clone());
    }
    
    return networkResponse;
  } catch (error) {
    console.error('❌ Network failed, trying cache:', request.url);
    
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      console.log('💾 Cache fallback:', request.url);
      return cachedResponse;
    }
    
    // If it's a navigation request, return the cached index
    if (request.destination === 'document') {
      const cachedIndex = await caches.match('/');
      if (cachedIndex) {
        return cachedIndex;
      }
    }
    
    throw error;
  }
}

// Background sync for failed API requests
self.addEventListener('sync', (event) => {
  console.log('🔄 Background sync:', event.tag);
  
  if (event.tag === 'trading-data-sync') {
    event.waitUntil(syncTradingData());
  }
});

// Sync trading data when connection is restored
async function syncTradingData() {
  try {
    console.log('🔄 Syncing trading data...');
    
    // Get stored requests from IndexedDB or localStorage
    const storedRequests = getStoredRequests();
    
    for (const request of storedRequests) {
      try {
        await fetch(request);
        removeStoredRequest(request);
      } catch (error) {
        console.error('❌ Failed to sync request:', request, error);
      }
    }
    
    console.log('✅ Trading data sync completed');
  } catch (error) {
    console.error('❌ Background sync failed:', error);
  }
}

// Push notifications for trading alerts
self.addEventListener('push', (event) => {
  console.log('📱 Push notification received');
  
  let options = {
    body: 'Bot durumunda değişiklik var',
    icon: '/static/icon-192.png',
    badge: '/static/icon-96.png',
    tag: 'trading-alert',
    requireInteraction: true,
    actions: [
      {
        action: 'view',
        title: 'Görüntüle',
        icon: '/static/icon-96.png'
      },
      {
        action: 'dismiss',
        title: 'Kapat'
      }
    ]
  };
  
  if (event.data) {
    const data = event.data.json();
    options.body = data.message || options.body;
    options.title = data.title || 'Crypto Bot';
  }
  
  event.waitUntil(
    self.registration.showNotification('Crypto Bot', options)
  );
});

// Handle notification clicks
self.addEventListener('notificationclick', (event) => {
  console.log('📱 Notification clicked:', event.action);
  
  event.notification.close();
  
  if (event.action === 'view' || !event.action) {
    // Open or focus the app
    event.waitUntil(
      clients.matchAll({ type: 'window', includeUncontrolled: true })
        .then((clientList) => {
          // If app is already open, focus it
          for (const client of clientList) {
            if (client.url.includes(self.registration.scope) && 'focus' in client) {
              return client.focus();
            }
          }
          
          // Otherwise open new window
          if (clients.openWindow) {
            return clients.openWindow('/');
          }
        })
    );
  }
});

// Handle notification close
self.addEventListener('notificationclose', (event) => {
  console.log('📱 Notification closed');
  
  // Track notification engagement
  // You could send this data to analytics
});

// Handle app updates
self.addEventListener('message', (event) => {
  console.log('📨 Message received:', event.data);
  
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
  
  if (event.data && event.data.type === 'GET_VERSION') {
    event.ports[0].postMessage({ version: CACHE_NAME });
  }
});

// Utility functions for offline storage
function getStoredRequests() {
  // In a real implementation, you'd use IndexedDB
  // For now, return empty array
  return [];
}

function removeStoredRequest(request) {
  // Remove request from storage
  console.log('🗑️ Removing stored request:', request);
}

// Periodic background sync (if supported)
self.addEventListener('periodicsync', (event) => {
  console.log('⏰ Periodic sync:', event.tag);
  
  if (event.tag === 'trading-update') {
    event.waitUntil(syncTradingData());
  }
});

// Handle app shortcuts
self.addEventListener('launch', (event) => {
  console.log('🚀 App launched with:', event.action);
  
  // Handle different launch actions
  switch (event.action) {
    case 'start':
      // Direct to bot start page
      break;
    case 'status':
      // Direct to status page
      break;
    case 'risk':
      // Direct to risk management
      break;
    default:
      // Default launch
      break;
  }
});

console.log('📋 Service Worker loaded successfully');
