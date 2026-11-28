import { useState } from 'react';
import { useSetAtom } from 'jotai';
import { useNavigate } from 'react-router';
import { getConsumerAccount, signOutConsumer } from '../api/consumerAccountApi';
import { usePublicContent } from '../hooks/usePublicContent';
import { loginStatusAtom, userInfoAtom } from '../stores/userAtom';
import { ContentPage, ContentStatus } from '../components/ui/ContentPage';
import { panelClass } from '../components/ui/contentPageValues';
import Button from '../components/ui/Button';
import MyPageNavigation from '../components/mypage/MyPageNavigation';

export default function AccountSettingsPage() {
  const state = usePublicContent(getConsumerAccount);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const setLogin = useSetAtom(loginStatusAtom);
  const setUser = useSetAtom(userInfoAtom);
  const navigate = useNavigate();
  async function signOut() {
    if (busy) return;
    setBusy(true);
    setError('');
    try {
      await signOutConsumer();
      setUser(null);
      setLogin('loggedOut');
      navigate('/', { replace: true });
    } catch (cause) {
      setError(
        cause instanceof Error ? cause.message : 'ログアウトできませんでした。',
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <ContentPage
      eyebrow="ACCOUNT"
      title="アカウント設定"
      intro="ログイン情報とアカウントを管理します。"
    >
      <MyPageNavigation />
      <ContentStatus {...state} />
      {state.data && (
        <div className="max-w-3xl space-y-5">
          <section className={panelClass}>
            <h2 className="mt-0 font-serif text-xl">ログイン情報</h2>
            <dl className="m-0">
              <dt className="text-sm text-marche-muted">メールアドレス</dt>
              <dd className="m-0 break-all font-bold">
                {state.data.user.email}
              </dd>
            </dl>
            <p className="mb-0 text-sm text-marche-green">
              {state.data.user.emailVerified
                ? 'メールアドレス確認済み'
                : 'メールアドレス未確認'}
            </p>
          </section>
          <section className={panelClass}>
            <h2 className="mt-0 font-serif text-xl">パスワード変更</h2>
            <p className="text-sm text-marche-muted">
              この画面からの変更は準備中です。
            </p>
            <Button disabled variant="outline">
              パスワードを変更（準備中）
            </Button>
          </section>
          <section className={panelClass}>
            <h2 className="mt-0 font-serif text-xl">ログアウト</h2>
            <p className="text-sm text-marche-muted">
              この端末からログアウトします。
            </p>
            {error && (
              <p role="alert" className="text-marche-red">
                {error}
              </p>
            )}
            <Button onClick={signOut} disabled={busy} variant="outline">
              {busy ? 'ログアウト中…' : 'ログアウトする'}
            </Button>
          </section>
          <section className={panelClass}>
            <h2 className="mt-0 font-serif text-xl">退会</h2>
            <p className="text-sm text-marche-muted">
              退会手続きは準備中です。現在この画面からアカウントを削除することはできません。
            </p>
            <Button disabled variant="outline">
              退会手続き（準備中）
            </Button>
          </section>
        </div>
      )}
    </ContentPage>
  );
}
