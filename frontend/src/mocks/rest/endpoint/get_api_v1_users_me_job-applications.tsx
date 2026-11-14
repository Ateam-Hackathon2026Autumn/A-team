import type { RestMock } from '../../types';
import { getAllJobApplications, initialJobApplications } from '../../demoJobApplications';

// 初期データと追加応募の共通ストアを参照する。再読み込みすると初期状態へ戻る。
const myJobApplications: RestMock = {
  method: 'GET', path: '/api/v1/users/me/job-applications', status: 200,
  body: { items: initialJobApplications, total: initialJobApplications.length, page: 1, pageSize: 20, totalPages: 1 },
  handler: () => {
    const items = getAllJobApplications();
    return { status: 200, body: { items, total: items.length, page: 1, pageSize: Math.max(20, items.length), totalPages: items.length ? 1 : 0 } };
  },
};
export { myJobApplications };
