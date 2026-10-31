import { Navigate, Route, Routes } from 'react-router';

import AuthWrapper from './components/AuthWrapper';
import DashboardLayout from './Layouts/DashboardLayout';
import MainLayout from './Layouts/MainLayout';
import AuthLayout from "./Layouts/AuthLayout";

import AccountSettingsPage from './pages/AccountSettingsPage';
import CartPage from './pages/CartPage';
import CheckoutCompletePage from './pages/CheckoutCompletePage';
import CheckoutPage from './pages/CheckoutPage';
import ExperienceApplicationsPage from './pages/ExperienceApplicationsPage';
import ExperienceApplyPage from './pages/ExperienceApplyPage';
import ExperienceDetailPage from './pages/ExperienceDetailPage';
import ExperienceListPage from './pages/ExperienceListPage';
import FavoritesPage from './pages/FavoritesPage';
import HomePage from './pages/HomePage';
import InternalServerErrorPage from './pages/InternalServerErrorPage';
import JobApplicationsPage from './pages/JobApplicationsPage';
import JobApplyPage from './pages/JobApplyPage';
import JobDetailPage from './pages/JobDetailPage';
import JobListPage from './pages/JobListPage';
import LearnPage from './pages/LearnPage';
import MyPage from './pages/MyPage';
import NotFoundPage from './pages/NotFoundPage';
import OrderDetailPage from './pages/OrderDetailPage';
import OrderHistoryPage from './pages/OrderHistoryPage';
import ProducerApplicationEditPage from './pages/ProducerApplicationEditPage';
import ProducerApplicationNewPage from './pages/ProducerApplicationNewPage';
import ProducerApplicationStatusPage from './pages/ProducerApplicationStatusPage';
import ProducerListPage from './pages/ProducerListPage';
import ProducerProfilePage from './pages/ProducerProfilePage';
import ProductDetailPage from './pages/ProductDetailPage';
import ProductListPage from './pages/ProductListPage';
import ProfileEditPage from './pages/ProfileEditPage';
import SigninPage from './pages/SigninPage';
import SignupPage from './pages/SignupPage';
import StoryDetailPage from './pages/StoryDetailPage';

import DashboardExperienceEditPage from './pages/dashboard/DashboardExperienceEditPage';
import DashboardExperienceListPage from './pages/dashboard/DashboardExperienceListPage';
import DashboardExperienceNewPage from './pages/dashboard/DashboardExperienceNewPage';
import DashboardExperienceParticipantsPage from './pages/dashboard/DashboardExperienceParticipantsPage';
import DashboardHomePage from './pages/dashboard/DashboardHomePage';
import DashboardJobApplicantsPage from './pages/dashboard/DashboardJobApplicantsPage';
import DashboardJobEditPage from './pages/dashboard/DashboardJobEditPage';
import DashboardJobListPage from './pages/dashboard/DashboardJobListPage';
import DashboardJobNewPage from './pages/dashboard/DashboardJobNewPage';
import DashboardProductEditPage from './pages/dashboard/DashboardProductEditPage';
import DashboardProductListPage from './pages/dashboard/DashboardProductListPage';
import DashboardProductNewPage from './pages/dashboard/DashboardProductNewPage';
import DashboardProfileEditPage from './pages/dashboard/DashboardProfileEditPage';
import DashboardStoryEditPage from './pages/dashboard/DashboardStoryEditPage';

import AdminDashboardPage from './pages/admin/AdminDashboardPage';
import AdminExperienceDetailPage from './pages/admin/AdminExperienceDetailPage';
import AdminExperienceListPage from './pages/admin/AdminExperienceListPage';
import AdminJobDetailPage from './pages/admin/AdminJobDetailPage';
import AdminJobListPage from './pages/admin/AdminJobListPage';
import AdminProducerApplicationDetailPage from './pages/admin/AdminProducerApplicationDetailPage';
import AdminProducerApplicationListPage from './pages/admin/AdminProducerApplicationListPage';
import AdminProducerDetailPage from './pages/admin/AdminProducerDetailPage';
import AdminProducerListPage from './pages/admin/AdminProducerListPage';
import AdminProductDetailPage from './pages/admin/AdminProductDetailPage';
import AdminProductListPage from './pages/admin/AdminProductListPage';
import AdminSigninPage from './pages/admin/AdminSigninPage';
import AdminStoryDetailPage from './pages/admin/AdminStoryDetailPage';
import AdminStoryListPage from './pages/admin/AdminStoryListPage';

