# AI Chat Module

## Overview
The `ai_chat` module provides integration with ZOA's AI chat assistant endpoint.

## Endpoint
`POST https://dev.api.zoasuite.com/api/pipelines/assistant-chat/ai`

## Usage

### Basic Request Format

```json
{
  "company_id": "your_company_id",
  "action": "ai_chat",
  "option": "send",
  "user_id": "202",
  "body": {
    "data": "Hola, ¿cómo estás?"
  }
}
```

### Request with Body Type

```json
{
  "company_id": "your_company_id",
  "action": "ai_chat",
  "option": "send",
  "user_id": "202",
  "body": {
    "data": "Hola de nuevo"
  },
  "body_type": "text"
}
```

## Parameters

### Required Parameters
- `company_id` (str): Company identifier
- `action` (str): Must be "ai_chat"
- `option` (str): Must be "send"
- `user_id` (str): The user ID for the chat session
- `body` (dict): The message body. **Must be a dictionary with 'data' key**. Format: `{"data": "your message"}`

### Optional Parameters
- `body_type` (str): Type of body content. Default: "text"

## Response

Successful response (200/201):
```json
{
  "response": "AI assistant response here",
  ...
}
```

Error responses:

Missing user_id (400):
```json
{
  "error": "El campo 'user_id' es obligatorio."
}
```

Missing body (400):
```json
{
  "error": "El campo 'body' es obligatorio."
}
```

Invalid body format (400):
```json
{
  "error": "El campo 'body' debe ser un diccionario con la clave 'data'. Ejemplo: {'data': 'tu mensaje'}"
}
```

## Example with Python

```python
import requests
import json

url = "http://localhost:8080"  # or your deployed endpoint

payload = {
    "company_id": "your_company_id",
    "action": "ai_chat",
    "option": "send",
    "user_id": "202",
    "body": {
        "data": "Hola de nuevo"
    }
}

headers = {
    'Content-Type': 'application/json'
}

response = requests.post(url, headers=headers, json=payload)
print(response.json())
```

## Direct API Example (matching ZOA API format)

```python
import requests
import json

url = "https://dev.api.zoasuite.com/api/pipelines/assistant-chat/ai"

payload = json.dumps({
  "body_type": "text",
  "body": {
    "data": "Hola de nuevo"
  },
  "user_id": "202"
})

headers = {
  'Accept': 'application/json',
  'apiKey': 'sk_test_9f8a7b6c5d4e3f2a',
  'Content-Type': 'application/json'
}

response = requests.request("POST", url, headers=headers, data=payload)
print(response.text)
```

## Testing

Run the tests with:
```bash
pytest tests/test_ai_chat.py -v
```

## Architecture

### Model: `models/ai_chat.py`
Contains the `ZoaAIChat` class with the `send()` method.

### Router: `main.py`
Action "ai_chat" is registered in the main router.

### Interface: `interface.py`
`AIChatInterface` provides a clean abstraction layer following the project pattern.

### Tests: `tests/test_ai_chat.py`
Comprehensive test suite including:
- Basic text message sending
- Body with explicit body_type
- Error validation (missing user_id, missing body, invalid body format)
