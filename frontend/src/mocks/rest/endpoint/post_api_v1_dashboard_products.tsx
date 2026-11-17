import type { RestMock } from '../../types';
import { createProduct } from '../store/dashboardProducts';

// 商品登録API POST /api/v1/dashboard/products
//
// 登録した商品を返す（評価なし・etag は v1）。一覧・詳細にも追加される
//
// 入力不正（400）:
//   {
//     errorCode: 'VALIDATION_ERROR',
//     errorMsg: '入力内容に誤りがあります。',
//     details: { name: ['商品名を入力してください。'] },
//   }
//
// 公開条件（画像・商品説明・在庫数・1円以上の販売価格）を満たさず登録できない（409）:
//   { errorCode: 'PRODUCT_STATE_CONFLICT', errorMsg: '公開するには画像・商品説明・在庫数が必要です。' }
const dashboardProductCreate: RestMock = {
  method: 'POST',
  path: '/api/v1/dashboard/products',
  status: 201,
  handler: (_url, init) => createProduct(init),
};

export { dashboardProductCreate };
