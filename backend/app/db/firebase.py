import firebase_admin, os
from firebase_admin import credentials, auth, firestore
from dotenv import load_dotenv
load_dotenv()

current_file = os.path.abspath(__file__)  # backend/app/db/firebase.py
db_dir = os.path.dirname(current_file)    # backend/app/db/
app_dir = os.path.dirname(db_dir)         # backend/app/
backend_dir = os.path.dirname(app_dir)    # backend/

firebase_key = os.path.join(backend_dir, "firebase_key.json")



if not os.path.exists(firebase_key):
    raise ValueError(f"Firebase key file not found at: {firebase_key}")

try:
    #get already exisiting app
    firebase_admin.get_app()
        
except ValueError:
    try:
        cred = credentials.Certificate(firebase_key)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        print(f"Firebase initialization failed: {e}")
        raise

firebase_auth=auth
firebase_db=firestore.client()