import type { RestMock } from '../../types';

// 画像アップロードAPI POST /api/v1/uploads/images
//
// multipart/form-data の file に画像（JPEG・PNG、5MB 以下）を入れて送る。DB には書き込まない
//   key : S3 のキー（images/{userId}/{UUID}.jpg|png）。
//         商品登録の imageKeys、生産者プロフィール更新の profileImage / coverImage などにそのまま渡す
//   url : プレビュー表示用の URL
//
// エラーにしたい場合は status と body を下記に書き換える
//
// 入力不正（status: 400。file なし・JPEG/PNG 以外など）:
//   {
//     errorCode: 'VALIDATION_ERROR',
//     errorMsg: '入力内容に誤りがあります。',
//     details: { file: ['JPEGまたはPNGの画像を選択してください。'] },
//   }
// 未ログイン（status: 401）:
//   { errorCode: 'UNAUTHENTICATED', errorMsg: 'ログインしてください。' }
// サイズ超過（status: 413。上限 5MB）:
//   { errorCode: 'PAYLOAD_TOO_LARGE', errorMsg: '画像は5MB以下にしてください。' }
const uploadsImageCreate: RestMock = {
  method: 'POST',
  path: '/api/v1/uploads/images',
  status: 201,
  body: {
    key: 'images/1/3f2b8c1e-6a4d-4f0e-9b7a-2d5c8e1f4a90.jpg',
    url: 'https://picsum.photos/seed/upload1/800/600',
  },
};

export { uploadsImageCreate };
