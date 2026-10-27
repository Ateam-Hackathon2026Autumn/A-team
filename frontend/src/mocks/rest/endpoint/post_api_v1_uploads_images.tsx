import type { RestMock } from '../../types';

// 画像アップロードAPI POST /api/v1/uploads/images
//
// ※ 仕様書が未作成のため、レスポンスは仮の形（仕様が決まったら合わせて直す）
//   key : 生産者登録などの profileImage / coverImage に渡す S3 のキー
//   url : プレビュー表示用の URL
//
// 入力不正（400。形式・サイズ違反など）:
//   {
//     errorCode: 'VALIDATION_ERROR',
//     errorMsg: '入力内容に誤りがあります。',
//     details: { file: ['JPEG または PNG の画像を選択してください。'] },
//   }
//
// 未ログイン（401）:
//   { errorCode: 'NOT_AUTHENTICATED', errorMsg: 'ログインしてください。' }
const uploadsImageCreate: RestMock = {
  method: 'POST',
  path: '/api/v1/uploads/images',
  status: 201,
  body: {
    imageId: 101,
    key: 'uploads/images/mock-upload-101.jpg',
    url: 'https://picsum.photos/seed/upload101/800/600',
  },
};

export { uploadsImageCreate };
