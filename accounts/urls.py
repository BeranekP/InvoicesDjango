"""accounts URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, re_path
from invoices import views
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('admin/', admin.site.urls),
    re_path(r'^invoices/delete/(?P<id>\w+)/$',
            views.InvoiceDeleteView.as_view()),
    re_path(r'^advance/delete/(?P<id>\w+)/$',
            views.AdvanceDeleteView.as_view()),
    re_path(r'^invoices/detail/(?P<id>\w+)/$',
            views.InvoiceDetailView.as_view()),
    re_path(r'^advance/detail/(?P<id>\w+)/$',
            views.AdvanceDetailView.as_view()),
    re_path(r'^invoices/edit/(?P<id>\w+)/$',
            views.InvoiceUpdateView.as_view()),
    re_path(r'^advance/edit/(?P<id>\w+)/$',
            views.AdvanceUpdateView.as_view()),
    re_path(r'^users/edit/(?P<id>\w+)/$',
            views.UserProfileUpdateView.as_view()),
    re_path(r'^recipient/edit/(?P<id>\w+)/$',
            views.RecipientUpdateView.as_view()),
    re_path(r'^invoices/print/(?P<id>\w+)/$',
            views.PrintInvoiceView.as_view()),
    re_path(r'^advance/print/(?P<id>\w+)/$',
            views.PrintAdvanceView.as_view()),
    path('invoices/create/', views.InvoiceView.as_view()),
    path('advance/create/', views.AdvanceView.as_view()),
    path('recipient/create/', views.RecipientView.as_view()),
    path('recipient/', views.RecipientOverView.as_view()),
    path('invoices/', views.InvoiceOverView.as_view()),
    path('advance/', views.AdvanceOverView.as_view()),
    path('login/', views.LoginView.as_view()),
    path('logout/', views.LogoutView.as_view()),
    path('signup/', views.SignupView.as_view()),
    path('dash/', views.DashView.as_view()),
    path('mailcopy/', views.MailCopy.as_view()),
    path('print/', views.PrintInvoiceView.as_view()),
    path('', views.HomeView.as_view()),
    path('robots.txt', views.robots),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
