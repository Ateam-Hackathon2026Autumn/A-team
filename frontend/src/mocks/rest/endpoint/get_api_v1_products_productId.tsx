import type { RestMock } from '../../types';

// 商品詳細取得API GET /api/v1/products/:productId
//
// 公開中の商品1「安曇野ふじ 家庭用 5kg」を返す。shipping.shippingFee は基準送料で、確定送料は注文API で計算する
//
// 商品が存在しない・公開対象外（404）:
//   { errorCode: 'PRODUCT_NOT_FOUND', errorMsg: '商品が見つかりません。' }
const productDetail: RestMock = {
  method: 'GET',
  path: '/api/v1/products/:productId',
  status: 200,
  body: {
    id: 1,
    name: '安曇野ふじ 家庭用 5kg',
    volume: '5kg（14〜20玉）',
    price: 4800,
    discountRate: null,
    salePrice: 4800,
    taxRate: 8,
    ratingAvg: 4.8,
    reviewCount: 126,
    stock: 40,
    isSubscription: false,
    isPreorder: false,
    thumbnailUrl: 'https://picsum.photos/seed/product1/800/600',
    category: { id: 2, name: '果物', sortOrder: 2 },
    producer: { id: 1, businessName: '山本農園', prefectureId: 20, prefectureName: '長野県', city: '安曇野市' },
    description:
      '北アルプスの雪どけ水で育てた、蜜たっぷりの「ふじ」です。樹上で完熟させてから収穫するので、シャキッとした歯ざわりと濃い甘みが自慢。キズや形の不ぞろいがある家庭用なので、お得にお届けします。',
    method: '草生栽培・減農薬（県基準の50%以下）',
    acceptsDeliveryDate: true,
    images: [
      { id: 1, url: 'https://picsum.photos/seed/product1/800/600', sortOrder: 1 },
      { id: 2, url: 'https://picsum.photos/seed/product1-orchard/800/600', sortOrder: 2 },
      { id: 3, url: 'https://picsum.photos/seed/product1-cut/800/600', sortOrder: 3 },
    ],
    shipping: {
      temperatureZone: 'normal',
      shippingFee: 900,
      freeShippingThreshold: null,
      leadTimeText: 'ご注文から3〜5日以内に発送',
    },
  },
};

export { productDetail };
