from django.urls import path
from .views import register_view
from django.contrib.auth import views as auth_views

app_name = 'user_auth'


urlpatterns = [
    path('register/', register_view, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='user_auth/login.html', next_page='weather_search:search'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='weather_search:search'), name='logout'),
]
