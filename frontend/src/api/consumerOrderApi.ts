import { contentJson } from './publicContentApi';
import { apiFetch } from './client';
import { toApiError } from './apiError';
import { getCsrfToken } from './authApi';
import type { OrderSummary, OrderDetail, OrderInput, OrderReceipt, OrderQuery } from '../types/consumerOrder';
import type { PageResult } from '../types/experience';

export function getConsumerOrders(query: OrderQuery = {}, signal?: AbortSignal) {
  const params = new URLSearchParams({ page: String(query.page ?? 1), pageSize: '20' });
  if (query.paymentStatus) params.set('paymentStatus', query.paymentStatus);
  return contentJson<PageResult<OrderSummary>>(`/api/v1/users/me/orders?${params}`, signal);
}
export const getConsumerOrder = (id: number, signal?: AbortSignal) => contentJson<OrderDetail>(`/api/v1/users/me/orders/${id}`, signal);

export async function createConsumerOrder(input: OrderInput, key: string): Promise<OrderReceipt> {
  const response = await apiFetch('/api/v1/orders', {
    method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': await getCsrfToken(), 'Idempotency-Key': key },
    // StrictSerializerが受け付ける項目のみ送る。
    body: JSON.stringify({
      ...(input.shippingAddress ? { shippingAddress: input.shippingAddress } : { addressId: input.addressId }),
      paymentMethod: input.paymentMethod,
      expectedGrandTotal: input.expectedGrandTotal,
    }),
  });
  if (!response.ok) throw await toApiError(response, '注文を受け付けられませんでした。カートをご確認ください。');
  return response.json() as Promise<OrderReceipt>;
}
