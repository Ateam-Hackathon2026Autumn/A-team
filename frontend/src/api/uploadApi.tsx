import { toApiError } from './apiError';
import { getCsrfToken } from './authApi';
import { apiFetch } from './client';

// 画像アップロードAPIのレスポンス
type UploadedImage = {
  // 商品登録などの imageKeys に渡すキー
  key: string;
  // 表示用URL
  url: string;
};

// 画像（JPEG・PNG、5MB以下）をアップロードし、保存用のキーを受け取る
async function uploadImage(file: File): Promise<UploadedImage> {
  const csrfToken = await getCsrfToken();
  const formData = new FormData();
  formData.append('file', file);

  // Content-Type は FormData から自動で付く（境界文字列が必要なため指定しない）
  const response = await apiFetch('/api/v1/uploads/images', {
    method: 'POST',
    headers: { 'X-CSRFToken': csrfToken },
    body: formData,
  });

  if (response.ok) {
    return (await response.json()) as UploadedImage;
  }

  throw await toApiError(response, '画像をアップロードできませんでした');
}

export { uploadImage };
export type { UploadedImage };
