import type { RestMock } from '../../types';
import { hoursFromNow } from '../../helpers';

// 商品詳細取得API GET /api/v1/dashboard/products/:productId
//
// 編集画面用。本人の商品なら下書き・非公開でも取得できる
// 更新・削除・在庫更新の If-Match には etag の値をそのまま送る
//
// ID 1〜3 は一覧モック（get_api_v1_dashboard_products.tsx）と同じ内容を、パスの完全一致で返す
// それ以外の ID は :productId のモックで 404 を返す
// 商品を追加する場合は、一覧モックと同じ内容で dashboardProductDetailN を追加し、rest/index.tsx に登録する
const dashboardProductDetail1: RestMock = {
  method: 'GET',
  path: '/api/v1/dashboard/products/1',
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

const dashboardProductDetail2: RestMock = {
  method: 'GET',
  path: '/api/v1/dashboard/products/2',
  status: 200,
  body: {
    id: 2,
    producerId: 1,
    name: 'シャインマスカット',
    volume: '2房',
    categoryId: 2,
    shippingSettingId: 1,
    price: 5400,
    taxRate: 8,
    discountRate: null,
    description:
      '皮ごと食べられる、香り高いシャインマスカット。糖度18度以上のものだけを選んでお届けします。',
    method: '減農薬（県基準の50%以下）',
    isSubscription: false,
    isPreorder: false,
    acceptsDeliveryDate: true,
    publishStatus: 'public',
    salePrice: 5400,
    // 残りわずか
    stock: 3,
    ratingAvg: 4.9,
    reviewCount: 48,
    images: [
      {
        id: 4,
        key: 'products/2/shine-muscat-1.jpg',
        url: 'https://picsum.photos/seed/shine1/800/600',
        sortOrder: 0,
      },
    ],
    createdAt: hoursFromNow(-24 * 60),
    updatedAt: hoursFromNow(-2),
    etag: '"product-2-v5"',
  },
};

const dashboardProductDetail3: RestMock = {
  method: 'GET',
  path: '/api/v1/dashboard/products/3',
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
    // 非公開
    publishStatus: 'private',
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
    updatedAt: hoursFromNow(-24 * 3),
    etag: '"product-3-v2"',
  },
};

const dashboardProductDetail: RestMock = {
  method: 'GET',
  path: '/api/v1/dashboard/products/:productId',
  status: 404,
  body: {
    errorCode: 'NOT_FOUND',
    errorMsg: '商品が見つかりません。',
  },
};

export {
  dashboardProductDetail,
  dashboardProductDetail1,
  dashboardProductDetail2,
  dashboardProductDetail3,
};
