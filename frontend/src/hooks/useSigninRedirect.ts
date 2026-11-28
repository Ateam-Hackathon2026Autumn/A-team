import { useCallback, useEffect, useRef } from 'react';
import { useLocation, useNavigate } from 'react-router';
import { useSetAtom } from 'jotai';

import { getAuthReturnPath } from '../utils/authRedirect';
import { loginStatusAtom, userInfoAtom } from '../stores/userAtom';

// 401 時に未ログインへ戻し、遷移元を state.from に入れてサインインへ移動（全画面リロードはしない）
// 戻り値は同一参照なので、依存配列に入れても再実行されない
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
    current.navigate('/signin', {
      replace: true,
      state: { from: getAuthReturnPath(current.location) },
    });
  }, []);
}
