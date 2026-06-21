/**
 * CYBER SHATS V1.3 — Web Push Notifications (frontend)
 *
 * Foydalanuvchi ovozli bildirishnomalarni yoqqanda (yoki alohida ruxsat berganda),
 * brauzer push obunasi yaratiladi. Bu orqali SAYTDAN CHIQIB KETGAN BO'LSA HAM
 * (brauzer yopiq, lekin qurilma yoqilgan va internetda) bildirishnoma keladi.
 *
 * Talab: HTTPS (yoki localhost). Productionda SSL sertifikat shart.
 * iOS Safari: faqat 16.4+ va "Home Screen"ga qo'shilgan holatda ishlaydi.
 */
(function() {
    'use strict';

    function isLoggedIn() {
        return document.body.classList.contains('has-sidebar') ||
               document.querySelector('[data-current-user]') !== null;
    }
    if (!isLoggedIn()) return;
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
        console.log('[CyberShats] Bu brauzer Web Push qo\'llab-quvvatlamaydi.');
        return;
    }

    function urlBase64ToUint8Array(base64String) {
        var padding = '='.repeat((4 - base64String.length % 4) % 4);
        var base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
        var rawData = window.atob(base64);
        var outputArray = new Uint8Array(rawData.length);
        for (var i = 0; i < rawData.length; ++i) {
            outputArray[i] = rawData.charCodeAt(i);
        }
        return outputArray;
    }

    var swRegistration = null;

    function registerServiceWorker() {
        return navigator.serviceWorker.register('/sw.js', { scope: '/' })
            .then(function(reg) {
                swRegistration = reg;
                return reg;
            })
            .catch(function(err) {
                console.error('[CyberShats] Service Worker ro\'yxatdan o\'tmadi:', err);
                return null;
            });
    }

    function getVapidKey() {
        return fetch('/api/push/vapid-public-key', { credentials: 'same-origin' })
            .then(function(r) { return r.json(); })
            .then(function(d) {
                if (d.success && d.data.configured) return d.data.publicKey;
                return null;
            })
            .catch(function() { return null; });
    }

    function subscribeToPush() {
        if (!swRegistration) return Promise.resolve(false);
        return getVapidKey().then(function(vapidKey) {
            if (!vapidKey) {
                console.log('[CyberShats] Push sozlanmagan (VAPID kalit yo\'q).');
                return false;
            }
            return swRegistration.pushManager.getSubscription().then(function(existingSub) {
                if (existingSub) return sendSubscriptionToServer(existingSub);
                return swRegistration.pushManager.subscribe({
                    userVisibleOnly: true,
                    applicationServerKey: urlBase64ToUint8Array(vapidKey)
                }).then(function(sub) {
                    return sendSubscriptionToServer(sub);
                }).catch(function(err) {
                    console.warn('[CyberShats] Push obuna xatosi:', err);
                    return false;
                });
            });
        });
    }

    function sendSubscriptionToServer(subscription) {
        var subJson = subscription.toJSON();
        return fetch('/api/push/subscribe', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'same-origin',
            body: JSON.stringify(subJson)
        }).then(function(r) { return r.json(); })
          .then(function(d) { return d.success === true; })
          .catch(function() { return false; });
    }

    function unsubscribeFromPush() {
        if (!swRegistration) return Promise.resolve();
        return swRegistration.pushManager.getSubscription().then(function(sub) {
            if (!sub) return;
            var endpoint = sub.endpoint;
            return sub.unsubscribe().then(function() {
                return fetch('/api/push/unsubscribe', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    credentials: 'same-origin',
                    body: JSON.stringify({ endpoint: endpoint })
                });
            });
        });
    }

    // Global funksiyalar — voice-notifications.js shu yerdan chaqiradi
    window.CyberShatsPush = {
        init: function() {
            return registerServiceWorker();
        },
        subscribe: function() {
            if (Notification.permission === 'granted') {
                return subscribeToPush();
            }
            if (Notification.permission === 'denied') {
                console.log('[CyberShats] Push bildirishnomalar brauzerda bloklangan.');
                return Promise.resolve(false);
            }
            return Notification.requestPermission().then(function(perm) {
                if (perm === 'granted') return subscribeToPush();
                return false;
            });
        },
        unsubscribe: unsubscribeFromPush,
        isSupported: true,
    };

    // Sahifa yuklanganda Service Worker'ni ro'yxatdan o'tkazamiz (push so'ramasdan)
    registerServiceWorker();
})();
