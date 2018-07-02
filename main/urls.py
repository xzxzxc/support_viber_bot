# coding: utf-8
from django.conf.urls import url
from . import views

urlpatterns = [
	url(r'^bot_link/', views.link, name='link'),
    url(r'^$', views.index, name='index')
]
