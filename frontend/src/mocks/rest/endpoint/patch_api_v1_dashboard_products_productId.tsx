import type { RestMock } from '../../types';
import { hoursFromNow } from '../../helpers';

// 商品更新API（公開・非公開の切り替えを含む） PATCH /api/v1/dashboard/products/:productId
//
// 更新後の商品をそのまま返す。ここでは「りんごのドライチップス」を非公開 → 公開に切り替えた結果
//
// 公開条件を満たさない（409）:
//   { errorCode: 'PRODUCT_STATE_CONFLICT', errorMsg: '公開するには画像・商品説明・在庫数が必要です。' }
//
// 他の画面で先に更新されていた（412）:
//   { errorCode: 'PRECONDITION_FAILED', errorMsg: '他の操作で更新されています。画面を再読み込みしてください。' }
const dashboardProductUpdate: RestMock = {
  method: 'PATCH',
  path: '/api/v1/dashboard/products/:productId',
  status: 200,
  body: {
    id: 3,
    producerId: 1,
    name: 'りんごのドライチップス',
    volume: '50g×3',
    categoryId: 7,
    shippingSettingId: 1,
    price: 1500,
    taxRate: 8,
    discountRate: null,
    description: '規格外のりんごを薄切りにして、低温でじっくり乾燥させました。砂糖不使用です。',
    method: null,
    isSubscription: false,
    isPreorder: false,
    acceptsDeliveryDate: false,
    publishStatus: 'public',
    salePrice: 1500,
    stock: 2,
    ratingAvg: null,
    reviewCount: 0,
    images: [
      {
        id: 3,
        key: 'products/3/apple-chips-1.jpg',
        url: 'https://picsum.photos/seed/chips1/800/600',
        sortOrder: 0,
      },
    ],
    createdAt: hoursFromNow(-24 * 30),
    updatedAt: hoursFromNow(0),
    etag: '"product-3-v3"',
  },
};

export { dashboardProductUpdate };
