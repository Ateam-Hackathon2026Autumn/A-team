import { useCallback, useEffect, useRef } from 'react';
import { useLocation, useNavigate } from 'react-router';
import { useSetAtom } from 'jotai';

import { getAuthReturnPath } from '../utils/authRedirect';
import { loginStatusAtom, userInfoAtom } from '../stores/userAtom';

// セッション切れ（401）時にサインイン画面へ移動する。
// AuthWrapper と同じく認証状態を未ログインに戻し、現在の画面を state.from に保持して、
// ログイン後に元の画面へ戻れるようにする（window.location による全画面再読み込みはしない）。
// 返される関数は再描画しても同一参照のため、useEffect / useCallback の依存配列に入れても再実行されない。
export function useSigninRedirect(): () => void {
  const navigate = useNavigate();
  const location = useLocation();
  const setLoginStatus = useSetAtom(loginStatusAtom);
  const setUserInfo = useSetAtom(userInfoAtom);
  const latest = useRef({ navigate, location, setLoginStatus, setUserInfo });

  useEffect(() => {
    latest.current = { navigate, location, setLoginStatus, setUserInfo };
  });

  return useCallback(() => {
    const current = latest.current;
    current.setUserInfo(null);
    current.setLoginStatus('loggedOut');
    current.navigate('/signin', { replace: true, state: { from: getAuthReturnPath(current.location) } });
  }, []);
}
