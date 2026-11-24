import { useEffect } from "react";
import { matchPath, Navigate, Outlet, useLocation, useNavigate } from "react-router";
import { useAtom, useStore } from "jotai";

import { checkSession } from "../api/authApi";
import { isCheckingSessionAtom, loginStatusAtom, userInfoAtom, pendingAuthNavigationAtom } from "../stores/userAtom";
import type { UserInfo } from "../types/user";

// ログイン済みの場合はアクセスできないページ（ゲスト向け）
const guestOnlyPaths = ["/signin", "/signup"];

// ログインしていないとアクセスできないページ
const memberOnlyPaths = ["/signup/complete", "/mypage/*", "/jobs/:jobId/apply", "/experiences/:experienceId/apply", "/producer-application/*", "/dashboard/*"];

// 生産者でないとアクセスできないページ
const producerOnlyPaths = ["/dashboard/*"];

function matchesAny(patterns: string[], pathname: string) {
  return patterns.some((pattern) => matchPath(pattern, pathname) !== null);
}

// 生産者管理画面を使えるか（承認済み、または審査中）
function canUseDashboard(user: UserInfo) {
  return user.isProducer || user.producerApplicationStatus === "pending";
}

function AuthWrapper() {
  const location = useLocation();
  const navigate = useNavigate();

  // 現在のログイン状況
  const [loginStatus, setLoginStatus] = useAtom(loginStatusAtom);

  // ユーザー情報
  const [userInfo, setUserInfo] = useAtom(userInfoAtom);
  const [authNavigation, setAuthNavigation] = useAtom(pendingAuthNavigationAtom);

  const store = useStore();

  // 現在のパスがどのアクセス制限に該当するか判定
  const isGuestOnlyPage = guestOnlyPaths.includes(location.pathname);
  const isMemberOnlyPage = matchesAny(memberOnlyPaths, location.pathname);
  const isProducerOnlyPage = matchesAny(producerOnlyPaths, location.pathname);

  // 認証画面を離れた後は、一時的な遷移先を次回のログインへ持ち越さない。
  useEffect(() => {
    if (loginStatus === "loggedIn" && !isGuestOnlyPage && authNavigation) {
      setAuthNavigation(null);
    }
  }, [loginStatus, isGuestOnlyPage, authNavigation, setAuthNavigation]);

  // 初期表示時に一度だけログイン状況をサーバーに確認（ユーザー情報も同時に返る）
  useEffect(() => {
    if (loginStatus !== "unchecked") {
      return;
    }

    // 2重呼び出し防止
    if (store.get(isCheckingSessionAtom)) {
      return;
    }
    store.set(isCheckingSessionAtom, true);

    async function fetchLoginStatus() {
      try {
        const session = await checkSession();

        setUserInfo(session.user);
        setLoginStatus(session.authenticated ? "loggedIn" : "loggedOut");
      } catch {
        navigate("/500");
      } finally {
        store.set(isCheckingSessionAtom, false);
      }
    }

    fetchLoginStatus();
  }, [loginStatus, setLoginStatus, setUserInfo, navigate, store]);

  // ログイン状況が確認できていない場合は何も表示しない
  if (loginStatus === "unchecked") {
    return null;
  }

  // 認証成功直後は、状態更新が画面遷移より先に反映されても成功時の遷移先へ。
  // それ以外でログイン済みのユーザーが認証画面を開いた場合はホームへ。
  if (loginStatus === "loggedIn" && isGuestOnlyPage) {
    return (
      <Navigate
        to={authNavigation?.to ?? "/"}
        state={authNavigation?.state}
        replace
      />
    );
  }

  // 未ログインなのに会員向けの画面にいる場合はサインインへ
  // （ログイン後に元の画面へ戻れるよう、遷移元を state で渡す）
  if (loginStatus === "loggedOut" && isMemberOnlyPage) {
    return (
      <Navigate
        to="/signin"
        replace
        state={{ from: location }}
      />
    );
  }

  // 生産者でないのに生産者管理画面にいる場合（URL を直接入力した場合など）はホームへ
  // 未申請・却下・利用停止中が該当（審査中は canUseDashboard で許可）
  if (isProducerOnlyPage && userInfo !== null && !canUseDashboard(userInfo)) {
    return (
      <Navigate
        to="/"
        replace
      />
    );
  }

  // 認証チェックを通過したら、実際のページを表示
  return <Outlet />;
}

export default AuthWrapper;
