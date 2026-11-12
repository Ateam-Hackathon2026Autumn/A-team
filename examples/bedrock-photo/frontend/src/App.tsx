import { useEffect, useRef, useState } from 'react'
import type { ChangeEvent, DragEvent, FormEvent, ReactNode } from 'react'
import { analyzePhoto, ApiError, preparePhoto, verifyAccess } from './api'
import type { AnalysisResponse, SelectedPhoto } from './api'

// UI の状態管理と表示を担当する。画像加工・HTTP 通信の実装は api.ts にまとめる。
function Icon({ name, size = 20 }: { name: 'image' | 'arrow' | 'scan' | 'check' | 'upload' | 'copy' | 'close'; size?: number }) {
  const paths: Record<string, ReactNode> = {
    image: <><rect x="3" y="3" width="18" height="18" rx="3" /><circle cx="8.5" cy="8.5" r="1.5" /><path d="m21 15-5-5L5 21" /></>,
    arrow: <><path d="M4 12h15m-5-5 5 5-5 5" /></>,
    scan: <><path d="M8 3H4a1 1 0 0 0-1 1v4m13-5h4a1 1 0 0 1 1 1v4M3 16v4a1 1 0 0 0 1 1h4m8 0h4a1 1 0 0 0 1-1v-4M3 12h18" /></>,
    check: <path d="m5 12 4 4L19 6" />,
    upload: <><path d="M12 16V3m-5 5 5-5 5 5M4 16v4a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-4" /></>,
    copy: <><rect x="8" y="8" width="12" height="13" rx="2" /><path d="M16 8V4a1 1 0 0 0-1-1H4a1 1 0 0 0-1 1v11a1 1 0 0 0 1 1h4" /></>,
    close: <path d="m6 6 12 12M6 18 18 6" />,
  }
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]}</svg>
}

function fileSize(bytes: number) {
  return bytes >= 1024 * 1024 ? `${(bytes / 1024 / 1024).toFixed(1)} MB` : `${Math.ceil(bytes / 1024)} KB`
}

function Brand() {
  return <a className="brand" href="/index.html" aria-label="Photo Notes ホーム"><span className="brand-mark"><Icon name="scan" size={22} /></span><span>photo notes<span className="brand-dot">.</span></span></a>
}

