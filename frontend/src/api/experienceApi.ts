import { toApiError } from './apiError';
import { getCsrfToken } from './authApi';
import { apiFetch } from './client';
import { contentItems, contentJson, submitContent } from './publicContentApi';
import type {
  Experience,
  ExperienceDetail,
  ExperienceApplyInput,
  ExperienceReceipt,
  MyExperienceApplication,
} from '../types/experience';

export const getExperiences = (signal?: AbortSignal, query: { producerId?: number } = {}) =>
  contentItems<Experience>('/api/v1/experiences', signal, query);
export const getExperience = (id: number, signal?: AbortSignal) =>
  contentJson<ExperienceDetail>(`/api/v1/experiences/${id}`, signal);
export const applyExperience = (id: number, input: ExperienceApplyInput) =>
  submitContent<ExperienceReceipt>(`/api/v1/experiences/${id}/applications`, input);
export const getExperienceApplications = (signal?: AbortSignal) =>
  contentItems<MyExperienceApplication>('/api/v1/users/me/experience-applications', signal);

export async function cancelExperienceApplication(applicationId: number): Promise<MyExperienceApplication> {
  const csrfToken = await getCsrfToken();
  const response = await apiFetch(`/api/v1/users/me/experience-applications/${applicationId}/cancel`, {
    method: 'POST',
    headers: { 'X-CSRFToken': csrfToken },
  });
  if (!response.ok) {
    throw await toApiError(response, '予約をキャンセルできませんでした。');
  }
  return (await response.json()) as MyExperienceApplication;
}

