// 生産者ストーリー（ER図の producer_stories。1生産者につき1件）
// GET /api/v1/producers/:producerId/story の形。タイトル・カテゴリーはない（記事の stories は拡張）
export type StoryProducer = {
  id: number; businessName: string; genre: string; prefectureName: string; city: string;
  coverImageUrl: string | null; acceptsExperience: boolean; recruiting: boolean;
};
export type Story = {
  id: number; producerId: number;
  craft: string | null;        // 生産へのこだわり
  method: string | null;       // 栽培・飼育・漁の方法
  process: string | null;      // ものができるまで
  environment: string | null;  // 環境への取り組み
  reason: string | null;       // この仕事を選んだ理由
  goal: string | null;         // これからの目標
  updatedAt: string;
};
export type StoryArticle = Story & { producer: StoryProducer };
