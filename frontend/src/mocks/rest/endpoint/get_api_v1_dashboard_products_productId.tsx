import type { RestMock } from '../../types';
import { getProduct } from '../store/dashboardProducts';

// 商品詳細取得API GET /api/v1/dashboard/products/:productId
//
// 編集画面用。本人の商品なら下書き・非公開でも取得できる（データは store/dashboardProducts.tsx）
// 更新・削除・在庫更新の If-Match には etag の値をそのまま送る
//
// 存在しない・削除済み・他人の商品（404）:
//   { errorCode: 'NOT_FOUND', errorMsg: '商品が見つかりません。' }
const dashboardProductDetail: RestMock = {
  method: 'GET',
  path: '/api/v1/dashboard/products/:productId',
  status: 200,
  handler: (url) => getProduct(url),
};

export { dashboardProductDetail };
