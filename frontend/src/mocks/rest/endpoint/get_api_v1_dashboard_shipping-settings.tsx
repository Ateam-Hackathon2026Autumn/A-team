import type { RestMock } from '../../types';

// 配送設定取得API GET /api/v1/dashboard/shipping-settings
//
// ※ Notion の API 一覧では「追加機能」で、仕様ページが未作成のため、レスポンスは仮の形
//    （DB の shipping_settings：生産者 × 温度帯で1件。送料・送料無料になる金額・発送目安）
//    商品登録画面の「配送方法」の選択肢に使う
//
// 配送設定がまだない場合:
//   { items: [] }
const dashboardShippingSettings: RestMock = {
  method: 'GET',
  path: '/api/v1/dashboard/shipping-settings',
  status: 200,
  body: {
    items: [
      {
        id: 1,
        temperatureZone: 'normal',
        shippingFee: 900,
        freeShippingThreshold: null,
        leadTimeText: '2〜4日で発送',
      },
      {
        id: 2,
        temperatureZone: 'chilled',
        shippingFee: 1200,
        freeShippingThreshold: 10000,
        leadTimeText: '翌日発送',
      },
    ],
  },
};

export { dashboardShippingSettings };
