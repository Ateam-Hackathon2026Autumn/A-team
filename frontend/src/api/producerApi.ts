import { contentItems } from './publicContentApi';
import type { ProducerSummary } from '../types/producer';

export const getProducers = (signal?: AbortSignal) => contentItems<ProducerSummary>('/api/v1/producers', signal);
