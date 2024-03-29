from django.conf import settings
from django.urls import path
from .views import signup, activate, resend_activation_link, user_login, upload_pdf, query_pdf, delete_pdf
from django.views.static import serve
from django.urls import re_path

urlpatterns = [
    path('signup/', signup, name='signup'),
    path('activate/<str:uidb64>/<str:token>/', activate, name='activate'),
    path('resend-activation/', resend_activation_link, name='resend_activation_link'),
    path('login/', user_login, name='user_login'),
    path('upload/', upload_pdf, name='upload_pdf'),
    path('query/', query_pdf, name='query_pdf'),
    path('delete/', delete_pdf, name='delete_pdf'),
    re_path(r'^media/(?P<path>.*)$', serve, {
            'document_root': settings.MEDIA_ROOT,
        }),
]
