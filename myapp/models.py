from django.db import models
from barcode import Code128
from barcode.writer import ImageWriter
from io import BytesIO
from django.core.files.base import ContentFile
import hashlib
import string
from django.db import models
from django.contrib.auth.hashers import make_password, check_password
from django.db.models.signals import post_migrate
from django.utils import timezone
from datetime import date

class Patient(models.Model):
    TITLE_CHOICES = [
        ('MR', 'Mr'),
        ('MS', 'Ms'),
        ('MRS', 'Mrs'),
    ]

    MARITAL_STATUS_CHOICES = [
        ('SINGLE', 'Single'),
        ('MARRIED', 'Married'),
        ('DIVORCED', 'Divorced'),
        ('WIDOWED', 'Widowed'),
    ]

    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]

    # Basic Information (Form 1)
    title = models.CharField(max_length=3, choices=TITLE_CHOICES)
    first_name = models.CharField(max_length=50)
    middle_name = models.CharField(max_length=50, blank=True, null=True)
    last_name = models.CharField(max_length=50)
    father_name = models.CharField(max_length=100, null=True, blank=True)
    patient_phone = models.CharField(max_length=20)
    patient_email = models.CharField(max_length=50, blank=True, null=True)
    date_of_birth = models.DateField()
    age = models.CharField(max_length=4, blank=True)
    birth_time = models.CharField(max_length=10)
    marital_status = models.CharField(max_length=10, choices=MARITAL_STATUS_CHOICES)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    patient_id = models.CharField(max_length=20, unique=True)
    issue_date = models.DateField()
    expiry_date = models.DateField()

    # Address (Form 2)
    street = models.CharField(max_length=200)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100)

    # Visa Details (Form 3)
    visa_number = models.CharField(max_length=50, blank=True, null=True, unique=True)
    visa_type = models.CharField(max_length=50, blank=True, null=True)
    visa_expiry = models.DateField(blank=True, null=True)

    # Insurance (Form 4)
    insurance_name = models.CharField(max_length=100, blank=True, null=True)
    insurance_plan = models.CharField(max_length=100, blank=True, null=True)
    insurance_benefits = models.TextField(blank=True, null=True)

    # Auto-generated fields
    mrn_number = models.CharField(max_length=64, unique=True, blank=True, null=True)
    barcode = models.ImageField(upload_to='barcodes/', blank=True, null=True)

    class Meta:
        ordering = ['-issue_date']

    def __str__(self):
        return f"{self.full_name} ({self.patient_id})"

    @property
    def full_name(self):
        """Returns the full name of the patient."""
        return f"{self.first_name} {self.middle_name or ''} {self.last_name}".strip()

    def save(self, *args, **kwargs):
        """Overrides save method to generate MRN number and barcode."""
        if not self.mrn_number:
            name_and_id = f"{self.full_name}{self.patient_id}"
            self.mrn_number = hashlib.sha256(name_and_id.encode('utf-8')).hexdigest()

        if not self.barcode and self.mrn_number:
            barcode_buffer = BytesIO()
            Code128(self.mrn_number, writer=ImageWriter()).write(barcode_buffer)
            self.barcode.save(f"barcode_{self.patient_id}.png", ContentFile(barcode_buffer.getvalue()), save=False)

        super().save(*args, **kwargs)

class EmergencyContact(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='emergency_contacts')
    emergency_name = models.CharField(max_length=100)
    emergency_relationship = models.CharField(max_length=50)
    emergency_phone = models.CharField(max_length=20)
    emergency_email = models.CharField(max_length=100, blank=True, null=True)

class FamilyMember(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='family_members')
    family_name = models.CharField(max_length=100)
    family_relationship = models.CharField(max_length=50)
    family_contact = models.CharField(max_length=20)

class Guarantor(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='guarantors')
    guarantor_name = models.CharField(max_length=100)
    guarantor_relationship = models.CharField(max_length=50)
    guarantor_contact = models.CharField(max_length=20)
    guarantor_address = models.TextField()

class MedicalTest(models.Model):
    test_code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    
    def __str__(self):
        return f"{self.test_code} - {self.name}"

class People(models.Model):
    DESIGNATION_CHOICES = [
        ('ad', 'Admin'),
        ('dr', 'Doctor'),
        ('fd', 'Frontdesk'),
        ('nu', 'Nurse'),
        ('ph', 'Pharmacist'),
        ('su', 'Superuser'),
    ]

    username = models.CharField(max_length=50, blank=True, null=True)
    password = models.CharField(max_length=1000, blank=True, null=True)
    designation = models.CharField(max_length=2, choices=DESIGNATION_CHOICES)
    member_fname = models.CharField(max_length=50)
    member_lname = models.CharField(max_length=50)
    member_phone = models.CharField(max_length=50)
    member_email = models.CharField(max_length=100)
    member_dob = models.DateField()
    last_login = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        self.member_dob = str(self.member_dob)
        self.member_date = self.member_dob[5:].replace('-','')
        if self.username != 'su.superuser':
            self.username = f"{self.designation.lower()}.{self.member_fname.lower()}{self.member_date}"
            self.password = make_password(self.username)
        super().save(*args, **kwargs)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    def __str__(self):
        return f"{self.designation.upper()} - {self.member_fname} {self.member_lname}"

