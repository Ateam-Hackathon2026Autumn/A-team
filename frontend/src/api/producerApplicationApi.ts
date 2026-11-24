import type {
  MyProducerApplication,
  ProducerApplicationAccepted,
  ProducerApplicationInput,
  ProducerApplicationResubmitInput,
} from '../types/producerApplication';
import { toApiError } from './apiError';
import { getCsrfToken } from './authApi';
import { apiFetch } from './client';

export async function getMyProducerApplication(signal?: AbortSignal): Promise<MyProducerApplication> {
  const response = await apiFetch('/api/v1/producer-applications/me', { signal });
  if (response.ok) {
    return (await response.json()) as MyProducerApplication;
  }
  throw await toApiError(response, '生産者登録申請の状況を取得できませんでした。');
}

export async function createProducerApplication(
  input: ProducerApplicationInput,
): Promise<ProducerApplicationAccepted> {
  const csrfToken = await getCsrfToken();
  const response = await apiFetch('/api/v1/producer-applications', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
    body: JSON.stringify(input),
  });
  if (response.ok) {
    return (await response.json()) as ProducerApplicationAccepted;
  }
  throw await toApiError(response, '生産者登録申請を送信できませんでした。');
}

export async function resubmitProducerApplication(
  input: ProducerApplicationResubmitInput,
): Promise<ProducerApplicationAccepted> {
  const csrfToken = await getCsrfToken();
  const response = await apiFetch('/api/v1/producer-applications/me', {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
    body: JSON.stringify(input),
  });
  if (response.ok) {
    return (await response.json()) as ProducerApplicationAccepted;
  }
  throw await toApiError(response, '申請内容を再送信できませんでした。');
}
