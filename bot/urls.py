# coding: utf-8
from django.conf.urls import include, url
from django.contrib import admin

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = [
    url(r'^', include('main.urls')),
    url(r'^admin/', admin.site.urls)
    # Examples:
    # url(r'^$', bot.views.home, name='home'),
    # url(r'^bot/', include('bot.bot.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # url(r'^admin/', include(admin.site.urls)),
]
