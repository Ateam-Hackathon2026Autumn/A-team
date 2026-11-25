import { contentJson } from './publicContentApi';
import { apiFetch, clearCsrfToken } from './client';
import { toApiError } from './apiError';
import type { ConsumerAccount, ConsumerProfileInput } from '../types/consumerAccount';

export const getConsumerAccount = (signal?: AbortSignal) => contentJson<ConsumerAccount>('/api/v1/users/me', signal);

export async function updateConsumerProfile(input: ConsumerProfileInput): Promise<ConsumerAccount> {
  const response = await apiFetch('/api/v1/users/me', {
    method: 'PATCH', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  });
  if (!response.ok) throw await toApiError(response, 'プロフィールを保存できませんでした。');
  return response.json() as Promise<ConsumerAccount>;
}

export async function signOutConsumer(): Promise<void> {
  const response = await apiFetch('/api/v1/auth/signout', { method: 'POST', headers: {} });
  if (!response.ok) throw await toApiError(response, 'ログアウトできませんでした。');
  clearCsrfToken();
}
