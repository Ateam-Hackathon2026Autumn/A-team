import { createContext, useContext } from 'react';

// 管理画面はスクロールするコンテナが window ではないため、先頭へ戻す処理を DashboardLayout から受け取る。
// レイアウト外で使われた場合は window を先頭へ戻す。
export const DashboardScrollContext = createContext<() => void>(() => window.scrollTo({ top: 0 }));

export function useScrollDashboardToTop(): () => void {
  return useContext(DashboardScrollContext);
}
