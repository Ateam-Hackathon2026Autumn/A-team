import type { RestMock } from '../../types';
import { hoursFromNow } from '../../helpers';

// 注文詳細取得API GET /api/v1/dashboard/orders/:orderId
//
// 発送作業用。注文時のお届け先（shippingAddress）はこのAPIでだけ返る
// 配送状況更新の If-Match には、更新したい箱の shipments[].etag を送る
//
// 存在しない・他の生産者の注文（404）:
//   { errorCode: 'NOT_FOUND', errorMsg: '注文が見つかりません。' }
const dashboardOrderDetail: RestMock = {
  method: 'GET',
  path: '/api/v1/dashboard/orders/:orderId',
  status: 200,
  body: {
    orderId: 1012,
    orderNo: 'TM-1012',
    orderedAt: hoursFromNow(-3),
    paymentStatus: 'paid',
    producerItemsTotal: 4800,
    producerShippingTotal: 900,
    producerTotal: 5700,
    shipments: [
      {
        id: 2012,
        temperatureZone: 'normal',
        status: 'unshipped',
        shippingFee: 900,
        desiredDate: null,
        desiredTime: null,
        trackingNo: null,
        shippedAt: null,
        cancelReason: null,
        canceledAt: null,
        refundedAmount: null,
        updatedAt: hoursFromNow(-3),
        etag: '"shipment-2012-v1"',
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
    ],
    shippingAddress: {
      name: '佐藤 花子',
      postalCode: '154-0001',
      prefecture: '東京都',
      city: '世田谷区',
      addressLine1: '池尻1-2-3',
      addressLine2: 'マルシェハイツ201',
      phone: '090-1234-5678',
    },
  },
};

export { dashboardOrderDetail };
