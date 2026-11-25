import type { DashboardProfile } from '../../../types/dashboardProfile';
import type { MockResult } from '../../types';
import {
  conflict,
  imageUrlFor,
  isObject,
  loadState,
  nowIso,
  readJsonBody,
  saveState,
  validationError,
} from './common';

// 生産者プロフィール（GET・PATCH /api/v1/dashboard/profile）のモックストア
//
// 実API（backend/api/views/dashboard/profile.py・serializers/dashboard/profile.py）に合わせる:
//   - 画像は profileImage・coverImage（キー）＋ profileImageUrl・coverImageUrl、農園画像は images [{id, key, url, sortOrder}]
//   - PATCH は送った項目だけ変える。空のオブジェクト・未知の項目（事業者名・代表者名・ジャンルを含む）は 400
//   - city 50文字・productionItems 100文字まで。city・productionItems・intro は空にできない
//   - 年は null か1〜今年。画像のキーは自分がアップロードしたもの（images/{userId}/）だけ
//   - imageKeys は10枚まで・重複なしで、配列で置き換え（順番が表示順）
//   - publishStatus は public・private。掲載停止中に送ると 409 PRODUCER_SUSPENDED
//   - reason・goal・storyPublishStatus はストーリーの値（ここでは変えない）
//   - ETag・If-Match は使わない
//
// 保存した内容は sessionStorage に持つ（再読み込みしても消えない。タブを閉じると初期状態に戻る）

const STORAGE_KEY = 'mock:dashboardProfile:v1';
// ログイン中の会員（山本 健太）の ID。アップロードした画像のキーは images/1/ で始まる
const IMAGE_PREFIX = 'images/1/';
const MAX_IMAGES = 10;

const initialProfile = (): DashboardProfile => ({
  id: 1,
  businessName: '山本農園',
  representativeName: '山本 健太',
  genre: 'agriculture',
  // 長野県
  prefectureId: 20,
  city: '安曇野市',
  productionItems: 'りんご・ぶどう',
  intro: '北アルプスの雪どけ水で育てる、蜜たっぷりのりんご。三代目として減農薬栽培に取り組んでいます。',
  careerStartYear: 2022,
  foundedYear: 1962,
  acceptsExperience: true,
  recruiting: true,
  profileImage: `${IMAGE_PREFIX}yamamoto-profile.jpg`,
  coverImage: `${IMAGE_PREFIX}yamamoto-cover.jpg`,
  profileImageUrl: 'https://picsum.photos/seed/yamamoto-profile/400/400',
  coverImageUrl: 'https://picsum.photos/seed/yamamoto-cover/1200/600',
  images: [1, 2, 3].map((n, index) => ({
    id: n,
    key: `${IMAGE_PREFIX}yamamoto-farm-${n}.jpg`,
    url: `https://picsum.photos/seed/yamamoto${n}/800/600`,
    sortOrder: index,
  })),
  approvalStatus: 'approved',
  publishStatus: 'public',
  reason: '祖父の代から続く園地を、次の世代にも残したいと思い会社を辞めて戻りました。',
  goal: '収穫体験と短期スタッフ受け入れで、りんご産地の担い手を増やしたい。',
  storyPublishStatus: 'public',
  updatedAt: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
});

function isProfile(value: unknown): value is DashboardProfile {
  return (
    isObject(value) &&
    typeof value.businessName === 'string' &&
    typeof value.city === 'string' &&
    typeof value.intro === 'string' &&
    Array.isArray(value.images) &&
    typeof value.publishStatus === 'string'
  );
}

let profile: DashboardProfile = loadState(STORAGE_KEY, isProfile) ?? initialProfile();

// 初期データ・保存済みの画像は、キーから元のURLを引けるようにしておく
const knownImageUrls = new Map<string, string>();

function rememberImages(target: DashboardProfile) {
  if (target.profileImage !== null && target.profileImageUrl !== null) {
    knownImageUrls.set(target.profileImage, target.profileImageUrl);
  }

  if (target.coverImage !== null && target.coverImageUrl !== null) {
    knownImageUrls.set(target.coverImage, target.coverImageUrl);
  }

  target.images.forEach((image) => knownImageUrls.set(image.key, image.url));
}

rememberImages(profile);

const urlFor = (key: string) => knownImageUrls.get(key) ?? imageUrlFor(key);

const EDITABLE = [
  'prefectureId',
  'city',
  'productionItems',
  'intro',
  'careerStartYear',
  'foundedYear',
  'acceptsExperience',
  'recruiting',
  'profileImage',
  'coverImage',
  'imageKeys',
  'publishStatus',
];

const isOwnImage = (key: string) => key.startsWith(IMAGE_PREFIX) && !key.includes('..');

function textError(value: unknown, max: number | null): string | null {
  if (value === null) return 'この項目はnullにできません。';
  if (typeof value !== 'string') return '有効な文字列を入力してください。';
  if (value.trim() === '') return 'この項目は空にできません。';
  if (max !== null && value.trim().length > max) return `この項目が${max}文字より長くならないようにしてください。`;
  return null;
}

