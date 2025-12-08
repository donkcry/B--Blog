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

]
