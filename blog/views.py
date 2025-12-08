from django.shortcuts import render,redirect
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.urls import reverse_lazy,reverse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods,require_POST,require_GET
from .models import *
from .forms import EditBlogForm
from django.http.response import JsonResponse
from django.db.models import Q

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
    try:
        blog=Blog.objects.get(pk=blog_id)
    except Exception as e:
        blog=None
    return render(request,'blog_detail.html',context={'blog':blog})






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






@require_POST
@login_required(login_url=reverse_lazy('BLauth:login'))
def pub_comment(request):
    blog_id=request.POST.get('blog_id')
    content=request.POST.get('content')
    BlogComment.objects.create(blog_id=blog_id,content=content,author=request.user)
    return redirect(reverse('blog:blog_detail',kwargs={'blog_id':blog_id}))






@require_GET
def search(request):
    #/search?q=xxx
    q=request.GET.get('q')
    blogs=Blog.objects.filter(Q(title__icontains=q) | Q(content__icontains=q)).all()
    return render(request,'index.html',context={'blogs':blogs})