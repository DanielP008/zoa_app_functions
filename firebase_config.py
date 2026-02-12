from typing import Optional, Tuple

import firebase_admin
from firebase_admin import firestore


def get_company_token_and_env(company_id: str) -> Optional[Tuple[str, bool]]:
    """
    Returns (token, is_test) for a given company_id from Firestore.

    - token: ZOA API token stored in clientIDs document
    - is_test: True if the document corresponds to the test tenant (e.g. '0000-test')
    """
    if not company_id:
        return None

    # Ensure Firebase app is initialized (idempotent)
    if not firebase_admin._apps:
        firebase_admin.initialize_app()

    db = firestore.client()

    try:
        # Use filter keyword argument to avoid deprecation warning
        docs = (
            db.collection(u"clientIDs")
            .where(filter=firestore.FieldFilter("ids", "array_contains", company_id))
            .get()
        )
    except Exception as e:
        return None

    if not docs:
        return None

    doc = docs[0]
    data = doc.to_dict() or {}
    token = data.get("token")

    if not token:
        return None

    # is_test is True if the Firestore document id is '0000-test'
    is_test = (doc.id == "0000-test")
    return token, is_test

