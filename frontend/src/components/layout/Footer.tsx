import { Link } from "react-router";
export default function Footer() {
  return (
    <footer className="footer">
      <div className="wrap">
        <div className="row">
          <Link className="brand" to="/"><span className="mark">つ</span>つながるマルシェ</Link>
          <div className="footer-links"><Link to="/signup?purpose=producer">生産者の方へ</Link><Link to="/signin">ログイン</Link><Link to="/signup">新規登録</Link></div>
        </div>
        <p className="copyright">© 2026 つながるマルシェ · Hackathon prototype</p>
      </div>
    </footer>
  );
}
