from django.shortcuts import render,redirect
from django.http.response import JsonResponse
import random
import string
from django.core.mail import send_mail
from .models import CaptchaModel
from django.views.decorators.http import require_http_methods
from .forms import RegisterForm,LoginForm
from django.contrib.auth import get_user_model,login,logout
from django.urls import reverse
import json

User = get_user_model()


# 登录装饰器：防止已登录用户重复操作
def login_required_redirect(func):
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('/index')
        return func(request, *args, **kwargs)

    return wrapper


@require_http_methods(['GET', 'POST'])
@login_required_redirect
def BLlogin(request):
    if request.method == 'GET':
        context = {
            'login_error': request.session.pop('login_error', False),
            'prev_email': request.session.pop('prev_email', ''),
            'empty_error': request.session.pop('empty_error', False),
            'register_success': request.session.pop('register_success', False),
        }
        return render(request, 'login.html', context)
    else:
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()

        if not email or not password:
            request.session['empty_error'] = True
            request.session['prev_email'] = email
            request.session.set_expiry(5)
            return redirect(reverse('BLauth:login'))

        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            remember_me = form.cleaned_data['remember_me']

            user = User.objects.filter(email=email).first()
            if user and user.check_password(password):
                login(request, user)
                request.session.set_expiry(0 if not remember_me else 60 * 60 * 24 * 7)
                return redirect('/index')

        request.session['login_error'] = True
        request.session['prev_email'] = email
        request.session.set_expiry(5)
        return redirect(reverse('BLauth:login'))

def BLlogout(request):
    logout(request)
    return redirect('/index')


@require_http_methods(['GET', 'POST'])
@login_required_redirect
def register(request):
    if request.method == 'GET':
        return render(request, 'register.html')
    else:
        form = RegisterForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']

            if User.objects.filter(email=email).exists():
                return render(request, 'register.html', {
                    'form': form,
                    'custom_error': '该邮箱已注册，请直接登录！'
                })

            user = User.objects.create_user(username=username, email=email, password=password)

            request.session['register_success'] = True
            request.session.set_expiry(5)
            return redirect(reverse('BLauth:login'))
        else:
            return render(request, 'register.html', {'form': form})


# 验证码接口：修复时间更新逻辑
@require_http_methods(['GET'])
def captcha(request):
    email = request.GET.get('email')
    if not email or not email.endswith('@qq.com'):
        return JsonResponse({'code': 400, 'message': '仅支持QQ邮箱！'})

    # 生成4位数字验证码
    captcha_code = ''.join(random.choices(string.digits, k=4))

    # 修复：移除手动更新create_time，模型auto_now=True会自动刷新
    CaptchaModel.objects.update_or_create(
        email=email,
        defaults={'captcha': captcha_code}  # 仅更新验证码，时间自动更新
    )

    # 发送邮件（需配置settings.py中的邮箱参数）
    try:
        send_mail(
            subject='注册验证码',
            message=f'您的注册验证码是：{captcha_code}（有效期6分钟）',
            from_email='2839788640@qq.com',  # 替换为实际发件邮箱
            recipient_list=[email],
            fail_silently=False,
        )
        return JsonResponse({'code': 200, 'message': '验证码已发送至您的QQ邮箱！（有效期6分钟）'})
    except Exception as e:
        print(f'邮件发送失败：{e}')  # 调试用
        return JsonResponse({'code': 500, 'message': '邮件发送失败，请检查邮箱配置！'})




def send_email_captcha(request):
    email=request.GET.get('email')
    if not email:
        return JsonResponse({'code':400,'message':'必须传递邮箱！'})
    captcha = ''.join(random.sample(string.digits,4))
    CaptchaModel.objects.update_or_create(email=email,defaults={'captcha':captcha})
    send_mail('BL博客注册验证码',message=f'您的注册验证码是：{captcha}',recipient_list=[email],from_email=None)
    return JsonResponse({'code':200,'message':'邮箱验证码发送成功！'})


@require_http_methods(['GET', 'POST'])
def forgot_password(request):
    """忘记密码页面"""
    if request.method == 'GET':
        return render(request, 'forgot_password.html')
    # （后续可扩展：验证通过后重置密码，这里先做验证码验证）


# 修复忘记密码的验证码接口（同理移除手动更新时间）
def send_forgot_captcha(request):
    """发送忘记密码的验证码"""
    email = request.GET.get('email')
    if not email:
        return JsonResponse({'code': 400, 'message': '必须传递邮箱！'})
    # 检查邮箱是否已注册
    if not User.objects.filter(email=email).exists():
        return JsonResponse({'code': 400, 'message': '该邮箱未注册！'})
    # 生成并保存验证码（时间自动更新）
    captcha = ''.join(random.sample(string.digits, 4))
    CaptchaModel.objects.update_or_create(email=email, defaults={'captcha': captcha})
    # 发送邮件
    send_mail(
        'BL博客忘记密码验证码',
        message=f'您的忘记密码验证码是：{captcha}（有效期6分钟）',
        recipient_list=[email],
        from_email='你的QQ邮箱@qq.com'  # 替换为实际发件邮箱
    )
    return JsonResponse({'code': 200, 'message': '验证码已发送至邮箱！（有效期6分钟）'})


def verify_forgot_captcha(request):
    """验证忘记密码的验证码"""
    email = request.GET.get('email')
    captcha = request.GET.get('captcha')
    if not (email and captcha):
        return JsonResponse({'code': 400, 'message': '邮箱和验证码不能为空！'})
    # 验证验证码
    captcha_model = CaptchaModel.objects.filter(email=email, captcha=captcha).first()
    if not captcha_model:
        return JsonResponse({'code': 400, 'message': '验证码错误！'})
    # 验证通过，删除验证码（避免重复使用）
    captcha_model.delete()
    return JsonResponse({'code': 200, 'message': '验证码验证成功！'})


@require_http_methods(['POST'])
def reset_password(request):
    """重置密码接口"""
    try:
        data = json.loads(request.body)
        email = data.get('email')
        new_password = data.get('new_password')

        if not (email and new_password):
            return JsonResponse({'code': 400, 'message': '参数不全！'})

        user = User.objects.filter(email=email).first()
        if not user:
            return JsonResponse({'code': 400, 'message': '用户不存在！'})

        # 修改密码
        user.set_password(new_password)
        user.save()

        return JsonResponse({'code': 200, 'message': '密码重置成功！'})
    except Exception as e:
        return JsonResponse({'code': 500, 'message': f'服务器错误：{str(e)}'})