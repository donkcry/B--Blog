from django.urls import path
from . import views

app_name = 'private'

urlpatterns = [
    #个人中心首页
    path('my/', views.user_profile, name='user_profile'),
    # 评论跳转（跳转到博客详情页）
    path('comment/<int:comment_id>/', views.comment_redirect, name='comment_redirect'),
    # 可选：个人信息编辑
    path('edit/', views.edit_profile, name='edit_profile'),
    # 新增：发送注销验证码接口
    path('send-logout-code/', views.send_logout_verify_code, name='send_logout_code'),
    # 新增：验证并注销账号接口
    path('confirm-logout/', views.confirm_logout, name='confirm_logout'),
]
