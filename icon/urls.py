from django.urls import path
from . import views

app_name = 'icon'

urlpatterns = [
    path('',views.iconclick,name='iconclick'),
]