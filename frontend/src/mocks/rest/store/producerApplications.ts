import type {
  MyProducerApplication,
  MyProducerApplicationProducer,
  ProducerApplicationAccepted,
} from '../../../types/producerApplication';
import { hoursFromNow } from '../../helpers';
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

const STORAGE_KEY = 'mock:producerApplication:v1';

const GENRES = ['agriculture', 'livestock', 'fishery'];
const STATUSES = ['pending', 'approved', 'rejected', 'returned'];
const FIELDS = [
  'businessName',
  'representativeName',
  'genre',
  'prefectureId',
  'city',
  'productionItems',
  'intro',
  'acceptsExperience',
  'recruiting',
  'careerStartYear',
  'foundedYear',
  'profileImage',
  'coverImage',
  'applicationReason',
];

const initialApplication = (): MyProducerApplication => ({
  applicationId: 1,
  producerId: 1,
  status: 'approved',
  reviewComment: null,
  submittedAt: hoursFromNow(-24 * 400),
  reviewedAt: hoursFromNow(-24 * 397),
  canResubmit: false,
  producer: {
    businessName: '山本農園',
    representativeName: '山本 健太',
    genre: 'agriculture',
    prefectureId: 20,
    city: '安曇野市',
    productionItems: 'りんご・ぶどう',
    intro:
      '北アルプスの雪どけ水で育てる、蜜たっぷりのりんご。三代目として減農薬栽培に取り組んでいます。',
    acceptsExperience: true,
    recruiting: true,
    careerStartYear: 2015,
    foundedYear: null,
    profileImage: 'producers/yamamoto-farm-profile.jpg',
    coverImage: 'producers/yamamoto-farm-cover.jpg',
    profileImageUrl: 'https://picsum.photos/seed/producer1-profile/800/600',
    coverImageUrl: 'https://picsum.photos/seed/producer1-cover/800/600',
    applicationReason:
      '祖父の代から続く園地を、次の世代にも残したいと思い会社を辞めて戻りました。',
  },
});

function isApplication(value: unknown): value is MyProducerApplication {
  return (
    isObject(value) &&
    typeof value.applicationId === 'number' &&
    typeof value.producerId === 'number' &&
    typeof value.status === 'string' &&
    STATUSES.includes(value.status) &&
    typeof value.canResubmit === 'boolean' &&
    isObject(value.producer) &&
    typeof value.producer.businessName === 'string'
  );
}

let currentApplication: MyProducerApplication =
  loadState(STORAGE_KEY, isApplication) ?? initialApplication();

const knownUrls = new Map<string, string>();
if (
  currentApplication.producer.profileImage &&
  currentApplication.producer.profileImageUrl
) {
  knownUrls.set(
    currentApplication.producer.profileImage,
    currentApplication.producer.profileImageUrl,
  );
}
if (
  currentApplication.producer.coverImage &&
  currentApplication.producer.coverImageUrl
) {
  knownUrls.set(
    currentApplication.producer.coverImage,
    currentApplication.producer.coverImageUrl,
  );
}

const urlFor = (key: string | null) =>
  key === null ? null : (knownUrls.get(key) ?? imageUrlFor(key));

