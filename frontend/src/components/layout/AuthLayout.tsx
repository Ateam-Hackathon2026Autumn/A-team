import { Outlet } from "react-router";
import Header from "./Header";
import Footer from "./Footer";
import "../../styles/auth.css";

export default function AuthLayout() {
  return (
    <>
      <Header />
      <main id="main" className="auth-page">
        <div className="auth-shell">
          <aside className="auth-aside">
            <div><p className="eyebrow">A NEW CONNECTION</p><h2>つくる人を知る。<br />暮らしが、変わる。</h2><p>おいしい出会いも、新しい挑戦も。<br />あなたと産地をつなぐ場所へ。</p></div>
            <div className="aside-art" aria-hidden="true">🌿</div>
            <small>買う ・ 体験する ・ 働く ・ 学ぶ</small>
          </aside>
          <section className="auth-content"><Outlet /></section>
        </div>
        <p className="auth-note">画面確認用デモです。APIは未接続です。実際の個人情報や普段使うパスワードは入力しないでください。</p>
      </main>
      <Footer />
    </>
  );
}
