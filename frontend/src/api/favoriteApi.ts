import type { PageResult } from '../types/experience';
import type { FavoriteProducerItem, FavoriteProductItem } from '../types/favorite';
import { toApiError } from './apiError';
import { apiFetch } from './client';
import { contentJson } from './publicContentApi';

export function getFavoriteProducts(
  query: { page?: number; pageSize?: number } = {},
  signal?: AbortSignal,
): Promise<PageResult<FavoriteProductItem>> {
  const params = new URLSearchParams({
    type: 'product',
    page: String(query.page ?? 1),
    pageSize: String(query.pageSize ?? 20),
  });
  return contentJson<PageResult<FavoriteProductItem>>(`/api/v1/users/me/favorites?${params}`, signal);
}

export function getFavoriteProducers(
  query: { page?: number; pageSize?: number } = {},
  signal?: AbortSignal,
): Promise<PageResult<FavoriteProducerItem>> {
  const params = new URLSearchParams({
    type: 'producer',
    page: String(query.page ?? 1),
    pageSize: String(query.pageSize ?? 20),
  });
  return contentJson<PageResult<FavoriteProducerItem>>(`/api/v1/users/me/favorites?${params}`, signal);
}

export async function addFavoriteProduct(productId: number): Promise<void> {
  const response = await apiFetch(`/api/v1/users/me/favorites/products/${productId}`, {
    method: 'PUT',
  });
  if (!response.ok) {
    throw await toApiError(response, '商品をお気に入りに登録できませんでした。');
  }
}

export async function removeFavoriteProduct(productId: number): Promise<void> {
  const response = await apiFetch(`/api/v1/users/me/favorites/products/${productId}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    throw await toApiError(response, '商品のお気に入りを解除できませんでした。');
  }
}

export async function addFavoriteProducer(
  producerId: number,
  options?: { notify?: boolean },
): Promise<void> {
  const hasNotify = options?.notify !== undefined;
  const response = await apiFetch(`/api/v1/users/me/favorites/producers/${producerId}`, {
    method: 'PUT',
    headers: hasNotify
      ? { 'Content-Type': 'application/json' }
      : undefined,
    body: hasNotify ? JSON.stringify({ notify: options.notify }) : undefined,
  });
  if (!response.ok) {
    throw await toApiError(response, '生産者をお気に入りに登録できませんでした。');
  }
}

export async function removeFavoriteProducer(producerId: number): Promise<void> {
  const response = await apiFetch(`/api/v1/users/me/favorites/producers/${producerId}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    throw await toApiError(response, '生産者のお気に入りを解除できませんでした。');
  }
}
