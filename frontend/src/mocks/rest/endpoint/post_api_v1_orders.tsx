import type { RestMock } from '../../types';
import { hoursFromNow } from '../../helpers';

// 注文・決済API POST /api/v1/orders
//
// GET /api/v1/cart のカート（安曇野ふじ×1・あじの開き干し×2）を注文した結果を返す。
// 箱は生産者×温度帯ごと：山本農園（常温）送料900円 + 海風水産（冷蔵）送料1,100円。
// paymentStatus は常に pending。支払い完了は Stripe の Webhook で確定する（checkoutUrl へ遷移して支払う）
//
// カートが空・在庫不足・見積の期限切れなど（409）:
//   { errorCode: 'QUOTE_CHANGED', errorMsg: 'カートの内容または価格が変更されました。もう一度ご確認ください。' }
//
// 未ログイン（401）:
//   { errorCode: 'UNAUTHENTICATED', errorMsg: 'ログインしてください。' }
//
// 決済連携の一時障害（503）:
//   { errorCode: 'PAYMENT_UNAVAILABLE', errorMsg: '決済サービスに接続できません。時間をおいて再度お試しください。' }
const orderCreate: RestMock = {
  method: 'POST',
  path: '/api/v1/orders',
  status: 201,
  body: {
    id: 1013,
    orderNo: 'TM-1013',
    paymentStatus: 'pending',
    itemsTotal: 11200,
    shippingTotal: 2000,
    grandTotal: 13200,
    checkoutUrl: 'https://checkout.stripe.com/c/pay/cs_test_mock_tm1013',
    // Stripe Checkout の有効期限（30分後）
    expiresAt: hoursFromNow(0.5),
  },
};

export { orderCreate };
