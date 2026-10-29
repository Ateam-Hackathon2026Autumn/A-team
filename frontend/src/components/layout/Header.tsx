import { Link, useLocation } from "react-router";

const links = [
  { href: "#products", label: "買う" },
  { href: "#experiences", label: "体験する" },
  { href: "#jobs", label: "働く" },
  { href: "#learn", label: "学ぶ" },
];

export default function Header() {
  const isHome = useLocation().pathname === "/";
  return (
    <>
      <a className="skip" href="#main">本文へ</a>
      <div className="demo">2026 秋ハッカソン · 画面サンプル｜掲載情報は架空です。登録・ログインはデモ動作です。</div>
      <header className="header">
        <div className="wrap bar">
          <Link className="brand" to="/"><span className="mark">つ</span>つながるマルシェ</Link>
          {isHome && <nav className="nav" aria-label="メインメニュー">{links.map((link) => <a href={link.href} key={link.href}>{link.label}</a>)}</nav>}
          <div className="actions">
            <Link className={isHome ? "plain" : "btn outline"} to="/signin">ログイン</Link>
            {isHome && <Link className="btn" to="/signup">新規登録</Link>}
          </div>
        </div>
      </header>
    </>
  );
}
