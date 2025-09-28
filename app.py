from flask import Flask, request, jsonify, session, redirect, url_for, render_template
from pymongo import MongoClient
from bson import ObjectId
import datetime
import json
from passlib.hash import pbkdf2_sha256

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this to a secure secret key in production

# MongoDB setup
client = MongoClient('mongodb://localhost:27017/')
db = client['user_login_system']
complaints_collection = db['complaints']
users_collection = db['users']

# Home route
@app.route('/')
def home():
    if 'user' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

# Dashboard route
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    try:
        complaints = list(complaints_collection.find().sort('created_at', -1))
        
        if not session['user'].get('is_admin', False):
            user_email = session['user']['email']
            complaints = [c for c in complaints if c.get('user_email') == user_email]
        
        for complaint in complaints:
            complaint['_id'] = str(complaint['_id'])
            if 'resolved' not in complaint:
                complaint['resolved'] = False
            if 'created_at' not in complaint:
                complaint['created_at'] = datetime.datetime.utcnow()
            if 'updated_at' not in complaint:
                complaint['updated_at'] = complaint['created_at']
        
        return render_template('dashboard.html', complaints=complaints, user=session['user'])
        
    except Exception as e:
        print(f"Error fetching complaints: {str(e)}")
        return render_template('dashboard.html', complaints=[], user=session['user'])

# Submit complaint route (traditional form POST)
@app.route('/submit_complaint', methods=['POST'])
def submit_complaint():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    if session['user'].get('is_admin', False):
        return redirect(url_for('dashboard'))
    
    complaint_text = request.form.get('complaint')
    if not complaint_text or not complaint_text.strip():
        return redirect(url_for('dashboard'))
    
    if len(complaint_text.strip()) < 10:
        return redirect(url_for('dashboard'))

    print(f"User submitting complaint: {session['user']['email']}")
    print(f"Complaint text: {complaint_text.strip()}")
    
    try:
        complaint_data = {
            'user_email': session['user']['email'],
            'user_name': session['user'].get('name', session['user']['email']),
            'complaint': complaint_text.strip(),
            'resolved': False,
            'created_at': datetime.datetime.utcnow(),
            'updated_at': datetime.datetime.utcnow(),
            'resolved_by': None,
            'status_updated_at': None
        }
        
        result = complaints_collection.insert_one(complaint_data)
        print(f"Complaint submitted successfully with ID: {result.inserted_id}")
        
        return redirect(url_for('dashboard'))
        
    except Exception as e:
        print(f"Error submitting complaint: {str(e)}")
        return redirect(url_for('dashboard'))

# Submit complaint via AJAX
@app.route('/submit_complaint_ajax', methods=['POST'])
def submit_complaint_ajax():
    if 'user' not in session:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401

    if session['user'].get('is_admin', False):
        return jsonify({'success': False, 'message': 'Admins cannot submit complaints'}), 403

    data = request.get_json()
    complaint_text = data.get('complaint', '').strip()

    if not complaint_text:
        return jsonify({'success': False, 'message': 'Complaint cannot be empty'}), 400
    if len(complaint_text) < 10:
        return jsonify({'success': False, 'message': 'Complaint must be at least 10 characters long'}), 400

    try:
        complaint_data = {
            'user_email': session['user']['email'],
            'user_name': session['user'].get('name', session['user']['email']),
            'complaint': complaint_text,
            'resolved': False,
            'created_at': datetime.datetime.utcnow(),
            'updated_at': datetime.datetime.utcnow(),
            'resolved_by': None,
            'status_updated_at': None
        }

        result = complaints_collection.insert_one(complaint_data)
        complaint_data['_id'] = str(result.inserted_id)

        return jsonify({'success': True, 'complaint': complaint_data})

    except Exception as e:
        print(f"Error submitting complaint via AJAX: {e}")
        return jsonify({'success': False, 'message': 'Server error'}), 500

# Update complaint
@app.route('/update_complaint', methods=['POST'])
def update_complaint():
    try:
        if 'user' not in session:
            return jsonify({'success': False, 'message': 'Not authenticated'}), 401
        
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
            
        complaint_id = data.get('complaint_id')
        new_complaint = data.get('complaint')
        
        if not complaint_id or not new_complaint:
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
        
        new_complaint = new_complaint.strip()
        if len(new_complaint) < 10:
            return jsonify({'success': False, 'message': 'Complaint must be at least 10 characters long'}), 400
        
        complaint = complaints_collection.find_one({'_id': ObjectId(complaint_id)})
        if not complaint:
            return jsonify({'success': False, 'message': 'Complaint not found'}), 404
        
        user_email = session['user']['email']
        is_admin = session['user'].get('is_admin', False)
        if not is_admin and complaint.get('user_email') != user_email:
            return jsonify({'success': False, 'message': 'Permission denied'}), 403
        
        result = complaints_collection.update_one(
            {'_id': ObjectId(complaint_id)},
            {'$set': {'complaint': new_complaint, 'updated_at': datetime.datetime.utcnow()}}
        )
        
        if result.modified_count > 0:
            return jsonify({'success': True, 'message': 'Complaint updated successfully'})
        else:
            return jsonify({'success': False, 'message': 'No changes made'}), 400
            
    except Exception as e:
        print(f"Error updating complaint: {str(e)}")
        return jsonify({'success': False, 'message': 'Server error'}), 500

