from django.shortcuts import render

# Create your views here.

def iconclick(request):
    return render(request,'iconclick.html')