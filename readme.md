# Retiree Connect 

Retiree Connect is a mentorship platform where retired professionals (mentors) can connect with seekers (learners) to share their experience, guidance, and knowledge.

---

##  Features
- Retiree Registration & Login
- Seeker Registration & Login
- Role-based login system
- Secure password storage (hashed)
- Admin management of users
- Session-based authentication

---

##  Tech Stack
- **Backend**: Python, Django
- **Frontend**: HTML, CSS, Bootstrap
- **Database**: Postgresql
- **Auth**: Django sessions & hashed passwords

---

<!-- virtual environment: -->
python -m venv venv
venv\Scripts\activate

<!-- Install dependencies: -->
pip install -r requirements.txt

<!-- Run migrations: -->
python manage.py migrate

<!-- Start the development server: -->
python manage.py runserver

 <!-- Install daphne if not already -->
pip install daphne

<!-- # Install required packages -->
pip install channels channels-redis

<!-- download Redis from https://github.com/microsoftarchive/redis/releases -->