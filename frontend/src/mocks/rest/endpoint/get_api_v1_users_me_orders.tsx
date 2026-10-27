import type { RestMock } from '../../types';
import { hoursFromNow } from '../../helpers';

// 注文履歴取得API GET /api/v1/users/me/orders
//
// ログイン中のユーザー（山本 健太）が購入者として注文した履歴。注文日時の新しい順。
// 1注文に複数の生産者の商品があれば shipments（箱）が複数になり、配送状況は箱ごとに見る
//
// 注文なし:
//   { items: [], total: 0, page: 1, pageSize: 20, totalPages: 0 }
//
// 未ログイン（401）:
//   { errorCode: 'UNAUTHENTICATED', errorMsg: 'ログインしてください。' }
const myOrdersList: RestMock = {
  method: 'GET',
  path: '/api/v1/users/me/orders',
  status: 200,
  body: {
    items: [
      {
        // 支払い待ち（POST /api/v1/orders 直後の注文）
        id: 1013,
        orderNo: 'TM-1013',
        paymentStatus: 'pending',
        itemsTotal: 11200,
        shippingTotal: 2000,
        grandTotal: 13200,
        orderedAt: hoursFromNow(-0.2),
        shipments: [
          { id: 1021, producerId: 1, temperatureZone: 'normal', status: 'unshipped', shippingFee: 900 },
          { id: 1022, producerId: 2, temperatureZone: 'chilled', status: 'unshipped', shippingFee: 1100 },
        ],
      },
      {
        id: 998,
        orderNo: 'TM-0998',
        paymentStatus: 'paid',
        itemsTotal: 2980,
        shippingTotal: 1000,
        grandTotal: 3980,
        orderedAt: hoursFromNow(-24 * 5),
        shipments: [{ id: 1003, producerId: 5, temperatureZone: 'chilled', status: 'shipped', shippingFee: 1000 }],
      },
      {
        id: 975,
        orderNo: 'TM-0975',
        paymentStatus: 'paid',
        itemsTotal: 6140,
        shippingTotal: 1200,
        grandTotal: 7340,
        orderedAt: hoursFromNow(-24 * 20),
        shipments: [{ id: 978, producerId: 3, temperatureZone: 'chilled', status: 'delivered', shippingFee: 1200 }],
      },
    ],
    total: 3,
    page: 1,
    pageSize: 20,
    totalPages: 1,
  },
};

export { myOrdersList };
