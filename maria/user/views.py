from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django import forms
from .models import User


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('email', 'telefono', 'google_api_key', 'openai_api_key', 'anthropic_api_key')
        widgets = {
            'google_api_key': forms.PasswordInput(render_value=True),
            'openai_api_key': forms.PasswordInput(render_value=True),
            'anthropic_api_key': forms.PasswordInput(render_value=True),
        }


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard')
    else:
        form = RegisterForm()
    return render(request, 'user/register.html', {'form': form})


@login_required
def profile_view(request):
    saved = False
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            saved = True
    else:
        form = ProfileForm(instance=request.user)
    return render(request, 'user/profile.html', {'form': form, 'saved': saved})
