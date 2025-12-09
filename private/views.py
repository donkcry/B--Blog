from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django import forms
from django.contrib.auth.models import User
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from blog.models import Blog, BlogComment
from django.urls.base import reverse
from django.core.mail import send_mail
import random
import string
import json
import traceback
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from .models import VerifyCode


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


# 发送注销验证码
@login_required
def send_logout_verify_code(request):
    if request.method == 'POST':
        email = request.user.email
        if not email:
            return JsonResponse({'status': 'error', 'msg': '账号未绑定邮箱，无法发送验证码'})

        # 生成6位数字验证码
        code = ''.join(random.choices(string.digits, k=6))

        # 先删除该用户旧的验证码
        VerifyCode.objects.filter(user=request.user).delete()

        # 保存新验证码
        VerifyCode.objects.create(
            user=request.user,
            code=code,
            email=email
        )

        # 发送邮件
        try:
            send_mail(
                subject='账号注销验证码',
                message=f'你的账号注销验证码为：{code}（5分钟内有效），请勿泄露给他人！',
                from_email=None,  # 使用DEFAULT_FROM_EMAIL
                recipient_list=[email],
                fail_silently=False,
            )
            return JsonResponse({'status': 'success', 'msg': '验证码已发送至你的邮箱'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'msg': f'发送失败：{str(e)}'})
    return JsonResponse({'status': 'error', 'msg': '请求方式错误'})


# 验证并注销账号
# 移除@login_required，手动校验登录状态
def confirm_logout(request):
    # 手动校验用户是否登录（替代装饰器）
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'msg': '请先登录后再注销'}, status=200)

    if request.method == 'POST':
        try:
            # 1. 解析前端JSON
            data = json.loads(request.body)
            verify_code = data.get('verifyCode', '').strip()
            password = data.get('verifyPassword', '').strip()

            # 2. 密码校验
            if not request.user.check_password(password):
                return JsonResponse({'status': 'error', 'msg': '账号密码错误'}, status=200)

            # 3. 验证码校验
            try:
                code_obj = VerifyCode.objects.filter(user=request.user).latest('created_at')
            except VerifyCode.DoesNotExist:
                return JsonResponse({'status': 'error', 'msg': '请先获取验证码'}, status=200)

            if not code_obj.is_valid():
                return JsonResponse({'status': 'error', 'msg': '验证码已过期，请重新获取'}, status=200)

            if code_obj.code != verify_code:
                return JsonResponse({'status': 'error', 'msg': '验证码错误'}, status=200)

            # 4. 删除用户及验证码
            user_id = request.user.id
            User = get_user_model()
            User.objects.filter(id=user_id).delete()
            VerifyCode.objects.filter(user_id=user_id).delete()

            # 5. 返回成功（跳转首页/index）
            return JsonResponse({
                'status': 'success',
                'msg': '账号已成功注销',
                'redirect_url': '/index'  # 核心：指向你的首页/index
            }, status=200)

        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'msg': '请求数据格式错误'}, status=200)
        except Exception as e:
            traceback.print_exc()
            return JsonResponse({'status': 'error', 'msg': f'服务器错误：{str(e)}'}, status=200)
    else:
        return JsonResponse({'status': 'error', 'msg': '仅支持POST请求'}, status=405)


# 新增：发送修改密码验证码接口（复用注销接口逻辑）
@login_required
def send_change_pwd_verify_code(request):
    if request.method == 'POST':
        email = request.user.email
        if not email:
            return JsonResponse({'status': 'error', 'msg': '账号未绑定邮箱，无法发送验证码'})

        # 生成6位数字验证码（和注销接口一致）
        code = ''.join(random.choices(string.digits, k=6))

        # 先删除该用户旧的验证码（避免重复）
        VerifyCode.objects.filter(user=request.user).delete()

        # 保存新验证码（复用同一张表）
        VerifyCode.objects.create(
            user=request.user,
            code=code,
            email=email
        )

        # 发送修改密码邮件（仅主题/内容不同）
        try:
            send_mail(
                subject='修改密码验证码',  # 区别注销的主题
                message=f'你的修改密码验证码为：{code}（5分钟内有效），请勿泄露给他人！',  # 区别注销的内容
                from_email=None,  # 使用DEFAULT_FROM_EMAIL
                recipient_list=[email],
                fail_silently=False,
            )
            return JsonResponse({'status': 'success', 'msg': '验证码已发送至你的邮箱'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'msg': f'发送失败：{str(e)}'})
    return JsonResponse({'status': 'error', 'msg': '请求方式错误'})


# 新增：修改密码接口（仅验证验证码，无需原密码）
@login_required
def change_password(request):
    if request.method == 'POST':
        # 仅解析JSON格式参数（前端传递的是JSON）
        try:
            # 正确解析JSON数据
            data = json.loads(request.body)  # ✅ 替换 request.json
            verify_code = data.get('verifyCode', '').strip()
            new_password = data.get('newPassword', '').strip()
        except json.JSONDecodeError:  # 精准捕获JSON解析错误
            return JsonResponse({'status': 'error', 'msg': '参数格式错误（请传递JSON格式）'})

        # 1. 校验参数
        if not verify_code or len(verify_code) != 6:
            return JsonResponse({'status': 'error', 'msg': '请输入6位有效验证码'})
        if not new_password or len(new_password) < 6:
            return JsonResponse({'status': 'error', 'msg': '新密码至少6位'})

        # 2. 验证验证码
        # 优先获取最新创建的验证码
        try:
            code_obj = VerifyCode.objects.filter(
                user=request.user,
                code=verify_code
            ).latest('created_at')  # ✅ 按创建时间取最新
            if not code_obj.is_valid():
                return JsonResponse({'status': 'error', 'msg': '验证码已过期（有效期5分钟）'})
        except VerifyCode.DoesNotExist:
            return JsonResponse({'status': 'error', 'msg': '验证码错误，请重新输入'})

        # 3. 修改密码
        user = request.user
        user.set_password(new_password)
        user.save()

        # 4. 删除验证码
        VerifyCode.objects.filter(user=request.user).delete()

        return JsonResponse({'status': 'success', 'msg': '密码修改成功，请重新登录'})

    return JsonResponse({'status': 'error', 'msg': '请求方式错误'})