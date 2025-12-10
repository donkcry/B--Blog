from django.db import models

class CaptchaModel(models.Model):
    email = models.EmailField(unique=True)
    captcha = models.CharField(max_length=4)
    # 修复：auto_now=True 每次保存都会更新时间
    create_time = models.DateTimeField(auto_now=True)  

    class Meta:
        ordering = ['-create_time']  # 按时间倒序，优先取最新验证码