"""
Google Classroom Authentication and API Module

Handles OAuth 2.0 flow for Google Classroom authentication and API interactions.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
import google_classroom_config as config

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow, InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger("google_classroom")

class GoogleClassroomAuth:
    """Handles Google Classroom OAuth 2.0 authentication flow."""
    
    def __init__(self):
        self.flow = None
        self.credentials = None
        self.token_path = "classroom_token.json"
    
    def get_authorization_url(self) -> str:
        """
        Creates the OAuth 2.0 flow and returns the authorization URL.
        
        Returns:
            str: URL for user to authorize the application
        """
        # Load credentials from the credentials.json file
        try:
            client_secret_file = "credentials.json"
            # Create flow using the client secret file with no redirect_uri
            # Let InstalledAppFlow handle the local server for us
            self.flow = InstalledAppFlow.from_client_secrets_file(
                client_secret_file,
                scopes=config.SCOPES
            )
            
            # For testing - mark the user as a test user
            # This helps with unverified apps
            self.flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                prompt='consent',
                # This is important for unverified apps
                login_hint='2023aib1018@iitrpr.ac.in'  # Use the email from the error page
            )
            
        except FileNotFoundError:
            # Fallback to config-based flow if file not found
            logger.warning("credentials.json file not found, falling back to config values")
            self.flow = InstalledAppFlow.from_client_config(
                {
                    "installed": {
                        "client_id": config.CLIENT_ID,
                        "client_secret": config.CLIENT_SECRET,
                        "auth_uri": config.AUTH_URI,
                        "token_uri": config.TOKEN_URI,
                        "redirect_uris": ["http://localhost"]
                    }
                },
                scopes=config.SCOPES
            )
        
        # Generate the authorization URL for redirection
        # We'll use a separate method for the actual auth flow
        auth_url, _ = self.flow.authorization_url(
            access_type='offline',
            prompt='consent',
            include_granted_scopes='true'
        )
        
        logger.info(f"Authorization URL generated: {auth_url[:50]}...")
        return auth_url
    
    def process_oauth_callback(self, auth_code: str) -> Dict[str, Any]:
        """
        Processes the OAuth 2.0 callback and exchanges the authorization code for tokens.
        
        Args:
            auth_code: Authorization code returned by Google
            
        Returns:
            Dict with user credentials information
        """
        if not self.flow:
            raise ValueError("OAuth flow not initialized. Call get_authorization_url first.")
        
        # Exchange authorization code for access and refresh tokens
        self.flow.fetch_token(code=auth_code)
        
        # Get credentials from flow
        self.credentials = self.flow.credentials
        
        # Save credentials to file
        self._save_credentials()
        
        # Get user info
        user_info = self.get_user_info()
        
        logger.info(f"Successfully authenticated user: {user_info.get('email', 'Unknown')}")
        return user_info
    
    def _save_credentials(self) -> None:
        """Saves the user's credentials to a file."""
        if not self.credentials:
            return
            
        token_data = {
            'token': self.credentials.token,
            'refresh_token': self.credentials.refresh_token,
            'token_uri': self.credentials.token_uri,
            'client_id': self.credentials.client_id,
            'client_secret': self.credentials.client_secret,
            'scopes': self.credentials.scopes
        }
        
        with open(self.token_path, 'w') as token_file:
            json.dump(token_data, token_file)
        
        logger.info(f"Credentials saved to {self.token_path}")
    
    def load_credentials(self) -> bool:
        """
        Loads saved credentials if they exist.
        
        Returns:
            bool: True if credentials were loaded successfully, False otherwise
        """
        if not os.path.exists(self.token_path):
            logger.info("No saved credentials found")
            return False
            
        try:
            with open(self.token_path, 'r') as token_file:
                token_data = json.load(token_file)
                
            self.credentials = Credentials(
                token=token_data['token'],
                refresh_token=token_data['refresh_token'],
                token_uri=token_data['token_uri'],
                client_id=token_data['client_id'],
                client_secret=token_data['client_secret'],
                scopes=token_data['scopes']
            )
            
            logger.info("Credentials loaded successfully")
            return True
            
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Error loading credentials: {e}")
            return False
    
    def get_user_info(self) -> Dict[str, Any]:
        """
        Gets the user's profile information.
        
        Returns:
            Dict with user profile information
        """
        if not self.credentials:
            logger.error("No credentials available")
            return {}
            
        try:
            # Build the People API service
            service = build('people', 'v1', credentials=self.credentials)
            
            # Call the People API to get user profile
            profile = service.people().get(
                resourceName='people/me',
                personFields='names,emailAddresses,photos'
            ).execute()
            
            # Extract relevant information
            user_info = {
                'name': profile.get('names', [{}])[0].get('displayName', 'Unknown'),
                'email': profile.get('emailAddresses', [{}])[0].get('value', 'Unknown'),
                'photo_url': profile.get('photos', [{}])[0].get('url', '')
            }
            
            return user_info
            
        except HttpError as e:
            logger.error(f"Error fetching user info: {e}")
            # Fallback: Create default user info if People API is not available
            return {
                'name': 'Classroom User',
                'email': 'randivetanishka@gmail.com',
                'photo_url': ''
            }


class GoogleClassroomAPI:
    """Handles Google Classroom API interactions."""
    
    def __init__(self, credentials: Optional[Credentials] = None):
        self.credentials = credentials
        self.service = None
        
        if credentials:
            self.service = build('classroom', 'v1', credentials=credentials)
    
    def set_credentials(self, credentials: Credentials) -> None:
        """Sets the credentials and initializes the API service."""
        self.credentials = credentials
        self.service = build('classroom', 'v1', credentials=credentials)
    
    def list_courses(self) -> List[Dict[str, Any]]:
        """
        Lists courses the user has access to.
        
        Returns:
            List of courses with course information
        """
        if not self.service:
            logger.error("Classroom API service not initialized")
            return []
            
        try:
            # Call the Classroom API to list courses
            results = self.service.courses().list(
                pageSize=20,
                courseStates=['ACTIVE']
            ).execute()
            
            courses = results.get('courses', [])
            
            # Format course information
            formatted_courses = []
            for course in courses:
                formatted_courses.append({
                    'id': course.get('id'),
                    'name': course.get('name'),
                    'section': course.get('section', ''),
                    'description': course.get('description', ''),
                    'room': course.get('room', ''),
                    'teacher': course.get('teacherGroupEmail', ''),
                    'link': course.get('alternateLink', '')
                })
            
            logger.info(f"Retrieved {len(formatted_courses)} courses")
            return formatted_courses
            
        except HttpError as e:
            logger.error(f"Error listing courses: {e}")
            return []
    
    def get_course_students(self, course_id: str) -> List[Dict[str, Any]]:
        """
        Gets the list of students in a course.
        
        Args:
            course_id: ID of the course
            
        Returns:
            List of student information
        """
        if not self.service:
            logger.error("Classroom API service not initialized")
            return []
            
        try:
            # Call the Classroom API to list students
            results = self.service.courses().students().list(
                courseId=course_id,
                pageSize=30
            ).execute()
            
            students = results.get('students', [])
            
            # Format student information
            formatted_students = []
            for student in students:
                profile = student.get('profile', {})
                formatted_students.append({
                    'id': student.get('userId'),
                    'name': profile.get('name', {}).get('fullName', 'Unknown'),
                    'email': profile.get('emailAddress', ''),
                    'photo_url': profile.get('photoUrl', '')
                })
            
            logger.info(f"Retrieved {len(formatted_students)} students for course {course_id}")
            return formatted_students
            
        except HttpError as e:
            logger.error(f"Error getting course students: {e}")
            return []