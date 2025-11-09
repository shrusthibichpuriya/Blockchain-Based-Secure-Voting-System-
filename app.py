from flask import Flask, render_template, request, redirect, url_for, flash, session
import json
import re
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SESSION_SECRET', 'voting-system-secret-key-2024')

VOTERS_FILE = 'voters.json'
VOTES_FILE = 'votes.json'
PHASES_FILE = 'phases.json'

ADMIN_ID = 'admin'
ADMIN_PASSWORD = 'admin123'

CANDIDATES = [
    {'id': 0, 'name': 'Candidate A'},
    {'id': 1, 'name': 'Candidate B'},
    {'id': 2, 'name': 'Candidate C'},
    {'id': 3, 'name': 'Candidate D'}
]

def load_json(filename):
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return [] if filename != PHASES_FILE else {'registration': False, 'voting': False, 'result': False}

def save_json(filename, data):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)

def get_phases():
    return load_json(PHASES_FILE)

def validate_aadhaar(aadhaar):
    if not aadhaar:
        return False
    if not re.match(r'^\d{12}$', aadhaar):
        return False
    return True

@app.route('/')
def index():
    phases = get_phases()
    return render_template('index.html', phases=phases)

@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    phases = get_phases()
    
    if request.method == 'POST':
        admin_id = request.form.get('admin_id', '').strip()
        admin_password = request.form.get('admin_password', '').strip()
        
        if admin_id == ADMIN_ID and admin_password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            flash('Login successful! Welcome Admin.', 'success')
            return redirect(url_for('admin'))
        else:
            flash('Invalid admin credentials. Please try again.', 'danger')
            return render_template('admin_login.html', phases=phases)
    
    return render_template('admin_login.html', phases=phases)

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if not session.get('admin_logged_in'):
        flash('Please login as admin to access the control panel.', 'warning')
        return redirect(url_for('admin_login'))
    
    phases = get_phases()
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'toggle_registration':
            phases = {'registration': True, 'voting': False, 'result': False}
        elif action == 'toggle_voting':
            phases = {'registration': False, 'voting': True, 'result': False}
        elif action == 'toggle_result':
            phases = {'registration': False, 'voting': False, 'result': True}
        
        save_json(PHASES_FILE, phases)
        flash(f'Phase updated successfully! Only one phase is active now.', 'success')
        return redirect(url_for('admin'))
    
    return render_template('admin.html', phases=phases)

@app.route('/register', methods=['GET', 'POST'])
def register():
    phases = get_phases()
    
    if not phases['registration']:
        flash('⚠️ This phase is currently turned off by the Admin.', 'warning')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        aadhaar = request.form.get('aadhaar', '').strip()
        
        if not name:
            flash('Please enter your full name.', 'danger')
            return render_template('register.html', phases=phases, name=name, aadhaar=aadhaar)
        
        if not validate_aadhaar(aadhaar):
            flash('Invalid Aadhaar number. Must be 12 digits.', 'danger')
            return render_template('register.html', phases=phases, name=name, aadhaar=aadhaar)
        
        voters = load_json(VOTERS_FILE)
        
        if any(v['aadhaar'] == aadhaar for v in voters):
            flash('This Aadhaar number is already registered.', 'danger')
            return render_template('register.html', phases=phases, name=name, aadhaar=aadhaar)
        
        voters.append({'name': name, 'aadhaar': aadhaar})
        save_json(VOTERS_FILE, voters)
        
        flash('Registration successful! You can now login to vote.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html', phases=phases)

@app.route('/login', methods=['GET', 'POST'])
def login():
    phases = get_phases()
    
    if not phases['voting']:
        flash('⚠️ This phase is currently turned off by the Admin.', 'warning')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        aadhaar = request.form.get('aadhaar', '').strip()
        
        voters = load_json(VOTERS_FILE)
        voter = next((v for v in voters if v['name'] == name and v['aadhaar'] == aadhaar), None)
        
        if not voter:
            flash('Invalid credentials. Please check your name and Aadhaar number.', 'danger')
            return render_template('login.html', phases=phases)
        
        session['voter_name'] = name
        session['voter_aadhaar'] = aadhaar
        
        return redirect(url_for('vote'))
    
    return render_template('login.html', phases=phases)

@app.route('/vote', methods=['GET', 'POST'])
def vote():
    phases = get_phases()
    
    if not phases['voting']:
        flash('⚠️ This phase is currently turned off by the Admin.', 'warning')
        return redirect(url_for('index'))
    
    if 'voter_aadhaar' not in session:
        flash('Please login first to vote.', 'warning')
        return redirect(url_for('login'))
    
    votes = load_json(VOTES_FILE)
    voter_aadhaar = session['voter_aadhaar']
    
    if any(v['aadhaar'] == voter_aadhaar for v in votes):
        flash('You have already voted. Thank you!', 'info')
        session.pop('voter_aadhaar', None)
        session.pop('voter_name', None)
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        candidate_id = request.form.get('candidate_id')
        
        if candidate_id is None:
            flash('Please select a candidate.', 'danger')
            return render_template('vote.html', phases=phases, candidates=CANDIDATES, voter_name=session.get('voter_name'))
        
        try:
            candidate_id = int(candidate_id)
        except (ValueError, TypeError):
            flash('Invalid candidate selection.', 'danger')
            return render_template('vote.html', phases=phases, candidates=CANDIDATES, voter_name=session.get('voter_name'))
        
        if candidate_id < 0 or candidate_id >= len(CANDIDATES):
            flash('Invalid candidate selection.', 'danger')
            return render_template('vote.html', phases=phases, candidates=CANDIDATES, voter_name=session.get('voter_name'))
        
        votes.append({
            'aadhaar': voter_aadhaar,
            'candidate_id': candidate_id,
            'candidate_name': CANDIDATES[candidate_id]['name']
        })
        save_json(VOTES_FILE, votes)
        
        session.pop('voter_aadhaar', None)
        session.pop('voter_name', None)
        
        flash('Your vote has been recorded successfully!', 'success')
        return redirect(url_for('index'))
    
    return render_template('vote.html', phases=phases, candidates=CANDIDATES, voter_name=session.get('voter_name'))

@app.route('/result')
def result():
    phases = get_phases()
    
    if not phases['result']:
        flash('⚠️ This phase is currently turned off by the Admin.', 'warning')
        return redirect(url_for('index'))
    
    votes = load_json(VOTES_FILE)
    
    vote_counts = {c['id']: {'name': c['name'], 'count': 0} for c in CANDIDATES}
    
    for vote in votes:
        candidate_id = vote['candidate_id']
        if candidate_id in vote_counts:
            vote_counts[candidate_id]['count'] += 1
    
    results = list(vote_counts.values())
    results.sort(key=lambda x: x['count'], reverse=True)
    
    winner = results[0] if results and results[0]['count'] > 0 else None
    
    return render_template('result.html', phases=phases, results=results, winner=winner, total_votes=len(votes))

@app.route('/logout')
def logout():
    session.pop('voter_aadhaar', None)
    session.pop('voter_name', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/admin-logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    flash('Admin logged out successfully.', 'info')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
