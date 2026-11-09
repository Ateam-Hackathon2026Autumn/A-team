import type { RestMock } from '../../types';
import { updateStock } from '../store/dashboardProducts';

// 在庫更新API PATCH /api/v1/dashboard/products/:productId/stock
//
// 在庫数は増減ではなく絶対値で設定する（0 は売り切れ、null は未設定）
// 返却: { productId, stock, updatedAt, etag }（etag は次回の If-Match に使う）
//
// 公開中の商品の在庫を未設定（null）にしようとした（409）:
//   { errorCode: 'STOCK_STATE_CONFLICT', errorMsg: '公開中の商品は在庫数を未設定にできません。' }
//
// If-Match が古い（412）:
//   { errorCode: 'PRECONDITION_FAILED', errorMsg: '他の操作で更新されています。再読み込みしてください。' }
const dashboardProductStockUpdate: RestMock = {
  method: 'PATCH',
  path: '/api/v1/dashboard/products/:productId/stock',
  status: 200,
  handler: (url, init) => updateStock(url, init),
};

export { dashboardProductStockUpdate };
