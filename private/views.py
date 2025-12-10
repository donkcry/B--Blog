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
import json,re
import traceback
from django.http import JsonResponse, HttpResponse
from django.contrib.auth import get_user_model
from .models import VerifyCode,UserProfile


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
    # 新增：新邮箱输入框（用于修改邮箱时填写）
    new_email = forms.EmailField(
        required=False,
        label="新电子邮箱地址",
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    # 新增：邮箱验证码输入框
    email_verify_code = forms.CharField(
        required=False,
        label="邮箱验证码",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '输入6位验证码'})
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']  # 保留原字段
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),  # 原邮箱设为只读
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean_new_email(self):
        new_email = self.cleaned_data.get('new_email')
        if new_email:  # 只有填写了新邮箱才校验
            # 正则匹配：QQ邮箱格式为「数字@qq.com」
            qq_email_pattern = r'^\d+@qq\.com$'
            if not re.match(qq_email_pattern, new_email):
                raise forms.ValidationError("新邮箱必须是QQ邮箱（格式：数字@qq.com）")
        return new_email


    def clean(self):
        cleaned_data = super().clean()
        current_email = self.instance.email  # 当前用户的原邮箱
        new_email = cleaned_data.get('new_email')
        verify_code = cleaned_data.get('email_verify_code')

        # 1. 校验新邮箱唯一性（如果填写了新邮箱且和原邮箱不同）
        if new_email and new_email != current_email:
            # 检查新邮箱是否已被其他用户占用
            if User.objects.filter(email=new_email).exclude(id=self.instance.id).exists():
                self.add_error('new_email', '该邮箱已被其他账号绑定，请更换邮箱')
                return cleaned_data  # 提前返回，不执行后续验证码校验

            # 2. 校验验证码是否存在且有效
            try:
                code_obj = VerifyCode.objects.filter(
                    user=self.instance,
                    email=new_email,
                    code=verify_code
                ).latest('created_at')
                if not code_obj.is_valid():
                    self.add_error('email_verify_code', '验证码已过期，请重新获取')
                else:
                    # 验证码验证通过，立即删除该验证码（避免重复使用）
                    code_obj.delete()
            except VerifyCode.DoesNotExist:
                self.add_error('email_verify_code', '验证码错误或未获取，请重新输入')
        return cleaned_data


@login_required
def edit_profile(request):
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            # 处理邮箱修改逻辑
            new_email = form.cleaned_data.get('new_email')
            if new_email and new_email != request.user.email:
                # 验证通过后，更新邮箱
                request.user.email = new_email
                request.user.save()
                # 兜底：删除该用户所有关联的验证码（避免残留）
                VerifyCode.objects.filter(user=request.user, email=new_email).delete()

            # 保存其他字段
            form.save()

            # 清空旧消息 + 添加成功消息
            message_storage = messages.get_messages(request)
            message_storage.used = True
            messages.success(request, '个人信息修改成功！')

            # 兼容AJAX请求：返回JSON或重定向
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'success', 'msg': '个人信息修改成功！'})
            return redirect('private:edit_profile')
        else:
            # 表单验证失败，兼容AJAX请求返回页面
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                # 返回包含错误的页面HTML
                html = render(request, 'private/edit_profile.html', {'form': form}).content
                return HttpResponse(html, status=200)
    else:
        message_storage = messages.get_messages(request)
        message_storage.used = True
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


@login_required
def send_email_change_code(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            new_email = data.get('new_email', '').strip()
            current_email = request.user.email

            # 新增：先校验QQ邮箱格式
            qq_email_pattern = r'^\d+@qq\.com$'
            if not re.match(qq_email_pattern, new_email):
                return JsonResponse({'status': 'error', 'msg': '新邮箱必须是QQ邮箱（格式：数字@qq.com）'})


            # 1. 校验新邮箱是否和原邮箱重复
            if new_email == current_email:
                return JsonResponse({'status': 'error', 'msg': '新邮箱不能与原邮箱相同'})

            # 2. 新增：校验新邮箱是否已被其他用户占用
            if User.objects.filter(email=new_email).exclude(id=request.user.id).exists():
                return JsonResponse({'status': 'error', 'msg': '该邮箱已被其他账号绑定，请更换邮箱'})

            # 3. 校验新邮箱格式
            try:
                forms.EmailField().clean(new_email)
            except forms.ValidationError:
                return JsonResponse({'status': 'error', 'msg': '发送失败，请输入一个有效的邮箱地址'})

            # 生成6位验证码
            code = ''.join(random.choices(string.digits, k=6))
            # 删除该用户旧的验证码（避免重复）
            VerifyCode.objects.filter(user=request.user, email=new_email).delete()
            # 保存新验证码（关联新邮箱）
            VerifyCode.objects.create(
                user=request.user,
                code=code,
                email=new_email
            )

            # 发送邮件
            send_mail(
                subject='邮箱修改验证码',
                message=f'你的邮箱修改验证码为：{code}（5分钟内有效），请勿泄露给他人！',
                from_email=None,
                recipient_list=[new_email],
                fail_silently=False,
            )
            return JsonResponse({'status': 'success', 'msg': '验证码已发送至新邮箱'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'msg': f'发送失败：{str(e)}'})
    return JsonResponse({'status': 'error', 'msg': '请求方式错误'})



@login_required
def update_avatar(request):
    if request.method == 'POST' and request.FILES.get('avatar'):
        # 获取用户的UserProfile（没有则创建）
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        # 保存新头像（会自动存储到media/avatars下）
        profile.avatar = request.FILES['avatar']
        profile.save()
        # 返回成功信息和新头像的URL
        return JsonResponse({
            'status': 'success',
            'msg': '头像保存成功',
            'avatar_url': profile.avatar.url
        })
    return JsonResponse({'status': 'error', 'msg': '请求方式错误或未保存文件'})