import { contentItems, contentJson } from './publicContentApi';
import type { ApiFetchOptions } from './client';
import type { ProducerSummary, ProducerProfile } from '../types/producer';

// featured=true で注目生産者（featured_score > 0）だけを、featured_score の高い順に取得する。badges では判定しない。
export const getProducers = (signal?: AbortSignal, query: { featured?: boolean } = {}, options?: ApiFetchOptions) =>
  contentItems<ProducerSummary>('/api/v1/producers', signal, query.featured ? { featured: 'true', sort: 'featured' } : {}, options);
export const getProducer = (id: number, signal?: AbortSignal) => contentJson<ProducerProfile>(`/api/v1/producers/${id}`, signal);
