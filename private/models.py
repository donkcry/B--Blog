from django.db import models
from django.contrib.auth import get_user_model
from datetime import datetime, timedelta

User = get_user_model()

class VerifyCode(models.Model):
    """邮箱验证码模型"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='所属用户')
    code = models.CharField(max_length=6, verbose_name='验证码')
    email = models.EmailField(verbose_name='接收邮箱')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        verbose_name = '注销验证码'
        verbose_name_plural = verbose_name

    def is_valid(self):
        """验证验证码是否有效（5分钟内）"""
        return datetime.now() < self.created_at + timedelta(minutes=5)
