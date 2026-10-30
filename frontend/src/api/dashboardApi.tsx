import type { DashboardSummary } from '../types/dashboard';
import ApiError from './apiError';
import { apiFetch } from './client';

// ダッシュボード上部の集計（公開中の件数・申込/応募件数・売上）を取得
async function getDashboardSummary(): Promise<DashboardSummary> {
  const response = await apiFetch('/api/v1/dashboard/summary');

  if (response.ok) {
    return (await response.json()) as DashboardSummary;
  }

  throw new ApiError(response.status, 'ダッシュボードの集計を取得できませんでした');
}

export { getDashboardSummary };
