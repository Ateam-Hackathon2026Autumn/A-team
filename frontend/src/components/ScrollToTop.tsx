import { useEffect } from 'react';
import { useLocation } from 'react-router';

// パス（pathname）が変わったとき、ページ先頭へスクロールする。
// クエリやハッシュだけの変化では動かさない（絞り込みやアンカー移動を妨げないため）。
export default function ScrollToTop() {
  const { pathname } = useLocation();

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);

  return null;
}
