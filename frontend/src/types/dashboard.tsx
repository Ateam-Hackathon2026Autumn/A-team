// 売上（商品注文のみ・全期間・税込送料込み・手数料控除前）
type DashboardSales = {
  currency: 'JPY';
  scope: 'product_orders';
  grossAmount: number;
  refundedAmount: number;
  netAmount: number;
};

// ダッシュボード集計取得API（GET /api/v1/dashboard/summary）のレスポンス
type DashboardSummary = {
  // 集計した日時
  asOf: string;
  publishedProductCount: number;
  publishedExperienceCount: number;
  publishedJobCount: number;
  // 体験申込・求人応募は全状態の累計
  experienceApplicationCount: number;
  jobApplicationCount: number;
  sales: DashboardSales;
};

export type { DashboardSales, DashboardSummary };