class Doctor(models.Model):
    name = models.CharField(max_length=100)
    department = models.CharField(max_length=100)
    
    def __str__(self):
        return f"{self.name} - {self.department}"

class Schedule(models.Model):
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.doctor.name} - {self.date} ({self.start_time} to {self.end_time})"

class Appointment(models.Model):
    STATUS_CHOICES = [
        ('NEW', 'New'),
        ('CONFIRMED', 'Confirmed'),
        ('CANCELLED', 'Cancelled'),
        ('COMPLETED', 'Completed')
    ]
    
    patient_name = models.CharField(max_length=100)
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='NEW')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.patient_name} - {self.doctor.name} - {self.schedule.date}"
    
class Symptom(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)
    category = models.CharField(
        max_length=100, 
        choices=[
            ('GENERAL', 'General'),
            ('CARDIOVASCULAR', 'Cardiovascular'),
            ('RESPIRATORY', 'Respiratory'),
            ('GASTROINTESTINAL', 'Gastrointestinal'),
            ('NEUROLOGICAL', 'Neurological'),
            ('MUSCULOSKELETAL', 'Musculoskeletal'),
            ('ENDOCRINE', 'Endocrine'),
        ],
        default='GENERAL'  # Add this default value
    )

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['category', 'name']

class ICD10Code(models.Model):
    code = models.CharField(max_length=10)
    description = models.TextField()
    symptoms = models.ManyToManyField(Symptom)
    
    def __str__(self):
        return f"{self.code} - {self.description}"

class CPTCode(models.Model):
    code = models.CharField(max_length=10)
    description = models.TextField()
    fee = models.DecimalField(max_digits=10, decimal_places=2)
    icd10_codes = models.ManyToManyField(ICD10Code, related_name='cpt_codes')
    
    def __str__(self):
        return f"{self.code} - {self.description}"

class PatientDiagnosis(models.Model):
    diagnosis_id = models.CharField(max_length=50, blank=True, null=True)
    patient_id = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='diagnosis')
    patient_name = models.CharField(max_length=200)
    symptoms = models.ManyToManyField(Symptom)
    icd10_code = models.ForeignKey(ICD10Code, on_delete=models.CASCADE)
    cpt_codes = models.ManyToManyField(CPTCode)
    diagnosis_date = models.DateTimeField(default=date.today)
    notes = models.TextField(null=True, blank=True)
    
    def save(self, *args, **kwargs):
        print(self.diagnosis_date)
        self.diagnosis_id = f"diag_{(str(self.patient_id))[-5:-1]}_{(str(self.diagnosis_date))[5:].replace('-','')}"
        super().save(*args, **kwargs)
    def __str__(self):
        return f"Diagnosis for {self.patient_name} on {self.diagnosis_date}"

class TreatmentProcedure(models.Model):
    PRIORITY_CHOICES = [
        ('URGENT', 'Urgent'),
        ('HIGH', 'High Priority'),
        ('REGULAR', 'Regular'),
    ]
    
    STATUS_CHOICES = [
        ('SCHEDULED', 'Scheduled'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled')
    ]

    diagnosis_id = models.ForeignKey(PatientDiagnosis, on_delete=models.CASCADE)
    cpt_code = models.ForeignKey(CPTCode, on_delete=models.CASCADE)
    procedure_name = models.CharField(max_length=200)
    description = models.TextField()
    preparation_instructions = models.TextField(blank=True)
    
    # Scheduling & Assignment
    scheduled_date = models.DateTimeField()
    department = models.CharField(max_length=100)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='REGULAR')
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SCHEDULED')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    completion_date = models.DateTimeField(null=True, blank=True)
    completion_notes = models.TextField(blank=True)
    performed_by = models.CharField(max_length=100, blank=True)
    results_summary = models.TextField(blank=True)
    follow_up_required = models.BooleanField(default=False)
    follow_up_date = models.DateTimeField(null=True, blank=True)

    def update_status(self, new_status, **kwargs):
        self.status = new_status
        if new_status == 'COMPLETED':
            self.completion_date = timezone.now()
        for field, value in kwargs.items():
            setattr(self, field, value)
        self.save()

    def __str__(self):
        return f"{self.procedure_name} for {self.diagnosis_id.patient_name}"

