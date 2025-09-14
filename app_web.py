from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import asyncio
import logging
import time
import os
import secrets
from functools import wraps

from google_classroom_auth import GoogleClassroomAuth, GoogleClassroomAPI
from classroom_agent_integrator import get_integrator
from utils.text_formatter import format_response_for_web

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = secrets.token_hex(16)  # For session management

# Initialize integrator, classroom auth, and API
integrator = get_integrator(use_classroom_agent=True)
classroom_auth = GoogleClassroomAuth()
classroom_api = GoogleClassroomAPI()

# Check if user is authenticated
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/index')
def index():
    user = session.get('user')
    if not user:
        # User not logged in, show landing page
        return redirect(url_for('login'))
    
    # User is logged in, show chat interface
    return render_template('index.html', user=user)

@app.route('/login')
def login():
    # Show login page
    return render_template('login.html')

@app.route('/auth/google')
def auth_google():
    # Instead of redirecting to Google's OAuth flow directly,
    # inform the user to run the CLI tool first
    return render_template('auth_instructions.html')

@app.route('/')
def home():
    # Check if token file exists, if so, load credentials
    if os.path.exists('classroom_token.json'):
        try:
            # Load credentials from token file
            success = classroom_auth.load_credentials()
            if success:
                # Set credentials for API client first
                classroom_api.set_credentials(classroom_auth.credentials)
                
                # Try to get user info, but proceed even if it fails
                try:
                    user_info = classroom_auth.get_user_info()
                    if user_info:
                        # Store user info in session
                        session['user'] = user_info
                except Exception as e:
                    logging.warning(f"Could not get user info, but proceeding: {e}")
                    # Use a default user if we can't get real user info
                    session['user'] = {
                        'name': 'Classroom User',
                        'email': 'randivetanishka@gmail.com',
                        'photo_url': ''
                    }
        except Exception as e:
            logging.error(f"Error loading credentials: {e}")
    
    # Check if user is authenticated
    user = session.get('user')
    if user:
        # User is logged in, show chat interface
        return render_template('index.html', user=user)
    else:
        # User not logged in, show landing page
        return render_template('login.html')

@app.route('/logout')
def logout():
    # Clear session and redirect to login page
    session.clear()
    return redirect(url_for('login'))

@app.route('/chat', methods=['POST'])
@login_required
def chat():
    data = request.get_json()
    user_message = data.get('message', '')
    # Get the show_reasoning parameter from the request, default to False
    show_reasoning = data.get('show_reasoning', False)
    
    if not user_message:
        return jsonify({'reply': "Please enter a message."})
    
    logging.info(f"Received message: {user_message[:50]}... (show_reasoning={show_reasoning})")
    
    # Add a small delay to simulate thinking (more realistic UI)
    # Remove in production for faster responses
    time.sleep(1)
    
    # Run integrator.ask_question asynchronously
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        start_time = time.time()
        answer = loop.run_until_complete(integrator.ask_question(user_message, show_reasoning=show_reasoning))
        elapsed_time = time.time() - start_time
        logging.info(f"Response generated in {elapsed_time:.2f} seconds")
        
        # Check if the response contains a reasoning chain (marked by separator)
        has_reasoning = "=" * 50 in answer
        
        # If the response has reasoning, we'll provide both the answer and reasoning separately
        if has_reasoning and show_reasoning:
            parts = answer.split("=" * 50, 1)
            main_answer = parts[0].strip()
            reasoning = "=" * 50 + parts[1] if len(parts) > 1 else ""
            
            # Format the response for better presentation
            response_data = format_response_for_web({
                'reply': main_answer,
                'has_reasoning': True,
                'reasoning': reasoning
            })
            return jsonify(response_data)
        
    except Exception as e:
        logging.error(f"Error processing message: {e}")
        answer = f"I'm sorry, I encountered an error while processing your question. Please try again."
    finally:
        loop.close()
    
    # Default response format (no reasoning or reasoning not requested)
    response_data = format_response_for_web({'reply': answer, 'has_reasoning': False})
    return jsonify(response_data)

@app.route('/api/topics', methods=['GET'])
@login_required
def get_topics():
    # You can implement this to retrieve available topics
    return jsonify({
        'topics': [
            'Machine Learning',
            'Python Programming',
            'Quantum Computing',
            'Data Science',
            'Artificial Intelligence'
        ]
    })

