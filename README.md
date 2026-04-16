# Zoa Flow Zoa

A middleware API that acts as a bridge between external systems (automations, chatbots, integrations) and the **ZoaSuite CRM API**. Built as a Google Cloud Function with Docker support for flexible deployment.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [API Reference](#api-reference)
  - [Request Structure](#request-structure)
  - [Modules](#modules)
- [Deployment](#deployment)
- [Error Handling](#error-handling)

---

## Overview

**Zoa Flow Zoa** simplifies integration with ZoaSuite by providing:

- **Unified interface**: Single endpoint for all CRM operations
- **Smart resolution**: Automatically resolves entity names to IDs (e.g., manager names → UUIDs)
- **Flexible search**: Find records by phone, email, NIF, or name
- **CORS support**: Ready for browser-based integrations

### Supported Operations

| Module | Search | Create | Update | Send | Assign | Status | Process |
|--------|:------:|:------:|:------:|:----:|:------:|:------:|:-------:|
| contacts | ✅ | ✅ | ✅ | - | - | - | - |
| users | ✅ | - | - | - | - | - | - |
| cards | ✅ | ✅ | ✅ | - | - | - | - |
| cardact | - | ✅ | ✅ | - | - | - | - |
| activities | ✅ | ✅ | ✅ | - | - | - | - |
| conversations | ✅ | - | - | ✅ | ✅ | ✅ | - |
| conversations2 | - | - | - | ✅ | ✅ | ✅ | - |
| notes | ✅ | ✅ | ✅ | - | - | - | - |
| tags | ✅ | ✅ | ✅ | - | - | - | - |
| departments | ✅ | - | - | - | - | - | - |
| scheduler | ✅ | - | - | - | - | - | - |
| readall | ✅ | - | - | - | - | - | - |
| email_module | - | - | - | ✅ | - | - | - |
| ai_chat | - | ✅ | ✅ | ✅ | - | - | - |

---

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  External App   │────▶│   Zoa Flow Zoa   │────▶│  ZoaSuite API   │
│  (Make, n8n,    │     │   (Middleware)   │     │                 │
│   Chatbot...)   │◀────│                  │◀────│                 │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌──────────────┐
                        │   Firebase   │
                        │  (Scheduler) │
                        └──────────────┘
```

### Tech Stack

- **Runtime**: Python 3.11
- **Framework**: Google Functions Framework
- **Database**: Firebase Firestore (for scheduler config)
- **Container**: Docker + Docker Compose

---

## Quick Start

### Prerequisites

- Python 3.11+
- Docker (optional)
- Firebase credentials (for scheduler module)

### Local Development

```bash
# Clone the repository
git clone https://github.com/DanielP008/zoa_app_functions.git
cd zoa_flow_zoa

# Install dependencies
pip install -r requirements.txt

# Run locally
functions-framework --target=main --port=8080
```

### Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up -d

# Or build manually
docker build -t zoa-flow-zoa .
docker run -p 8080:8080 zoa-flow-zoa
```

The API will be available at `http://localhost:8080`

---

## API Reference

### Request Structure

All requests use **POST** method with JSON body:

```json
{
  "company_id": "your-company-id",
  "action": "module_name",
  "option": "operation",
  ...additional fields
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `company_id` | string | ✅ | Your ZoaSuite company identifier |
| `action` | string | ✅ | Module to interact with |
| `option` | string | ✅ | Operation to perform |

### Response Structure

```json
{
  "success": true,
  "data": { ... }
}
```

Error responses:

```json
{
  "error": "Error description",
  "details": "Additional context"
}
```

---

## Modules

### Contacts

Manage CRM contacts with flexible search and automatic manager resolution.

#### Search Contact

```json
{
  "company_id": "xxx",
  "action": "contacts",
  "option": "search",
  "phone": "+34612345678"
}
```

**Search criteria** (use one):
- `phone` or `mobile` - Phone number
- `email` - Email address
- `nif` - Tax ID
- `name` - Contact name

#### Create Contact

```json
{
  "company_id": "xxx",
  "action": "contacts",
  "option": "create",
  "name": "John Doe",
  "email": "john@example.com",
  "mobile": "+34612345678",
  "nif": "12345678A",
  "contact_type": "particular",
  "gender": "male",
  "manager_name": "Sales Agent Name"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | ✅ | Contact full name |
| `email` | string | - | Primary email |
| `mobile` | string | - | Phone number |
| `nif` | string | - | Tax identification |
| `contact_type` | string | - | `particular` or `company` |
| `manager_name` | string | - | Assigned manager (resolved automatically) |

#### Update Contact

```json
{
  "company_id": "xxx",
  "action": "contacts",
  "option": "update",
  "phone": "+34612345678",
  "new_name": "John Smith",
  "new_phone": "+34698765432",
  "new_manager_name": "New Manager"
}
```

---

### Users

Search for CRM users/agents.

#### Search User

```json
{
  "company_id": "xxx",
  "action": "users",
  "option": "search",
  "name": "Agent Name"
}
```

```json
{
  "company_id": "xxx",
  "action": "users",
  "option": "search",
  "id": "user-uuid"
}
```

---

### Cards

Manage sales opportunities and tasks in pipelines.

#### Search Card

```json
{
  "company_id": "xxx",
  "action": "cards",
  "option": "search",
  "title": "Deal Name"
}
```

Or search by contact:

```json
{
  "company_id": "xxx",
  "action": "cards",
  "option": "search",
  "phone": "+34612345678"
}
```

#### Create Card

```json
{
  "company_id": "xxx",
  "action": "cards",
  "option": "create",
  "title": "New Opportunity",
  "phone": "+34612345678",
  "card_type": "opportunity",
  "pipeline_name": "Sales Pipeline",
  "stage_name": "Qualification",
  "amount": 5000,
  "tags_name": "Hot Lead, Q1",
  "description": "Optional description of the card",
  "manager_name": "Sales Agent Name"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | string | ✅ | Card title |
| `phone`/`email` | string | ✅ | Contact identifier |
| `card_type` | string | - | `opportunity` (default) or `task` |
| `pipeline_name` | string | - | Target pipeline (auto-detected) |
| `stage_name` | string | - | Target stage (defaults to first) |
| `amount` | number | - | Deal value |
| `tags_name` | string | - | Comma-separated tag names |
| `description` | string | - | Card description |
| `manager_name` | string | - | Assigned manager (resolved automatically) |

#### Update Card

```json
{
  "company_id": "xxx",
  "action": "cards",
  "option": "update",
  "title": "Deal Name",
  "new_title": "Updated Deal",
  "new_stage_name": "Negotiation",
  "amount": 7500,
  "description": "Updated description",
  "manager_name": "New Manager Name"
}
```

---

### CardAct (Card + Activity)

Create or update a card and an associated activity in a single request.

#### Create Card + Activity

```json
{
  "company_id": "xxx",
  "action": "cardact",
  "option": "create",
  "title": "New Deal",
  "phone": "+34612345678",
  "card_type": "opportunity",
  "amount": 1000,
  "description": "Card description",
  "manager_name": "Agent Name",
  "type_of_activity": "llamada",
  "activity_title": "Intro Call",
  "activity_description": "Discuss requirements",
  "date": "2024-02-01",
  "start_time": "10:00",
  "duration": "30",
  "guests_names": "Support Agent"
}
```

#### Update Card + Activity

```json
{
  "company_id": "xxx",
  "action": "cardact",
  "option": "update",
  "title": "New Deal",
  "new_title": "Updated Deal",
  "description": "Updated card description",
  "manager_name": "New Agent",
  "type_of_activity": "reunion",
  "activity_title": "Follow-up Meeting",
  "date": "2024-02-05",
  "start_time": "15:00"
}
```

---

### Activities

Manage calendar activities (calls, meetings, tasks).

#### Search Activities

```json
{
  "company_id": "xxx",
  "action": "activities",
  "option": "search",
  "phone": "+34612345678"
}
```

#### Create Activity

```json
{
  "company_id": "xxx",
  "action": "activities",
  "option": "create",
  "title": "Follow-up Call",
  "phone": "+34612345678",
  "type_of_activity": "llamada",
  "date": "2024-01-15",
  "start_time": "10:00",
  "duration": "30",
  "card_name": "Related Deal",
  "guests_names": "Agent 1, Agent 2",
  "description": "Discuss proposal"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | string | ✅ | Activity title |
| `type_of_activity` | string | - | `llamada`, `reunion`, `tarea` |
| `date` | string | - | YYYY-MM-DD format |
| `start_time` | string | - | HH:MM format |
| `duration` | string | - | Minutes |
| `card_name` | string | - | Link to card by title |
| `guests_names` | string | - | Comma-separated user names |
| `completed` | string | - | `completed` or `not_completed` |

#### Update Activity

```json
{
  "company_id": "xxx",
  "action": "activities",
  "option": "update",
  "title": "Follow-up Call",
  "phone": "+34612345678",
  "new_description": "Updated notes",
  "completed": "completed"
}
```

---

### Conversations (WhatsApp)

Send WhatsApp messages and manage conversation state.

#### Send Text Message

```json
{
  "company_id": "phone_number_id",
  "action": "conversations",
  "option": "send",
  "type": "text",
  "conversation_id": "conv-uuid",
  "text": "Hello! How can I help you?"
}
```

Or to a new number:

```json
{
  "company_id": "phone_number_id",
  "action": "conversations",
  "option": "send",
  "type": "text",
  "to": "+34612345678",
  "text": "Hello!"
}
```

#### Send Template Message

```json
{
  "company_id": "phone_number_id",
  "action": "conversations",
  "option": "send",
  "type": "template",
  "to": "+34612345678",
  "template_name": "welcome_message",
  "data": {
    "body": ["John", "Acme Corp"],
    "button": [],
    "header": []
  }
}
```

#### Assign Conversation

```json
{
  "company_id": "phone_number_id",
  "action": "conversations",
  "option": "assign",
  "conversation_id": "conv-uuid",
  "manager_name": "Agent Name"
}
```

#### Update Sales Status

```json
{
  "company_id": "phone_number_id",
  "action": "conversations",
  "option": "status",
  "conversation_id": "conv-uuid",
  "sales_status": "qualified"
}
```

---

### Notes

Attach notes to contacts and cards.

#### Search Notes

```json
{
  "company_id": "xxx",
  "action": "notes",
  "option": "search",
  "phone": "+34612345678"
}
```

#### Create Note

```json
{
  "company_id": "xxx",
  "action": "notes",
  "option": "create",
  "phone": "+34612345678",
  "content": "Customer requested callback next week",
  "manager_name": "Agent Name",
  "is_pinned": true
}
```

#### Update Note

```json
{
  "company_id": "xxx",
  "action": "notes",
  "option": "update",
  "phone": "+34612345678",
  "date": "2024-01-15",
  "new_content": "Updated note content"
}
```

---

### Tags

Manage pipeline tags/labels.

#### Search Tags

```json
{
  "company_id": "xxx",
  "action": "tags",
  "option": "search"
}
```

#### Create Tag

```json
{
  "company_id": "xxx",
  "action": "tags",
  "option": "create",
  "name": "VIP Client",
  "type": "sales",
  "color": "#FF5722"
}
```

#### Update Card Tags

Update tags for a specific card. You can provide tag names (resolved automatically) or direct tag IDs.

```json
{
  "company_id": "xxx",
  "action": "tags",
  "option": "update",
  "card_id": "card-uuid",
  "tags_name": "VIP Client, Priority"
}
```

Or using direct IDs:

```json
{
  "company_id": "xxx",
  "action": "tags",
  "option": "update",
  "card_id": "card-uuid",
  "tag_id": ["tag-uuid-1", "tag-uuid-2"]
}
```

---

### Departments

Get team information based on contact's assigned manager.

```json
{
  "company_id": "xxx",
  "action": "departments",
  "option": "search",
  "phone": "+34612345678"
}
```

**Response:**

```json
{
  "department_id": "dept-uuid",
  "primary_manager_extension": "101",
  "team": [
    {"name": "John Doe", "extension": "101", "is_primary": true},
    {"name": "Jane Smith", "extension": "102"}
  ],
  "all_extensions": "101,102",
  "voip_extensions": "Local/101@users&Local/102@users"
}
```

---

### Scheduler

Get schedule configuration from Firebase.

```json
{
  "company_id": "phone_number_id",
  "action": "scheduler",
  "option": "search"
}
```

**Response:**

```json
{
  "morning": "09:00-14:00",
  "afternoon": "16:00-20:00"
}
```

---

### ReadAll (Aggregated Contact Info)

Get comprehensive contact information in a single request.

```json
{
  "company_id": "xxx",
  "action": "readall",
  "option": "search",
  "phone": "+34612345678"
}
```

**Response:**

```json
{
  "contact": {
    "id": "contact-uuid",
    "name": "John Doe",
    "nif": "12345678A"
  },
  "manager": {
    "id": "user-uuid",
    "name": "Sales Agent",
    "phone": "+34600000000"
  },
  "open_activities_count": 2,
  "activities_details": [
    {"title": "Follow-up", "type": "opportunity", "stage": "Qualification"},
    {"title": "Support ticket", "type": "task", "stage": "In Progress"}
  ]
}
```

---

### Email Module

Send emails through ZoaSuite.

```json
{
  "company_id": "xxx",
  "action": "email_module",
  "option": "send",
  "to": "recipient@example.com",
  "subject": "Meeting Confirmation",
  "body": "<h1>Hello!</h1><p>Your meeting is confirmed.</p>",
  "body_type": "html",
  "cc": "copy@example.com",
  "reply_to": "noreply@company.com"
}
```

---

### AI Chat Assistant

Interface for interacting with the AI chat and managing tarification sheets.

#### Send Message
```json
{
  "company_id": "xxx",
  "action": "ai_chat",
  "option": "send",
  "user_id": "user-uuid",
  "body": {"data": "Hello assistant"},
  "body_type": "text"
}
```

#### Create Tarification Sheet
```json
{
  "company_id": "xxx",
  "action": "ai_chat",
  "option": "create",
  "user_id": "user-uuid",
  "call_id": "call-uuid",
  "body_type": "auto_sheet",
  "data": {
    "vehiculo": {"matricula": "1234ABC"},
    "tomador": {"nombre": "John"}
  }
}
```

---

## Deployment

### Environment Variables

| Variable | Description |
|----------|-------------|
| `PORT` | Server port (default: 8080) |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to Firebase service account JSON |

### Google Cloud Functions

```bash
gcloud functions deploy zoa-flow-zoa \
  --runtime python311 \
  --trigger-http \
  --entry-point main \
  --allow-unauthenticated
```

### Docker

The included `Dockerfile` and `docker-compose.yml` provide production-ready containerization:

```bash
docker-compose up -d
```

Health check endpoint: `GET /` returns 200 when healthy.

---

## Error Handling

### HTTP Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 400 | Bad request (missing fields) |
| 404 | Resource not found |
| 500 | Internal server error |

### Common Errors

```json
{"error": "request_json missing"}
```
Request body is empty or not valid JSON.

```json
{"error": "Faltan campos obligatorios: 'action' u 'option'"}
```
Missing required `action` or `option` fields.

```json
{"error": "Se requiere 'company_id'"}
```
Missing company identifier.

```json
{"error": "Action 'xyz' not recognized"}
```
Invalid module name in `action` field.

```json
{"error": "Option 'xyz' is not valid for action 'abc'"}
```
The requested operation is not supported by the module.

---

## Project Structure

```
zoa_flow_zoa/
├── main.py              # Entry point & request router
├── models/
│   ├── ai_chat.py       # AI Chat and tarification sheets
│   ├── activities.py    # Activity management
│   ├── cards.py         # Pipeline cards (opportunities/tasks)
│   ├── contacts.py      # Contact management
│   ├── conversations.py # WhatsApp messaging
│   ├── departments.py   # Department/team info
│   ├── email_module.py  # Email sending
│   ├── notes.py         # Notes management
│   ├── readall.py       # Aggregated contact data
│   ├── scheduler.py     # Schedule config (Firebase)
│   ├── tags.py          # Tag management
│   └── users.py         # User/agent lookup
├── requirements.txt     # Python dependencies
├── Dockerfile          # Container configuration
└── docker-compose.yml  # Docker orchestration
```

---

## License

Proprietary - DanielP008

---

