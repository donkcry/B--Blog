from django.db import models
from django.contrib.auth import get_user_model
from datetime import timedelta
from django.utils import timezone
import os
from uuid import uuid4

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
        return timezone.now() < self.created_at + timedelta(minutes=5)



def avatar_upload_path(instance, filename):
    """自定义头像存储路径：media/avatars/用户ID/随机文件名"""
    ext = filename.split('.')[-1]
    filename = f"{uuid4()}.{ext}"  # 避免文件名冲突
    return os.path.join('avatars', str(instance.user.id), filename)



class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    # 头像字段：upload_to指定存储到media/avatars下
    avatar = models.ImageField(upload_to=avatar_upload_path, blank=True, null=True)