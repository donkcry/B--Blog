from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django import forms
from django.contrib.auth.models import User
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from blog.models import Blog, BlogComment
from django.urls.base import reverse


@login_required
def user_profile(request):
    # 1. 切换类型（默认显示博客）
    tab = request.GET.get('tab', 'blogs')  # tab=blogs或comments
    search_key = request.GET.get('q', '')

    # 2. 处理博客数据（带搜索+分页）
    if tab == 'blogs':
        # 按标题/内容搜索
        blog_list = Blog.objects.filter(
            author=request.user,
            title__icontains=search_key
        ) | Blog.objects.filter(
            author=request.user,
            content__icontains=search_key
        )
        blog_list = blog_list.distinct().order_by('-edit_time')  # 去重+最新在前
        # 分页（每页8条）
        paginator = Paginator(blog_list, 8)
        page = request.GET.get('page', 1)
        try:
            user_blogs = paginator.page(page)
        except PageNotAnInteger:
            user_blogs = paginator.page(1)
        except EmptyPage:
            user_blogs = paginator.page(paginator.num_pages)
        data_list = user_blogs
        placeholder = '搜索标题或内容'

    # 3. 处理评论数据（带搜索+分页）
    else:
        # 按评论内容搜索
        comment_list = BlogComment.objects.filter(
            author=request.user,
            content__icontains=search_key
        ).order_by('-edit_time')  # 最新在前
        # 分页（每页8条）
        paginator = Paginator(comment_list, 8)
        page = request.GET.get('page', 1)
        try:
            user_comments = paginator.page(page)
        except PageNotAnInteger:
            user_comments = paginator.page(1)
        except EmptyPage:
            user_comments = paginator.page(paginator.num_pages)
        data_list = user_comments
        placeholder = '搜索评论内容'

    context = {
        'tab': tab,
        'data_list': data_list,
        'search_key': search_key,
        'placeholder': placeholder,
        'user': request.user,
    }
    return render(request, 'private/profile.html', context)




# 修复后的评论跳转（兼容Django 5.x）
@login_required
def comment_redirect(request, comment_id):
    # 仅允许访问自己的评论，增强权限校验
    comment = get_object_or_404(BlogComment, id=comment_id, author=request.user)
    # 1. 先用reverse生成纯URL字符串
    blog_url = reverse('blog:blog_detail', kwargs={'blog_id': comment.blog.id})
    # 2. 拼接锚点后再跳转
    return redirect(f"{blog_url}#comment-{comment.id}")


# 个人信息编辑表单
class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']  # 可编辑的字段
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
        }


@login_required
def edit_profile(request):
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            # 1. 先清空残留的旧消息，避免叠加
            message_storage = messages.get_messages(request)
            message_storage.used = True  # 标记所有消息为「已读」，自动从session删除

            # 2. 添加新的成功消息
            messages.success(request, '个人信息修改成功！')

            # 3. 重定向（必须重定向，避免刷新页面重复提交+消息残留）
            return redirect('private:edit_profile')  # 重定向回编辑页面（也可改回个人中心）
    else:
        # 进入编辑页面时，主动清空残留的消息（关键！）
        message_storage = messages.get_messages(request)
        message_storage.used = True  # 标记已读，session中删除消息
        form = UserProfileForm(instance=request.user)

    context = {'form': form}
    return render(request, 'private/edit_profile.html', context)




