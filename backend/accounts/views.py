from django.shortcuts import render,redirect
from django.contrib.auth.decorators import login_required
from .forms import SignUpForm,EditProfileForm
from .models import Profile
from django.contrib.auth import login
from django.contrib import messages

# Create your views here.
def signup(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            Profile.objects.get_or_create(user=user)
            login(request, user)
            return redirect('home')

    else:
        form = SignUpForm()
    return render(request, 'accounts/signup.html', {'form': form})


@login_required
def home(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    return render(request, 'accounts/home.html', {'profile': profile})


@login_required
def edit_profile(request):
    profile, _ =Profile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = EditProfileForm(request.POST,request.FILES,instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request,'profile saved.')
            return redirect('edit_profile')
    else:
        form=EditProfileForm(instance=profile)
    return render(request,'accounts/edit_profile.html',{'form':form,'profile':profile})