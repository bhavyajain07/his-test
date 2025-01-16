from django.contrib import admin
from .models import Patient, EmergencyContact, FamilyMember, Guarantor, People

# Register your models here.
admin.site.register(Patient)
admin.site.register(EmergencyContact)
admin.site.register(FamilyMember)
admin.site.register(Guarantor)
admin.site.register(People)