function validateFields(
  body: Record<string, unknown>,
  partial: boolean,
): Record<string, string[]> {
  const details: Record<string, string[]> = {};
  const add = (field: string, msg: string | null) => {
    if (msg !== null) details[field] = [msg];
  };

  for (const key of Object.keys(body)) {
    if (!FIELDS.includes(key)) {
      add(key, 'この項目は受け付けていません。');
    }
  }

  const checkText = (field: string, max: number | null) => {
    if (!(field in body)) {
      if (!partial) add(field, 'この項目は必須です。');
      return;
    }
    const val = body[field];
    if (val === null) add(field, 'この項目はnullにできません。');
    else if (typeof val !== 'string')
      add(field, '有効な文字列を入力してください。');
    else if (val.trim() === '') add(field, 'この項目は空にできません。');
    else if (max !== null && val.trim().length > max) {
      add(field, `この項目が${max}文字より長くならないようにしてください。`);
    }
  };

  checkText('businessName', 100);
  checkText('representativeName', 100);
  checkText('city', 50);
  checkText('productionItems', 100);
  checkText('intro', null);

  if (!partial || 'genre' in body) {
    const g = body.genre;
    if (g === undefined) add('genre', 'この項目は必須です。');
    else if (typeof g !== 'string' || !GENRES.includes(g)) {
      add('genre', `"${String(g)}"は有効な選択肢ではありません。`);
    }
  }

  if (!partial || 'prefectureId' in body) {
    const p = body.prefectureId;
    if (p === undefined) add('prefectureId', 'この項目は必須です。');
    else if (typeof p !== 'number' || !Number.isInteger(p)) {
      add('prefectureId', '有効な整数を入力してください。');
    } else if (p < 1 || p > 47) {
      add('prefectureId', '都道府県が見つかりません。');
    }
  }

  for (const bField of ['acceptsExperience', 'recruiting']) {
    if (!partial || bField in body) {
      if (!(bField in body)) add(bField, 'この項目は必須です。');
      else if (typeof body[bField] !== 'boolean')
        add(bField, '有効な真偽値を入力してください。');
    }
  }

  const thisYear = new Date().getFullYear();
  for (const yField of ['careerStartYear', 'foundedYear']) {
    if (yField in body && body[yField] !== null && body[yField] !== undefined) {
      const y = body[yField];
      if (typeof y !== 'number' || !Number.isInteger(y))
        add(yField, '有効な整数を入力してください。');
      else if (y < 1) add(yField, 'この値は1以上にしてください。');
      else if (y > 9999) add(yField, 'この値は9999以下にしてください。');
      else if (y > thisYear) add(yField, '今年以前の年を入力してください。');
    }
  }

  for (const imgField of ['profileImage', 'coverImage']) {
    if (
      imgField in body &&
      body[imgField] !== null &&
      body[imgField] !== undefined
    ) {
      const k = body[imgField];
      if (
        typeof k !== 'string' ||
        k.trim() === '' ||
        k.length > 500 ||
        k.includes('..')
      ) {
        add(imgField, 'アップロードした画像を指定してください。');
      }
    }
  }

  if (
    'applicationReason' in body &&
    body.applicationReason !== null &&
    body.applicationReason !== undefined
  ) {
    if (typeof body.applicationReason !== 'string') {
      add('applicationReason', '有効な文字列を入力してください。');
    }
  }

  if (
    partial &&
    Object.keys(details).length === 0 &&
    Object.keys(body).length === 0
  ) {
    details.nonFieldErrors = ['変更する項目を指定してください。'];
  }

  return details;
}

function applyChanges(
  base: MyProducerApplicationProducer,
  changes: Record<string, unknown>,
): MyProducerApplicationProducer {
  const next = { ...base };
  if (typeof changes.businessName === 'string')
    next.businessName = changes.businessName.trim();
  if (typeof changes.representativeName === 'string')
    next.representativeName = changes.representativeName.trim();
  if (typeof changes.genre === 'string')
    next.genre = changes.genre as MyProducerApplicationProducer['genre'];
  if (typeof changes.prefectureId === 'number')
    next.prefectureId = changes.prefectureId;
  if (typeof changes.city === 'string') next.city = changes.city.trim();
  if (typeof changes.productionItems === 'string')
    next.productionItems = changes.productionItems.trim();
  if (typeof changes.intro === 'string') next.intro = changes.intro.trim();
  if (typeof changes.acceptsExperience === 'boolean')
    next.acceptsExperience = changes.acceptsExperience;
  if (typeof changes.recruiting === 'boolean')
    next.recruiting = changes.recruiting;
  if ('careerStartYear' in changes)
    next.careerStartYear = (changes.careerStartYear as number | null) ?? null;
  if ('foundedYear' in changes)
    next.foundedYear = (changes.foundedYear as number | null) ?? null;
  if ('profileImage' in changes) {
    const key = (changes.profileImage as string | null) ?? null;
    next.profileImage = key;
    next.profileImageUrl = urlFor(key);
  }
  if ('coverImage' in changes) {
    const key = (changes.coverImage as string | null) ?? null;
    next.coverImage = key;
    next.coverImageUrl = urlFor(key);
  }
  if ('applicationReason' in changes) {
    const reason =
      typeof changes.applicationReason === 'string'
        ? changes.applicationReason.trim()
        : '';
    next.applicationReason = reason || null;
  }
  return next;
}

