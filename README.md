# Mortgage Document Processing and NLP API

A RESTful API that provides document processing and natural language query capabilities for mortgage-related documents and guidelines.

## Features

- Document processing and data extraction
- Natural language query processing for mortgage guidelines
- JWT-based authentication
- Comprehensive error handling and logging
- Support for large document processing

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd <repository-name>
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables in `.env`:
```
API_USER=your_api_user
API_PASSWORD=your_api_password
API_SECRET_KEY=your_secret_key
ADDY_API_KEY=your_addy_api_key
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
OPENAI_API_KEY=your_openai_api_key
FLASK_DEBUG=False
```

## Running the API

Start the API server:
```bash
python api.py
```

The API will be available at `http://localhost:5000`.

## API Endpoints

### Authentication

#### POST /api/auth/token
Generate an authentication token.

**Request:**
- Basic Authentication with username and password

**Response:**
```json
{
    "token": "your.jwt.token"
}
```

### Document Processing

#### POST /api/document/process
Process a document through the document processor.

**Request:**
- Header: `Authorization: Bearer <token>`
- Form Data:
  - `file`: PDF file

**Response:**
```json
{
    "success": true,
    "data": {
        "income": 75000.0,
        "credit_score": 750,
        "debt": 25000.0,
        "property_value": 400000.0
    }
}
```

### NLP Endpoints

#### POST /api/nlp/query
Process a natural language query about mortgage guidelines.

**Request:**
- Header: `Authorization: Bearer <token>`
- Content-Type: `application/json`
- Body:
```json
{
    "query": "What is the maximum LTV for a single-family home in California?"
}
```

**Response:**
```json
{
    "success": true,
    "intent": "ltv_inquiry",
    "entities": {
        "state": "California",
        "property_type": "single-family"
    },
    "guidelines": ["..."],
    "response": "The maximum LTV is 97% for single-family homes in California."
}
```

#### POST /api/nlp/document
Process a document through the NLP engine.

**Request:**
- Header: `Authorization: Bearer <token>`
- Form Data:
  - `file`: PDF file
  - `document_type`: (optional) Stated document type
  - `applicants`: (optional) JSON array of applicant data

**Response:**
```json
{
    "success": true,
    "classification": {
        "documentType": "W2",
        "confidence": 0.95
    },
    "extraction": {
        "document_type": "W2",
        "data": {
            "wages": 75000,
            "employer": "Test Corp"
        }
    }
}
```

### Health Check

#### GET /api/health
Check API health status.

**Response:**
```json
{
    "status": "healthy",
    "timestamp": "2024-01-01T00:00:00Z"
}
```

## Error Handling

All endpoints return appropriate HTTP status codes and error messages:

```json
{
    "success": false,
    "error": "Error message",
    "error_type": "ErrorType"
}
```

Common status codes:
- 200: Success
- 400: Bad Request
- 401: Unauthorized
- 500: Internal Server Error

## Testing

Run the test suite:
```bash
python -m pytest tests/ -v --cov=.
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 