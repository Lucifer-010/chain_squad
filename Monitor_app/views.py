from django.shortcuts import render
from . import tasks

# Create your views here.

def home(request):
    return render(request, "index.html", {})