export function getMockProducerApplication(): MockResult {
  return { status: 200, body: currentApplication };
}

export function postMockProducerApplication(init?: RequestInit): MockResult {
  const body = readJsonBody(init);
  if (!isObject(body)) {
    return validationError({ nonFieldErrors: ['無効なデータです。'] });
  }
  const details = validateFields(body, false);
  if (Object.keys(details).length > 0) {
    return validationError(details);
  }

  const submittedAt = nowIso();
  const producer = applyChanges(
    {
      businessName: '',
      representativeName: '',
      genre: 'agriculture',
      prefectureId: 20,
      city: '',
      productionItems: '',
      intro: '',
      acceptsExperience: false,
      recruiting: false,
      careerStartYear: null,
      foundedYear: null,
      profileImage: null,
      coverImage: null,
      profileImageUrl: null,
      coverImageUrl: null,
      applicationReason: null,
    },
    body,
  );
  const nextId = currentApplication.applicationId + 1;
  currentApplication = {
    applicationId: nextId,
    producerId: 7,
    status: 'pending',
    reviewComment: null,
    submittedAt,
    reviewedAt: null,
    canResubmit: false,
    producer,
  };
  saveState(STORAGE_KEY, currentApplication);

  const accepted: ProducerApplicationAccepted = {
    message: '生産者登録申請を受け付けました。',
    producerId: currentApplication.producerId,
    applicationId: currentApplication.applicationId,
    approvalStatus: 'pending',
    applicationStatus: 'pending',
    publishStatus: 'draft',
    isProducer: false,
    submittedAt,
  };
  return { status: 201, body: accepted };
}

export function patchMockProducerApplication(init?: RequestInit): MockResult {
  const body = readJsonBody(init);
  if (!isObject(body)) {
    return validationError({ nonFieldErrors: ['無効なデータです。'] });
  }

  const topDetails: Record<string, string[]> = {};
  for (const key of Object.keys(body)) {
    if (key !== 'applicationId' && key !== 'changes') {
      topDetails[key] = ['この項目は受け付けていません。'];
    }
  }
  if (
    typeof body.applicationId !== 'number' ||
    !Number.isInteger(body.applicationId) ||
    body.applicationId < 1
  ) {
    topDetails.applicationId = ['有効な整数を入力してください。'];
  }
  if (!isObject(body.changes)) {
    topDetails.changes = ['有効なオブジェクトを入力してください。'];
  }
  if (Object.keys(topDetails).length > 0) {
    return validationError(topDetails);
  }

  const changes = body.changes as Record<string, unknown>;
  const changeDetails = validateFields(changes, true);
  if (Object.keys(changeDetails).length > 0) {
    return validationError(changeDetails);
  }

  if (body.applicationId !== currentApplication.applicationId) {
    return conflict(
      'APPLICATION_CONFLICT',
      '申請情報が更新されました。再取得してください。',
    );
  }
  if (!['returned', 'rejected'].includes(currentApplication.status)) {
    return conflict(
      'APPLICATION_NOT_RETURNED',
      '差し戻し・却下された申請のみ再申請できます。',
    );
  }

  const submittedAt = nowIso();
  const nextId = currentApplication.applicationId + 1;
  currentApplication = {
    applicationId: nextId,
    producerId: currentApplication.producerId,
    status: 'pending',
    reviewComment: null,
    submittedAt,
    reviewedAt: null,
    canResubmit: false,
    producer: applyChanges(currentApplication.producer, changes),
  };
  saveState(STORAGE_KEY, currentApplication);

  const accepted: ProducerApplicationAccepted = {
    message: '修正内容を保存し、再申請を受け付けました。',
    producerId: currentApplication.producerId,
    applicationId: currentApplication.applicationId,
    approvalStatus: 'pending',
    applicationStatus: 'pending',
    publishStatus: 'draft',
    isProducer: false,
    submittedAt,
  };
  return { status: 200, body: accepted };
}
