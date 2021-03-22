from ._modules import *


class SignupView(LoginRequiredMixin, View):
    template_name = 'signup/form.html'
    login_url = '/'
    redirect_field_name = ''

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('/invoices')
        return render(request, self.template_name)

    def post(self, request):
        username = request.POST['username']
        password = request.POST['password']
        user = User.objects.create_user(username, '', password)
        user_profile = UserProfile()
        user_profile.user = user
        user_profile.email = request.POST['email']
        user_profile.web = request.POST['web']
        user_profile.name = request.POST['name']
        user_profile.street = request.POST['street']
        user_profile.town = request.POST['town']
        user_profile.zipcode = request.POST['zipcode']
        user_profile.ic = request.POST['ic']
        user_profile.logo = request.FILES['logo']
        user_profile.sign = request.FILES['sign']
        user_profile.rnd_id = randstring(25)
        if request.POST['dic']:
            user_profile.dic = request.POST['dic']
        user_profile.bank = request.POST['bank']

        user_profile.save()
        user.save()
        return redirect('/')


class LoginView(View):
    def post(self, request):
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('/dash')
        else:
            messages.error(request, 'Neplatné uživatelské jméno nebo heslo.')
            return redirect('/')


class LogoutView(View):
    def get(self, request):
        logout(request)
        return redirect('/')


class UserProfileUpdateView(LoginRequiredMixin, View):
    login_url = '/'
    redirect_field_name = 'invoices/'
    template_name = 'user/profile.html'

    def get(self, request, id):
        ref = request.META['HTTP_REFERER']
        profile = UserProfile.objects.get(id=id, user=request.user)
        context = {'profile': profile,
                   'user': request.user,
                   'ref': ref}
        response = render(request, self.template_name, context)
        response.set_cookie(key='ref', value=ref)
        return response

    def post(self, request, id):
        user_profile = UserProfile.objects.get(id=id, user=request.user)
        user_profile.email = request.POST['email']
        user_profile.web = request.POST['web']
        user_profile.name = request.POST['name']
        user_profile.street = request.POST['street']
        user_profile.town = request.POST['town']
        user_profile.zipcode = request.POST['zipcode']
        user_profile.ic = request.POST['ic']
        if request.POST['dic']:
            user_profile.dic = request.POST['dic']
        user_profile.bank = request.POST['bank']
        try:
            user_profile.logo = request.FILES['logo']
        except:
            pass
        try:
            user_profile.sign = request.FILES['sign']
        except:
            pass

        user = User.objects.get(id=request.user.id)
        password1 = request.POST['password']
        password2 = request.POST['password-confirm']
        ref = request.COOKIES.get('ref')

        if password1 and password2:
            if password1 == password2:
                user.set_password(password1)
                user.save()
                messages.success(
                    request, 'Heslo změněno.')
            else:
                messages.warning(request, 'Hesla se neshodují.')
                return redirect(ref)

        user_profile.save()
        messages.success(
            request, 'Vaše údaje byly aktualizovány.')

        return redirect(ref)
