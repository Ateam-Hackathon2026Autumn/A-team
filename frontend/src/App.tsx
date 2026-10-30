import { Routes, Route } from "react-router";
import MainLayout from "./components/layout/MainLayout";
import AuthLayout from "./components/layout/AuthLayout";

import HomePage from "./pages/HomePage";
import SigninPage from "./pages/SigninPage";
import SignupPage from "./pages/SignupPage";

export default function App() {
  return (
    <Routes>
      <Route element={<MainLayout />}>
        <Route path="/" element={<HomePage />} />
        <Route
          path="*"
          element={
            <div className="wrap not-found">
              <h1>ページが見つかりません</h1>
              <p>この画面はまだ実装されていないか、URLが異なります。</p>
              <a href="/">ホームへ戻る</a>
            </div>
          }
        />
      </Route>
      <Route element={<AuthLayout />}>
        <Route path="/signin" element={<SigninPage />} />
        <Route path="/signup" element={<SignupPage />} />
      </Route>
    </Routes>
  );
}
