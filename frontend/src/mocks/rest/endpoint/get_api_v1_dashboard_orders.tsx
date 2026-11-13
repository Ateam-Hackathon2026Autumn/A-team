import type { RestMock } from '../../types';
import { daysFromNow, hoursFromNow } from '../../helpers';

// 注文一覧取得API GET /api/v1/dashboard/orders
//
// ログイン中の生産者（山本農園）宛ての注文を新しい順に返す
// shipments は本人の箱だけ。金額は注文時の保存値（税込・円）で、producerTotal = 商品合計 + 送料
// 購入者の氏名・住所は一覧では返らない（注文詳細取得APIで取得する）
//
// 注文が1件もない場合:
//   { items: [], total: 0, page: 1, pageSize: 20, totalPages: 0 }
const dashboardOrdersList: RestMock = {
  method: 'GET',
  path: '/api/v1/dashboard/orders',
  status: 200,
  body: {
    items: [
      {
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
      },
      {
        orderId: 1011,
        orderNo: 'TM-1011',
        orderedAt: hoursFromNow(-20),
        paymentStatus: 'paid',
        producerItemsTotal: 10800,
        producerShippingTotal: 900,
        producerTotal: 11700,
        shipments: [
          {
            id: 2011,
            temperatureZone: 'normal',
            status: 'unshipped',
            shippingFee: 900,
            // お届け希望日あり
            desiredDate: daysFromNow(3),
            desiredTime: '午前中',
            trackingNo: null,
            shippedAt: null,
            cancelReason: null,
            canceledAt: null,
            refundedAmount: null,
            updatedAt: hoursFromNow(-20),
            etag: '"shipment-2011-v1"',
            items: [
              {
                id: 3011,
                productId: 2,
                productName: 'シャインマスカット 2房',
                unitPrice: 5400,
                discountRate: null,
                paidUnitPrice: 5400,
                quantity: 2,
                taxRate: 8,
                subtotal: 10800,
              },
            ],
          },
        ],
      },
      {
        orderId: 1010,
        orderNo: 'TM-1010',
        orderedAt: hoursFromNow(-30),
        paymentStatus: 'paid',
        producerItemsTotal: 4800,
        producerShippingTotal: 900,
        producerTotal: 5700,
        shipments: [
          {
            id: 2010,
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
            updatedAt: hoursFromNow(-30),
            etag: '"shipment-2010-v1"',
            items: [
              {
                id: 3010,
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
      },
      {
        orderId: 1009,
        orderNo: 'TM-1009',
        orderedAt: hoursFromNow(-72),
        paymentStatus: 'paid',
        producerItemsTotal: 9600,
        producerShippingTotal: 900,
        producerTotal: 10500,
        shipments: [
          {
            id: 2009,
            temperatureZone: 'normal',
            // 発送済み
            status: 'shipped',
            shippingFee: 900,
            desiredDate: null,
            desiredTime: null,
            trackingNo: '4321-5678-9012',
            shippedAt: hoursFromNow(-48),
            cancelReason: null,
            canceledAt: null,
            refundedAmount: null,
            updatedAt: hoursFromNow(-48),
            etag: '"shipment-2009-v2"',
            items: [
              {
                id: 3009,
                productId: 1,
                productName: '安曇野ふじ 家庭用 5kg',
                unitPrice: 4800,
                discountRate: null,
                paidUnitPrice: 4800,
                quantity: 2,
                taxRate: 8,
                subtotal: 9600,
              },
            ],
          },
        ],
      },
    ],
    total: 4,
    page: 1,
    pageSize: 20,
    totalPages: 1,
  },
};

export { dashboardOrdersList };
