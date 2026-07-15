from django.urls import path

from . import views

urlpatterns = [
    path('', views.SopLoginView.as_view(), name='login'),
    path('registro/', views.RegistroEstudianteView.as_view(), name='registro'),
    path('logout/', views.SopLogoutView.as_view(), name='logout'),

    path('inicio/', views.inicio_view, name='inicio'),

    path('agenda/', views.agenda_view, name='agenda'),
    path('agenda/cancelar/<int:pk>/', views.agenda_cancelar_view, name='agenda_cancelar'),
    path('agenda/cambiar-psicologo/', views.agenda_cambiar_psicologo_view, name='agenda_cambiar_psicologo'),

    path('calendario/', views.calendario_view, name='calendario'),
    path('calendario/toggle/', views.calendario_toggle_view, name='calendario_toggle'),
    path('calendario/eliminar/<int:pk>/', views.calendario_eliminar_view, name='calendario_eliminar'),

    path('citas/', views.gestion_citas_view, name='gestion_citas'),
    path('citas/<int:pk>/atender/', views.gestion_citas_cerrar_view, name='gestion_citas_cerrar'),
    path('citas/<int:pk>/cancelar/', views.gestion_citas_cancelar_view, name='gestion_citas_cancelar'),

    path('expedientes/', views.expedientes_view, name='expedientes'),
    path('expedientes/<str:cedula>/', views.expedientes_view, name='expedientes_detalle'),

    path('registros/', views.registros_view, name='registros'),

    path('psicologos/', views.supervision_view, name='supervision'),
    path('psicologos/<str:cedula>/', views.supervision_view, name='supervision_detalle'),

    path('credenciales/', views.credenciales_view, name='credenciales'),
    path('credenciales/<int:pk>/eliminar/', views.credenciales_eliminar_view, name='credenciales_eliminar'),
]
