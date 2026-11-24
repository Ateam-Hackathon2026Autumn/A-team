import { contentItems, contentJson } from './publicContentApi';
import ApiError, { toApiError } from './apiError';
import { getCsrfToken } from './authApi';
import { apiFetch } from './client';
import type { Experience, ExperienceDetail, ExperienceApplyInput, ExperienceReceipt } from '../types/experience';
export const getExperiences = (signal?: AbortSignal, query: { producerId?: number } = {}) => contentItems<Experience>('/api/v1/experiences', signal, query);
export const getExperience = (id: number, signal?: AbortSignal) => contentJson<ExperienceDetail>(`/api/v1/experiences/${id}`, signal);

export async function applyExperience(id: number, input: ExperienceApplyInput): Promise<ExperienceReceipt> {
  // API が受け付ける項目だけを送る。確認画面の金額はここで再計算しない。
  const body = JSON.stringify({
    slotId: input.slotId, adultCount: input.adultCount, childCount: input.childCount,
    infantCount: input.infantCount, lastName: input.lastName, firstName: input.firstName,
    phone: input.phone, message: input.message, agreedToCancelPolicy: input.agreedToCancelPolicy,
    eligibilityConfirmed: input.eligibilityConfirmed, expectedTotalAmount: input.expectedTotalAmount,
  });
  const send = (token: string) => apiFetch(`/api/v1/experiences/${id}/applications`, {
    method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': token }, body,
  });
  let response = await send(await getCsrfToken());
  if (!response.ok) {
    const error = await toApiError(response, '申込できませんでした。内容を確認して再度お試しください。');
    if (error.status !== 403 || error.errorCode !== 'CSRF_FAILED') throw error;
    // CSRF で拒否された POST に限り1回再送する。通信断や業務エラーは再送しない。
    response = await send(await getCsrfToken());
  }
  if (!response.ok) throw await toApiError(response, '申込できませんでした。内容を確認して再度お試しください。');
  const invalidReceipt = () => new ApiError(response.status, '申込結果を確認できませんでした。再送する前にマイページの申込状況を確認してください。');
  let result: unknown;
  try { result = await response.json(); } catch { throw invalidReceipt(); }
  if (response.status !== 201 || !result || typeof result !== 'object'
      || !('status' in result) || result.status !== 'confirmed'
      || !('reservationNo' in result) || typeof result.reservationNo !== 'string' || !result.reservationNo
      || !('totalAmount' in result) || typeof result.totalAmount !== 'number'
      || !Number.isSafeInteger(result.totalAmount) || result.totalAmount < 0) {
    throw invalidReceipt();
  }
  return result as ExperienceReceipt;
}
