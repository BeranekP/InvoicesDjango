from ._modules import *
mime = magic.Magic(mime=True)


class SignupView(View):
    template_name = 'user/profile.html'
    login_url = '/'
    redirect_field_name = ''

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('/invoices')
        return render(request, self.template_name, {'profile': None, 'create': True})

    def post(self, request):
        username = request.POST['name']
        password1 = request.POST['password']
        password2 = request.POST['password-confirm']

        user_profile = UserProfile()

        user_profile.email = request.POST['email']
        user_profile.web = request.POST['web']
        user_profile.name = request.POST['name']
        user_profile.street = request.POST['street']
        user_profile.town = request.POST['town']
        user_profile.zipcode = request.POST['zipcode']
        user_profile.ic = request.POST['ic']
        if UserProfile.objects.filter(ic=user_profile.ic).exists():
            messages.warning(request, f'Uživatel s tímto IČ již existuje')
            return redirect('/signup')
        try:
            user_profile.logo = request.FILES['logo']
            mime_type = mime.from_buffer(user_profile.logo.read())
            if mime_type != 'image/svg+xml':
                messages.warning(request, 'Vložte logo v SVG formátu.')
                return redirect('/signup/')
        except:
            pass
        try:
            user_profile.sign = request.FILES['sign']
            mime_type = mime.from_buffer(user_profile.sign.read())
            if mime_type != 'image/png' and mime_type != 'image/jpeg':
                messages.warning(
                    request, 'Vložte podpis v JPG nebo PNG formátu.')
                return redirect('/signup/')
        except:
            pass
        user_profile.rnd_id = randstring(25)

        if request.POST['dic']:
            user_profile.dic = request.POST['dic']

        user_profile.bank = request.POST['bank']

        if password1 and password2:
            if password1 == password2:
                if User.objects.filter(username=user_profile.email).exists():
                    messages.warning(
                        request, f'Uživatel {user_profile.email} již existuje')
                    return redirect('/signup/')
                user = User.objects.create_user(
                    user_profile.email, '', password1)
            else:
                messages.warning(request, 'Hesla se neshodují.')
                return redirect('/signup/')
        else:
            messages.warning(request, 'Neplatné heslo')
            return redirect('/signup/')
        user_profile.user = user

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