class Medication(models.Model):
    # diagnosis_id = models.ForeignKey(PatientDiagnosis, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    generic_name = models.CharField(max_length=200)
    form = models.CharField(max_length=50, choices=[
        ('TABLET', 'Tablet'),
        ('CAPSULE', 'Capsule'),
        ('SYRUP', 'Syrup'),
        ('INJECTION', 'Injection'),
        ('CREAM', 'Cream'),
        ('OINTMENT', 'Ointment')
    ])
    strength = models.CharField(max_length=50)
    icd10_codes = models.ManyToManyField('ICD10Code', related_name='medications')
    contraindications = models.TextField(blank=True)
    side_effects = models.TextField(blank=True)
    recommended_dosage = models.TextField(default=dict)
    interactions = models.ManyToManyField('self', blank=True, symmetrical=True)

    def __str__(self):
        return f"{self.name} {self.strength} ({self.form})"

class Prescription(models.Model):
    STATUS_CHOICES = [
        ('PRESCRIBED', 'Prescribed'),
        ('DISPENSING', 'Dispensing'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled')
    ]
    patient_diagnosis = models.ForeignKey(PatientDiagnosis, on_delete=models.CASCADE, null=True)
    medication = models.ForeignKey(Medication, on_delete=models.CASCADE, null=True)
    dosage = models.CharField(max_length=100, default='')  # Added default
    frequency = models.CharField(max_length=100, default='') 
    duration = models.CharField(max_length=100, default='')
    instructions = models.TextField(default='')
    prescribed_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PRESCRIBED')


class VitalSigns(models.Model):
    patient = models.ForeignKey(PatientDiagnosis, on_delete=models.CASCADE)
    recorded_at = models.DateTimeField(auto_now_add=True)
    recorded_by = models.CharField(max_length=100)  # Nurse name

    # Temperature
    temperature = models.DecimalField(max_digits=4, decimal_places=1)  # in Celsius
    temperature_method = models.CharField(max_length=20, choices=[
        ('ORAL', 'Oral'),
        ('AXILLARY', 'Axillary'),
        ('TYMPANIC', 'Tympanic'),
        ('RECTAL', 'Rectal')
    ])

    # Blood Pressure
    systolic_bp = models.IntegerField()  # in mmHg
    diastolic_bp = models.IntegerField()  # in mmHg

    # Heart Rate and Oxygen
    heart_rate = models.IntegerField()  # beats per minute
    respiratory_rate = models.IntegerField()  # breaths per minute
    oxygen_saturation = models.IntegerField()  # SpO2 in percentage

    # Pain Assessment
    pain_score = models.IntegerField(choices=[(i, str(i)) for i in range(11)])  # 0-10 scale
    pain_location = models.CharField(max_length=100, blank=True)

    # Additional Observations
    consciousness_level = models.CharField(max_length=50, choices=[
        ('ALERT', 'Alert'),
        ('VERBAL', 'Responds to Verbal'),
        ('PAIN', 'Responds to Pain'),
        ('UNRESPONSIVE', 'Unresponsive')
    ])
    notes = models.TextField(blank=True)

    @property
    def check_alerts(self):
        alerts = []
        
        # Temperature alerts (in Celsius)
        if self.temperature >= 38.3:
            alerts.append({
                'type': 'danger',
                'message': f'High Fever: {self.temperature}°C'
            })
        elif self.temperature >= 37.8:
            alerts.append({
                'type': 'warning',
                'message': f'Mild Fever: {self.temperature}°C'
            })
        elif self.temperature < 36:
            alerts.append({
                'type': 'danger',
                'message': f'Low Temperature: {self.temperature}°C'
            })

        # Blood Pressure alerts
        if self.systolic_bp >= 140 or self.diastolic_bp >= 90:
            alerts.append({
                'type': 'danger',
                'message': f'High Blood Pressure: {self.systolic_bp}/{self.diastolic_bp}'
            })
        elif self.systolic_bp < 90 or self.diastolic_bp < 60:
            alerts.append({
                'type': 'danger',
                'message': f'Low Blood Pressure: {self.systolic_bp}/{self.diastolic_bp}'
            })

        # Heart Rate alerts
        if self.heart_rate > 100:
            alerts.append({
                'type': 'warning',
                'message': f'Tachycardia: {self.heart_rate} bpm'
            })
        elif self.heart_rate < 60:
            alerts.append({
                'type': 'warning',
                'message': f'Bradycardia: {self.heart_rate} bpm'
            })

        # SpO2 alerts
        if self.oxygen_saturation < 95:
            alerts.append({
                'type': 'danger',
                'message': f'Low Oxygen Saturation: {self.oxygen_saturation}%'
            })

        # Respiratory Rate alerts
        if self.respiratory_rate > 20:
            alerts.append({
                'type': 'warning',
                'message': f'High Respiratory Rate: {self.respiratory_rate}'
            })
        elif self.respiratory_rate < 12:
            alerts.append({
                'type': 'danger',
                'message': f'Low Respiratory Rate: {self.respiratory_rate}'
            })

        return alerts

    def __str__(self):
        return f"Vitals for {self.patient} at {self.recorded_at}"

    class Meta:
        verbose_name_plural = "Vital Signs"
