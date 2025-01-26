from flask import Flask, request, jsonify
from functools import wraps
import jwt
import os
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
from document_processor import process_document
from nlp_engine import MortgageNLPEngine
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('API_SECRET_KEY', 'your-secret-key')

# Initialize NLP engine
nlp_engine = MortgageNLPEngine()

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        
        try:
            # Remove 'Bearer ' prefix if present
            if token.startswith('Bearer '):
                token = token[7:]
            
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user = data['user']
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
            
        return f(current_user, *args, **kwargs)
    
    return decorated

@app.route('/api/auth/token', methods=['POST'])
def get_token():
    """Generate authentication token"""
    auth = request.authorization
    
    if not auth or not auth.username or not auth.password:
        return jsonify({'error': 'Missing credentials'}), 401
    
    # In production, validate against user database
    if auth.username == os.getenv('API_USER') and auth.password == os.getenv('API_PASSWORD'):
        token = jwt.encode({
            'user': auth.username,
            'exp': datetime.utcnow() + timedelta(hours=24)
        }, app.config['SECRET_KEY'])
        
        return jsonify({'token': token})
    
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/api/health', methods=['GET'])
def health_check():
    """API health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat()
    })

@app.route('/api/document/process', methods=['POST'])
@token_required
def process_document_api(current_user):
    """Process a document through the document processor"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
            
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({'error': 'Only PDF files are supported'}), 400
        
        # Save file temporarily
        temp_path = f"/tmp/{file.filename}"
        file.save(temp_path)
        
        try:
            # Process the document
            result = process_document(temp_path)
            return jsonify(result)
            
        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
    except Exception as e:
        logger.error(f"Error processing document: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__
        }), 500

@app.route('/api/nlp/query', methods=['POST'])
@token_required
def process_query(current_user):
    """Process a natural language query"""
    try:
        data = request.get_json()
        
        if not data or 'query' not in data:
            return jsonify({'error': 'No query provided'}), 400
        
        query = data['query']
        
        # Extract entities from query
        entities = nlp_engine.extract_entities(query)
        
        # Detect intent
        intent = nlp_engine.detect_intent(query)
        
        # Search guidelines based on intent and entities
        guidelines = nlp_engine.search_guidelines(intent, entities)
        
        # Generate response
        response = nlp_engine.generate_response(query, intent, entities, guidelines)
        
        return jsonify({
            'success': True,
            'intent': intent,
            'entities': entities,
            'guidelines': guidelines,
            'response': response
        })
        
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__
        }), 500

@app.route('/api/nlp/document', methods=['POST'])
@token_required
def process_document_nlp(current_user):
    """Process a document through the NLP engine"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
            
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({'error': 'Only PDF files are supported'}), 400
        
        # Get optional parameters
        borrower_stated_type = request.form.get('document_type')
        applicants = request.form.get('applicants')
        if applicants:
            try:
                applicants = json.loads(applicants)
            except:
                return jsonify({'error': 'Invalid applicants data format'}), 400
        
        # Save file temporarily
        temp_path = f"/tmp/{file.filename}"
        file.save(temp_path)
        
        try:
            # Process the document
            result = nlp_engine.process_document(
                temp_path,
                borrower_stated_type=borrower_stated_type,
                applicants=applicants
            )
            return jsonify(result)
            
        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
    except Exception as e:
        logger.error(f"Error processing document: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__
        }), 500

if __name__ == '__main__':
    app.run(debug=os.getenv('FLASK_DEBUG', 'False').lower() == 'true') 