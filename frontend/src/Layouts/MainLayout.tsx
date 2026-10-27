import { Outlet } from 'react-router';

// 一般ユーザー向けの共通レイアウト（ヘッダー・フッターは今後追加）
function MainLayout() {
  return (
    <div className="min-h-dvh bg-[#f4f5f0] text-[#26332b]">
      <main>
        <Outlet />
      </main>
    </div>
  );
}

export default MainLayout;
