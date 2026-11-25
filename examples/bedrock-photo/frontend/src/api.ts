/**
 * 画面と解析 API の接続を担当する。
 * 写真をブラウザ内で JPEG/Base64 に変換し、Lambda に JSON を送る。
 * token は利用者が入力したテスト用パスワードで、AWS の認証情報ではない。
 */
export type PhotoAnalysis = {
  summary: string
  objects: string[]
  texts: string[]
  details: { label: string; value: string }[]
}

export type AnalysisResponse = {
  analysis: PhotoAnalysis
  meta: { elapsed_ms: number; request_id: string }
}

export type SelectedPhoto = {
  name: string
  originalBytes: number
  preview: string
  base64: string
}

const MAX_FILE_BYTES = 20 * 1024 * 1024
// JSON 化で容量が増えるため、変換後の画像本体を API の上限に収める。
const MAX_INPUT_BYTES = 2 * 1024 * 1024
let apiBaseUrl: Promise<string> | null = null

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function getApiBaseUrl(): Promise<string> {
  // 同時呼び出しでも設定の取得を1回にまとめる。失敗した場合は次回再取得する。
  if (!apiBaseUrl) {
    apiBaseUrl = (async () => {
      const response = await fetch('/config.json', { cache: 'no-store', credentials: 'omit', signal: AbortSignal.timeout(10000) })
      if (!response.ok) throw new Error('接続設定を読み込めませんでした。ページを再読み込みしてください。')
      const config: unknown = await response.json()
      if (!config || typeof config !== 'object' || !('apiBaseUrl' in config) || typeof config.apiBaseUrl !== 'string') {
        throw new Error('接続設定の形式を確認できませんでした。')
      }
      // 開発時の空文字は同一 origin の /api を表し、Vite が API へ転送する。
      if (config.apiBaseUrl === '' && import.meta.env.DEV) return ''
      // 接続先の誤設定によって共有パスワードを別のサーバーへ送ることを防ぐ。
      if (!/^https:\/\/[a-z0-9]+\.lambda-url\.[a-z0-9-]+\.on\.aws\/?$/.test(config.apiBaseUrl)) {
        throw new Error('解析の接続先が未設定です。デプロイ手順を確認してください。')
      }
      return config.apiBaseUrl.replace(/\/$/, '')
    })().catch(error => { apiBaseUrl = null; throw error })
  }
  return apiBaseUrl
}

async function requestApi(path: string, token: string, signal: AbortSignal, body?: string): Promise<unknown> {
  const baseUrl = await getApiBaseUrl()
  const response = await fetch(`${baseUrl}${path}`, {
    method: body === undefined ? 'GET' : 'POST',
    credentials: 'omit', // Cookie を使わず、リクエストごとの Bearer ヘッダーで認証する。
    headers: { Authorization: `Bearer ${token}`, ...(body === undefined ? {} : { 'Content-Type': 'application/json' }) },
    body,
    signal,
  })
  const data: unknown = await response.json().catch(() => null)
  if (!response.ok) {
    const message = data && typeof data === 'object' && 'error' in data && typeof data.error === 'string'
      ? data.error : '接続できませんでした。時間をおいてもう一度お試しください。'
    throw new ApiError(response.status, message)
  }
  return data
}

export async function verifyAccess(token: string): Promise<void> {
  // 認証と接続の確認だけを行う。ここでは Bedrock の推論を呼ばない。
  const data = await requestApi('/api/health', token, AbortSignal.timeout(15000))
  if (!data || typeof data !== 'object' || !('status' in data) || data.status !== 'ok') {
    throw new Error('接続先を確認できませんでした。')
  }
}

export async function preparePhoto(file: File): Promise<SelectedPhoto> {
  if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
    throw new Error('JPEG・PNG・WebP の写真を選んでください。HEIC は JPEG などに変換してください。')
  }
  if (file.size === 0 || file.size > MAX_FILE_BYTES) {
    throw new Error('20 MB 以下の写真を選んでください。')
  }

  let bitmap: ImageBitmap
  try {
    // スマートフォンの縦横の向きを反映してから canvas に描画する。
    bitmap = await createImageBitmap(file, { imageOrientation: 'from-image' })
  } catch {
    throw new Error('写真を開けませんでした。別の画像ファイルを選んでください。')
  }

  try {
    // 小さな画像は拡大せず、大きな画像だけ長辺1600px以下へ縮小する。
    const ratio = Math.min(1, 1600 / Math.max(bitmap.width, bitmap.height))
    const canvas = document.createElement('canvas')
    canvas.width = Math.max(1, Math.round(bitmap.width * ratio))
    canvas.height = Math.max(1, Math.round(bitmap.height * ratio))
    const context = canvas.getContext('2d')
    if (!context) throw new Error('このブラウザでは写真を処理できません。')
    // JPEG は透過を持たないため、透過部分の背景色を白に決めておく。
    context.fillStyle = '#ffffff'
    context.fillRect(0, 0, canvas.width, canvas.height)
    context.drawImage(bitmap, 0, 0, canvas.width, canvas.height)
    const preview = canvas.toDataURL('image/jpeg', 0.85)
    // API へは data:image/jpeg;base64, の接頭辞を除いたデータだけを渡す。
    const base64 = preview.split(',')[1]
    if (!base64 || Math.floor(base64.length * 3 / 4) > MAX_INPUT_BYTES) {
      throw new Error('送信する写真が大きすぎます。小さな写真でもう一度お試しください。')
    }
    return { name: file.name, originalBytes: file.size, preview, base64 }
  } finally {
    bitmap.close()
  }
}

function isResponse(value: unknown): value is AnalysisResponse {
  // TypeScript の型は通信相手を検証しないため、受信 JSON の形も実行時に確認する。
  if (!value || typeof value !== 'object') return false
  const data = value as Partial<AnalysisResponse>
  const result = data.analysis
  return !!result && typeof result.summary === 'string'
    && Array.isArray(result.objects) && result.objects.every(item => typeof item === 'string')
    && Array.isArray(result.texts) && result.texts.every(item => typeof item === 'string')
    && Array.isArray(result.details) && result.details.every(item => item
      && typeof item.label === 'string' && typeof item.value === 'string')
    && !!data.meta && typeof data.meta.elapsed_ms === 'number'
    && typeof data.meta.request_id === 'string'
}

export async function analyzePhoto(photo: SelectedPhoto, token: string, signal: AbortSignal): Promise<AnalysisResponse> {
  // preparePhoto() が JPEG に変換済みなので、元ファイルの形式によらず jpeg を送る。
  const body = JSON.stringify({ image: { format: 'jpeg', base64: photo.base64 } })
  const data = await requestApi('/api/analyze', token, signal, body)
  if (!isResponse(data)) throw new Error('読み取り結果の形式を確認できませんでした。もう一度お試しください。')
  return data
}
