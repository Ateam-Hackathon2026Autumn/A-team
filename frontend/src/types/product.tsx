// 商品の公開状態（suspended は運営による掲載停止で、生産者は変更できない）
type ProductPublishStatus = 'draft' | 'public' | 'private' | 'suspended';

type ProductImage = {
  id: number;
  key: string;
  url: string;
  sortOrder: number;
};

// 生産者向けの商品（GET /api/v1/dashboard/products の items）
type DashboardProduct = {
  id: number;
  producerId: number;
  name: string;
  volume: string;
  categoryId: number;
  shippingSettingId: number;
  price: number;
  taxRate: 8 | 10;
  discountRate: number | null;
  description: string | null;
  method: string | null;
  isSubscription: boolean;
  isPreorder: boolean;
  acceptsDeliveryDate: boolean;
  publishStatus: ProductPublishStatus;
  // 税込の実売価格（割引後）
  salePrice: number;
  // 0 は売り切れ、null は未設定
  stock: number | null;
  ratingAvg: number | null;
  reviewCount: number;
  images: ProductImage[];
  createdAt: string;
  updatedAt: string;
  // 更新時に If-Match で送る値（引用符付き）
  etag: string;
};

type DashboardProductList = {
  items: DashboardProduct[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
};

type Category = {
  id: number;
  name: string;
  sortOrder: number;
};

// 温度帯（常温・冷蔵・冷凍）
type TemperatureZone = 'normal' | 'chilled' | 'frozen';

// 配送設定（生産者 × 温度帯で1件）
type ShippingSetting = {
  id: number;
  temperatureZone: TemperatureZone;
  // 送料（円）
  shippingFee: number;
  // この金額以上で送料無料（円）。null は送料無料なし
  freeShippingThreshold: number | null;
  // 発送目安（例：2〜4日で発送）
  leadTimeText: string;
};

// 商品登録API（POST /api/v1/dashboard/products）のリクエスト
type ProductCreateInput = {
  name: string;
  volume: string;
  categoryId: number;
  shippingSettingId: number;
  price: number;
  taxRate: 8 | 10;
  discountRate: number | null;
  description: string | null;
  method: string | null;
  isSubscription: boolean;
  isPreorder: boolean;
  acceptsDeliveryDate: boolean;
  publishStatus: 'draft' | 'public' | 'private';
  // 画像アップロードAPIで受け取ったキー（最大10件、先頭がメイン画像）
  imageKeys: string[];
  stock: number | null;
};

// 商品更新API（PATCH /api/v1/dashboard/products/{productId}）のリクエスト
// 在庫数はこのAPIでは変更できない（在庫更新APIを使う）
type ProductUpdateInput = Omit<ProductCreateInput, 'stock'>;

export type {
  Category,
  ProductCreateInput,
  ProductUpdateInput,
  ShippingSetting,
  TemperatureZone,
  DashboardProduct,
  DashboardProductList,
  ProductImage,
  ProductPublishStatus,
};
