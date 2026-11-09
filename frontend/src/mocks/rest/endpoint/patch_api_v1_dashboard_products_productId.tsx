import type { RestMock } from '../../types';
import { updateProduct } from '../store/dashboardProducts';

// 商品更新API（公開・非公開の切り替えを含む） PATCH /api/v1/dashboard/products/:productId
//
// 送った項目だけ更新し、更新後の商品を返す（etag・updatedAt が新しくなる）。在庫は在庫更新APIで変える
//
// 公開条件を満たさない（409）:
//   { errorCode: 'PRODUCT_STATE_CONFLICT', errorMsg: '公開するには画像・商品説明・在庫数が必要です。' }
//
// 他の画面で先に更新されていた＝If-Match が古い（412）:
//   { errorCode: 'PRECONDITION_FAILED', errorMsg: '他の操作で更新されています。再読み込みしてください。' }
const dashboardProductUpdate: RestMock = {
  method: 'PATCH',
  path: '/api/v1/dashboard/products/:productId',
  status: 200,
  handler: (url, init) => updateProduct(url, init),
};

export { dashboardProductUpdate };
