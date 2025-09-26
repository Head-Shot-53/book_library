from django.urls import path
from . import views

urlpatterns = [
    path('', views.book_list, name='book_list'),
    path('book/add/', views.book_create, name='book_create'),
    path('book/<slug:slug>/', views.book_detail, name='book_detail'),
    path('book/update/<slug:slug>/', views.book_update, name='book_update'),
    path('book/delete/<slug:slug>/', views.book_delete, name='book_delete')
    
]