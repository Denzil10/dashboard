import os
import json
from flask import Flask, request, jsonify, session, redirect, url_for, render_template
import firebase_admin
from firebase_admin import credentials, db
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from flask_cors import CORS

# Load Firebase Admin SDK credentials from environment variable
firebase_cred_json = os.getenv('FIREBASE_CRED')
if firebase_cred_json:
    firebase_cred_dict = json.loads(firebase_cred_json)
    firebase_cred = credentials.Certificate(firebase_cred_dict)
    firebase_admin.initialize_app(firebase_cred, {
        'databaseURL': os.getenv('FIREBASE_DATABASE_URL', 'https://upi-buddy-default-rtdb.firebaseio.com/')
    })
else:
    raise ValueError("FIREBASE_CRED environment variable is not set")

# Load OAuth client configuration from environment variable
oauth_cred_json = os.getenv('OAUTH_CRED')
if oauth_cred_json:
    oauth_cred = json.loads(oauth_cred_json)
else:
    raise ValueError("OAUTH_CRED environment variable is not set")

# Initialize Flask application
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'habit_secret_key')
CORS(app)

# Save OAuth credentials to Firebase
def save_credentials(credentials):
    ref = db.reference('oauth_credentials')
    ref.set({
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret
    })

def load_credentials():
    ref = db.reference('oauth_credentials')
    stored_credentials = ref.get()
    if stored_credentials:
        credentials = Credentials(
            stored_credentials['token'],
            refresh_token=stored_credentials.get('refresh_token'),
            token_uri=stored_credentials['token_uri'],
            client_id=stored_credentials['client_id'],
            client_secret=stored_credentials['client_secret']
        )
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
            save_credentials(credentials)
        return credentials
    else:
        raise RuntimeError("Credentials not found in Firebase Realtime Database")

# OAuth authorization route
@app.route('/authorize')
def authorize():
    flow = Flow.from_client_config(oauth_cred, scopes=SCOPES)
    flow.redirect_uri = url_for('oauth2callback', _external=True)

    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )

    session['state'] = state
    return redirect(authorization_url)

# OAuth callback route
@app.route('/oauth2callback')
def oauth2callback():
    state = session.get('state')
    if not state or state != request.args.get('state'):
        return jsonify({"error": "State mismatch error"}), 400

    flow = Flow.from_client_config(oauth_cred, scopes=SCOPES, state=state)
    flow.redirect_uri = url_for('oauth2callback', _external=True)

    flow.fetch_token(authorization_response=request.url)
    credentials = flow.credentials
    save_credentials(credentials)

    return jsonify({"message": f"Authorization successful, credentials saved"}), 200

@app.route('/fetch_info/<param>', methods=['GET'])
def fetch_info(param):
    today = datetime.now().strftime('%Y-%m-%d')
    
    if param == "stocks":
        nifty_index = 17345.67
        return jsonify({"nifty_index": nifty_index})
    
    if param == "news":
        return jsonify({"news":"news"})

    elif param == "leetcode":
        ref = db.reference(f'progress/{today}/leetcode')
        leetcode_solved = ref.get() or 0
        return jsonify({"status": 1, "leetcode_solved_today": leetcode_solved})
 
    elif param == "fitness":
        steps_today = 7589  
        return jsonify({"steps_today": steps_today})

    elif param == "budget":
        ref = db.reference(f'budget')
        budget_status = ref.get() or False
        return jsonify({"budget_status": budget_status})

    else:
        return jsonify({"error": "Invalid parameter"}), 400

@app.route('/fetch-habit-data', methods=['GET'])
def fetch_habit_data(): 
    today = datetime.now().strftime('%Y-%m-%d')
    ref = db.reference(f'habit_server')
    data = ref.get() or {}
    return jsonify(data)

# Log progress and update streak
@app.route('/log-habit/<habit>', methods=['POST'])
def log_habit(habit):
    today = datetime.now().strftime('%Y-%m-%d')

    # Log progress in Firebase
    progress_ref = db.reference(f'habit_server/progress/{today}/{habit}')
    progress_ref.set(True)

    # Update streak
    streak_ref = db.reference(f'habit_server/habit/{habit}')
    streak_data = streak_ref.get() or {}
    last_collected = streak_data.get('lastCollected', "")
    current_streak = streak_data.get('streak', 0)

    if last_collected == today:
        return jsonify({"message": "Already updated for today", "streak": current_streak}), 200
    elif last_collected and (datetime.strptime(today, '%Y-%m-%d') - datetime.strptime(last_collected, '%Y-%m-%d')).days == 1:
        current_streak += 1
    else:
        current_streak = 1

    streak_ref.set({
        "streak": current_streak,
        "lastCollected": today
    })

    return jsonify({"message": "Habit logged", "status": 1}) , 200

@app.route('/check-habit/<habit>', methods=['POST'])
def check_habit(habit):
    return jsonify({"completed": True}), 200

@app.route('/update-habit/<habit>', methods=['POST'])
def update_habit(habit):
    habit_ref = db.reference(f'habit_server/habit/{habit}')
    habit_data = habit_ref.get()
    
    value_list = habit_data.get('values', [])
    if not value_list:
        return None
    current_index = habit_data.get('currentIndex', 0)
 
    current_index = (current_index + 1) % len(value_list)
    # next_value = value_list[current_index]

    habit_ref.update({
        'currentIndex': current_index
    })

    return jsonify({"message": "Updated"}), 200

@app.route('/complete-habit/<habit>', methods=['GET'])
def complete_habit(habit):
    today = datetime.now().strftime('%Y-%m-%d')

    check_list = ["leetcode"]
    # Step 1: Check habit
    if habit in check_list:
        check_habit_response, status_code = check_habit(habit)
        check_habit_response = check_habit_response.get_json()

        if not check_habit_response.get('completed', False):
            return jsonify({"message": "Habit pending"}), 200

    # Step 2: Log the habit
    log_habit_response, status_code = log_habit(habit)
    log_habit_response = log_habit_response.get_json()

    print("log", log_habit_response)
    if not log_habit_response.get('status', False):
        return jsonify({"error": "Failed to log habit"}), 500

    # Step 3: Update the habit's streak and rotate value
    update_habit_response = update_habit(habit).get_json()
    if not update_habit_response:
        return jsonify({"message": "No values"}), 200

    return jsonify({
        "message": "Habit completed",
    }), 200

@app.route('/photo', methods=['GET'])
def get_photos():
    ref = db.reference(f'habit_server/photo')
    photo = ref.get()
    return jsonify(photo)

# Main index route
@app.route('/')
def index():
    return render_template('index.html')
if __name__ == '__main__':
    app.run(port=5000)
