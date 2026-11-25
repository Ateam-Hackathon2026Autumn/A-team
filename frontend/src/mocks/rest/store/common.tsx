import type { MockResult } from '../../types';

// ダッシュボードのモックストア（store/*.tsx）で共通に使う処理
//
// 登録・更新・削除の結果を一覧・詳細に反映するため、データをメモリーに持ち、
// 同じタブのセッション（sessionStorage）にも保存する（再読み込みしても消えない。タブを閉じると初期状態に戻る）

// sessionStorage から復元する。保存がない・壊れている・形が違う場合は null
function loadState<T>(key: string, isValid: (value: unknown) => value is T): T | null {
  try {
    const saved: unknown = JSON.parse(window.sessionStorage.getItem(key) ?? 'null');

    return isValid(saved) ? saved : null;
  } catch {
    // 保存領域を使えない・壊れている場合は初期データで動かす
    return null;
  }
}

function saveState(key: string, state: unknown): void {
  try {
    window.sessionStorage.setItem(key, JSON.stringify(state));
  } catch {
    // 保存に失敗しても、メモリー上のデータで操作は続けられる
  }
}

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

// リクエスト本文（JSON）を読む。読めない場合は undefined
function readJsonBody(init?: RequestInit): unknown {
  if (typeof init?.body !== 'string') {
    return undefined;
  }

  try {
    return JSON.parse(init.body) as unknown;
  } catch {
    return undefined;
  }
}

function readHeader(init: RequestInit | undefined, name: string): string | null {
  return new Headers(init?.headers).get(name);
}

// If-Match が送られていて、現在の ETag と違う場合は true（412 を返す）
// ※ 送られていない場合は通す（モックでは必須にしない）
function isStale(init: RequestInit | undefined, currentEtag: string): boolean {
  const ifMatch = readHeader(init, 'If-Match');

  return ifMatch !== null && ifMatch !== currentEtag;
}

// '"product-3-v2"' → '"product-3-v3"'（末尾の版数を1つ上げる）
function nextEtag(prefix: string, id: number, etag?: string): string {
  const version = Number(/-v(\d+)"$/.exec(etag ?? '')?.[1] ?? 0);

  return `"${prefix}-${id}-v${version + 1}"`;
}

// パスの末尾から数えて indexFromEnd 番目（0 が末尾）の ID。数字でなければ NaN
function idFromPath(url: URL, indexFromEnd = 0): number {
  const segments = url.pathname.split('/');
  const value = segments[segments.length - 1 - indexFromEnd] ?? '';

  return /^[1-9][0-9]*$/.test(value) ? Number(value) : Number.NaN;
}

function nextId(items: { id: number }[]): number {
  return Math.max(0, ...items.map((item) => item.id)) + 1;
}

function nowIso(): string {
  return new Date().toISOString();
}

type Page<T> = {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
};

// ?page=&pageSize= を読んで切り出す。不正な値は null（400 を返す）
function paginate<T>(items: T[], url: URL, defaultPageSize = 20): Page<T> | null {
  const page = Number(url.searchParams.get('page') ?? 1);
  const pageSize = Number(url.searchParams.get('pageSize') ?? defaultPageSize);

  if (
    !Number.isSafeInteger(page) ||
    page < 1 ||
    !Number.isInteger(pageSize) ||
    pageSize < 1 ||
    pageSize > 100
  ) {
    return null;
  }

  return {
    items: items.slice((page - 1) * pageSize, page * pageSize),
    total: items.length,
    page,
    pageSize,
    totalPages: Math.ceil(items.length / pageSize),
  };
}

// ---------------------------------------------------------------------------
// エラー応答
// ---------------------------------------------------------------------------

function validationError(details: Record<string, string[]> = {}): MockResult {
  return {
    status: 400,
    body: { errorCode: 'VALIDATION_ERROR', errorMsg: '入力内容に誤りがあります。', details },
  };
}

function notFound(errorMsg: string): MockResult {
  return { status: 404, body: { errorCode: 'NOT_FOUND', errorMsg } };
}

function conflict(errorCode: string, errorMsg: string): MockResult {
  return { status: 409, body: { errorCode, errorMsg } };
}

function preconditionFailed(): MockResult {
  return {
    status: 412,
    body: {
      errorCode: 'PRECONDITION_FAILED',
      errorMsg: '他の操作で更新されています。再読み込みしてください。',
    },
  };
}

// ---------------------------------------------------------------------------
// アップロード画像
// ---------------------------------------------------------------------------

// 画像アップロードAPIのモックが返したキーと表示用URLの対応
// 商品・体験の登録・更新で imageKeys / images[].imageKey から URL を引くのに使う
const uploadedImageUrls = new Map<string, string>();

function registerUploadedImage(key: string, url: string): void {
  uploadedImageUrls.set(key, url);
}

// キーから表示用URLを引く（不明なキーでも表示できるよう、キーから画像URLを作る）
function imageUrlFor(key: string): string {
  return (
    uploadedImageUrls.get(key) ??
    `https://picsum.photos/seed/${encodeURIComponent(key)}/800/600`
  );
}

export {
  conflict,
  idFromPath,
  imageUrlFor,
  isObject,
  isStale,
  loadState,
  nextEtag,
  nextId,
  notFound,
  nowIso,
  paginate,
  preconditionFailed,
  readHeader,
  readJsonBody,
  registerUploadedImage,
  saveState,
  validationError,
};
export type { Page };
