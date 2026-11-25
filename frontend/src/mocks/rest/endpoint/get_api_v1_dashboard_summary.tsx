import type { RestMock } from '../../types';
import { hoursFromNow } from '../../helpers';
import { countPublishedProducts } from '../store/dashboardProducts';
import { summarizeExperiences } from '../store/dashboardExperiences';
import { summarizeJobs } from '../store/dashboardJobs';

// ダッシュボード集計取得API GET /api/v1/dashboard/summary
//
// ログイン中の生産者（山本農園）のダッシュボード上部の数字
// 申込・応募件数は全状態の累計。売上は商品注文のみ・全期間・税込送料込み（手数料控除前）
// 件数は商品・体験・求人のモックストア（store/*.tsx）から毎回数えるため、各管理画面の件数と一致する
// ※ 売上は注文のモックとつながっていないため、固定値（SALES）を返す
//
// まだ何もない生産者の場合:
//   各件数は 0、sales は { currency: 'JPY', scope: 'product_orders', grossAmount: 0, refundedAmount: 0, netAmount: 0 }
const SALES = {
  currency: 'JPY',
  scope: 'product_orders',
  grossAmount: 486300,
  refundedAmount: 5700,
  netAmount: 480600,
};

const dashboardSummary: RestMock = {
  method: 'GET',
  path: '/api/v1/dashboard/summary',
  status: 200,
  handler: () => {
    const experiences = summarizeExperiences();
    const jobs = summarizeJobs();

    return {
      status: 200,
      body: {
        asOf: hoursFromNow(0),
        // 公開中の商品・体験・求人
        publishedProductCount: countPublishedProducts(),
        publishedExperienceCount: experiences.publishedCount,
        publishedJobCount: jobs.publishedCount,
        // 体験申込・求人応募（全状態の累計）
        experienceApplicationCount: experiences.applicationCount,
        jobApplicationCount: jobs.applicationCount,
        sales: SALES,
      },
    };
  },
};

export { dashboardSummary };
