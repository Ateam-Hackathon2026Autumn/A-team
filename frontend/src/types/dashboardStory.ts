// 生産者ストーリー（学ぶページの内容。1生産者につき1件）
// 実API: backend/api/views/dashboard/story.py・serializers/dashboard/story.py（ER図の producer_stories の形）
// ※ Notion のタイトル・タグ（storyCategoryId・category）は拡張のストーリー記事の項目なので、ここにはない

// draft（下書き）/ public（公開）/ private（非公開）/ suspended（運営による掲載停止。生産者は選べない）
type StoryPublishStatus = 'draft' | 'public' | 'private' | 'suspended';

// 生産者が保存時に選べる公開状態
type StoryEditableStatus = Exclude<StoryPublishStatus, 'suspended'>;

// 本文の6項目（未入力は null）
type StoryTextField = 'craft' | 'method' | 'process' | 'environment' | 'reason' | 'goal';

type StoryTexts = Record<StoryTextField, string | null>;

// ストーリー取得API（GET /api/v1/dashboard/story）・保存API（PUT）のレスポンス
// まだ保存していない場合は、すべて null・draft・updatedAt null
type DashboardStory = StoryTexts & {
  publishStatus: StoryPublishStatus;
  updatedAt: string | null;
};

// ストーリー保存API（PUT /api/v1/dashboard/story）の本文。7項目すべて送って置き換える
type StoryInput = StoryTexts & {
  publishStatus: StoryEditableStatus;
};

export type {
  DashboardStory,
  StoryEditableStatus,
  StoryInput,
  StoryPublishStatus,
  StoryTextField,
  StoryTexts,
};
