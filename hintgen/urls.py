from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^feedback/([0-9]+)/([0-9]+)/$', views.feedback, name="feedback"),
    url(r'^hint/([0-9]+)/([0-9]+)/$', views.hint, name="hint"),
]