export default function App() {
  const input = useRef<HTMLInputElement>(null)
  // 画像の準備や API の応答が遅れて届いても、以前の選択結果で画面を上書きしない。
  const currentSelection = useRef(0)
  const activeRequest = useRef<AbortController | null>(null)
  const [photo, setPhoto] = useState<SelectedPhoto | null>(null)
  const [result, setResult] = useState<AnalysisResponse | null>(null)
  const [preparing, setPreparing] = useState(false)
  const [loading, setLoading] = useState(false)
  const [dragging, setDragging] = useState(false)
  const [error, setError] = useState('')
  const [copied, setCopied] = useState(false)
  // 認証成功後の共有パスワードをメモリだけに保持する。リロード時には再入力する。
  const [token, setToken] = useState('')
  const [password, setPassword] = useState('')
  const [accessError, setAccessError] = useState('')
  const [signingIn, setSigningIn] = useState(false)

  useEffect(() => () => { activeRequest.current?.abort(); currentSelection.current += 1 }, [])

  async function signIn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!password || signingIn) return
    setSigningIn(true)
    setAccessError('')
    try {
      // JWT 等を取得するログインではなく、入力したパスワードを API で照合する。
      await verifyAccess(password)
      setToken(password)
      setPassword('')
    } catch (failure) {
      setAccessError(failure instanceof Error ? failure.message : '接続できませんでした。')
    } finally {
      setSigningIn(false)
    }
  }

  async function selectFile(file?: File) {
    if (!file) return
    const selection = ++currentSelection.current
    // 選択し直した写真の結果と混ざらないよう、以前の通信と結果表示を解除する。
    activeRequest.current?.abort()
    activeRequest.current = null
    setLoading(false)
    setPreparing(true)
    setError('')
    setResult(null)
    setPhoto(null)
    setCopied(false)
    try {
      const prepared = await preparePhoto(file)
      if (selection === currentSelection.current) setPhoto(prepared)
    } catch (failure) {
      if (selection === currentSelection.current) setError(failure instanceof Error ? failure.message : '写真を選択できませんでした。')
    } finally {
      if (selection === currentSelection.current) setPreparing(false)
    }
  }

  function onFileChange(event: ChangeEvent<HTMLInputElement>) {
    void selectFile(event.target.files?.[0])
    event.target.value = ''
  }

  function onDrop(event: DragEvent<HTMLButtonElement>) {
    event.preventDefault()
    setDragging(false)
    if (!loading && !preparing) void selectFile(event.dataTransfer.files[0])
  }

  async function analyze() {
    if (!photo || loading) return
    const controller = new AbortController()
    activeRequest.current = controller
    setLoading(true)
    setError('')
    setResult(null)
    setCopied(false)
    // 同期 API の応答を最大75秒待つ。中断してもサーバー側の推論停止は保証されない。
    const timer = window.setTimeout(() => controller.abort('timeout'), 75000)
    try {
      const response = await analyzePhoto(photo, token, controller.signal)
      if (activeRequest.current === controller) setResult(response)
    } catch (failure) {
      if (activeRequest.current !== controller) return
      // 認証が拒否された場合はパスワード入力へ戻し、それ以外は結果欄に表示する。
      if (failure instanceof ApiError && failure.status === 401) {
        setToken('')
        setAccessError('テスト用パスワードをもう一度入力してください。')
      } else if (controller.signal.aborted) setError('読み取りがタイムアウトしました。時間をおいてもう一度お試しください。')
      else setError(failure instanceof Error ? failure.message : '通信できませんでした。接続を確認してください。')
    } finally {
      window.clearTimeout(timer)
      if (activeRequest.current === controller) { setLoading(false); activeRequest.current = null }
    }
  }

  function clear() {
    currentSelection.current += 1
    activeRequest.current?.abort()
    activeRequest.current = null
    setPhoto(null)
    setResult(null)
    setLoading(false)
    setPreparing(false)
    setError('')
    setCopied(false)
  }

  async function copyResult() {
    if (!result) return
    // 利用者が明示的に押したときだけ、解析結果部分をクリップボードへコピーする。
    try { await navigator.clipboard.writeText(JSON.stringify(result.analysis, null, 2)); setCopied(true) }
    catch { setError('コピーできませんでした。JSON を開いてテキストを選択してください。') }
  }

  const status = loading ? '読み取り中' : result ? '読み取り完了' : '待機中'

  // 認証前はパスワード画面、認証後は写真選択・解析結果の画面を表示する。
  if (!token) {
    return <div className="app-shell">
      <header className="site-header"><Brand /><span className="test-label"><span /> PHOTO READING TEST</span></header>
      <main className="access-main">
        <form className="access-card" onSubmit={event => void signIn(event)}>
          <span className="brand-mark"><Icon name="scan" size={22} /></span>
          <p className="eyebrow">TEST WORKSPACE</p>
          <h1>写真の読み取りをはじめる</h1>
          <p>共有されたテスト用パスワードを入力してください。</p>
          <label htmlFor="test-password">パスワード</label>
          <input id="test-password" type="password" autoComplete="current-password" value={password} onChange={event => setPassword(event.target.value)} disabled={signingIn} required />
          {accessError && <div className="error-message" role="alert">{accessError}</div>}
          <button className="analyze-button" type="submit" disabled={!password || signingIn}>{signingIn ? '接続を確認しています…' : 'テストページを開く'}<Icon name="arrow" /></button>
        </form>
        <footer className="page-footer"><span>PHOTO NOTES / TEST WORKSPACE</span><span>Powered by Amazon Bedrock · Claude Haiku 4.5</span></footer>
      </main>
    </div>
  }

  return (
    <div className="app-shell">
      <header className="site-header">
        <Brand />
        <span className="test-label"><span /> PHOTO READING TEST</span>
      </header>

      <main>
        <div className="intro"><p className="eyebrow">A CLOSER LOOK</p><h1>写真から、情報をひらく。</h1><p className="intro-description">写っているものも、そこにある文字も。<br className="mobile-break" /> 写真を選んで、読み取った情報を確認しましょう。</p></div>

        <div className="workspace">
          <section className="photo-panel" aria-labelledby="photo-heading">
            <div className="panel-heading"><div><span className="step">01</span><h2 id="photo-heading">写真を選ぶ</h2></div><span className="panel-caption">YOUR PHOTO</span></div>
            <input ref={input} type="file" accept="image/jpeg,image/png,image/webp" className="file-input" aria-label="読み取る写真" onChange={onFileChange} disabled={loading || preparing} />

            <button type="button" className={`drop-zone ${photo ? 'has-photo' : ''} ${dragging ? 'is-dragging' : ''}`} onClick={() => input.current?.click()} onDragOver={event => { event.preventDefault(); if (!loading && !preparing) setDragging(true) }} onDragLeave={() => setDragging(false)} onDrop={onDrop} disabled={loading || preparing} aria-label={photo ? '別の写真を選ぶ' : '写真を選ぶ、またはここにドラッグ＆ドロップ'}>
              {photo ? <><img src={photo.preview} alt="選択した写真のプレビュー" /><span className="replace-photo"><Icon name="image" size={16} /> 写真を変更</span></> : <div className="upload-prompt"><span className="upload-art"><Icon name="image" size={34} /><span className="upload-plus">+</span></span><strong>{preparing ? '写真を準備しています…' : '写真をここにドロップ'}</strong><span>または <span className="select-link">ファイルを選択</span></span><small>JPEG・PNG・WebP ／ 20 MB まで</small></div>}
            </button>

            <div className="file-line">{photo ? <><Icon name="image" size={16} /><span title={photo.name}>{photo.name}</span><small>{fileSize(photo.originalBytes)}</small><button className="icon-button" type="button" onClick={clear} disabled={loading} aria-label="写真を取り消す"><Icon name="close" size={15} /></button></> : <><Icon name="upload" size={15} /><span>{preparing ? '送信に適したサイズに調整中' : '写真は1枚ずつ読み取れます'}</span></>}</div>

            <button className="analyze-button" type="button" disabled={!photo || loading || preparing} onClick={() => void analyze()}>{loading ? <><span className="spinner" />読み取っています…</> : <>写真を読み取る<Icon name="arrow" /></>}</button>
            <p className="privacy-note">このページには写真の保存機能はありません。</p>
          </section>

          <section className={`result-panel ${result ? 'has-result' : ''}`} aria-labelledby="result-heading" aria-busy={loading}>
            <div className="panel-heading"><div><span className="step">02</span><h2 id="result-heading">読み取り結果</h2></div><span className={`status ${loading ? 'is-loading' : result ? 'is-complete' : ''}`} role="status"><span />{status}</span></div>

            {error && <div className="error-message" role="alert">{error}</div>}

            {result ? <div className="result-content" aria-live="polite">
              <div className="result-summary"><span className="result-kicker"><Icon name="check" size={15} /> 写真の内容</span><p>{result.analysis.summary}</p></div>
              <div className="result-section"><h3>写っているもの</h3>{result.analysis.objects.length ? <div className="object-tags">{result.analysis.objects.map((object, index) => <span key={`${index}-${object}`}>{object}</span>)}</div> : <p className="muted">識別できるものはありませんでした。</p>}</div>
              <div className="result-section"><h3>読み取れた文字</h3>{result.analysis.texts.length ? <div className="recognized-text">{result.analysis.texts.map((text, index) => <p key={index}>{text}</p>)}</div> : <p className="muted">文字は見つかりませんでした。</p>}</div>
              {result.analysis.details.length > 0 && <div className="result-section"><h3>その他の情報</h3><dl className="details-list">{result.analysis.details.map((detail, index) => <div key={index}><dt>{detail.label}</dt><dd>{detail.value}</dd></div>)}</dl></div>}
              <div className="result-bottom"><span>{(result.meta.elapsed_ms / 1000).toFixed(1)} 秒で読み取り</span><button className="copy-button" type="button" onClick={() => void copyResult()}><Icon name={copied ? 'check' : 'copy'} size={15} />{copied ? 'コピーしました' : '結果をコピー'}</button></div>
              <details className="raw-json"><summary>JSON を表示</summary><pre>{JSON.stringify(result, null, 2)}</pre></details>
            </div> : <div className={`empty-result ${loading ? 'reading' : ''}`} aria-live="polite"><span className="result-art"><Icon name="scan" size={32} /></span><h3>{loading ? '写真をじっくり読み取り中' : '写真の情報が、ここに。'}</h3><p>{loading ? '内容を整理しています。そのままお待ちください。' : <>写真を選んで「写真を読み取る」を押すと、<br />読み取った情報が表示されます。</>}</p>{loading ? <span className="progress-track"><span /></span> : <span className="empty-rule" />}</div>}
          </section>
        </div>

        <footer className="page-footer"><span>PHOTO NOTES <span className="footer-separator">/</span> TEST WORKSPACE</span><span>Powered by Amazon Bedrock · Claude Haiku 4.5</span></footer>
      </main>
    </div>
  )
}
