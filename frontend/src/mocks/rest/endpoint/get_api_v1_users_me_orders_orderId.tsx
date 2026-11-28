import type { RestMock } from '../../types';
import type { OrderDetail, OrderSummary } from '../../../types/consumerOrder';
import { myOrdersList } from './get_api_v1_users_me_orders';
import { consumerDemoOrders } from '../store/consumerOrders';
import { producersList } from './get_api_v1_producers';
import type { ProducerSummary } from '../../../types/producer';
const myOrderDetail: RestMock = {
  method: 'GET',
  path: '/api/v1/users/me/orders/:orderId',
  status: 200,
  handler(url) {
    const id = Number(url.pathname.split('/').at(-1));
    const created = consumerDemoOrders.find((order) => order.id === id);
    if (created) return { status: 200, body: created };
    const summary = (myOrdersList.body as { items: OrderSummary[] }).items.find(
      (order) => order.id === id,
    );
    if (!summary)
      return { status: 404, body: { errorMsg: '注文が見つかりません。' } };
    const detail: OrderDetail = {
      ...summary,
      shippingAddress: {
        name: '山本 健太',
        postalCode: '399-8303',
        prefecture: '長野県',
        city: '安曇野市',
        addressLine1: '穂高1-2-3',
        addressLine2: null,
        phone: '09012345678',
      },
      shipments: summary.shipments.map((box, index) => ({
        ...box,
        producer: {
          id: box.producerId,
          businessName:
            (producersList.body as { items: ProducerSummary[] }).items.find(
              (p) => p.id === box.producerId,
            )?.businessName ?? `生産者 #${box.producerId}`,
        },
        trackingNo: null,
        items:
          summary.id === 1013
            ? [
                {
                  id: box.id,
                  productId: index === 0 ? 1 : 6,
                  productName:
                    index === 0
                      ? '安曇野ふじ 家庭用 5kg'
                      : '沼津 あじの開き干し 10枚',
                  quantity: index === 0 ? 1 : 2,
                  subtotal: index === 0 ? 4800 : 6400,
                },
              ]
            : [
                {
                  id: box.id,
                  productId: null,
                  productName: '産地直送セット（サンプルの注文記録）',
                  quantity: 1,
                  subtotal: summary.itemsTotal,
                },
              ],
      })),
    };
    return { status: 200, body: detail };
  },
};
export { myOrderDetail };
