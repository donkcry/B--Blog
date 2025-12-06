from django.urls import path
from . import views

app_name = 'BLauth'

urlpatterns = [
    path('login', views.BLlogin, name='login'),
    path('logout', views.BLlogout, name='logout'),
    path('register', views.register, name='register'),
    path('captcha', views.send_email_captcha, name='captcha'),
]