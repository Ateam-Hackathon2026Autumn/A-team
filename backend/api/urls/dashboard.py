"""生産者向けの URL（/api/v1/dashboard/...）

api/urls/__init__.py から /api/v1/dashboard/ に include する。
パスは Notion の API 定義のとおり（末尾スラッシュなし）。:id は <int:...> にする。
"""
from django.urls import path

from ..views.dashboard import experiences, jobs
from ..views.dashboard.analytics import AnalyticsView

urlpatterns = [
    # 体験管理・予約枠・申込者
    path("experiences", experiences.ExperienceListCreateView.as_view(), name="dashboard-experiences"),
    path("experiences/<int:experience_id>", experiences.ExperienceDetailView.as_view(),
          name="dashboard-experience-detail"),
    path("experiences/<int:experience_id>/applications", experiences.ExperienceApplicationListView.as_view(),
          name="dashboard-experience-applications"),
    path("experiences/<int:experience_id>/slots", experiences.SlotListCreateView.as_view(),
          name="dashboard-experience-slots"),
    path("experiences/<int:experience_id>/slots/<int:slot_id>", experiences.SlotDetailView.as_view(),
          name="dashboard-experience-slot-detail"),

    # 求人管理・採用

    path("jobs", jobs.JobListCreateView.as_view(), name="dashboard-jobs"),
    path("jobs/<int:job_id>", jobs.JobDetailView.as_view(), name="dashboard-job-detail"),
    path("jobs/<int:job_id>/applications", jobs.JobApplicationListView.as_view(), name="dashboard-job-applications"),
    path("jobs/<int:job_id>/applications/<int:application_id>", jobs.JobApplicationDetailView.as_view(), 
         name="dashboard-job-application-detail"),      

    # 分析
    path("analytics", AnalyticsView.as_view(), name="dashboard-analytics"),
]
