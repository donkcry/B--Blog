from django.shortcuts import render


def ratelimited_view(request, exception=None):
    """自定义 429 错误页面视图"""
    return render(request, '429.html', status=429)
