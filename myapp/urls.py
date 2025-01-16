from django.urls import path
from . import views 

urlpatterns = [
    path('', views.user_login, name="user_login"),
    path('logout/', views.user_logout, name="logout"),
    path('superuser/', views.superuser, name = "superuser"),
    path('superuser/member_registration/', views.member_registration, name = "member_registration"),
    path('superuser/search_member/', views.search_member, name = "search_member"),
    path('superuser/update_member/', views.update_member, name = "update_member"),
    path('superuser/delete_member/', views.delete_member, name = "delete_member"),
    path('registration/', views.registration, name="registration"),
    path('registration/patient_registration/', views.patient_registration, name="patient_registration"),
    path('registration/patient_registration/clear/', views.clear_patient_registration, name='clear_patient_registration'),
    path('process-emirates-id/', views.process_emirates_id, name='process_emirates_id'),
    path('patient/update/', views.update_patient, name='update_patient'),
    path('patient/search/', views.search_patient, name='search_patient'),
    path('generate-id-card/<str:patient_id>/', views.generate_id_card, name='generate_id_card'),
    path('patient/<str:patient_id>/pdf/', views.generate_patient_pdf, name='generate_patient_pdf'),
    path('tests-report/', views.tests_report, name='tests_report'),
    path('doctor/', views.doctor, name = 'doctor'),
    path('useradmin/', views.useradmin, name = 'useradmin'),
    path('schedule/manage/', views.doctor_schedule_view, name='manage_schedule'),
    path('appointment/book/', views.appointment_booking_view, name='book_appointment'),
    path('api/available-slots/<int:doctor_id>/<str:date>/', views.get_available_slots, name='get_available_slots'),
    path('api/schedule/events/', views.get_schedule_events, name='schedule_events'),

    path('diagnosis/<int:patient_id>/', views.diagnosis_page, name='diagnosis_page'),  # Changed path
    path('diagnosis/api/icd10-codes/', views.get_icd10_codes, name='get_icd10_codes'),
    path('diagnosis/api/cpt-codes/', views.get_cpt_codes, name='get_cpt_codes'),
    path('diagnosis/api/save-diagnosis/', views.save_diagnosis, name='save_diagnosis'),

    path('treatment/procedure/<int:diagnosis_id>/', views.treatment_procedure_page, name='treatment_procedure'),
    path('treatment/procedure/save/', views.save_procedure, name='save_procedure'),
    path('treatment/procedure/<int:procedure_id>/update/', views.update_procedure_status, name='update_procedure_status'),
    path('treatment/procedure/<int:procedure_id>/view/', views.view_procedure_status, name='view_procedure_status'),
    path('treatment/monitoring/<int:diagnosis_id>/', views.procedure_monitoring, name='procedure_monitoring'),

    path('treatment/medication/<int:diagnosis_id>/', views.medication_list, name='medication_list'),
    path('treatment/medication/details/', views.get_medication_details, name='get_medication_details'),
    path('treatment/medication/save/', views.save_prescription, name='save_prescription'),
    path('treatment/medication/check-interactions/', views.check_interactions, name='check_interactions'),

    # urls.py
    path('pharmacy/prescriptions/', views.pharmacist_prescriptions, name='pharmacist_prescriptions'),
    path('pharmacy/prescription/<int:prescription_id>/', views.prescription_detail, name='prescription_detail'),


    path('nursing/dashboard/', views.nurse_dashboard, name='nurse_dashboard'),
    path('nursing/vitals/record/<int:diagnosis_id>/', views.record_vitals, name='record_vitals'),
    path('nursing/vitals/view/<int:diagnosis_id>/', views.view_vitals, name='view_vitals'),
    path('nursing/vitals/save/<int:diagnosis_id>/', views.save_vitals, name='save_vitals'),

]