// 画面一覧・URL（Notion「設計」）に沿ったルーティング
function App() {
  return (
    <Routes>
      {/* ログイン状態の確認とアクセス制限（対象パスは AuthWrapper 内で定義） */}
      <Route element={<AuthWrapper />}>
        {/* 一般ユーザー・共通 */}
        <Route element={<MainLayout />}>
          <Route element={<AuthLayout />}>
            <Route path="/signin" element={<SigninPage />} />
            <Route path="/signup" element={<SignupPage />} />
          </Route>
          
          <Route path="/" element={<HomePage />} />

          <Route path="/products" element={<ProductListPage />} />
          <Route path="/products/:productId" element={<ProductDetailPage />} />
          <Route path="/cart" element={<CartPage />} />
          <Route path="/checkout" element={<CheckoutPage />} />
          <Route
            path="/checkout/complete"
            element={<CheckoutCompletePage />}
          />

          <Route path="/jobs" element={<JobListPage />} />
          <Route path="/jobs/:jobId" element={<JobDetailPage />} />
          <Route path="/jobs/:jobId/apply" element={<JobApplyPage />} />

          <Route path="/experiences" element={<ExperienceListPage />} />
          <Route
            path="/experiences/:experienceId"
            element={<ExperienceDetailPage />}
          />
          <Route
            path="/experiences/:experienceId/apply"
            element={<ExperienceApplyPage />}
          />

          <Route path="/learn" element={<LearnPage />} />
          <Route path="/learn/:storyId" element={<StoryDetailPage />} />
          <Route path="/producers" element={<ProducerListPage />} />
          <Route
            path="/producers/:producerId"
            element={<ProducerProfilePage />}
          />

          <Route path="/mypage" element={<MyPage />} />
          <Route path="/mypage/profile" element={<ProfileEditPage />} />
          <Route path="/mypage/favorites" element={<FavoritesPage />} />
          <Route path="/mypage/orders" element={<OrderHistoryPage />} />
          <Route
            path="/mypage/orders/:orderId"
            element={<OrderDetailPage />}
          />
          <Route path="/mypage/jobs" element={<JobApplicationsPage />} />
          <Route
            path="/mypage/experiences"
            element={<ExperienceApplicationsPage />}
          />
          <Route path="/mypage/settings" element={<AccountSettingsPage />} />

          {/* 生産者申請 */}
          <Route
            path="/producer-application/new"
            element={<ProducerApplicationNewPage />}
          />
          <Route
            path="/producer-application"
            element={<ProducerApplicationStatusPage />}
          />
          <Route
            path="/producer-application/edit"
            element={<ProducerApplicationEditPage />}
          />
        </Route>

        {/* 生産者 */}
        <Route path="/dashboard" element={<DashboardLayout />}>
          <Route index element={<DashboardHomePage />} />
          <Route path="profile" element={<DashboardProfileEditPage />} />

          <Route path="products" element={<DashboardProductListPage />} />
          <Route path="products/new" element={<DashboardProductNewPage />} />
          <Route
            path="products/:productId/edit"
            element={<DashboardProductEditPage />}
          />

          <Route path="jobs" element={<DashboardJobListPage />} />
          <Route path="jobs/new" element={<DashboardJobNewPage />} />
          <Route path="jobs/:jobId/edit" element={<DashboardJobEditPage />} />
          <Route
            path="jobs/:jobId/applicants"
            element={<DashboardJobApplicantsPage />}
          />

          <Route
            path="experiences"
            element={<DashboardExperienceListPage />}
          />
          <Route
            path="experiences/new"
            element={<DashboardExperienceNewPage />}
          />
          <Route
            path="experiences/:experienceId/edit"
            element={<DashboardExperienceEditPage />}
          />
          <Route
            path="experiences/:experienceId/participants"
            element={<DashboardExperienceParticipantsPage />}
          />

          <Route path="story" element={<DashboardStoryEditPage />} />
        </Route>
      </Route>

      {/* 管理者（管理者用のログインチェックAPIで別途制御する） */}
      <Route path="/admin">
        <Route path="signin" element={<AdminSigninPage />} />
        <Route index element={<AdminDashboardPage />} />
        <Route
          path="producer-applications"
          element={<AdminProducerApplicationListPage />}
        />
        <Route
          path="producer-applications/:applicationId"
          element={<AdminProducerApplicationDetailPage />}
        />
        <Route path="producers" element={<AdminProducerListPage />} />
        <Route
          path="producers/:producerId"
          element={<AdminProducerDetailPage />}
        />
        <Route path="products" element={<AdminProductListPage />} />
        <Route
          path="products/:productId"
          element={<AdminProductDetailPage />}
        />
        <Route path="jobs" element={<AdminJobListPage />} />
        <Route path="jobs/:jobId" element={<AdminJobDetailPage />} />
        <Route path="experiences" element={<AdminExperienceListPage />} />
        <Route
          path="experiences/:experienceId"
          element={<AdminExperienceDetailPage />}
        />
        <Route path="stories" element={<AdminStoryListPage />} />
        <Route path="stories/:storyId" element={<AdminStoryDetailPage />} />
      </Route>

      <Route path="/404" element={<NotFoundPage />} />
      <Route path="/500" element={<InternalServerErrorPage />} />

      <Route path="*" element={<Navigate to="/404" replace />} />
    </Routes>
  );
}

export default App;
