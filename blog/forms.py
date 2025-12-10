# forms.py 完整代码
from django import forms
from blog.models import BlogCategory

class EditBlogForm(forms.Form):
    title = forms.CharField(max_length=200, min_length=1, error_messages={
        'required': '标题不能为空',
        'min_length': '标题长度不能少于1个字符',
        'max_length': '标题长度不能超过200个字符'
    })
    content = forms.CharField(min_length=1, error_messages={
        'required': '内容不能为空',
        'min_length': '内容长度不能少于1个字符'
    })
    category_name = forms.CharField(max_length=200, min_length=1, error_messages={
        'required': '分类不能为空',
        'min_length': '分类长度不能少于1个字符',
        'max_length': '分类长度不能超过200个字符'
    })

    def clean_category_name(self):
        """关键：验证分类，存在则返回ID，不存在则创建并返回ID"""
        category_name = self.cleaned_data.get("category_name").strip()
        # 查找已有分类（不区分大小写）
        category, created = BlogCategory.objects.get_or_create(
            name__iexact=category_name,  # 忽略大小写匹配
            defaults={"name": category_name}  # 不匹配则创建新分类
        )
        return category.id  # 返回分类ID，供视图使用