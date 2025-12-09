from django import forms
from django.contrib.auth import get_user_model
from .models import CaptchaModel

User = get_user_model()



class RegisterForm(forms.Form):
    username = forms.CharField(
        max_length=20,
        min_length=1,
        error_messages={
            'required': '请传入用户名',
            'max_length': '用户名长度在1-20之间',
            'min_length': '用户名长度在1-20之间',
        }
    )
    email = forms.EmailField(
        error_messages={
            'required': '请传入邮箱',
            'invalid': '请传入一个正确的邮箱！'
        }
    )
    captcha = forms.CharField(
        max_length=4,
        min_length=4,
        error_messages={
            'max_length': '验证码长度为4',
            'min_length': '验证码长度为4'
        }
    )
    password = forms.CharField(
        max_length=20,
        min_length=6,
        error_messages={
            'max_length': '密码长度在6-20之间',
            'min_length': '密码长度在6-20之间'
        }
    )

    # 1. 移除独立的clean_username/clean_email/clean_captcha方法
    # 2. 统一在clean方法中按顺序校验（确保先提示邮箱/用户名错误，再校验验证码）
    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get('username')
        email = cleaned_data.get('email')
        captcha = cleaned_data.get('captcha')
        password = cleaned_data.get('password')

        # 第一步：校验用户名（基础+唯一性）
        if username:
            if User.objects.filter(username=username).exists():
                self.add_error('username', '用户名已存在')
            if len(username) < 1 or len(username) > 20:
                self.add_error('username', '用户名长度在1-20之间')

        # 第二步：校验邮箱（格式+唯一性）- 优先于验证码
        if email:
            if not email.endswith('@qq.com'):
                self.add_error('email', '仅支持QQ邮箱注册！')
            if User.objects.filter(email=email).exists():
                self.add_error('email', '该邮箱已注册！')  # 优先提示邮箱错误

        # 第三步：校验密码（基础）
        if password and (len(password) < 6 or len(password) > 20):
            self.add_error('password', '密码长度在6-20之间')

        # 第四步：仅当邮箱无错误时，才校验验证码（核心！）
        if email and not self.errors.get('email') and captcha:
            captcha_model = CaptchaModel.objects.filter(email=email, captcha=captcha).first()
            if not captcha_model:
                self.add_error('captcha', '验证码错误！')
            else:
                captcha_model.delete()

        # 返回清理后的数据（即使有错误也要返回）
        return cleaned_data



class LoginForm(forms.Form):
    email = forms.EmailField(error_messages={'required': '请传入邮箱', 'invalid': '请传入一个正确的邮箱！'})
    password = forms.CharField(max_length=20, min_length=6,error_messages={'max_length': '密码长度在6-20之间', 'min_length': '密码长度在6-20之间'})
    remember_me = forms.BooleanField(required=False)