import { contentItems, contentJson, submitContent } from './publicContentApi';
import type { Job, JobDetail, JobApplication, JobInput } from '../types/job';
export const getJobs = (signal?: AbortSignal) => contentItems<Job>('/api/v1/jobs', signal);
export const getJob = (id: number, signal?: AbortSignal) => contentJson<JobDetail>(`/api/v1/jobs/${id}`, signal);
export const getJobApplications = (signal?: AbortSignal) => contentItems<JobApplication>('/api/v1/users/me/job-applications', signal);
export const applyJob = (id: number, input: JobInput) => submitContent<{ id: number }>(`/api/v1/jobs/${id}/applications`, input);
