from django.shortcuts import get_object_or_404, render, HttpResponse, redirect
from django.contrib import messages
from django.contrib.auth import login, logout
from .models import *
from .forms import (PatientRegistrationForm, EmergencyContactForm, FamilyMemberForm, GuarantorForm, PatientUpdateForm , MemberForm, MemberUpdateForm, LoginForm)
from .utils import EmiratesIDProcessor
from django.http import HttpResponseRedirect, JsonResponse
from django.conf import settings
from django.template.loader import get_template
from xhtml2pdf import pisa
from io import BytesIO
from datetime import datetime, timedelta
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.utils import timezone
from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
import json
from django.urls import reverse
from PIL import Image, ImageDraw, ImageFont
from django.http import HttpResponse
from django.templatetags.static import static
from django.conf import settings
import os
import io
from django.db.models import Q



# In views.py, modify the registration view:
def registration(request):
    # Get statistics
    total_patients = Patient.objects.count()
    total_appointments = Appointment.objects.count()
    recent_appointments = Appointment.objects.order_by('-created_at')[:5]
    today_appointments = Appointment.objects.filter(
        schedule__date=datetime.today()
    ).count()
    
    context = {
        'total_patients': total_patients,
        'total_appointments': total_appointments,
        'recent_appointments': recent_appointments,
        'today_appointments': today_appointments
    }
    
    return render(request, 'frontdesk/frontdesk.html', context)

# def doctor(request):
#     return render(request, "doctor/doctor_home.html")

def clear_patient_registration(request):
    """
    View to handle clearing the patient registration form
    
    This method will reset all forms related to patient registration
    """
    # Reset all forms to their initial state
    patient_form = PatientRegistrationForm()
    emergency_form = EmergencyContactForm()
    family_form = FamilyMemberForm()
    guarantor_form = GuarantorForm()

    context = {
        'patient_form': patient_form,
        'emergency_form': emergency_form,
        'family_form': family_form,
        'guarantor_form': guarantor_form,
    }

    return render(request, 'frontdesk/patient_registration.html', context)

from datetime import date

def useradmin(request):
    total_schedules = Schedule.objects.count()
    total_doctors = Doctor.objects.count()
    doctors = Doctor.objects.all()
    
    context = {
        'total_schedules': total_schedules,
        'total_doctors': total_doctors,
        'doctors': doctors,
        'today': date.today()
    }
    return render(request, 'admin/admin_home.html', context)

def superuser(request):
    total_members = People.objects.count()
    new_members = People.objects.filter(last_login__isnull=True).count()
    
    recent_activities = []
    for member in People.objects.exclude(last_login__isnull=True).order_by('-last_login')[:5]:
        recent_activities.append({
            'member_name': f"{member.member_fname} {member.member_lname}",
            'action': 'Last login',
            'date': member.last_login
        })
    
    context = {
        'total_members': total_members,
        'new_members': new_members,
        'recent_activities': recent_activities
    }
    return render(request, "superuser/superuser.html", context)

def tests_report(request):
    return render(request, 'frontdesk/test_reports.html')

def search_patient(request):
    patient_data = None
    error_message = None

    if request.method == "POST":
        patient_id = request.POST.get('patient_id')
        try:
            # Fetch patient and related data
            patient = get_object_or_404(Patient, patient_id=patient_id)
            emergency = EmergencyContact.objects.filter(patient=patient)
            family = FamilyMember.objects.filter(patient=patient)
            guarantor = Guarantor.objects.filter(patient=patient)

            patient_data = {
                'patient': patient,
                'emergency': emergency,
                'family': family,
                'guarantor': guarantor,
            }
        except Exception as e:
            print(f"Error: {str(e)}")  # Add this for debugging
            error_message = f"Patient with ID {patient_id} not found."

    return render(request, 'frontdesk/patient_data.html', {
        'patient_data': patient_data,
        'error_message': error_message,
    })

