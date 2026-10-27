import type { RestMock } from '../types';
import { cartItemDelete } from './endpoint/delete_api_v1_cart_items_itemId';
import { dashboardExperienceDelete } from './endpoint/delete_api_v1_dashboard_experiences_experienceId';
import { dashboardExperienceSlotDelete } from './endpoint/delete_api_v1_dashboard_experiences_experienceId_slots_slotId';
import { dashboardJobDelete } from './endpoint/delete_api_v1_dashboard_jobs_jobId';
import { dashboardProductDelete } from './endpoint/delete_api_v1_dashboard_products_productId';
import { authCsrf } from './endpoint/get_api_v1_auth_csrf';
import { authSession } from './endpoint/get_api_v1_auth_session';
import { cart } from './endpoint/get_api_v1_cart';
import { categoriesList } from './endpoint/get_api_v1_categories';
import { dashboardExperiencesList } from './endpoint/get_api_v1_dashboard_experiences';
import { dashboardExperienceDetail } from './endpoint/get_api_v1_dashboard_experiences_experienceId';
import { dashboardExperienceApplicationsList } from './endpoint/get_api_v1_dashboard_experiences_experienceId_applications';
import { dashboardExperienceSlotsList } from './endpoint/get_api_v1_dashboard_experiences_experienceId_slots';
import { dashboardJobsList } from './endpoint/get_api_v1_dashboard_jobs';
import { dashboardJobDetail } from './endpoint/get_api_v1_dashboard_jobs_jobId';
import { dashboardJobApplicationsList } from './endpoint/get_api_v1_dashboard_jobs_jobId_applications';
import { dashboardOrdersList } from './endpoint/get_api_v1_dashboard_orders';
import { dashboardOrderDetail } from './endpoint/get_api_v1_dashboard_orders_orderId';
import { dashboardProductsList } from './endpoint/get_api_v1_dashboard_products';
import { dashboardProductDetail } from './endpoint/get_api_v1_dashboard_products_productId';
import { dashboardProfile } from './endpoint/get_api_v1_dashboard_profile';
import { dashboardStory } from './endpoint/get_api_v1_dashboard_story';
import { dashboardSummary } from './endpoint/get_api_v1_dashboard_summary';
import { experiencesList } from './endpoint/get_api_v1_experiences';
import { experienceDetail } from './endpoint/get_api_v1_experiences_experienceId';
import { jobsList } from './endpoint/get_api_v1_jobs';
import { jobDetail } from './endpoint/get_api_v1_jobs_jobId';
import { producerApplicationMe } from './endpoint/get_api_v1_producer-applications_me';
import { producersList } from './endpoint/get_api_v1_producers';
import { producerProfile } from './endpoint/get_api_v1_producers_producerId';
import { producerStory } from './endpoint/get_api_v1_producers_producerId_story';
import { productsList } from './endpoint/get_api_v1_products';
import { productDetail } from './endpoint/get_api_v1_products_productId';
import { usersMe } from './endpoint/get_api_v1_users_me';
import { myExperienceApplications } from './endpoint/get_api_v1_users_me_experience-applications';
import { myJobApplications } from './endpoint/get_api_v1_users_me_job-applications';
import { myOrdersList } from './endpoint/get_api_v1_users_me_orders';
import { cartItemUpdate } from './endpoint/patch_api_v1_cart_items_itemId';
import { dashboardExperienceUpdate } from './endpoint/patch_api_v1_dashboard_experiences_experienceId';
import { dashboardExperienceSlotUpdate } from './endpoint/patch_api_v1_dashboard_experiences_experienceId_slots_slotId';
import { dashboardJobUpdate } from './endpoint/patch_api_v1_dashboard_jobs_jobId';
import { dashboardJobApplicationUpdate } from './endpoint/patch_api_v1_dashboard_jobs_jobId_applications_applicationId';
import { dashboardOrderShippingUpdate } from './endpoint/patch_api_v1_dashboard_orders_orderId_shipping';
import { dashboardProductUpdate } from './endpoint/patch_api_v1_dashboard_products_productId';
import { dashboardProductStockUpdate } from './endpoint/patch_api_v1_dashboard_products_productId_stock';
import { dashboardProfileUpdate } from './endpoint/patch_api_v1_dashboard_profile';
import { producerApplicationResubmit } from './endpoint/patch_api_v1_producer-applications_me';
import { usersMeUpdate } from './endpoint/patch_api_v1_users_me';
import { emailVerificationConfirm } from './endpoint/post_api_v1_auth_email-verification_confirm';
import { emailVerificationResend } from './endpoint/post_api_v1_auth_email-verification_resend';
import { authSignin } from './endpoint/post_api_v1_auth_signin';
import { authSignout } from './endpoint/post_api_v1_auth_signout';
import { cartItemAdd } from './endpoint/post_api_v1_cart_items';
import { dashboardExperienceCreate } from './endpoint/post_api_v1_dashboard_experiences';
import { dashboardExperienceSlotCreate } from './endpoint/post_api_v1_dashboard_experiences_experienceId_slots';
import { dashboardJobCreate } from './endpoint/post_api_v1_dashboard_jobs';
import { dashboardPayoutAccountLink } from './endpoint/post_api_v1_dashboard_payouts_account';
import { dashboardProductCreate } from './endpoint/post_api_v1_dashboard_products';
import { experienceApply } from './endpoint/post_api_v1_experiences_experienceId_applications';
import { jobApply } from './endpoint/post_api_v1_jobs_jobId_applications';
import { orderCreate } from './endpoint/post_api_v1_orders';
import { producerApplicationCreate } from './endpoint/post_api_v1_producer-applications';
import { uploadsImageCreate } from './endpoint/post_api_v1_uploads_images';
import { usersCreate } from './endpoint/post_api_v1_users';
import { myJobApplicationWithdraw } from './endpoint/post_api_v1_users_me_job-applications_applicationId_withdraw';
import { dashboardStoryUpsert } from './endpoint/put_api_v1_dashboard_story';

