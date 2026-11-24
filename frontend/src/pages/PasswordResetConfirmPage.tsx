import { useState, type FormEvent } from 'react';
import { Link, useSearchParams } from 'react-router';
import { confirmPasswordReset } from '../api/authApi';
import ApiError from '../api/apiError';
import Button from '../components/ui/Button';
import { fieldClass } from '../components/ui/ContentPage';

export default function PasswordResetConfirmPage() {
  const [params] = useSearchParams();
  const uid = params.get('uid');
  const token = params.get('token');
  const validLink = Boolean(uid && token && params.getAll('uid').length === 1 && params.getAll('token').length === 1);
  const [password, setPassword] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState('');

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!validLink || !uid || !token || busy) return;
    if (password !== confirmation) { setError('確認用パスワードが一致しません。'); return; }
    setBusy(true);
    setError('');
    try {
      await confirmPasswordReset(uid, token, password);
      setPassword(''); setConfirmation(''); setDone(true);
    } catch (cause) {
      if (cause instanceof ApiError) setError(cause.details.newPassword?.join(' ') || cause.message);
      else setError('通信に失敗しました。もう一度お試しください。');
    } finally { setBusy(false); }
  }

  return <section className="mx-auto w-full max-w-md">
    <h1 className="font-serif text-3xl">パスワード再設定</h1>
    {!validLink ? <p role="alert">再設定リンクが無効です。もう一度再設定を申請してください。</p> : done ? <>
      <p role="status">パスワードを再設定しました。</p><Link to="/signin">ログインへ</Link>
    </> : <form onSubmit={submit} aria-busy={busy} className="space-y-5">
      <label className="block">新しいパスワード<input className={fieldClass} type="password" autoComplete="new-password" minLength={8} maxLength={128} required value={password} onChange={event => setPassword(event.target.value)} /></label>
      <label className="block">新しいパスワード（確認）<input className={fieldClass} type="password" autoComplete="new-password" required value={confirmation} onChange={event => setConfirmation(event.target.value)} /></label>
      {error && <p role="alert" className="text-marche-red">{error}</p>}
      <Button type="submit" disabled={busy}>{busy ? '再設定中…' : 'パスワードを変更する'}</Button>
    </form>}
  </section>;
}
