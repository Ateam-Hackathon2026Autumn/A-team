import type { RestMock } from '../../types';
import { hoursFromNow } from '../../helpers';

// 在庫更新API PATCH /api/v1/dashboard/products/:productId/stock
//
// 在庫数は増減ではなく絶対値で設定する（0 は売り切れ、null は未設定）
// ここでは「シャインマスカット」の在庫を 3 → 10 に変更した結果
//
// 公開中の商品の在庫を未設定（null）にしようとした（409）:
//   { errorCode: 'STOCK_STATE_CONFLICT', errorMsg: '公開中の商品は在庫数を未設定にできません。' }
const dashboardProductStockUpdate: RestMock = {
  method: 'PATCH',
  path: '/api/v1/dashboard/products/:productId/stock',
  status: 200,
  body: {
    productId: 2,
    stock: 10,
    updatedAt: hoursFromNow(0),
    etag: '"product-2-v6"',
  },
};

export { dashboardProductStockUpdate };