def update_patient(request):
    patient_form = None
    emergency_forms = []
    family_forms = []
    guarantor_forms = []
    success_message = None

    # Step 1: Handle GET request with patient_id to fetch patient data
    if request.method == "GET" and 'patient_id' in request.GET:
        patient_id = request.GET.get('patient_id')
        try:
            patient = Patient.objects.get(patient_id=patient_id)
            patient_form = PatientUpdateForm(instance=patient)
            emergency_forms = [EmergencyContactForm(instance=e) for e in patient.emergency_contacts.all()]
            family_forms = [FamilyMemberForm(instance=f) for f in patient.family_members.all()]
            guarantor_forms = [GuarantorForm(instance=g) for g in patient.guarantors.all()]
        except Patient.DoesNotExist:
            return render(request, 'frontdesk/update_patient.html', {'error': 'Patient not found'})

    # Step 2: Handle POST request to update patient data
    if request.method == "POST":
        patient_id = request.POST.get('patient_id')
        patient = get_object_or_404(Patient, patient_id=patient_id)
        patient_form = PatientUpdateForm(request.POST, instance=patient)

        if patient_form.is_valid():
            patient_form.save()

            emergency_forms = [EmergencyContactForm(request.POST, instance=e) for e in patient.emergency_contacts.all()]
            for form in emergency_forms:
                if form.is_valid():
                    form.save()

            family_forms = [FamilyMemberForm(request.POST, instance=f) for f in patient.family_members.all()]
            for form in family_forms:
                if form.is_valid():
                    form.save()

            guarantor_forms = [GuarantorForm(request.POST, instance=g) for g in patient.guarantors.all()]
            for form in guarantor_forms:
                if form.is_valid():
                    form.save()

            success_message = 'Patient updated successfully!'
            
            # Refresh the forms with updated data
            patient_form = PatientUpdateForm(instance=patient)
            emergency_forms = [EmergencyContactForm(instance=e) for e in patient.emergency_contacts.all()]
            family_forms = [FamilyMemberForm(instance=f) for f in patient.family_members.all()]
            guarantor_forms = [GuarantorForm(instance=g) for g in patient.guarantors.all()]

    context = {
        'patient_form': patient_form,
        'emergency_forms': emergency_forms,
        'family_forms': family_forms,
        'guarantor_forms': guarantor_forms,
        'success_message': success_message,
    }

    return render(request, 'frontdesk/update_patient.html', context)

def patient_registration(request):
    if request.method == 'POST':
        try:
            # Create a modified POST data dictionary
            emergency_data = {
                'emergency_name': request.POST.get('emergency_name'),
                'emergency_relationship': request.POST.get('emergency_relationship'),
                'emergency_phone': request.POST.get('emergency_phone'),
                'emergency_email': request.POST.get('emergency_email')
            }
            
            family_data = {
                'family_name': request.POST.get('family_name'),
                'family_relationship': request.POST.get('family_relationship'),
                'family_contact': request.POST.get('family_contact')
            }
            
            guarantor_data = {
                'guarantor_name': request.POST.get('guarantor_name'),
                'guarantor_relationship': request.POST.get('guarantor_relationship'),
                'guarantor_contact': request.POST.get('guarantor_contact'),
                'guarantor_address': request.POST.get('guarantor_address')
            }

            patient_form = PatientRegistrationForm(request.POST)
            emergency_form = EmergencyContactForm(emergency_data)
            family_form = FamilyMemberForm(family_data)
            guarantor_form = GuarantorForm(guarantor_data)

            if all([
                patient_form.is_valid(),
                emergency_form.is_valid(),
                family_form.is_valid(),
                guarantor_form.is_valid()
            ]):
                patient = patient_form.save()
                
                emergency_contact = emergency_form.save(commit=False)
                emergency_contact.patient = patient
                emergency_contact.save()
                
                family_member = family_form.save(commit=False)
                family_member.patient = patient
                family_member.save()
                
                guarantor = guarantor_form.save(commit=False)
                guarantor.patient = patient
                guarantor.save()
                
                messages.success(request, 'Patient registered successfully!')
                return redirect('registration')
            else:
                print("Patient Form Errors:", patient_form.errors)
                print("Emergency Form Errors:", emergency_form.errors)
                print("Family Form Errors:", family_form.errors)
                print("Guarantor Form Errors:", guarantor_form.errors)
                messages.error(request, 'Please correct the errors in the form.')
        except Exception as e:
            print(f"Exception occurred: {str(e)}")
            messages.error(request, f'An error occurred: {str(e)}')
    else:
        patient_form = PatientRegistrationForm()
        emergency_form = EmergencyContactForm()
        family_form = FamilyMemberForm()
        guarantor_form = GuarantorForm()

    return render(request, 'frontdesk/patient_registration.html', {
        'patient_form': patient_form,
        'emergency_form': emergency_form,
        'family_form': family_form,
        'guarantor_form': guarantor_form,
    })

