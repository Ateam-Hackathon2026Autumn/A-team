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
//
// 本物の API は画像ごとに別のキーを返すため、モックも呼ばれるたびに連番で別のキー・URL を返す
// （同じキーだと、複数枚追加しても保存時に1枚にまとまってしまう）
let uploadCount = 0;

const uploadsImageCreate: RestMock = {
  method: 'POST',
  path: '/api/v1/uploads/images',
  status: 201,
  get body() {
    uploadCount += 1;

    return {
      key: `images/1/mock-upload-${uploadCount}.jpg`,
      url: `https://picsum.photos/seed/upload${uploadCount}/800/600`,
    };
  },
};

export { uploadsImageCreate };
