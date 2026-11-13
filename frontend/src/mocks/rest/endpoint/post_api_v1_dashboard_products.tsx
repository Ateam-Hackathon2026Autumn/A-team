import type { RestMock } from '../../types';
import { hoursFromNow } from '../../helpers';

// 商品登録API POST /api/v1/dashboard/products
//
// 登録した商品をそのまま返す（省略した項目は既定値: 下書き・在庫未設定・評価なし）
//
// 入力不正（400）:
//   {
//     errorCode: 'VALIDATION_ERROR',
//     errorMsg: '入力内容に誤りがあります。',
//     details: { name: ['商品名を入力してください。'] },
//   }
//
// 公開条件を満たさず登録できない（409）:
//   { errorCode: 'PRODUCT_CONFLICT', errorMsg: '公開するには画像・商品説明・在庫数が必要です。' }
const dashboardProductCreate: RestMock = {
  method: 'POST',
  path: '/api/v1/dashboard/products',
  status: 201,
  body: {
    id: 10,
    producerId: 1,
    name: '秋映 家庭用',
    volume: '3kg',
    categoryId: 2,
    shippingSettingId: 1,
    price: 3200,
    taxRate: 8,
    discountRate: null,
    description: '深い赤色と甘酸っぱさが特徴の長野県オリジナル品種です。',
    method: '草生栽培・減農薬（県基準の50%以下）',
    isSubscription: false,
    isPreorder: false,
    acceptsDeliveryDate: true,
    publishStatus: 'draft',
    salePrice: 3200,
    stock: null,
    ratingAvg: null,
    reviewCount: 0,
    images: [
      {
        id: 10,
        key: 'products/10/akibae-1.jpg',
        url: 'https://picsum.photos/seed/akibae1/800/600',
        sortOrder: 0,
      },
    ],
    createdAt: hoursFromNow(0),
    updatedAt: hoursFromNow(0),
    etag: '"product-10-v1"',
  },
};

export { dashboardProductCreate };
