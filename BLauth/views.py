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

User = get_user_model()

# Create your views here.
@require_http_methods(['GET','POST'])
def BLlogin(request):
    if request.method == 'GET':
        context = {
            'login_error': request.session.pop('login_error', False),
            'prev_email': request.session.pop('prev_email', ''),
        }
        return render(request, 'login.html', context)
    else:
        form = LoginForm(request.POST)
        prev_email = request.POST.get('email', '')
        if form.is_valid():
            email = form.cleaned_data.get('email')
            password = form.cleaned_data.get('password')
            remember_me = form.cleaned_data.get('remember_me')
            user=User.objects.filter(email=email).first()
            if user and user.check_password(password):
                login(request,user)
                if not remember_me:
                    request.session.set_expiry(0)
                else:
                    request.session.set_expiry(None)
                return redirect('/index')

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
            return redirect(resolve_url('BLauth:login'))
        else:
            print(form.errors)
            return redirect(resolve_url('BLauth:register'))

def send_email_captcha(request):
    email=request.GET.get('email')
    if not email:
        return JsonResponse({'code':400,'message':'必须传递邮箱！'})
    captcha = ''.join(random.sample(string.digits,4))
    CaptchaModel.objects.update_or_create(email=email,defaults={'captcha':captcha})
    send_mail('BL博客注册验证码',message=f'您的注册验证码是：{captcha}',recipient_list=[email],from_email=None)
    return JsonResponse({'code':200,'message':'邮箱验证码发送成功！'})