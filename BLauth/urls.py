from django.urls import path
from . import views

app_name = 'BLauth'

urlpatterns = [
    path('login', views.BLlogin, name='login'),
    path('logout', views.BLlogout, name='logout'),
    path('register', views.register, name='register'),
    path('captcha', views.send_email_captcha, name='captcha'),
    path('forgot-password', views.forgot_password, name='forgot_password'),
    path('send-forgot-captcha', views.send_forgot_captcha, name='send_forgot_captcha'),
    path('verify-forgot-captcha', views.verify_forgot_captcha, name='verify_forgot_captcha'),
    path('reset-password', views.reset_password, name='reset_password'),
]