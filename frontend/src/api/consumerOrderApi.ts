import { contentItems, contentJson } from './publicContentApi';
import { apiFetch } from './client';
import { toApiError } from './apiError';
import { getCsrfToken } from './authApi';
import { USE_MOCK } from '../config/env';
import type { OrderSummary, OrderDetail, OrderInput, OrderReceipt } from '../types/consumerOrder';

export const getConsumerOrders = (signal?: AbortSignal) => contentItems<OrderSummary>('/api/v1/users/me/orders', signal);
export const getConsumerOrder = (id: number, signal?: AbortSignal) => contentJson<OrderDetail>(`/api/v1/users/me/orders/${id}`, signal);

export async function createConsumerOrder(input: OrderInput, key: string): Promise<OrderReceipt> {
  // 現行カートAPIには配送先別の正式見積りがない。確認金額を保証できるモックのみ送信する。
  if (!USE_MOCK) throw new Error('送料見積りの接続準備中のため、現在は注文できません。');
  const response = await apiFetch('/api/v1/orders', {
    method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': await getCsrfToken(), 'Idempotency-Key': key },
    body: JSON.stringify(input),
  });
  if (!response.ok) throw await toApiError(response, '注文を受け付けられませんでした。カートをご確認ください。');
  return response.json() as Promise<OrderReceipt>;
}
