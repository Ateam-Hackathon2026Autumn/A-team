import type { RestMock } from '../../types';
import { listProducts } from '../store/dashboardProducts';

// 商品一覧取得API GET /api/v1/dashboard/products?page=
//
// ログイン中の生産者（山本農園）本人の商品を、公開状態に関係なく返す（updatedAt の新しい順・20件ずつ）
// データは store/dashboardProducts.tsx。登録・更新・在庫変更・削除の結果がそのまま反映される
//
// 商品が1件もない場合:
//   { items: [], total: 0, page: 1, pageSize: 20, totalPages: 0 }
//
// 未ログイン（401）を確認する場合は status を 401 にし、body に次を書く:
//   { errorCode: 'UNAUTHENTICATED', errorMsg: 'ログインしてください。' }
const dashboardProductsList: RestMock = {
  method: 'GET',
  path: '/api/v1/dashboard/products',
  status: 200,
  handler: (url) => listProducts(url),
};

export { dashboardProductsList };