@app.route('/api/courses', methods=['GET'])
@login_required
def get_courses():
    try:
        # Try using the integrator to get courses first
        integrator_courses = integrator.list_courses()
        if integrator_courses:
            return jsonify({'courses': integrator_courses})
            
        # Fall back to the API client if integrator fails
        courses = classroom_api.list_courses()
        return jsonify({'courses': courses})
    except Exception as e:
        logging.error(f"Error fetching courses: {e}")
        return jsonify({'error': 'Failed to fetch courses'}), 500

@app.route('/api/courses/<course_id>/students', methods=['GET'])
@login_required
def get_course_students(course_id):
    try:
        # Get students in a specific course
        students = classroom_api.get_course_students(course_id)
        return jsonify({'students': students})
    except Exception as e:
        logging.error(f"Error fetching students: {e}")
        return jsonify({'error': 'Failed to fetch students'}), 500

@app.route('/api/classroom/initialize', methods=['POST'])
@login_required
def initialize_classroom_agent():
    """Initialize the classroom agent with Google Classroom data."""
    try:
        # Run initialization asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            success = loop.run_until_complete(integrator.initialize_classroom_agent())
        finally:
            loop.close()
        
        if success:
            return jsonify({'success': True, 'message': 'Classroom agent initialized successfully'})
        else:
            return jsonify({'success': False, 'message': 'Failed to initialize classroom agent'}), 500
    except Exception as e:
        logging.error(f"Error initializing classroom agent: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/study-plan', methods=['POST'])
@login_required
def create_study_plan():
    """Generate a study plan based on classroom content."""
    try:
        data = request.get_json()
        course_name = data.get('course')  # Optional course name
        timeframe = data.get('timeframe', 'week')  # Default to weekly plan
        show_reasoning = data.get('show_reasoning', False)  # Get the show_reasoning parameter
        
        # Validate timeframe
        if timeframe not in ['week', 'month', 'all']:
            return jsonify({'error': 'Invalid timeframe. Must be "week", "month", or "all"'}), 400
        
        # Run study plan generation asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(integrator.create_study_plan(course_name, timeframe, show_reasoning))
        finally:
            loop.close()
        
        # Handle different return formats based on whether reasoning was requested
        if isinstance(result, dict) and show_reasoning:
            # Check if the response contains a reasoning chain (marked by separator)
            study_plan = result.get('answer', result.get('study_plan', ''))
            has_reasoning = "=" * 50 in study_plan
            
            if has_reasoning:
                parts = study_plan.split("=" * 50, 1)
                main_plan = parts[0].strip()
                reasoning = "=" * 50 + parts[1] if len(parts) > 1 else ""
                
                # Format the response for better presentation
                response_data = format_response_for_web({
                    'study_plan': main_plan,
                    'has_reasoning': True,
                    'reasoning': reasoning
                })
                return jsonify(response_data)
        
        # Default response format (no reasoning or reasoning not requested)
        study_plan = result if isinstance(result, str) else result.get('answer', result.get('study_plan', ''))
        response_data = format_response_for_web({'study_plan': study_plan, 'has_reasoning': False})
        return jsonify(response_data)
    except Exception as e:
        logging.error(f"Error creating study plan: {e}")
        return jsonify({'error': f'Failed to create study plan: {str(e)}'}), 500

@app.route('/api/bulletin-board', methods=['GET'])
@login_required
def get_bulletin_board():
    """Get important deadlines, quizzes, and announcements for the bulletin board."""
    try:
        # Run bulletin board data retrieval asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            bulletin_data = loop.run_until_complete(integrator.get_bulletin_board_data())
        finally:
            loop.close()
        
        return jsonify({'bulletin_items': bulletin_data})
    except Exception as e:
        logging.error(f"Error getting bulletin board data: {e}")
        return jsonify({'error': f'Failed to get bulletin board data: {str(e)}', 'bulletin_items': []}), 500

@app.route('/api/search', methods=['POST'])
@login_required
def search_classroom_content():
    """Search for content in classroom knowledge base."""
    try:
        data = request.get_json()
        query = data.get('query')
        course = data.get('course')  # Optional course filter
        
        if not query:
            return jsonify({'error': 'Query parameter is required'}), 400
            
        # Run search asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            results = loop.run_until_complete(integrator.search_course_content(query, course))
        finally:
            loop.close()
            
        return jsonify({'results': results})
    except Exception as e:
        logging.error(f"Error searching classroom content: {e}")
        return jsonify({'error': f'Search failed: {str(e)}'}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def server_error(error):
    return jsonify({'error': 'Server error'}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5005)
