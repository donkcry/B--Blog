from django.shortcuts import render,redirect,resolve_url
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

# Create your views here.
@require_http_methods(['GET', 'POST'])
def BLlogin(request):
    if request.method == 'GET':
        context = {
            'login_error': request.session.pop('login_error', False),
            'prev_email': request.session.pop('prev_email', ''),
            'empty_error': request.session.pop('empty_error', False),  # 新增：空值错误标识
            'register_success': request.session.pop('register_success', False),
        }
        return render(request, 'login.html', context)
    else:
        # 1. 先校验是否为空提交
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '').strip()
        if not email or not password:
            request.session['empty_error'] = True  # 空值错误
            request.session['prev_email'] = email
            request.session.set_expiry(5)
            return redirect(reverse('BLauth:login'))  # 强制返回登录页，避免跳注册

        # 2. 表单验证
        form = LoginForm(request.POST)
        prev_email = email
        if form.is_valid():
            remember_me = form.cleaned_data.get('remember_me')
            user = User.objects.filter(email=email).first()
            if user and user.check_password(password):
                login(request, user)
                if not remember_me:
                    request.session.set_expiry(0)
                else:
                    request.session.set_expiry(None)
                return redirect('/index')

        # 3. 验证失败（邮箱/密码错误）
        request.session['login_error'] = True
        request.session['prev_email'] = prev_email
        request.session.set_expiry(5)
        return redirect(reverse('BLauth:login'))

def BLlogout(request):
    logout(request)
    return redirect('/index')


@require_http_methods(['GET','POST'])
def register(request):
    if request.method == 'GET':
        return render(request,'register.html')
    else:
        form = RegisterForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            User.objects.create_user(username=username, email=email, password=password)
            # 修复：直接传递上下文，而非依赖Session
            return render(request, 'login.html', {'register_success': True})
        else:
            # 将错误信息传递到前端
            context = {'form': form}
            return render(request, 'register.html', context)



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


def send_forgot_captcha(request):
    """发送忘记密码的验证码"""
    email = request.GET.get('email')
    if not email:
        return JsonResponse({'code': 400, 'message': '必须传递邮箱！'})
    # 检查邮箱是否已注册
    if not User.objects.filter(email=email).exists():
        return JsonResponse({'code': 400, 'message': '该邮箱未注册！'})
    # 生成并保存验证码
    captcha = ''.join(random.sample(string.digits, 4))
    CaptchaModel.objects.update_or_create(email=email, defaults={'captcha': captcha})
    # 发送邮件
    send_mail(
        'BL博客忘记密码验证码',
        message=f'您的忘记密码验证码是：{captcha}',
        recipient_list=[email],
        from_email=None
    )
    return JsonResponse({'code': 200, 'message': '验证码已发送至邮箱！'})


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