"use strict";
const SHELL_CACHE = "alertachuva-shell-v1";
const SHELL = ["/", "/app.js", "/styles.css", "/icon.svg", "/icon-180.png", "/icon-192.png", "/icon-512.png", "/manifest.webmanifest"];
self.addEventListener("install", (event) => { event.waitUntil(caches.open(SHELL_CACHE).then((cache) => cache.addAll(SHELL)).then(() => self.skipWaiting())); });
self.addEventListener("activate", (event) => { event.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((key) => key.startsWith("alertachuva-shell-") && key !== SHELL_CACHE).map((key) => caches.delete(key)))).then(() => self.clients.claim())); });
self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  // Never reuse forecasts or subscriptions offline.
  if (event.request.method !== "GET" || url.origin !== self.location.origin || !SHELL.includes(url.pathname)) return;
  event.respondWith(fetch(event.request).catch(() => caches.match(url.pathname)));
});
self.addEventListener("push", (event) => {
  let payload;
  try { payload = event.data.json(); } catch { return; }
  const expires = Date.parse(payload.expires_at_utc);
  if (!Number.isFinite(expires) || expires <= Date.now() || typeof payload.body !== "string" || typeof payload.event_id !== "string") return;
  event.waitUntil(self.registration.showNotification("AlertaChuva Recife", {body: payload.body, icon: "/icon-192.png", tag: `rain-${payload.event_id}`, data: {url: "/", expires_at_utc: payload.expires_at_utc}}));
});
self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  event.waitUntil(self.clients.matchAll({type: "window", includeUncontrolled: true}).then(async (windows) => {
    const existing = windows.find((client) => new URL(client.url).origin === self.location.origin && new URL(client.url).pathname === "/");
    if (existing) { await existing.focus(); return; }
    await self.clients.openWindow("/");
  }));
});
