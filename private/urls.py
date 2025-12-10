from django.urls import path
from . import views

app_name = 'private'

urlpatterns = [
    # 个人中心首页
    path('my/', views.user_profile, name='user_profile'),
    # 评论跳转
    path('comment/<int:comment_id>/', views.comment_redirect, name='comment_redirect'),
    # 个人信息编辑
    path('edit/', views.edit_profile, name='edit_profile'),
    # 发送注销验证码（名称和模板一致）
    path('send-logout-code/', views.send_logout_verify_code, name='send_logout_verify_code'),
    # 确认注销账号
    path('confirm-logout/', views.confirm_logout, name='confirm_logout'),
    # 发送修改密码验证码（名称和模板一致）
    path('send_change_pwd_code/', views.send_change_pwd_verify_code, name='send_change_pwd_verify_code'),
    # 确认修改密码
    path('change_password/', views.change_password, name='change_password'),
    # 发送邮箱修改验证码
    path('send-email-change-code/', views.send_email_change_code, name='send_email_change_code'),
    path('update_avatar/', views.update_avatar, name='update_avatar'),
]