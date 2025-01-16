pip install -r requirements.txt

python manage.py migrate

python manage.py loaddata initial_cpt_codes.json 
python manage.py loaddata initial_icd10_codes.json 
python manage.py loaddata initial_medications.json 
python manage.py loaddata initial_symptoms.json 