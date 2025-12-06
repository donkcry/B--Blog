from django.urls import path
from . import views

app_name = 'blog'

urlpatterns = [
    path('index', views.index, name='index'),
    path('blog/<int:blog_id>', views.blog_detail, name='blog_detail'),
    path('blog/edit',views.blog_edit,name='blog_edit'),
    path('blog/comment/pub',views.pub_comment,name='pub_comment'),
    path('search',views.search,name='search'),
]