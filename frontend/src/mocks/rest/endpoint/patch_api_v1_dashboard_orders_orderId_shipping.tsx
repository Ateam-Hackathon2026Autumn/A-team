import type { RestMock } from '../../types';
import { hoursFromNow } from '../../helpers';

// 配送状況更新API PATCH /api/v1/dashboard/orders/:orderId/shipping
//
// 1回で箱（shipment）1件だけを更新し、更新後の箱を返す
// ここでは注文 TM-1012 の箱を 未発送 → 発送済み にした結果（送り状番号を入力）
//
// 状態を変更できない（支払い未完了・逆戻り・キャンセル済みなど）（409）:
//   { errorCode: 'SHIPMENT_STATE_CONFLICT', errorMsg: 'この注文は現在の状態では更新できません。' }
//
// 他の画面で先に更新されていた（412）:
//   { errorCode: 'PRECONDITION_FAILED', errorMsg: '他の操作で更新されています。画面を再読み込みしてください。' }
const dashboardOrderShippingUpdate: RestMock = {
  method: 'PATCH',
  path: '/api/v1/dashboard/orders/:orderId/shipping',
  status: 200,
  body: {
    id: 2012,
    temperatureZone: 'normal',
    status: 'shipped',
    shippingFee: 900,
    desiredDate: null,
    desiredTime: null,
    trackingNo: '1234-5678-9012',
    shippedAt: hoursFromNow(0),
    cancelReason: null,
    canceledAt: null,
    refundedAmount: null,
    updatedAt: hoursFromNow(0),
    etag: '"shipment-2012-v2"',
    items: [
      {
        id: 3012,
        productId: 1,
        productName: '安曇野ふじ 家庭用 5kg',
        unitPrice: 4800,
        discountRate: null,
        paidUnitPrice: 4800,
        quantity: 1,
        taxRate: 8,
        subtotal: 4800,
      },
    ],
  },
};

export { dashboardOrderShippingUpdate };
