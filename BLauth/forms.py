from django import forms
from django.contrib.auth import get_user_model
from .models import CaptchaModel
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


class RegisterForm(forms.Form):
    username = forms.CharField(
        max_length=50,
        min_length=1,
        error_messages={
            'required': '用户名不能为空',
            'max_length': '用户名长度不能超过50位',
            'min_length': '用户名长度不能少于1位'
        }
    )
    email = forms.EmailField(
        error_messages={
            'required': '邮箱不能为空',
            'invalid': '请输入有效的邮箱地址'
        }
    )
    captcha = forms.CharField(
        max_length=4,
        min_length=4,
        error_messages={
            'required': '验证码不能为空',
            'max_length': '验证码必须为4位',
            'min_length': '验证码必须为4位'
        }
    )
    password = forms.CharField(
        max_length=20,
        min_length=6,
        error_messages={
            'required': '密码不能为空',
            'max_length': '密码长度不能超过20位',
            'min_length': '密码长度不能少于6位'
        }
    )

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not email.endswith('@qq.com'):
            raise forms.ValidationError('仅支持QQ邮箱注册！')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('该邮箱已注册，请直接登录！')
        return email

    def clean_captcha(self):
        captcha = self.cleaned_data.get('captcha')
        email = self.cleaned_data.get('email')

        if not email:
            return captcha

        # 取最新的验证码（按create_time倒序，确保是刚发送的）
        captcha_obj = CaptchaModel.objects.filter(email=email).order_by('-create_time').first()

        if not captcha_obj:
            raise forms.ValidationError('请先获取验证码！')

        # 校验验证码是否正确
        if captcha_obj.captcha != captcha:
            raise forms.ValidationError('验证码错误！')

        # 修复：放宽有效期（比如6分钟），并确保时间差计算正确
        # 关键：使用 timezone 统一时间，避免本地时间/UTC时间差异
        time_diff = timezone.now() - captcha_obj.create_time
        if time_diff > timedelta(minutes=6):  # 原5分钟，放宽1分钟容错
            raise forms.ValidationError('验证码已过期，请重新获取！')

        return captcha


class LoginForm(forms.Form):
    email = forms.EmailField(
        error_messages={
            'required': '邮箱不能为空',
            'invalid': '请输入有效的邮箱地址'
        }
    )
    password = forms.CharField(
        error_messages={
            'required': '密码不能为空'
        }
    )
    remember_me = forms.BooleanField(required=False)

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not User.objects.filter(email=email).exists():
            raise forms.ValidationError('该邮箱未注册，请先注册！')
        return email