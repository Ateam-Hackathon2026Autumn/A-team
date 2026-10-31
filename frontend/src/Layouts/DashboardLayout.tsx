import { Outlet } from 'react-router';

// 生産者管理画面の共通レイアウト（サイドバーは今後追加）
function DashboardLayout() {
  return (
    <div className="min-h-dvh bg-[#f4f5f0] text-[#26332b]">
      <main>
        <Outlet />
      </main>
    </div>
  );
}

export default DashboardLayout;
