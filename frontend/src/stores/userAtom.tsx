import { atom } from 'jotai';

import type { LoginStatus } from '../types/auth';
import type { UserInfo } from '../types/user';

// 現在のログイン状態
const loginStatusAtom = atom<LoginStatus>('unchecked');

// ログインユーザーの情報
const userInfoAtom = atom<UserInfo | null>(null);

// ログインチェックAPIを呼び出し中か（2重呼び出し防止）
const isCheckingSessionAtom = atom(false);

type AuthNavigation = { to: string; state?: Record<string, unknown> };
const pendingAuthNavigationAtom = atom<AuthNavigation | null>(null);

// 遷移先をログイン状態より先に設定する。外部ストアの更新をガードが先に
// 検知しても、認証ページからホームへ誤転送せず成功時の遷移先を使える。
const authenticatedNavigationAtom = atom(
  null,
  (
    _get,
    set,
    { user, navigation }: { user: UserInfo; navigation: AuthNavigation },
  ) => {
    set(pendingAuthNavigationAtom, navigation);
    set(userInfoAtom, user);
    set(loginStatusAtom, 'loggedIn');
  },
);

export {
  loginStatusAtom,
  userInfoAtom,
  isCheckingSessionAtom,
  pendingAuthNavigationAtom,
  authenticatedNavigationAtom,
};
