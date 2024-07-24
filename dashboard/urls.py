from django.contrib import admin
from django.urls import path
from record import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index, name='index'),
    path('login/', views.login_user, name='login'),
    path('logout/', views.logout_user, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('statusrecord/', views.status_record, name='statusrecord'),
    path('update_record/', views.update_record, name='update_record'),
]