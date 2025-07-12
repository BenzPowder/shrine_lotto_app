# app.py - Stripped-down version for debugging 404 issue
from flask import Flask, render_template, session, redirect, url_for, jsonify
import os
# Removed: pymongo, requests, datetime, random, werkzeug.security,
# bs4, time, re, apscheduler, waitress

app = Flask(__name__)
app.secret_key = 'super_secret_key_for_dev' # Still needed for session access, even if not fully utilized

# --- Routes ---
@app.route('/')
def index():
    """
    Renders the main view. Shows public data or logged-in view based on session.
    Using dummy data for now, as DB/scraping is temporarily removed.
    """
    print("Attempting to render index.html in stripped-down app.") # Debug print

    latest_results = [
        {"draw_date": "01/06/2568", "two_digit_end": "XX"},
        {"draw_date": "16/05/2568", "two_digit_end": "XX"},
        {"draw_date": "02/05/2568", "two_digit_end": "XX"},
        {"draw_date": "16/04/2568", "two_digit_end": "XX"},
        {"draw_date": "01/04/2568", "two_digit_end": "XX"},
    ]
    ai_prediction_numbers = ["XX", "YY", "ZZ"]

    # Simulate login state using session (even though no real login logic)
    logged_in_status = session.get('logged_in', False)
    username = session.get('username', 'Guest')
    credits = session.get('credits', 0)

    return render_template('index.html',
                           latest_lotto_results=latest_results,
                           ai_prediction=ai_prediction_numbers,
                           logged_in=logged_in_status,
                           username=username,
                           credits=credits)

# Minimal login/logout routes to test session. No DB interaction.
@app.route('/login')
def login_page():
    return render_template('auth.html')

@app.route('/auth/login', methods=['POST'])
def auth_login():
    # Dummy login for stripped-down app
    session['logged_in'] = True
    session['username'] = request.form.get('username', 'debug_user')
    session['credits'] = 100
    return jsonify({"success": True, "redirect_url": url_for('index')})

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('username', None)
    session.pop('credits', None)
    return redirect(url_for('index'))

# Placeholder routes for topup/register pages, just to avoid 404
@app.route('/topup')
def topup_page_placeholder():
    return "Topup page (placeholder)"

@app.route('/register')
def register_page_placeholder():
    return render_template('auth.html')


if __name__ == '__main__':
    # Ensure templates folder exists
    os.makedirs('templates', exist_ok=True)
    # Run the Flask app with explicit host and port for stability
    # NO debug=True, NO use_reloader=True to prevent common Windows issues
    # Using built-in Flask server directly, not Waitress for this minimal test
    app.run(host='127.0.0.1', port=5000)
