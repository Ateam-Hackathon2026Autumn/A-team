import type { RestMock } from '../../types';
import { hoursFromNow } from '../../helpers';

// 商品詳細取得API GET /api/v1/dashboard/products/:productId
//
// 編集画面用。本人の商品なら下書き・非公開でも取得できる
// 更新・削除・在庫更新の If-Match には etag の値をそのまま送る
//
// 存在しない・他人の商品（404）:
//   { errorCode: 'NOT_FOUND', errorMsg: '商品が見つかりません。' }
const dashboardProductDetail: RestMock = {
  method: 'GET',
  path: '/api/v1/dashboard/products/:productId',
  status: 200,
  body: {
    id: 1,
    producerId: 1,
    name: '安曇野ふじ 家庭用',
    volume: '5kg',
    categoryId: 2,
    shippingSettingId: 1,
    price: 4800,
    taxRate: 8,
    discountRate: null,
    description:
      '北アルプスの雪どけ水で育てた、蜜たっぷりのふじりんご。見た目に小さな傷がある家庭用です。',
    method: '草生栽培・減農薬（県基準の50%以下）',
    isSubscription: false,
    isPreorder: false,
    acceptsDeliveryDate: true,
    publishStatus: 'public',
    salePrice: 4800,
    stock: 40,
    ratingAvg: 4.8,
    reviewCount: 126,
    images: [
      {
        id: 1,
        key: 'products/1/fuji-1.jpg',
        url: 'https://picsum.photos/seed/fuji1/800/600',
        sortOrder: 0,
      },
      {
        id: 2,
        key: 'products/1/fuji-2.jpg',
        url: 'https://picsum.photos/seed/fuji2/800/600',
        sortOrder: 1,
      },
    ],
    createdAt: hoursFromNow(-24 * 90),
    updatedAt: hoursFromNow(-5),
    etag: '"product-1-v12"',
  },
};

export { dashboardProductDetail };
