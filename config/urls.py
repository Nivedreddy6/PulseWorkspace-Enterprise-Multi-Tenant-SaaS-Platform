from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

import accounts.views as account_views
import core.views as core_views

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # Authentication
    path('login/', account_views.login_view, name='login'),
    path('register/', account_views.register_view, name='register'),
    path('logout/', account_views.logout_view, name='logout'),

    # Workspace Web App Dashboard
    path('', core_views.dashboard_view, name='dashboard'),
    path('switch-workspace/<slug:slug>/', core_views.switch_workspace_view, name='switch_workspace'),
    path('projects/', core_views.projects_view, name='projects'),
    path('projects/<slug:slug>/', core_views.project_detail_view, name='project_detail'),
    path('kanban/', core_views.kanban_view, name='kanban'),
    path('kanban/update-status/<int:task_id>/', core_views.update_task_status_ajax, name='update_task_status_ajax'),
    path('team/', core_views.team_view, name='team'),
    path('audit/', core_views.audit_logs_view, name='audit_logs'),
    path('billing/', core_views.billing_view, name='billing'),

    # REST APIs
    path('api/v1/', include('api.urls')),

    # Interactive OpenAPI / Swagger Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
