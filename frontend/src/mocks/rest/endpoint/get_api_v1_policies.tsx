import type { RestMock } from '../../types';

// 利用規約・プライバシーポリシーの版 GET /api/v1/policies
const policies: RestMock = {
  method: 'GET',
  path: '/api/v1/policies',
  status: 200,
  body: {
    termsVersion: '2026-10-01',
    privacyPolicyVersion: '2026-10-01',
  },
};

export { policies };
