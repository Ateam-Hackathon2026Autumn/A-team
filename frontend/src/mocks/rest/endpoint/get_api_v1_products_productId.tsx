import type { RestMock } from '../../types';
import { productSamples } from './get_api_v1_products';
import type { ProductDetail } from '../../../types/product';

// 商品詳細取得API GET /api/v1/products/:productId
//
// 公開中の商品をIDに応じて返す。shipping.shippingFee は基準送料で、確定送料は注文API で計算する
//
// 商品が存在しない・公開対象外（404）:
//   { errorCode: 'PRODUCT_NOT_FOUND', errorMsg: '商品が見つかりません。' }
const originalDetail = {
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

// 商品1以外は画面確認用の架空の詳細情報。画像は商品写真ではありません。
const descriptions: Record<number, [string, string]> = {
  2: ['みずみずしい果汁と爽やかな甘みを楽しめる、シャインマスカットのセットです。', '畑で一房ずつ状態を確認し、収穫してお届けします。'],
  4: ['季節の野菜を詰め合わせました。収穫状況によって内容が変わります。', '季節の移り変わりに合わせて、複数の野菜を栽培しています。'],
  5: ['毎日の食卓に楽しんでいただきたい、新潟県産のコシヒカリです。', '収穫した稲をはさがけにし、天日でゆっくり乾燥させています。'],
  6: ['あじのうまみを楽しめる干物のセットです。焼いてお召し上がりください。', '魚の状態に合わせて下処理し、干物に仕上げています。'],
  7: ['さまざまな料理に使いやすい、十勝牛の切り落としです。', '生育状態を日々確認しながら育てています。'],
  8: ['ジャージー牛乳の風味を楽しめるヨーグルトです。', '牛乳の風味を大切に、発酵させて仕上げています。'],
  9: ['日々の料理に使いやすい、平飼いたまごのセットです。', '鶏が動き回れる平飼いの環境で育てています。'],
};

const productDetail: RestMock = {
  ...originalDetail,
  handler(url) {
    const id = Number(url.pathname.split('/').at(-1));
    const product = productSamples.find((item) => item.id === id);
    if (!product) return { status: 404, body: { errorCode: 'PRODUCT_NOT_FOUND', errorMsg: '商品が見つかりません。' } };
    if (id === 1) return { status: 200, body: originalDetail.body };
    const [description, method] = descriptions[id];
    const body: ProductDetail = {
      ...product,
      description,
      method,
      acceptsDeliveryDate: true,
      images: [
        { id: id * 10, url: product.thumbnailUrl, sortOrder: 1 },
        { id: id * 10 + 1, url: `https://picsum.photos/seed/product${id}-detail/800/600`, sortOrder: 2 },
      ],
      shipping: {
        temperatureZone: [6, 7].includes(id) ? 'frozen' : [8, 9].includes(id) ? 'chilled' : 'normal',
        shippingFee: 900,
        freeShippingThreshold: null,
        leadTimeText: 'ご注文から3〜5日以内に発送',
      },
    };
    return { status: 200, body };
  },
};

export { productDetail };
