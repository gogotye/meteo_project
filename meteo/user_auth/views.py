from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import render, redirect
from django.contrib.auth import login


def register_view(request):
    """Стандартная view для регистрации пользователя"""

    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)

            request.session.pop('city_history', None)
            request.session.save()

            return redirect('weather_search:search')

    else:
        form = UserCreationForm()

    return render(request, 'user_auth/register.html', {'form': form})