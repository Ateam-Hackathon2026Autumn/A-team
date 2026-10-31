import type { RestMock } from '../../types';

// 商品削除API DELETE /api/v1/dashboard/products/:productId
//
// 成功時は本文なし（204）。削除できるのは非公開・下書きの商品だけ
//
// 公開中・注文などから参照されていて削除できない（409）:
//   { errorCode: 'PRODUCT_DELETE_CONFLICT', errorMsg: '公開中または注文のある商品は削除できません。' }
//
// 存在しない・削除済み・他人の商品（404）:
//   { errorCode: 'NOT_FOUND', errorMsg: '商品が見つかりません。' }
const dashboardProductDelete: RestMock = {
  method: 'DELETE',
  path: '/api/v1/dashboard/products/:productId',
  status: 204,
};

export { dashboardProductDelete };