# Delete complaint
@app.route('/delete_complaint', methods=['POST'])
def delete_complaint():
    try:
        if 'user' not in session:
            return jsonify({'success': False, 'message': 'Not authenticated'}), 401
        
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
            
        complaint_id = data.get('complaint_id')
        if not complaint_id:
            return jsonify({'success': False, 'message': 'Missing complaint ID'}), 400
        
        complaint = complaints_collection.find_one({'_id': ObjectId(complaint_id)})
        if not complaint:
            return jsonify({'success': False, 'message': 'Complaint not found'}), 404
        
        user_email = session['user']['email']
        is_admin = session['user'].get('is_admin', False)
        if not is_admin and complaint.get('user_email') != user_email:
            return jsonify({'success': False, 'message': 'Permission denied'}), 403
        
        result = complaints_collection.delete_one({'_id': ObjectId(complaint_id)})
        if result.deleted_count > 0:
            return jsonify({'success': True, 'message': 'Complaint deleted successfully'})
        else:
            return jsonify({'success': False, 'message': 'Failed to delete complaint'}), 400
            
    except Exception as e:
        print(f"Error deleting complaint: {str(e)}")
        return jsonify({'success': False, 'message': 'Server error'}), 500

# Toggle complaint status (admin only)
@app.route('/toggle_complaint_status', methods=['POST'])
def toggle_complaint_status():
    try:
        if 'user' not in session:
            return jsonify({'success': False, 'message': 'Not authenticated'}), 401
        if not session['user'].get('is_admin', False):
            return jsonify({'success': False, 'message': 'Admin access required'}), 403
        
        data = request.get_json()
        complaint_id = data.get('complaint_id')
        new_status = data.get('status')
        if not complaint_id or new_status not in ['pending', 'resolved']:
            return jsonify({'success': False, 'message': 'Invalid request data'}), 400
        
        complaint = complaints_collection.find_one({'_id': ObjectId(complaint_id)})
        if not complaint:
            return jsonify({'success': False, 'message': 'Complaint not found'}), 404
        
        resolved_status = new_status == 'resolved'
        update_data = {
            'resolved': resolved_status,
            'status_updated_at': datetime.datetime.utcnow(),
            'resolved_by': session['user']['email'] if resolved_status else None
        }
        
        result = complaints_collection.update_one(
            {'_id': ObjectId(complaint_id)},
            {'$set': update_data}
        )
        
        if result.modified_count > 0:
            action = 'resolved' if resolved_status else 'reopened'
            return jsonify({'success': True, 'message': f'Complaint {action} successfully'})
        else:
            return jsonify({'success': False, 'message': 'No changes made'}), 400
            
    except Exception as e:
        print(f"Error updating complaint status: {str(e)}")
        return jsonify({'success': False, 'message': 'Server error'}), 500

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user' in session:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        if not email or not password:
            return render_template('login.html', error='Please provide both email and password')
        
        user = users_collection.find_one({'email': email})
        if user and pbkdf2_sha256.verify(password, user['password']):
            session['user'] = {
                'email': user['email'],
                'name': user.get('name', email.split('@')[0]),
                'is_admin': user.get('is_admin', False)
            }
            print(f"Login successful - User: {email}, Is Admin: {user.get('is_admin', False)}")
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error='Invalid email or password')
    
    return render_template('login.html')

# Signup route
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if 'user' in session:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        name = request.form.get('name', '')
        if not email or not password:
            return render_template('signup.html', error='Please provide both email and password')
        
        if users_collection.find_one({'email': email}):
            return render_template('signup.html', error='Email already registered')
        
        hashed_password = pbkdf2_sha256.hash(password)
        new_user = {
            'email': email,
            'password': hashed_password,
            'name': name if name else email.split('@')[0],
            'is_admin': False,
            'created_at': datetime.datetime.utcnow()
        }
        users_collection.insert_one(new_user)
        session['user'] = {'email': email, 'name': name if name else email.split('@')[0], 'is_admin': False}
        return redirect(url_for('dashboard'))
    
    return render_template('signup.html')

# Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    if 'user' in session:
        return render_template('404.html'), 404
    return redirect(url_for('login'))

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
