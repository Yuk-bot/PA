import firebase_admin, os
import logging
from firebase_admin import credentials, auth, firestore
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger("db.firebase")

current_file = os.path.abspath(__file__)
db_dir = os.path.dirname(current_file)
app_dir = os.path.dirname(db_dir)
backend_dir = os.path.dirname(app_dir)

firebase_key = os.path.join(backend_dir, "firebase_key.json")

try:
    firebase_admin.get_app()
except ValueError:
    try:
        project_id = os.environ.get("FIREBASE_PROJECT_ID") or os.environ.get("GOOGLE_CLOUD_PROJECT")
        if os.path.exists(firebase_key):
            cred = credentials.Certificate(firebase_key)
            logger.info("Initializing Firebase with certificate file.")
            firebase_admin.initialize_app(cred)
        else:
            cred = credentials.ApplicationDefault()
            logger.info("Initializing Firebase with Application Default Credentials.")
            if project_id:
                firebase_admin.initialize_app(cred, {"projectId": project_id})
            else:
                firebase_admin.initialize_app(cred)
    except Exception as e:
        logger.error(f"Firebase initialization failed: {e}")
        raise

firebase_auth = auth
firebase_db = firestore.client()