import type { DashboardStory, StoryTextField } from '../../../types/dashboardStory';
import type { MockResult } from '../../types';
import { conflict, isObject, loadState, nowIso, readJsonBody, saveState, validationError } from './common';

// 生産者ストーリー（GET・PUT /api/v1/dashboard/story）のモックストア
//
// 実API（backend/api/views/dashboard/story.py・serializers/dashboard/story.py）に合わせる:
//   - 形は {craft, method, process, environment, reason, goal, publishStatus, updatedAt}（ER図の producer_stories）
//   - PUT は7項目すべて必須。定義にない項目は 400「この項目は受け付けていません。」
//   - 本文は null か2,000文字までの文字列。前後の空白を除き、空なら null
//   - publishStatus は draft・public・private。public には本文が1項目以上必要（400 details.publishStatus）
//   - 運営がストーリーを掲載停止中（suspended）は 409 STORY_SUSPENDED
//   - ETag・If-Match・Idempotency-Key は使わない。初回保存も 200
//
// 保存した内容は sessionStorage に持つ（再読み込みしても消えない。タブを閉じると初期状態に戻る）

const STORAGE_KEY = 'mock:dashboardStory:v1';

const TEXT_FIELDS: StoryTextField[] = ['craft', 'method', 'process', 'environment', 'reason', 'goal'];
const EDITABLE_STATUSES = ['draft', 'public', 'private'];
const ALL_STATUSES = [...EDITABLE_STATUSES, 'suspended'];
const MAX_TEXT = 2000;

// ログイン中の生産者（山本農園）のストーリー
const initialStory = (): DashboardStory => ({
  craft:
    '樹上でじっくり完熟させてから収穫しています。見た目よりも、ひと口目の甘さと香りを大切にしています。',
  method:
    '草生栽培・減農薬（県基準の50%以下）。下草を生やして土の力を引き出し、農薬は県基準の半分以下に抑えています。',
  process:
    '春の摘花・摘果から秋の収穫まで、1本ずつ手作業で手入れしています。収穫したりんごはその日のうちに選果して出荷します。',
  environment: '園地の下草は刈り取って土に戻し、化学肥料に頼らない土づくりを続けています。',
  reason: '祖父の代から続く園地を、次の世代にも残したいと思い会社を辞めて戻りました。',
  goal: '収穫体験と短期スタッフ受け入れで、りんご産地の担い手を増やしたい。',
  publishStatus: 'public',
  updatedAt: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
});

function isStory(value: unknown): value is DashboardStory {
  return (
    isObject(value) &&
    TEXT_FIELDS.every((field) => value[field] === null || typeof value[field] === 'string') &&
    typeof value.publishStatus === 'string' &&
    ALL_STATUSES.includes(value.publishStatus) &&
    (value.updatedAt === null || typeof value.updatedAt === 'string')
  );
}

let story: DashboardStory = loadState(STORAGE_KEY, isStory) ?? initialStory();

function getStory(): MockResult {
  return { status: 200, body: story };
}

function putStory(init?: RequestInit): MockResult {
  const body = readJsonBody(init);

  if (!isObject(body)) {
    return validationError({ nonFieldErrors: ['無効なデータです。辞書型を期待しましたが、別の型が送られました。'] });
  }

  const details: Record<string, string[]> = {};
  const texts = {} as Record<StoryTextField, string | null>;

  for (const key of Object.keys(body)) {
    if (!TEXT_FIELDS.includes(key as StoryTextField) && key !== 'publishStatus') {
      details[key] = ['この項目は受け付けていません。'];
    }
  }

  for (const field of TEXT_FIELDS) {
    const value = body[field];

    if (!(field in body)) {
      details[field] = ['この項目は必須です。'];
    } else if (value === null) {
      texts[field] = null;
    } else if (typeof value !== 'string') {
      details[field] = ['有効な文字列を入力してください。'];
    } else if (value.trim().length > MAX_TEXT) {
      details[field] = [`この項目が${MAX_TEXT}文字より長くならないようにしてください。`];
    } else {
      texts[field] = value.trim() === '' ? null : value.trim();
    }
  }

  const status = body.publishStatus;

  if (!('publishStatus' in body)) {
    details.publishStatus = ['この項目は必須です。'];
  } else if (typeof status !== 'string' || !EDITABLE_STATUSES.includes(status)) {
    details.publishStatus = [`"${String(status)}"は有効な選択肢ではありません。`];
  }

  if (Object.keys(details).length > 0) {
    return validationError(details);
  }

  if (status === 'public' && TEXT_FIELDS.every((field) => texts[field] === null)) {
    return validationError({ publishStatus: ['公開するには本文を1項目以上入力してください。'] });
  }

  if (story.publishStatus === 'suspended') {
    return conflict(
      'STORY_SUSPENDED',
      'このストーリーは運営により掲載停止中です。運営にお問い合わせください。',
    );
  }

  story = { ...texts, publishStatus: status as DashboardStory['publishStatus'], updatedAt: nowIso() };
  saveState(STORAGE_KEY, story);

  return { status: 200, body: story };
}

export { getStory, putStory };
