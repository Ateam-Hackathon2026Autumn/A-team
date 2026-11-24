export function safeCheckoutUrl(value: string, origin: string): string | null {
  try {
    const base = new URL(origin);
    const url = new URL(value, base);
    if (url.username || url.password) return null;
    if (url.origin === base.origin && (url.protocol === 'http:' || url.protocol === 'https:')) return url.href;
    if (url.protocol === 'https:' && url.hostname === 'checkout.stripe.com' && !url.port) return url.href;
  } catch { /* Invalid destination. */ }
  return null;
}