def process_emirates_id(request):
    if request.method == 'POST' and request.FILES.get('emirates_front') and request.FILES.get('emirates_back'):
        try:
            # Debug prints
            print("Files received:")
            print(f"Front file: {request.FILES['emirates_front'].name}")
            print(f"Back file: {request.FILES['emirates_back'].name}")
            print(f"Front file size: {request.FILES['emirates_front'].size}")
            print(f"Back file size: {request.FILES['emirates_back'].size}")

            processor = EmiratesIDProcessor(
                aws_access_key=settings.AWS_ACCESS_KEY,
                aws_secret_key=settings.AWS_SECRET_KEY,
                aws_region=settings.AWS_REGION,
                bucket_name=settings.AWS_BUCKET_NAME,
                openai_key=settings.OPENAI_API_KEY
            )

            front_file = request.FILES['emirates_front']
            back_file = request.FILES['emirates_back']

            try:
                extracted_data = processor.extract_emirates_data(front_file, back_file)
                
                if not extracted_data:
                    return JsonResponse({
                        'success': False,
                        'error': 'No data could be extracted from the Emirates ID'
                    })

                return JsonResponse({
                    'success': True,
                    'data': extracted_data
                })
            except Exception as e:
                print(f"Extraction error: {str(e)}")
                return JsonResponse({
                    'success': False,
                    'error': f'Data extraction failed: {str(e)}'
                })

        except Exception as e:
            print(f"Processing error: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': f'Processing failed: {str(e)}'
            })

    return JsonResponse({
        'success': False,
        'error': 'Invalid request or missing files'
    })

def generate_patient_pdf(request, patient_id):
    try:
        # Get patient by patient_id
        patient = Patient.objects.get(patient_id=patient_id)
        emergency_contact = patient.emergency_contacts.first()
        
        # Prepare template context
        context = {
            'patient': patient,
            'emergency_contact': emergency_contact,
            'registration_date': datetime.now().strftime("%d/%m/%Y")
        }
        
        # Render template
        template = get_template('frontdesk/patient_pdf.html')
        html = template.render(context)
        
        # Create PDF
        result = BytesIO()
        try:
            pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
            if not pdf.err:
                response = HttpResponse(result.getvalue(), content_type='application/pdf')
                filename = f"patient_{patient_id}.pdf"
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
                return response
            else:
                print("PDF generation error:", pdf.err)  # Add this for debugging
                return HttpResponse('Error generating PDF', status=400)
        except Exception as pdf_error:
            print("PDF creation error:", str(pdf_error))  # Add this for debugging
            return HttpResponse(f'Error creating PDF: {str(pdf_error)}', status=500)
            
    except Patient.DoesNotExist:
        print(f"Patient with ID {patient_id} not found")  # Add this for debugging
        return HttpResponse('Patient not found', status=404)
    except Exception as e:
        print("General error:", str(e))  # Add this for debugging
        return HttpResponse(f'Error: {str(e)}', status=500)



