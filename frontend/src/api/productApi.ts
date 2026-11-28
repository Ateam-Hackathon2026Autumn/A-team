import { toApiError } from './apiError';
import { apiFetch, type ApiFetchOptions } from './client';
import type {
  Category,
  ProductDetail,
  ProductListResponse,
  ProductQuery,
} from '../types/publicProduct';

async function getJson<T>(
  path: string,
  signal?: AbortSignal,
  options?: ApiFetchOptions,
): Promise<T> {
  const response = await apiFetch(path, { signal }, options);
  if (!response.ok) {
    throw await toApiError(response, '商品情報の取得に失敗しました。');
  }
  return response.json() as Promise<T>;
}

// true/falseは対象商品／対象外商品、未指定は絞り込みなし。
export function getProducts(
  query: ProductQuery = {},
  signal?: AbortSignal,
  options?: ApiFetchOptions,
): Promise<ProductListResponse> {
  const params = new URLSearchParams({
    page: String(query.page ?? 1),
    pageSize: String(query.pageSize ?? 9),
    sort: query.sort ?? 'popular',
  });
  if (query.q?.trim()) params.set('q', query.q.trim());
  if (query.categoryId !== undefined)
    params.set('categoryId', String(query.categoryId));
  if (query.producerId !== undefined)
    params.set('producerId', String(query.producerId));
  if (query.price && query.price !== 'all') params.set('price', query.price);
  if (query.subscription !== undefined)
    params.set('subscription', String(query.subscription));
  if (query.preorder !== undefined)
    params.set('preorder', String(query.preorder));
  return getJson<ProductListResponse>(
    `/api/v1/products?${params}`,
    signal,
    options,
  );
}

export const getCategories = (
  signal?: AbortSignal,
  options?: ApiFetchOptions,
) => getJson<{ items: Category[] }>('/api/v1/categories', signal, options);

export const getProduct = (
  id: number,
  signal?: AbortSignal,
  options?: ApiFetchOptions,
) => getJson<ProductDetail>(`/api/v1/products/${id}`, signal, options);
