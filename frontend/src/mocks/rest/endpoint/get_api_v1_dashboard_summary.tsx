import type { RestMock } from '../../types';
import { hoursFromNow } from '../../helpers';

// ダッシュボード集計取得API GET /api/v1/dashboard/summary
//
// ログイン中の生産者（山本農園）のダッシュボード上部の数字
// 申込・応募件数は全状態の累計。売上は商品注文のみ・全期間・税込送料込み（手数料控除前）
//
// まだ何もない生産者の場合:
//   各件数は 0、sales は { currency: 'JPY', scope: 'product_orders', grossAmount: 0, refundedAmount: 0, netAmount: 0 }
const dashboardSummary: RestMock = {
  method: 'GET',
  path: '/api/v1/dashboard/summary',
  status: 200,
  body: {
    asOf: hoursFromNow(0),
    // 公開中の商品
    publishedProductCount: 2,
    // 公開中の体験
    publishedExperienceCount: 2,
    // 公開中の求人
    publishedJobCount: 2,
    // 体験申込
    experienceApplicationCount: 19,
    // 求人応募
    jobApplicationCount: 3,
    sales: {
      currency: 'JPY',
      scope: 'product_orders',
      grossAmount: 486300,
      refundedAmount: 5700,
      netAmount: 480600,
    },
  },
};

export { dashboardSummary };
