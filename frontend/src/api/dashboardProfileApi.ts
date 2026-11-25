import type { DashboardProfile, ProfileUpdateInput } from '../types/dashboardProfile';
import { toApiError } from './apiError';
import { apiFetch } from './client';

// 生産者プロフィールの取得・更新
// 実API: backend/api/views/dashboard/profile.py（ETag・If-Match は使わない）

// 本人のプロフィールを取得（掲載停止中でも取得できる）
async function getDashboardProfile(signal?: AbortSignal): Promise<DashboardProfile> {
  const response = await apiFetch('/api/v1/dashboard/profile', { signal });

  if (response.ok) {
    return (await response.json()) as DashboardProfile;
  }

  throw await toApiError(response, 'プロフィールを取得できませんでした。');
}

// 送った項目だけ更新し、更新後のプロフィールを返す
// 400: 項目ごとの入力エラー（空のオブジェクト・未知の項目も 400）
// 409: PRODUCER_SUSPENDED（掲載停止中に publishStatus を送った）
async function updateDashboardProfile(input: ProfileUpdateInput): Promise<DashboardProfile> {
  const response = await apiFetch('/api/v1/dashboard/profile', {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  });

  if (response.ok) {
    return (await response.json()) as DashboardProfile;
  }

  throw await toApiError(response, 'プロフィールを保存できませんでした。');
}

export { getDashboardProfile, updateDashboardProfile };
