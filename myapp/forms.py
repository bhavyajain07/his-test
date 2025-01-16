from django import forms
from .models import Patient, EmergencyContact, FamilyMember, Guarantor, People

class PatientRegistrationForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = '__all__'
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'birth_time': forms.TimeInput(attrs={'type': 'time'}),
            'issue_date': forms.DateInput(attrs={'type': 'date'}),
            'expiry_date': forms.DateInput(attrs={'type': 'date'}),
            'visa_expiry': forms.DateInput(attrs={'type': 'date'}),
        }

class PatientUpdateForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = '__all__'

class EmergencyContactForm(forms.ModelForm):
    class Meta:
        model = EmergencyContact
        exclude = ['patient']

class FamilyMemberForm(forms.ModelForm):
    class Meta:
        model = FamilyMember
        exclude = ['patient']

class GuarantorForm(forms.ModelForm):
    class Meta:
        model = Guarantor
        exclude = ['patient']

class MemberForm(forms.ModelForm):
    class Meta:
        model = People
        fields = '__all__'

class MemberUpdateForm(forms.ModelForm):
    class Meta:
        model = People
        # exclude = ['username', 'password']
        fields = '__all__'

class LoginForm(forms.Form):

    DESIGNATION_CHOICES = People.DESIGNATION_CHOICES
    
    designation = forms.ChoiceField(choices=DESIGNATION_CHOICES, required=True)
    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'placeholder': 'Username'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Password'}))
