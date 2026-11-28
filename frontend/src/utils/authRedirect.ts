// location.state は外部から渡された値として検証する。
// pathname/search/hash 形式（ルートガード）と文字列形式の両方に対応。
export function getAuthReturnPath(from: unknown): string {
  let candidate: string;
  if (typeof from === 'string') {
    candidate = from;
  } else if (from && typeof from === 'object' && 'pathname' in from) {
    const {
      pathname,
      search = '',
      hash = '',
    } = from as Record<string, unknown>;
    if (
      typeof pathname !== 'string' ||
      typeof search !== 'string' ||
      typeof hash !== 'string'
    )
      return '/';
    if (pathname.includes('?') || pathname.includes('#')) return '/';
    if ((search && !search.startsWith('?')) || (hash && !hash.startsWith('#')))
      return '/';
    candidate = pathname + search + hash;
  } else return '/';

  if (
    !candidate.startsWith('/') ||
    candidate.startsWith('//') ||
    // リダイレクト先に制御文字を許可しない
    // eslint-disable-next-line no-control-regex
    /[\\\u0000-\u0020\u007f]/.test(candidate)
  )
    return '/';
  try {
    const url = new URL(candidate, 'https://auth-return.invalid');
    const pathname = decodeURIComponent(url.pathname);
    if (
      url.origin !== 'https://auth-return.invalid' ||
      pathname.startsWith('//') ||
      // eslint-disable-next-line no-control-regex
      /[\\\u0000-\u0020\u007f]/.test(pathname)
    )
      return '/';
    if (
      /^\/(?:signin|signup)(?:\/|$)/i.test(pathname) ||
      pathname === '/admin/signin'
    )
      return '/';
    return url.pathname + url.search + url.hash;
  } catch {
    return '/';
  }
}