def generate_id_card(request, patient_id):
    try:
        # Get patient
        patient = Patient.objects.get(patient_id=patient_id)
        
        # Create base image
        card_width = 1012  # 3.375 inches * 300 dpi
        card_height = 638  # 2.125 inches * 300 dpi
        image = Image.new('RGB', (card_width, card_height), 'white')
        draw = ImageDraw.Draw(image)
        
        # Draw header background
        draw.rectangle([(0, 0), (card_width, 150)], fill='#1de9b6')
        
        # Load fonts (using default for now, replace with your font paths)
        try:
            title_font = ImageFont.truetype('arial.ttf', 40)
            normal_font = ImageFont.truetype('arial.ttf', 30)
        except:
            title_font = ImageFont.load_default()
            normal_font = ImageFont.load_default()
        
        # Draw hospital name
        draw.text((30, 30), 'HOSPITAL MANAGEMENT SYSTEM', font=title_font, fill='white')
        
        # Load and paste avatar
        avatar_path = os.path.join(settings.BASE_DIR, 'myapp', 'static', 'assets', 'images', 'user', 'avatar-1.jpg')
        try:
            avatar = Image.open(avatar_path)
            # Create circular avatar
            size = (150, 150)
            mask = Image.new('L', size, 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse([0, 0, size[0], size[1]], fill=255)
            
            avatar = avatar.resize(size)
            output = Image.new('RGBA', size, (0, 0, 0, 0))
            output.paste(avatar, (0, 0))
            output.putalpha(mask)
            
            # Paste avatar
            image.paste(avatar, (50, 100), mask)
        except Exception as e:
            print(f"Error adding avatar: {str(e)}")
            
        # Draw patient info
        info_start_x = 250  # Starting x position for text
        y_offset = 180      # Starting y position for text
        
        # Draw patient name
        draw.text((info_start_x, y_offset), 
                 f"Name: {patient.first_name} {patient.middle_name} {patient.last_name}",
                 font=normal_font, fill='black')
        
        # Draw Patient ID
        y_offset += 50
        draw.text((info_start_x, y_offset), 
                 f"Patient ID: {patient.patient_id}",
                 font=normal_font, fill='black')
        
        # Draw MRN
        y_offset += 50
        draw.text((info_start_x, y_offset),
                 f"MRN: {patient.mrn_number}",
                 font=normal_font, fill='black')
        
        # Draw DOB
        y_offset += 50
        draw.text((info_start_x, y_offset),
                 f"DOB: {patient.date_of_birth.strftime('%d/%m/%Y')}",
                 font=normal_font, fill='black')
        
        # Draw Gender
        y_offset += 50
        draw.text((info_start_x, y_offset),
                 f"Gender: {patient.get_gender_display()}",
                 font=normal_font, fill='black')

        # Add barcode at the bottom
        if patient.barcode:
            try:
                barcode_img = Image.open(patient.barcode.path)
                barcode_width = 400
                barcode_height = 100
                barcode_img = barcode_img.resize((barcode_width, barcode_height))
                # Center the barcode at the bottom
                barcode_x = (card_width - barcode_width) // 2
                barcode_y = card_height - barcode_height - 20
                image.paste(barcode_img, (barcode_x, barcode_y))
            except Exception as e:
                print(f"Error adding barcode: {str(e)}")

        # Save image
        buffer = io.BytesIO()
        image.save(buffer, format='PNG', quality=95)
        buffer.seek(0)
        
        # Return response
        response = HttpResponse(buffer, content_type='image/png')
        response['Content-Disposition'] = f'attachment; filename="patient_id_card_{patient_id}.png"'
        return response

    except Patient.DoesNotExist:
        return HttpResponse('Patient not found', status=404)
    except Exception as e:
        return HttpResponse(f'Error: {str(e)}', status=500)

def member_registration(request):
    if request.method == 'POST':
        try:
            member_form = MemberForm(request.POST)
            
            if member_form.is_valid():
                member_form.save()
                
                messages.success(request, 'Member registered successfully!')
                return redirect('superuser')
            else:
                print("Member Form Errors:", member_form.errors)
                
                messages.error(request, 'Please correct the errors in the form.')
        except Exception as e:
            print(f"Exception occurred: {str(e)}")
            messages.error(request, f'An error occurred: {str(e)}')
    else:
        member_form = MemberForm()

    return render(request, 'superuser/member_registration.html', {
        'member_form': member_form,
    })

def search_member(request):
    member_data = None
    error_message = None

    if request.method == "POST":
        username = request.POST.get('username')
        try:
            # Fetch patient and related data
            member = get_object_or_404(People, username=username)
            member_data = {
                'member': member,
            }
        except:
            error_message = f"Patient with username: {username} not found."

    return render(request, 'superuser/member_data.html', {
        'member_data': member_data,
        'error_message': error_message,
    })

def update_member(request):
    member_form = None

    if request.method == "GET" and 'username' in request.GET:
        username = request.GET.get('username')
        try:
            member = People.objects.get(username=username)
            member_form = MemberUpdateForm(instance=member)

        except People.DoesNotExist:
            return render(request, 'update_member.html', {'error': 'Member not found'})

    if request.method == "POST":
        username = request.POST.get('username')
        username = get_object_or_404(People, username=username)
        member_form = MemberUpdateForm(request.POST, instance=username)

        if member_form.is_valid():
            member_form.save()

        messages.success(request, 'Member updated successfully!')
        return redirect('superuser')

    context = {
        'member_form': member_form,
    }

    return render(request, 'superuser/update_member.html', context)

def delete_member(request):
    if request.method == "POST":
        username = request.POST.get('username')
        try:
            # Fetch the member by username
            member = People.objects.get(username=username)
            member.delete()

            messages.success(request, f'Member with username "{username}" deleted successfully!')
        except People.DoesNotExist:
            messages.error(request, f'Member with username "{username}" not found.')
        except Exception as e:
            messages.error(request, f'An error occurred: {str(e)}')

        return redirect('superuser')

    return render(request, 'superuser/delete_member.html')


@csrf_protect
def user_login(request):
    next_url = request.GET.get("next", None)

    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            selected_designation = form.cleaned_data['designation']

            try:
                user = People.objects.get(username=username)
            except People.DoesNotExist:
                messages.error(request, 'Invalid username or password.')
                return render(request, 'index.html', {'form': form})

            if user.designation != selected_designation:
                messages.error(request, 'Invalid designation selected.')
                return render(request, 'index.html', {'form': form})

            if user.check_password(password):
                # Update the last_login field before logging in the user
                user.last_login = timezone.now()  # Set the current time
                user.save() 

                login(request, user)

                print(f"Logged in user: {user.username}, Designation: {user.designation}")

                if next_url:
                    print(f"Redirecting to next_url: {next_url}")
                    return redirect(next_url)
                elif user.designation == 'su':
                    print("superuser logged in")
                    return redirect("superuser")
                elif user.designation == 'ad':
                    print("admin logged in")
                    return redirect('useradmin')
                elif user.designation == 'dr':
                    print("doctor logged in")
                    return redirect('doctor')
                elif user.designation == 'fd':
                    print("frontdesk logged in")
                    return redirect('registration')
                elif user.designation == 'nu':
                    print("nurse logged in")
                    return redirect('nurse_dashboard')
                elif user.designation == 'ph':
                    print("pharmacist logged in")
                    return redirect('pharmacist_prescriptions')
            else:
                messages.error(request, 'Invalid username or password.')
    else:
        form = LoginForm()

    return render(request, 'index.html', {'form': form})

@csrf_protect
def user_logout(request):
    logout(request)
    return redirect('user_login')

def doctor_schedule_view(request):

    if not Doctor.objects.exists():
        Doctor.objects.create(name="Doctor A", department="General")
        Doctor.objects.create(name="Doctor B", department="General")

    if request.method == 'POST':
        doctor_id = request.POST.get('doctor')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        
        try:
            doctor = Doctor.objects.get(id=doctor_id)
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            
            current_date = start_date
            while current_date <= end_date:
                Schedule.objects.create(
                    doctor=doctor,
                    date=current_date,
                    start_time=start_time,
                    end_time=end_time
                )
                current_date += timedelta(days=1)
                
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    doctors = Doctor.objects.all()
    return render(request, 'admin\doctor_schedule.html', {'doctors': doctors})

def appointment_booking_view(request):
    if request.method == 'POST':
        patient_name = request.POST.get('patient_name')
        schedule_id = request.POST.get('schedule_id')
        
        try:
            schedule = Schedule.objects.get(id=schedule_id, is_available=True)
            
            Appointment.objects.create(
                patient_name=patient_name,
                doctor=schedule.doctor,
                schedule=schedule,
                status='CONFIRMED'
            )
            
            schedule.is_available = False
            schedule.save()
            
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    doctors = Doctor.objects.all()
    return render(request, 'frontdesk/appointment_booking.html', {'doctors': doctors})

def get_schedule_events(request):
    """API endpoint to get schedule events for calendar"""
    try:
        doctor_id = request.GET.get('doctor')
        events = []
        
        schedules = Schedule.objects.all()
        if doctor_id:
            schedules = schedules.filter(doctor_id=doctor_id)

        for schedule in schedules:
            events.append({
                'title': f'Dr. {schedule.doctor.name} ({schedule.start_time}-{schedule.end_time})',
                'start': schedule.date.isoformat(),
                'className': 'available' if schedule.is_available else 'booked'
            })

        return JsonResponse({'events': events})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

def get_available_slots(request, doctor_id, date):
    """API endpoint to get available slots"""
    try:
        available_slots = Schedule.objects.filter(
            doctor_id=doctor_id,
            date=date,
            is_available=True
        ).values('id', 'start_time', 'end_time')
        
        slots_list = list(available_slots)
        for slot in slots_list:
            slot['start_time'] = slot['start_time'].strftime('%H:%M')
            slot['end_time'] = slot['end_time'].strftime('%H:%M')

        return JsonResponse({
            'status': 'success',
            'slots': slots_list
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

def diagnosis_page(request, patient_id):
    """Main diagnosis page view"""

    patient = get_object_or_404(Patient, patient_id = patient_id)
    symptoms = Symptom.objects.all().order_by('category', 'name')
    symptoms_by_category = {}
    
    for symptom in symptoms:
        if symptom.category not in symptoms_by_category:
            symptoms_by_category[symptom.category] = []
        symptoms_by_category[symptom.category].append(symptom)
    
    return render(request, 'doctor/diagnosis_form.html', {
        'patient': patient,
        'symptoms_by_category': symptoms_by_category
    })

def get_icd10_codes(request):
    """Get ICD10 codes based on symptoms"""
    symptom_ids = request.GET.getlist('symptoms[]')
    
    if not symptom_ids:
        return JsonResponse({'icd10_codes': []})
    
    # Find ICD10 codes that match any of the selected symptoms
    matching_codes = ICD10Code.objects.filter(symptoms__id__in=symptom_ids).distinct()
    
    # Calculate match percentage for each code
    results = []
    for code in matching_codes:
        code_symptom_ids = set(code.symptoms.values_list('id', flat=True))
        selected_symptom_ids = set(map(int, symptom_ids))
        
        # Calculate matching percentage
        matching_symptoms = len(code_symptom_ids.intersection(selected_symptom_ids))
        total_code_symptoms = len(code_symptom_ids)
        match_percentage = (matching_symptoms / total_code_symptoms) * 100
        
        if match_percentage >= 50:  # Only include codes with >50% match
            results.append({
                'id': code.id,
                'code': code.code,
                'description': code.description,
                'match_percentage': round(match_percentage, 1)
            })
    
    # Sort by match percentage
    results.sort(key=lambda x: x['match_percentage'], reverse=True)
    
    return JsonResponse({'icd10_codes': results})

def get_cpt_codes(request):
    """Get CPT codes based on ICD10 code"""
    icd10_code_id = request.GET.get('icd10_code')
    icd10_code = get_object_or_404(ICD10Code, id=icd10_code_id)
    
    cpt_codes = icd10_code.cpt_codes.all().order_by('code')
    
    return JsonResponse({
        'cpt_codes': [
            {
                'id': code.id,
                'code': code.code,
                'description': code.description,
                'fee': str(code.fee)
            } for code in cpt_codes
        ]
    })

@csrf_exempt
def save_diagnosis(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        try:
            patient = get_object_or_404(Patient, patient_id=data['patient_id'])
            icd10_code = get_object_or_404(ICD10Code, id=data['icd10_code_id'])
            
            diagnosis = PatientDiagnosis.objects.create(
                patient_id=patient,
                patient_name=data['patient_name'],
                icd10_code=icd10_code,
                notes=data.get('notes', '')
            )
            
            diagnosis.symptoms.set(data['symptom_ids'])
            diagnosis.cpt_codes.set(data['cpt_code_ids'])
            
            return JsonResponse({
                'status': 'success',
                'diagnosis_id': diagnosis.id,  # Changed from diagnosis_id to id
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)
 
def treatment_procedure_page(request, diagnosis_id):
    diagnosis = get_object_or_404(PatientDiagnosis, id=diagnosis_id)
    procedures = TreatmentProcedure.objects.filter(diagnosis_id=diagnosis)
    
    return render(request, 'doctor/treatment_form.html', {
        'diagnosis': diagnosis,
        'procedures': procedures,
    })

def save_procedure(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            diagnosis = get_object_or_404(PatientDiagnosis, id=data['diagnosis_id'])
            cpt_code = get_object_or_404(CPTCode, id=data['cpt_code_id'])
            
            procedure = TreatmentProcedure.objects.create(
                diagnosis_id=diagnosis,  # Changed from patient_diagnosis to diagnosis_id
                cpt_code=cpt_code,
                procedure_name=data['procedure_name'],
                description=data['description'],
                preparation_instructions=data.get('preparation_instructions', ''),
                scheduled_date=data['scheduled_date'],
                department=data['department'],
                priority=data['priority']
            )
            
            return JsonResponse({
                'status': 'success',
                'procedure_id': procedure.id
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)
        
def update_procedure_status(request, procedure_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            procedure = get_object_or_404(TreatmentProcedure, id=procedure_id)
            
            procedure.update_status(
                new_status=data['status'],
                completion_notes=data.get('completion_notes', ''),
                performed_by=data.get('performed_by', ''),
                results_summary=data.get('results_summary', ''),
                follow_up_required=data.get('follow_up_required', False),
                follow_up_date=datetime.strptime(data.get('follow_up_date', ''), '%Y-%m-%d %H:%M') if data.get('follow_up_date') else None
            )
            
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

def view_procedure_status(request, procedure_id):
    procedure = get_object_or_404(TreatmentProcedure, id=procedure_id)
    return render(request, 'doctor/procedure_status.html', {
        'procedure': procedure
    })

def procedure_monitoring(request, diagnosis_id):
    diagnosis = get_object_or_404(PatientDiagnosis, id=diagnosis_id)
    
    # Get procedures with different statuses
    scheduled_procedures = TreatmentProcedure.objects.filter(
        diagnosis_id=diagnosis,  # Changed from patient_diagnosis to diagnosis_id
        status='SCHEDULED'
    )
    
    in_progress_procedures = TreatmentProcedure.objects.filter(
        diagnosis_id=diagnosis,  # Changed from patient_diagnosis to diagnosis_id
        status='IN_PROGRESS'
    )
    
    completed_procedures = TreatmentProcedure.objects.filter(
        diagnosis_id=diagnosis,  # Changed from patient_diagnosis to diagnosis_id
        status='COMPLETED'
    )
    
    # Check for overdue procedures
    current_time = timezone.now()
    overdue_procedures = scheduled_procedures.filter(
        scheduled_date__lt=current_time
    )
    
    return render(request, 'doctor/monitoring_dashboard.html', {
        'diagnosis': diagnosis,
        'scheduled_procedures': scheduled_procedures,
        'in_progress_procedures': in_progress_procedures,
        'completed_procedures': completed_procedures,
        'overdue_procedures': overdue_procedures,
    })

def medication_list(request, diagnosis_id):
    diagnosis = get_object_or_404(PatientDiagnosis, id=diagnosis_id)
    medications = Medication.objects.filter(icd10_codes=diagnosis.icd10_code)
    prescriptions = Prescription.objects.filter(patient_diagnosis=diagnosis)
    
    return render(request, 'doctor/medication_form.html', {
        'diagnosis': diagnosis,
        'medications': medications,
        'prescriptions': prescriptions
    })

def get_medication_details(request):
    medication_id = request.GET.get('medication_id')
    medication = get_object_or_404(Medication, id=medication_id)
    
    return JsonResponse({
        'contraindications': medication.contraindications,
        'side_effects': medication.side_effects,
        'recommended_dosage': medication.recommended_dosage
    })

@csrf_exempt
def save_prescription(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            diagnosis = get_object_or_404(PatientDiagnosis, id=data['diagnosis_id'])
            medication = get_object_or_404(Medication, id=data['medication_id'])
            
            prescription = Prescription.objects.create(
                patient_diagnosis=diagnosis,
                medication=medication,
                dosage=data['dosage'],
                frequency=data['frequency'],
                duration=data['duration'],
                instructions=data['instructions']
            )
            
            return JsonResponse({
                'status': 'success',
                'prescription_id': prescription.id
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)

def check_interactions(request):
    if request.method == 'POST':
        new_med_id = request.POST.get('new_med')
        current_med_ids = request.POST.getlist('current_meds[]')
        
        new_med = get_object_or_404(Medication, id=new_med_id)
        interactions = []
        
        for med_id in current_med_ids:
            current_med = get_object_or_404(Medication, id=med_id)
            if new_med.interactions.filter(id=current_med.id).exists():
                interactions.append({
                    'medication': current_med.name,
                    'warning': f"Interaction between {new_med.name} and {current_med.name}"
                })
        
        return JsonResponse({'interactions': interactions})
    
def pharmacist_prescriptions(request):
    prescriptions = Prescription.objects.filter(
        status='PRESCRIBED'
    ).order_by('-prescribed_date')
    return render(request, 'pharmacy/prescription_list.html', {
        'prescriptions': prescriptions
    })

def prescription_detail(request, prescription_id):
    prescription = get_object_or_404(Prescription, id=prescription_id)
    return render(request, 'pharmacy/prescription_detail.html', {
        'prescription': prescription
    })

def doctor(request):
    patient_data = None
    error_message = None

    if request.method == "POST":
        patient_id = request.POST.get('patient_id')
        try:
            # Fetch patient and related data
            patient = get_object_or_404(Patient, patient_id=patient_id)
            patient_data = {
                'patient': patient,

            }
        except:
            error_message = f"Patient with ID {patient_id} not found."

    return render(request, 'doctor/doctor_home.html', {
        'patient_data': patient_data,
        'error_message': error_message,
        
    })

def nurse_dashboard(request):
    # Get all patients with active diagnoses
    patients = PatientDiagnosis.objects.all()
    
    today = timezone.now().date()
    
    # Get latest vital signs for each patient
    for patient in patients:
        latest_vitals = VitalSigns.objects.filter(patient=patient).order_by('-recorded_at').first()
        patient.last_vitals = latest_vitals
        
        # Set status based on vitals
        if latest_vitals:
            patient.status = 'Active'
            if (latest_vitals.temperature >= 38.3 or 
                latest_vitals.systolic_bp >= 140 or 
                latest_vitals.diastolic_bp >= 90 or 
                latest_vitals.oxygen_saturation < 95):
                patient.status = 'Critical'
        else:
            patient.status = 'Inactive'

    # Dashboard statistics
    critical_vitals = VitalSigns.objects.filter(
        recorded_at__date=today,
        patient__in=patients
    ).filter(
        Q(temperature__gte=38.3) |
        Q(systolic_bp__gte=140) |
        Q(diastolic_bp__gte=90) |
        Q(oxygen_saturation__lt=95)
    ).count()
    
    todays_assessments = VitalSigns.objects.filter(
        recorded_at__date=today
    ).count()
    
    active_patients = sum(1 for p in patients if p.status in ['Active', 'Critical'])

    return render(request, 'nursing/dashboard.html', {
        'patients': patients,
        'critical_vitals': critical_vitals,
        'todays_assessments': todays_assessments,
        'active_patients': active_patients
    })

# views.py
from django.shortcuts import render, redirect, get_object_or_404
from .models import VitalSigns, PatientDiagnosis

def record_vitals(request, diagnosis_id):
    diagnosis = get_object_or_404(PatientDiagnosis, id=diagnosis_id)
    
    if request.method == 'POST':
        vital_signs = VitalSigns.objects.create(
            patient=diagnosis,
            recorded_by=request.POST.get('recorded_by'),
            temperature=request.POST.get('temperature'),
            temperature_method=request.POST.get('temperature_method'),
            systolic_bp=request.POST.get('systolic_bp'),
            diastolic_bp=request.POST.get('diastolic_bp'),
            heart_rate=request.POST.get('heart_rate'),
            respiratory_rate=request.POST.get('respiratory_rate'),
            oxygen_saturation=request.POST.get('oxygen_saturation'),
            pain_score=request.POST.get('pain_score'),
            pain_location=request.POST.get('pain_location'),
            consciousness_level=request.POST.get('consciousness_level'),
            notes=request.POST.get('notes')
        )
        return redirect('view_vitals', diagnosis_id=diagnosis_id)

    return render(request, 'nursing/record_vitals.html', {
        'diagnosis': diagnosis
    })

def view_vitals(request, diagnosis_id):
    diagnosis = get_object_or_404(PatientDiagnosis, id=diagnosis_id)
    vital_signs = VitalSigns.objects.filter(patient=diagnosis).order_by('-recorded_at')
    
    return render(request, 'nursing/view_vitals.html', {
        'diagnosis': diagnosis,
        'vital_signs': vital_signs
    })

# views.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def save_vitals(request, diagnosis_id):
    if request.method == 'POST':
        try:
            diagnosis = get_object_or_404(PatientDiagnosis, id=diagnosis_id)
            
            vital_signs = VitalSigns.objects.create(
                patient=diagnosis,
                temperature=request.POST.get('temperature'),
                temperature_method=request.POST.get('temperature_method'),
                systolic_bp=request.POST.get('systolic_bp'),
                diastolic_bp=request.POST.get('diastolic_bp'),
                heart_rate=request.POST.get('heart_rate'),
                respiratory_rate=request.POST.get('respiratory_rate'),
                oxygen_saturation=request.POST.get('oxygen_saturation'),
                pain_score=request.POST.get('pain_score'),
                pain_location=request.POST.get('pain_location', ''),
                consciousness_level=request.POST.get('consciousness_level'),
                notes=request.POST.get('notes', ''),
                recorded_by=request.POST.get('recorded_by', 'Nurse')  # You might want to change this when you add authentication
            )
            
            return JsonResponse({
                'status': 'success',
                'message': 'Vital signs recorded successfully'
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)
    
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    }, status=405)



def superuser_dashboard(request):
    total_members = People.objects.count()
    new_members = People.objects.filter(created_at__gte=datetime.now() - timedelta(days=30)).count()
    
    recent_activities = MemberActivity.objects.all().order_by('-timestamp')[:5]
    
    context = {
        'total_members': total_members,
        'new_members': new_members,
        'recent_activities': recent_activities
    }
    return render(request, 'superuser/superuser.html', context)


def view_doctor_schedules(request):
    # Handle date and doctor filtering
    doctor_filter = request.GET.get('doctor', '')
    date_filter = request.GET.get('date', '')
    
    # Base queryset
    schedules = Schedule.objects.select_related('doctor').all()
    
    # Apply filters
    if doctor_filter:
        schedules = schedules.filter(doctor_id=doctor_filter)
    
    if date_filter:
        schedules = schedules.filter(date=date_filter)
    
    # Get list of doctors for filter dropdown
    doctors = Doctor.objects.all()
    
    context = {
        'schedules': schedules,
        'doctors': doctors,
        'selected_doctor': doctor_filter,
        'selected_date': date_filter
    }
    
    return render(request, 'admin/view_schedules.html', context)


def doctor(request):
    patient_data = None
    error_message = None
    
    if request.method == "POST":
        patient_id = request.POST.get('patient_id')
        try:
            patient = get_object_or_404(Patient, patient_id=patient_id)
            patient_data = {
                'patient': patient,
                'latest_diagnosis': PatientDiagnosis.objects.filter(patient_id=patient).last()
            }
        except:
            error_message = f"Patient with ID {patient_id} not found."

    context = {
        'total_patients': Patient.objects.count(),
        'total_diagnoses': PatientDiagnosis.objects.count(),
        'active_treatments': TreatmentProcedure.objects.filter(status='IN_PROGRESS').count(),
        'patient_data': patient_data,
        'error_message': error_message,
    }
    
    return render(request, 'doctor/doctor_home.html', context)