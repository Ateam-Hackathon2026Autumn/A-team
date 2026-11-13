import type { RestMock } from '../../types';
import { hoursFromNow } from '../../helpers';

// 売上受取口座連携API POST /api/v1/dashboard/payouts/account
//
// Stripe の口座登録画面（ホスト型オンボーディング）の URL を発行する。リクエスト本文は {}
// onboardingUrl は短時間・1回限り有効。モックではダミーの URL を返す
//
// 同じ Idempotency-Key のリンクが期限切れ（409）:
//   { errorCode: 'LINK_EXPIRED', errorMsg: 'リンクの有効期限が切れました。もう一度お試しください。' }
//
// 決済事業者の一時障害（503）:
//   { errorCode: 'PAYMENT_PROVIDER_UNAVAILABLE', errorMsg: '現在口座連携を利用できません。時間をおいて再度お試しください。' }
const dashboardPayoutAccountLink: RestMock = {
  method: 'POST',
  path: '/api/v1/dashboard/payouts/account',
  status: 200,
  body: {
    provider: 'stripe',
    onboardingUrl: 'https://connect.stripe.com/setup/e/acct_mock/mock-onboarding',
    expiresAt: hoursFromNow(0.25),
  },
};

export { dashboardPayoutAccountLink };
