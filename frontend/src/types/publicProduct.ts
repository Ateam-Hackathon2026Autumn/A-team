export type Category = { id: number; name: string; sortOrder: number };

export type Product = {
  id: number;
  name: string;
  volume: string;
  price: number;
  discountRate: number | null;
  salePrice: number;
  taxRate: number;
  ratingAvg: number | null;
  reviewCount: number;
  stock: number | null;
  isSubscription: boolean;
  isPreorder: boolean;
  thumbnailUrl: string | null;
  category: Category;
  producer: {
    id: number;
    businessName: string;
    prefectureId: number;
    prefectureName: string;
    city: string;
  };
};

export type ProductDetail = Product & {
  description: string;
  method: string;
  acceptsDeliveryDate: boolean;
  images: { id: number; url: string; sortOrder: number }[];
  shipping: {
    temperatureZone: string;
    shippingFee: number;
    freeShippingThreshold: number | null;
    leadTimeText: string;
  };
};

export type ProductListResponse = {
  items: Product[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
};
