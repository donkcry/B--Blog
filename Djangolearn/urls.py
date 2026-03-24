from django.contrib import admin
from django.urls import path, include

import blog.urls
import BLauth.urls
from django.conf import settings
from django.conf.urls.static import static



urlpatterns = [
    path('orkj2830504asx8yadmin/', admin.site.urls),
    path('',include(blog.urls)),
    path('BLauth/', include(BLauth.urls)),
    path('icon',include('icon.urls')),
    path('private/',include('private.urls')),
]


from django.views.static import serve
urlpatterns += [
    path('media/<path:path>', serve, {'document_root': settings.MEDIA_ROOT}),
]