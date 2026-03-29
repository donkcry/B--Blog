from django.shortcuts import render,redirect,get_object_or_404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.urls import reverse_lazy,reverse
from django.contrib.auth.decorators import login_required as django_login_required
from django.views.decorators.http import require_http_methods,require_POST,require_GET
from .models import *
from .forms import EditBlogForm
from django.http.response import JsonResponse
from django.db.models import Q
from django.contrib import messages
from django_ratelimit.decorators import ratelimit

# 自定义登录装饰器，添加登录提示
def login_required(function=None, login_url=None):
    def decorator(view_func):
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.info(request, '请先登录！')
                return redirect(login_url or reverse_lazy('BLauth:login'))
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    if function:
        return decorator(function)
    return decorator

# Create your views here.

def index(request):
    blog_list = Blog.objects.all().order_by('-edit_time')

    # 手机8个，电脑6个 —— 只改数量
    user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
    is_mobile = 'mobile' in user_agent or 'android' in user_agent or 'iphone' in user_agent
    per_page = 8 if is_mobile else 6

    paginator = Paginator(blog_list, per_page)
    page = request.GET.get('page', 1)

    try:
        blogs = paginator.page(page)
    except PageNotAnInteger:
        blogs = paginator.page(1)
    except EmptyPage:
        blogs = paginator.page(paginator.num_pages)

    return render(request, 'index.html', {'blogs': blogs})


def blog_detail(request, blog_id):
    blog = get_object_or_404(Blog, pk=blog_id)
    comment_list = blog.comments.all().order_by('-edit_time')
    paginator = Paginator(comment_list, 6)

    # 新增：页码范围校验
    comment_page = request.GET.get('comment_page', 1)
    # 转换为整数，失败则设为1
    try:
        comment_page = int(comment_page)
    except ValueError:
        comment_page = 1
    # 限制页码在1到总页数之间
    comment_page = max(1, min(comment_page, paginator.num_pages))

    try:
        comments = paginator.page(comment_page)
    except PageNotAnInteger:
        comments = paginator.page(1)
    except EmptyPage:
        comments = paginator.page(paginator.num_pages)

    return render(request, 'blog_detail.html', context={
        'blog': blog,
        'comments': comments,
        'comment_paginator': paginator,
        'current_comment_page': comment_page  # 用校验后的页码
    })







@require_http_methods(['GET','POST'])
@ratelimit(key='ip', rate='5/m', method='POST', block=True)
@ratelimit(key='user', rate='3/m', method='POST', block=True)
@login_required(login_url=reverse_lazy('BLauth:login'))
def blog_edit(request):
    if request.method == 'GET':
        categories = BlogCategory.objects.all()
        return render(request,'blog_edit.html',context={'categories':categories})
    else:
        form = EditBlogForm(request.POST)
        if form.is_valid():
            title = form.cleaned_data.get('title')
            content = form.cleaned_data.get('content')
            category_id = form.cleaned_data.get('category_name')

            # ====================== 新增：后端强制判断内容不能为空 ======================
            if not content or content.strip() == '' or content.strip() == '<p><br></p>':
                return JsonResponse({
                    'code': 400,
                    'message': '文章内容不能为空！',
                    'errors': {'content': '文章内容不能为空！'}
                })
            # ========================================================================

            try:
                blog = Blog.objects.create(
                    title=title,
                    content=content,
                    category_id=category_id,
                    author=request.user
                )
                messages.success(request, '博客发布成功！')
                return JsonResponse({
                    'code':200,
                    'message':'博客发布成功！',
                    "data":{"blog_id":blog.id, "redirect_url": f"/blog/{blog.id}"}
                })
            except Exception as e:
                print(f"创建博客失败：{str(e)}")
                messages.error(request, f'博客发布失败：{str(e)}')
                return JsonResponse({
                    'code':500,
                    'message':'博客发布失败！',
                    'error':str(e)
                })
        else:
            error_msg = {}
            for field, errors in form.errors.items():
                error_msg[field] = errors[0]
            print("表单错误：", error_msg)
            return JsonResponse({
                'code':400,
                'message':'参数错误！',
                'errors':error_msg
            })




from .models import Blog, BlogComment


@login_required(login_url=reverse_lazy('BLauth:login'))
@ratelimit(key='ip', rate='10/m', method='POST', block=True)
@ratelimit(key='user', rate='5/m', method='POST', block=True)
def pub_comment(request):
    if request.method != 'POST':
        messages.error(request, '无效的请求方式！')
        return redirect(reverse('blog:index'))

    blog_id = request.POST.get('blog_id')
    content = request.POST.get('content', '').strip()

    if not content:
        messages.error(request, '评论内容不能为空！')
        comment_page = request.GET.get('comment_page', 1)
        return redirect(f"{reverse('blog:blog_detail', args=[blog_id])}?comment_page={comment_page}")

    blog = get_object_or_404(Blog, pk=blog_id)

    try:
        BlogComment.objects.create(
            content=content,
            blog=blog,
            author=request.user
        )
        messages.success(request, '评论发布成功！')
    except Exception as e:
        messages.error(request, f'评论发布失败：{str(e)}')
        comment_page = request.GET.get('comment_page', 1)
        return redirect(f"{reverse('blog:blog_detail', args=[blog_id])}?comment_page={comment_page}")

    # 修复：最新评论在第1页，所以跳转到第1页
    return redirect(f"{reverse('blog:blog_detail', args=[blog_id])}?comment_page=1#comment-area")





@require_GET
@ratelimit(key='ip', rate='30/m', method='GET', block=True)
def search(request):
    #/search?q=xxx
    q=request.GET.get('q')
    blogs=Blog.objects.filter(Q(title__icontains=q) | Q(content__icontains=q)).all()
    return render(request,'index.html',context={'blogs':blogs})