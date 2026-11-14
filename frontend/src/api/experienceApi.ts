import { contentItems, contentJson, submitContent } from './publicContentApi';
import type { Experience, ExperienceDetail, ExperienceApplyInput, ExperienceReceipt } from '../types/experience';
export const getExperiences = (signal?: AbortSignal) => contentItems<Experience>('/api/v1/experiences', signal);
export const getExperience = (id: number, signal?: AbortSignal) => contentJson<ExperienceDetail>(`/api/v1/experiences/${id}`, signal);
export const applyExperience = (id: number, input: ExperienceApplyInput) => submitContent<ExperienceReceipt>(`/api/v1/experiences/${id}/applications`, input);