function yearError(value: unknown): string | null {
  if (value === null) return null;
  if (typeof value !== 'number' || !Number.isInteger(value)) return '有効な整数を入力してください。';
  if (value < 1) return 'この値は1以上にしてください。';
  if (value > 9999) return 'この値は9999以下にしてください。';
  if (value > new Date().getFullYear()) return '今年以前の年を入力してください。';
  return null;
}

function getProfile(): MockResult {
  return { status: 200, body: profile };
}

function patchProfile(init?: RequestInit): MockResult {
  const body = readJsonBody(init);

  if (!isObject(body)) {
    return validationError({ nonFieldErrors: ['無効なデータです。辞書型を期待しましたが、別の型が送られました。'] });
  }

  const details: Record<string, string[]> = {};
  const add = (field: string, message: string | null) => {
    if (message !== null) details[field] = [message];
  };

  Object.keys(body).forEach((key) => {
    if (!EDITABLE.includes(key)) add(key, 'この項目は受け付けていません。');
  });

  if ('prefectureId' in body) {
    const id = body.prefectureId;
    add(
      'prefectureId',
      typeof id !== 'number' || !Number.isInteger(id)
        ? '有効な整数を入力してください。'
        : id < 1 || id > 47
          ? '都道府県が見つかりません。'
          : null,
    );
  }

  if ('city' in body) add('city', textError(body.city, 50));
  if ('productionItems' in body) add('productionItems', textError(body.productionItems, 100));
  if ('intro' in body) add('intro', textError(body.intro, null));
  if ('careerStartYear' in body) add('careerStartYear', yearError(body.careerStartYear));
  if ('foundedYear' in body) add('foundedYear', yearError(body.foundedYear));

  for (const field of ['acceptsExperience', 'recruiting']) {
    if (field in body && typeof body[field] !== 'boolean') add(field, '有効な真偽値を入力してください。');
  }

  for (const field of ['profileImage', 'coverImage']) {
    const key = body[field];

    if (field in body && key !== null) {
      add(
        field,
        typeof key !== 'string' || !isOwnImage(key) ? 'アップロードした画像を指定してください。' : null,
      );
    }
  }

  if ('imageKeys' in body) {
    const keys = body.imageKeys;

    if (!Array.isArray(keys)) {
      add('imageKeys', 'リスト形式で入力してください。');
    } else if (keys.length > MAX_IMAGES) {
      add('imageKeys', `この項目は${MAX_IMAGES}個以下にしてください。`);
    } else if (keys.some((key) => typeof key !== 'string' || !isOwnImage(key))) {
      add('imageKeys', 'アップロードした画像を指定してください。');
    } else if (new Set(keys).size !== keys.length) {
      add('imageKeys', '同じ画像を複数指定することはできません。');
    }
  }

  if ('publishStatus' in body && body.publishStatus !== 'public' && body.publishStatus !== 'private') {
    add('publishStatus', `"${String(body.publishStatus)}"は有効な選択肢ではありません。`);
  }

  if (Object.keys(details).length > 0) {
    return validationError(details);
  }

  if (Object.keys(body).length === 0) {
    return validationError({ nonFieldErrors: ['変更する項目を指定してください。'] });
  }

  if ('publishStatus' in body && profile.publishStatus === 'suspended') {
    return conflict('PRODUCER_SUSPENDED', '掲載停止中のため、この操作はできません。運営にお問い合わせください。');
  }

  const next: DashboardProfile = { ...profile, updatedAt: nowIso() };
  const text = (value: unknown) => (value as string).trim();

  if ('prefectureId' in body) next.prefectureId = body.prefectureId as number;
  if ('city' in body) next.city = text(body.city);
  if ('productionItems' in body) next.productionItems = text(body.productionItems);
  if ('intro' in body) next.intro = text(body.intro);
  if ('careerStartYear' in body) next.careerStartYear = body.careerStartYear as number | null;
  if ('foundedYear' in body) next.foundedYear = body.foundedYear as number | null;
  if ('acceptsExperience' in body) next.acceptsExperience = body.acceptsExperience as boolean;
  if ('recruiting' in body) next.recruiting = body.recruiting as boolean;

  if ('profileImage' in body) {
    const key = body.profileImage as string | null;
    next.profileImage = key;
    next.profileImageUrl = key === null ? null : urlFor(key);
  }

  if ('coverImage' in body) {
    const key = body.coverImage as string | null;
    next.coverImage = key;
    next.coverImageUrl = key === null ? null : urlFor(key);
  }

  if ('imageKeys' in body) {
    // 実APIは置き換えのたびに行を作り直すため、ID も新しくなる
    const firstId = Math.max(0, ...profile.images.map(({ id }) => id)) + 1;
    next.images = (body.imageKeys as string[]).map((key, index) => ({
      id: firstId + index,
      key,
      url: urlFor(key),
      sortOrder: index,
    }));
  }

  if ('publishStatus' in body) next.publishStatus = body.publishStatus as 'public' | 'private';

  profile = next;
  rememberImages(profile);
  saveState(STORAGE_KEY, profile);

  return { status: 200, body: profile };
}

export { getProfile, patchProfile };
