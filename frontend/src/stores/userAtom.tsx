import { atom } from 'jotai';

import type { LoginStatus } from '../types/auth';
import type { UserInfo } from '../types/user';

// 現在のログイン状態
const loginStatusAtom = atom<LoginStatus>('unchecked');

// ログインユーザーの情報
const userInfoAtom = atom<UserInfo | null>(null);

// ログインチェックAPIを呼び出し中か（2重呼び出し防止）
const isCheckingSessionAtom = atom(false);

export { loginStatusAtom, userInfoAtom, isCheckingSessionAtom };
