// 生産者プロフィール（生産者管理画面のプロフィール編集）
// 実API: backend/api/views/dashboard/profile.py・serializers/dashboard/profile.py

type ProducerGenre = 'agriculture' | 'livestock' | 'fishery';

// 審査の状態（プロフィールAPIを使えるのは承認済みだけ）
type ProducerApprovalStatus = 'pending' | 'approved' | 'rejected';

// public（公開）/ private（非公開）/ suspended（運営による掲載停止。生産者は選べない）
type ProducerPublishStatus = 'public' | 'private' | 'suspended' | 'draft';

// ストーリーの公開状態
type ProfileStoryStatus = 'draft' | 'public' | 'private' | 'suspended';

// 農園画像 {id, key, url, sortOrder}（key は更新の imageKeys にそのまま送れる）
type ProducerImage = {
  id: number;
  key: string;
  url: string;
  sortOrder: number;
};

// 生産者プロフィール取得API（GET /api/v1/dashboard/profile）・更新API（PATCH）のレスポンス
type DashboardProfile = {
  id: number;
  // 事業者名・代表者名・ジャンルは変更できない（運営への問い合わせで対応）
  businessName: string;
  representativeName: string;
  genre: ProducerGenre;
  prefectureId: number;
  city: string;
  productionItems: string;
  intro: string;
  careerStartYear: number | null;
  foundedYear: number | null;
  acceptsExperience: boolean;
  recruiting: boolean;
  // 画像のキー（更新に送る値）と表示用URL
  profileImage: string | null;
  coverImage: string | null;
  profileImageUrl: string | null;
  coverImageUrl: string | null;
  images: ProducerImage[];
  approvalStatus: ProducerApprovalStatus;
  publishStatus: ProducerPublishStatus;
  // ストーリーの値（表示用。変更はストーリーAPIで行う）。ストーリーがなければ null
  reason: string | null;
  goal: string | null;
  storyPublishStatus: ProfileStoryStatus | null;
  updatedAt: string;
};

// 生産者プロフィール更新API（PATCH /api/v1/dashboard/profile）の本文。送った項目だけ変わる
type ProfileUpdateInput = Partial<{
  prefectureId: number;
  city: string;
  productionItems: string;
  intro: string;
  careerStartYear: number | null;
  foundedYear: number | null;
  acceptsExperience: boolean;
  recruiting: boolean;
  profileImage: string | null;
  coverImage: string | null;
  // 配列で置き換え（順番が表示順。10枚まで・重複なし）
  imageKeys: string[];
  publishStatus: 'public' | 'private';
}>;

export type {
  DashboardProfile,
  ProducerApprovalStatus,
  ProducerGenre,
  ProducerImage,
  ProducerPublishStatus,
  ProfileStoryStatus,
  ProfileUpdateInput,
};
