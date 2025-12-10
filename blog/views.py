from django.shortcuts import render,redirect,get_object_or_404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.urls import reverse_lazy,reverse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods,require_POST,require_GET
from .models import *
from .forms import EditBlogForm
from django.http.response import JsonResponse
from django.db.models import Q
from django.contrib import messages

# Create your views here.

def index(request):
    # 1. 获取所有博客（按编辑时间倒序）
    blog_list = Blog.objects.all().order_by('-edit_time')

    # 2. 初始化分页器：每页显示6条（可根据需求调整）
    paginator = Paginator(blog_list, 6)

    # 3. 获取当前页码（从GET请求中获取，默认第1页）
    page = request.GET.get('page', 1)

    try:
        # 4. 获取当前页的博客数据
        blogs = paginator.page(page)
    except PageNotAnInteger:
        # 如果页码不是整数，返回第一页
        blogs = paginator.page(1)
    except EmptyPage:
        # 如果页码超出范围，返回最后一页
        blogs = paginator.page(paginator.num_pages)

    # 5. 将分页数据传入模板
    return render(request, 'index.html', {
        'blogs': blogs,
        'paginator': paginator  # 可选：传递分页器对象供前端使用
    })


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
@login_required(login_url=reverse_lazy('BLauth:login'))
def blog_edit(request):
    if request.method == 'GET':
        categories = BlogCategory.objects.all()
        return render(request,'blog_edit.html',context={'categories':categories})
    else:
        form=EditBlogForm(request.POST)
        if form.is_valid():
            title=form.cleaned_data.get('title')
            content=form.cleaned_data.get('content')
            category_id=form.cleaned_data.get('category')
            blog=Blog.objects.create(title=title,content=content,category_id=category_id,author=request.user)
            return JsonResponse({'code':200,'message':'博客发布成功！',"data":{"blog_id":blog.id}})
        else:
            print(form.errors)
            return JsonResponse({'code':400,'message':'参数错误！'})


from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required  # 必须加登录验证，避免匿名评论
from .models import Blog, BlogComment


@login_required
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
def search(request):
    #/search?q=xxx
    q=request.GET.get('q')
    blogs=Blog.objects.filter(Q(title__icontains=q) | Q(content__icontains=q)).all()
    return render(request,'index.html',context={'blogs':blogs})