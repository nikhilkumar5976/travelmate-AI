from django.shortcuts import render,redirect
from django.contrib.auth.decorators import login_required
from .forms import SignUpForm
from .models import Profile
from django.contrib.auth import login

# Create your views here.
def sigup(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method=='POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user=form.save()
            Profile.objects.create(user=user)
            login(request,user)
            return redirect('home')

    else:
        form=SignUpForm()
    return render(request,'accounts/signup.html',{'form':form})


@login_required
def home(request):
    return render(request,'home.html')