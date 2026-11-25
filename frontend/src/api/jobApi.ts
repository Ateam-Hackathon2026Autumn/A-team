import { contentItems, contentJson, submitContent } from './publicContentApi';
import type { Job, JobDetail, JobApplication, JobInput, JobReceipt } from '../types/job';
import ApiError from './apiError';
export const getJobs = (signal?: AbortSignal, query: { producerId?: number } = {}) => contentItems<Job>('/api/v1/jobs', signal, query);
export const getJob = (id: number, signal?: AbortSignal) => contentJson<JobDetail>(`/api/v1/jobs/${id}`, signal);
export const getJobApplications = (signal?: AbortSignal) => contentItems<JobApplication>('/api/v1/users/me/job-applications', signal);
export async function applyJob(id: number, input: JobInput): Promise<JobReceipt> {
  const result = await submitContent<unknown>(`/api/v1/jobs/${id}/applications`, {
    workDateIds: input.workDateIds, message: input.message, answers: input.answers,
    requirementsConfirmed: input.requirementsConfirmed,
  }, 201);
  if (!result || typeof result !== 'object' || !('id' in result) || typeof result.id !== 'number'
      || !Number.isSafeInteger(result.id) || result.id < 1 || !('status' in result) || result.status !== 'applied') {
    throw new ApiError(201, '応募結果を確認できませんでした。再送する前にマイページの応募状況を確認してください。');
  }
  return result as JobReceipt;
}
