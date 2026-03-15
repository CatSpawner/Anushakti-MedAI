# Hospital AI System — MSc CS Final Year (200-mark level demo)

## Roles
### Admin (single seeded admin)
- username: aditi
- password: Aditi#@!123
- role: admin

### Doctors (seeded)
Password: Doctor@1234
- dr_ashwini, dr_rahul, dr_meera, dr_sanjay, dr_neha, dr_priya, dr_omkar, dr_farhan, dr_kavita, dr_vivek, dr_anita, dr_rohit, dr_emergency

### Patients
- Register from homepage

## Run (Windows)
```bat
cd /d E:\aditi\hospital_ai_system
py -3.14 -m venv venv
venv\Scripts\activate
python -m pip install -U pip
pip install -r requirements.txt

set JWT_SECRET_KEY=SOME_RANDOM_SECRET_123456

REM optional Gemini:
set GEMINI_API_KEY=YOUR_REAL_KEY
set GEMINI_MODEL=models/gemini-2.5-flash

del hospital_ai_system.db

python -m uvicorn hospital_ai_system.main:app --host 127.0.0.1 --port 8000 --reload
```

Open:
- http://127.0.0.1:8000/

Important:
- Use ONLY 127.0.0.1 (don’t mix localhost), cookies are hostname-specific.