from django.apps import AppConfig
from django.db.models.signals import post_migrate
from django.contrib.auth.hashers import make_password
from django.db import IntegrityError

class MyappConfig(AppConfig):
    name = 'myapp'  # Replace 'yourapp' with your app name

    def ready(self):
        """Ensure the superuser is created after migrations."""
        # Connect the post_migrate signal to create the superuser
        post_migrate.connect(create_superuser, sender=self)

def create_superuser(sender, **kwargs):
    """Check if superuser exists, and create it if not."""
    from django.db import transaction

    # Import the People model inside the signal handler to avoid circular imports
    try:
        from .models import People  # Import the People model inside the function

        with transaction.atomic():
            # Check if the superuser already exists
            if not People.objects.filter(username='su.superuser').exists():
                # Create the superuser
                superuser = People.objects.create(
                    username='su.superuser',
                    member_fname='Superuser',
                    member_lname='Admin',
                    member_phone='123456789',
                    member_dob = '2000-1-1',
                    member_email='superuser@example.com',
                    designation='su'
                )
                # Set the password to 'superuser123'
                superuser.password = 'superuser123'
                superuser.password = make_password(superuser.password)
                superuser.save()
                print("Superuser created with username: su.superuser")
    except IntegrityError:
        pass  # Ignore if superuser already exists
