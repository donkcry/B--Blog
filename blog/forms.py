from django import forms

from blog.models import BlogCategory


class EditBlogForm(forms.Form):
    title=forms.CharField(max_length=200,min_length=1)
    content=forms.CharField(min_length=1)
    category=forms.IntegerField()