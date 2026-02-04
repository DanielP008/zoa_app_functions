from typing import Optional, Dict, Any

import firebase_admin
from firebase_admin import firestore


def get_company_config(company_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve configuration for a company from Firebase Firestore.

    The expected document structure in the collection is something like:

    {
        "ids": ["572778529248319"],         # numeric company id(s)
        "token": "<zoa_api_token>",
        "erp": {...},
        "erp_type": "mpm",
        "user": "vicente"
    }

    We search in the collection for any document whose `ids` array contains
    the provided `company_id` (which can be either the numeric id or an alias
    such as "0001-vimasegur") and return the first match as a plain dict.
    """
    if not company_id:
        return None

    # Ensure Firebase app is initialized (idempotent)
    if not firebase_admin._apps:
        firebase_admin.initialize_app()

    db = firestore.client()

    try:
        # NOTE: Adjust collection name here if needed to match your Firestore setup.
        docs = (
            db.collection(u"clientIDs")
            .where(u"ids", u"array_contains", company_id)
            .get()
        )
    except Exception as e:  # pragma: no cover - defensive
        # In production you might want to log this error with more detail
        print(f"[ERROR] Firestore connection failed: {e}")
        return None

    if not docs:
        return None

    return docs[0].to_dict()

