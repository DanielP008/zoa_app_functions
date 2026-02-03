# ZOA Flow Tests

Automated tests for the ZOA Flow API middleware.

## Setup

1. Install test dependencies:
```bash
pip install pytest requests
```

2. Set environment variables (optional, defaults to localhost):
```bash
export ZOA_TEST_URL="http://localhost:8080"
export ZOA_TEST_COMPANY_ID="521783407682043"
export ZOA_TEST_PHONE="+34622272095"
export ZOA_TEST_EMAIL="test@example.com"
```

## Running Tests

### Run all tests
```bash
pytest tests/
```

### Run specific test file
```bash
pytest tests/test_contacts.py
```

### Run specific test class
```bash
pytest tests/test_contacts.py::TestContacts
```

### Run specific test
```bash
pytest tests/test_contacts.py::TestContacts::test_search_contact_by_phone
```

### Run with verbose output
```bash
pytest tests/ -v
```

### Run with output from print statements
```bash
pytest tests/ -s
```

### Run tests matching a pattern
```bash
pytest tests/ -k "contact"
```

## Test Structure

```
tests/
├── __init__.py
├── conftest.py                    # Pytest configuration and fixtures
├── test_conversations.py          # WhatsApp messaging tests
├── test_contacts.py               # Contact management tests
├── test_cards.py                  # Cards (opportunities/tasks) tests
├── test_cardact.py                # Combined card+activity tests
├── test_activities.py             # Activity/calendar tests
├── test_notes.py                  # Notes tests
├── test_users_tags.py             # Users and tags tests
├── test_departments_readall.py    # Departments and readall tests
└── test_email_scheduler.py        # Email and scheduler tests
```

## Test Coverage

- ✅ **Conversations** - WhatsApp text/template messages, assign, status
- ✅ **Contacts** - Search, create, update by phone/email/NIF
- ✅ **Cards** - Search, create (opportunity/task), update
- ✅ **CardAct** - Combined card+activity creation
- ✅ **Activities** - Search, create, update calendar activities
- ✅ **Notes** - Search, create, update contact notes
- ✅ **Users** - Search users/managers
- ✅ **Tags** - Search, create tags
- ✅ **Departments** - Get team info
- ✅ **ReadAll** - Get aggregated contact data
- ✅ **Email** - Send emails
- ✅ **Scheduler** - Get schedule configuration

## Notes

- Tests use the flow-zoa middleware, not the ZOA API directly
- Some tests may return 404 if test data doesn't exist (this is expected)
- Tests are idempotent where possible (use unique timestamps in titles)
- Make sure the service is running before executing tests
