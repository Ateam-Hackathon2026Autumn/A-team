import { restMocks } from './rest';
import { delayMs as defaultDelayMs } from './rest/settings';
import type { RestMock } from './types';

// 通常、編集不要
// mocks/rest/ に書かれた内容から Response を組み立てる fetch 互換の関数
// src/api/client.tsx でモック有効時に fetch の代わりに使う

// 本文を持てないステータス
const NO_BODY_STATUSES = [204, 205, 304];

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// '/api/v1/dashboard/products/:productId' のような : 付きのパスと一致するか
function matchesPattern(pattern: string, pathname: string): boolean {
  const patternSegments = pattern.split('/');
  const pathSegments = pathname.split('/');

  return (
    patternSegments.length === pathSegments.length &&
    patternSegments.every((segment, i) =>
      segment.startsWith(':')
        ? pathSegments[i] !== ''
        : segment === pathSegments[i],
    )
  );
}

// メソッドとパスが一致するモックを探す（完全一致を優先）
function findMock(method: string, pathname: string): RestMock | undefined {
  const candidates = restMocks.filter(
    (mock) => mock.method.toUpperCase() === method,
  );

  return (
    candidates.find((mock) => mock.path === pathname) ??
    candidates.find((mock) => matchesPattern(mock.path, pathname))
  );
}

function toResponse(status: number, body: unknown): Response {
  if (body === undefined || NO_BODY_STATUSES.includes(status)) {
    return new Response(null, { status });
  }

  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json; charset=UTF-8' },
  });
}

// fetch の第1引数(文字列 / URL / Request)から URL 文字列を取り出す
function toUrlString(input: RequestInfo | URL): string {
  if (typeof input === 'string') {
    return input;
  }

  if (input instanceof URL) {
    return input.href;
  }

  return input.url;
}

const mockFetch: typeof fetch = async (input, init) => {
  const method = (
    init?.method ?? (input instanceof Request ? input.method : 'GET')
  ).toUpperCase();

  // 相対URLで呼ばれても解決できるように第2引数を渡しておく
  const url = new URL(toUrlString(input), window.location.origin);
  const key = `${method} ${url.pathname}`;
  const mock = findMock(method, url.pathname);
  const delay = mock?.delayMs ?? defaultDelayMs;

  if (delay > 0) {
    await sleep(delay);
  }

  if (mock === undefined) {
    console.warn(
      `[mock] "${key}" のモックがありません。src/mocks/rest/ にファイルを追加し、rest/index.tsx に登録してください。`,
    );

    return toResponse(404, {
      errorCode: 'NOT_FOUND',
      errorMsg: `モックが未定義です(${key})`,
    });
  }

  console.info(`[mock] ${key} -> ${mock.status}`);

  return toResponse(mock.status, mock.body);
};

export { mockFetch };
