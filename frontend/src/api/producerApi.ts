import { contentItems, contentJson } from './publicContentApi';
import type { ProducerSummary, ProducerProfile } from '../types/producer';

export const getProducers = (signal?: AbortSignal) => contentItems<ProducerSummary>('/api/v1/producers', signal);
export const getProducer = (id: number, signal?: AbortSignal) => contentJson<ProducerProfile>(`/api/v1/producers/${id}`, signal);