/**
 * REST APIのモック一覧
 *
 * レスポンス内容を変える場合は endpoint/ の各ファイルを書き換え
 *
 * ファイル名は HTTPメソッド + エンドポイントの URL を _ で繋いだもの
 * （{productId} のような可変部分は波括弧を外して productId と書く）
 * GET    /api/v1/auth/session                    -> endpoint/get_api_v1_auth_session.tsx
 * PATCH  /api/v1/dashboard/products/{productId}  -> endpoint/patch_api_v1_dashboard_products_productId.tsx
 *
 * エンドポイントを追加する場合は、
 * 上記のルールで endpoint/ にファイルを1つ作成し、下記の配列に追加
 */
const restMocks: RestMock[] = [
  authCsrf,
  emailVerificationConfirm,
  emailVerificationResend,
  authSession,
  authSignin,
  authSignout,
  cart,
  cartItemAdd,
  cartItemUpdate,
  cartItemDelete,
  categoriesList,
  dashboardExperiencesList,
  dashboardExperienceCreate,
  dashboardExperienceDetail,
  dashboardExperienceUpdate,
  dashboardExperienceDelete,
  dashboardExperienceApplicationsList,
  dashboardExperienceSlotsList,
  dashboardExperienceSlotCreate,
  dashboardExperienceSlotUpdate,
  dashboardExperienceSlotDelete,
  dashboardJobsList,
  dashboardJobCreate,
  dashboardJobDetail,
  dashboardJobUpdate,
  dashboardJobDelete,
  dashboardJobApplicationsList,
  dashboardJobApplicationUpdate,
  dashboardOrdersList,
  dashboardOrderDetail,
  dashboardOrderShippingUpdate,
  dashboardPayoutAccountLink,
  dashboardProductsList,
  dashboardProductCreate,
  dashboardProductDetail,
  dashboardProductUpdate,
  dashboardProductDelete,
  dashboardProductStockUpdate,
  dashboardProfile,
  dashboardProfileUpdate,
  dashboardStory,
  dashboardStoryUpsert,
  dashboardSummary,
  experiencesList,
  experienceDetail,
  experienceApply,
  jobsList,
  jobDetail,
  jobApply,
  orderCreate,
  producerApplicationCreate,
  producerApplicationMe,
  producerApplicationResubmit,
  producersList,
  producerProfile,
  producerStory,
  productsList,
  productDetail,
  uploadsImageCreate,
  usersCreate,
  usersMe,
  usersMeUpdate,
  myExperienceApplications,
  myJobApplications,
  myJobApplicationWithdraw,
  myOrdersList,
];

export { restMocks };
