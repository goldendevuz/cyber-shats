/**
 * CYBER SHATS V1.3 — Service Worker
 * Saytdan chiqib ketgan foydalanuvchiga ham bildirishnoma kelishi uchun.
 * Bu fayl ROOT papkada bo'lishi shart (/sw.js), chunki Service Worker scope
 * shu joylashuvga bog'liq.
 */

const CACHE_NAME = 'cyber-shats-v1';

self.addEventListener('install', function(event) {
    self.skipWaiting();
});

self.addEventListener('activate', function(event) {
    event.waitUntil(self.clients.claim());
});

// Push xabar kelganda — bildirishnoma ko'rsatish
self.addEventListener('push', function(event) {
    if (!event.data) return;

    var data;
    try {
        data = event.data.json();
    } catch (e) {
        data = { title: 'CYBER SHATS', body: event.data.text() };
    }

    var title = data.title || 'CYBER SHATS';
    var options = {
        body: data.body || '',
        icon: data.icon || '/static/img/icon-192.png',
        badge: '/static/img/icon-192.png',
        data: { url: data.url || '/' },
        vibrate: [200, 100, 200],
        tag: 'cyber-shats-notif',
        renotify: true,
        requireInteraction: false,
    };

    event.waitUntil(self.registration.showNotification(title, options));
});

// Bildirishnomaga bosilganda — saytni ochish/fokuslash
self.addEventListener('notificationclick', function(event) {
    event.notification.close();
    var targetUrl = (event.notification.data && event.notification.data.url) || '/';

    event.waitUntil(
        self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function(clientList) {
            for (var i = 0; i < clientList.length; i++) {
                var client = clientList[i];
                if (client.url.indexOf(self.registration.scope) === 0 && 'focus' in client) {
                    client.navigate(targetUrl);
                    return client.focus();
                }
            }
            if (self.clients.openWindow) {
                return self.clients.openWindow(targetUrl);
            }
        })
    );
});
