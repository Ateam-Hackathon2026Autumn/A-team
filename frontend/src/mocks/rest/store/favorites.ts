import type {
  FavoriteProducerItem,
  FavoriteProductItem,
} from '../../../types/favorite';
import type { ProducerSummary } from '../../../types/producer';
import { hoursFromNow } from '../../helpers';
import type { MockResult } from '../../types';
import { producersList } from '../endpoint/get_api_v1_producers';
import { productSamples } from '../endpoint/get_api_v1_products';
import {
  idFromPath,
  isObject,
  loadState,
  notFound,
  nowIso,
  paginate,
  readJsonBody,
  saveState,
  validationError,
} from './common';

const PRODUCTS_KEY = 'mock:favoriteProducts:v1';
const PRODUCERS_KEY = 'mock:favoriteProducers:v1';

type StoredProductFav = { productId: number; favoritedAt: string };
type StoredProducerFav = {
  producerId: number;
  notify: boolean;
  favoritedAt: string;
};

const initialProductFavs = (): StoredProductFav[] => [
  { productId: 4, favoritedAt: hoursFromNow(-24 * 2) },
  { productId: 5, favoritedAt: hoursFromNow(-24 * 5) },
];

const initialProducerFavs = (): StoredProducerFav[] => [
  { producerId: 2, notify: true, favoritedAt: hoursFromNow(-24 * 3) },
  { producerId: 5, notify: false, favoritedAt: hoursFromNow(-24 * 8) },
];

function isProductFavList(val: unknown): val is StoredProductFav[] {
  return (
    Array.isArray(val) &&
    val.every(
      (item) =>
        isObject(item) &&
        typeof item.productId === 'number' &&
        typeof item.favoritedAt === 'string',
    )
  );
}

function isProducerFavList(val: unknown): val is StoredProducerFav[] {
  return (
    Array.isArray(val) &&
    val.every(
      (item) =>
        isObject(item) &&
        typeof item.producerId === 'number' &&
        typeof item.notify === 'boolean' &&
        typeof item.favoritedAt === 'string',
    )
  );
}

let productFavs: StoredProductFav[] =
  loadState(PRODUCTS_KEY, isProductFavList) ?? initialProductFavs();
let producerFavs: StoredProducerFav[] =
  loadState(PRODUCERS_KEY, isProducerFavList) ?? initialProducerFavs();

const allProducers = () =>
  (producersList.body as { items: ProducerSummary[] }).items;

export function isProductFavorited(productId: number): boolean {
  return productFavs.some((f) => f.productId === productId);
}

export function isProducerFavorited(producerId: number): boolean {
  return producerFavs.some((f) => f.producerId === producerId);
}

export function getFavoritesMock(url: URL): MockResult {
  const type = url.searchParams.get('type');
  for (const key of url.searchParams.keys()) {
    if (!['type', 'page', 'pageSize'].includes(key)) {
      return validationError({ [key]: ['この項目は受け付けていません。'] });
    }
  }
  if (type !== 'product' && type !== 'producer') {
    return validationError({
      type: ['type は product または producer を指定してください。'],
    });
  }

  if (type === 'product') {
    const items: FavoriteProductItem[] = productFavs.flatMap((fav) => {
      const product = productSamples.find((p) => p.id === fav.productId);
      if (!product) return [];
      return [
        {
          product: { ...product, isFavorited: true },
          isPublic: true,
          favoritedAt: fav.favoritedAt,
        },
      ];
    });
    const page = paginate(items, url);
    return page === null
      ? validationError({ page: ['ページ番号を確認してください。'] })
      : { status: 200, body: page };
  }

  const producers = allProducers();
  const items: FavoriteProducerItem[] = producerFavs.flatMap((fav) => {
    const producer = producers.find((p) => p.id === fav.producerId);
    if (!producer) return [];
    return [
      {
        producer: {
          ...producer,
          hasPublicStory: [1, 2, 3].includes(producer.id),
          isFavorited: true,
        },
        isPublic: true,
        notify: fav.notify,
        favoritedAt: fav.favoritedAt,
      },
    ];
  });
  const page = paginate(items, url);
  return page === null
    ? validationError({ page: ['ページ番号を確認してください。'] })
    : { status: 200, body: page };
}

export function putFavoriteProductMock(
  url: URL,
  init?: RequestInit,
): MockResult {
  if (
    init?.body !== undefined &&
    init?.body !== null &&
    String(init.body).trim() !== '' &&
    String(init.body).trim() !== '{}'
  ) {
    return validationError({
      nonFieldErrors: ['リクエスト本文は受け付けていません。'],
    });
  }
  const productId = idFromPath(url, 0);
  const product = productSamples.find((p) => p.id === productId);
  if (!product) {
    return notFound('商品が見つかりません。');
  }
  if (!isProductFavorited(productId)) {
    productFavs = [{ productId, favoritedAt: nowIso() }, ...productFavs];
    saveState(PRODUCTS_KEY, productFavs);
  }
  return { status: 204 };
}

export function deleteFavoriteProductMock(url: URL): MockResult {
  const productId = idFromPath(url, 0);
  if (!Number.isNaN(productId)) {
    productFavs = productFavs.filter((f) => f.productId !== productId);
    saveState(PRODUCTS_KEY, productFavs);
  }
  return { status: 204 };
}

export function putFavoriteProducerMock(
  url: URL,
  init?: RequestInit,
): MockResult {
  const producerId = idFromPath(url, 0);
  const producer = allProducers().find((p) => p.id === producerId);
  if (!producer) {
    return notFound('生産者が見つかりません。');
  }

  let notify: boolean | undefined;
  if (
    init?.body !== undefined &&
    init?.body !== null &&
    String(init.body).trim() !== ''
  ) {
    const body = readJsonBody(init);
    if (!isObject(body)) {
      return validationError({ nonFieldErrors: ['無効なデータです。'] });
    }
    for (const key of Object.keys(body)) {
      if (key !== 'notify') {
        return validationError({ [key]: ['この項目は受け付けていません。'] });
      }
    }
    if ('notify' in body) {
      if (typeof body.notify !== 'boolean') {
        return validationError({
          notify: ['有効な真偽値を入力してください。'],
        });
      }
      notify = body.notify;
    }
  }

  const existing = producerFavs.find((f) => f.producerId === producerId);
  if (!existing) {
    producerFavs = [
      { producerId, notify: Boolean(notify), favoritedAt: nowIso() },
      ...producerFavs,
    ];
  } else if (notify !== undefined) {
    producerFavs = producerFavs.map((f) =>
      f.producerId === producerId ? { ...f, notify: Boolean(notify) } : f,
    );
  }
  saveState(PRODUCERS_KEY, producerFavs);
  return { status: 204 };
}

export function deleteFavoriteProducerMock(url: URL): MockResult {
  const producerId = idFromPath(url, 0);
  if (!Number.isNaN(producerId)) {
    producerFavs = producerFavs.filter((f) => f.producerId !== producerId);
    saveState(PRODUCERS_KEY, producerFavs);
  }
  return { status: 204 };
}
