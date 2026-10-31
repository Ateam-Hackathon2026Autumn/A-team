import { Outlet } from "react-router";
import Header from "../components/layout/Header";
import Footer from "../components/layout/Footer";

export default function MainLayout() {
  return (
    <div className="flex min-h-dvh flex-col bg-marche-ivory text-marche-ink">
      <Header />

      <main id="main" tabIndex={-1} className="min-w-0 flex-1">
        <Outlet />
      </main>

      <Footer />
    </div>
  );
}
