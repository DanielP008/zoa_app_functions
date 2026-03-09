import os
from dotenv import load_dotenv

load_dotenv()

# Default to DEV credentials if not provided
DEFAULT_TOKEN = os.getenv("TOKEN")


# Model imports
from models.contacts import ZoaContact
from models.users import ZoaUser
from models.cards import ZoaCard
from models.cardact import ZoaCardAct
from models.activities import ZoaActivity
from models.departments import ZoaDepartment
from models.tags import ZoaTags
from models.readall import ZoaReadAll
from models.email_module import ZoaEmail
from models.conversations import ZoaConversation
from models.notes import ZoaNote
from models.scheduler import ZoaScheduler
from models.ai_chat import ZoaAIChat
from models.insurance_agent import ZoaInsuranceAgent

class ZoaBaseInterface:
    """Base class that handles common validation and dispatch logic."""
    
    def __init__(self, token=None):
        self.token = token or DEFAULT_TOKEN
        self.client = None
        self.action_name = None

    def execute(self, company_id, option, request_data=None):
        """
        Executes a specific action ensuring required parameters exist.
        
        Args:
            company_id (str): Company ID (required).
            option (str): Option to execute (search, create, etc.) (required).
            request_data (dict): Additional data for the request.
        """
        if request_data is None:
            request_data = {}

        # 1. Validate required fields
        if not company_id:
            return {"error": "El campo 'company_id' es obligatorio."}, 400
        
        if not option:
            return {"error": "El campo 'option' es obligatorio."}, 400

        # Ensure action is also present (defined by child class)
        if not self.action_name:
            return {"error": "Error interno: 'action' no definido en la clase."}, 500

        # 2. Enrich request data
        # Ensure required parameters are in the dict passed to models (many expect them there).
        request_data['company_id'] = company_id
        request_data['option'] = option
        request_data['action'] = self.action_name

        # 3. Dispatch option to the corresponding client method
        try:
            if option == "search":
                return self.client.search(request_data)
            elif option == "create":
                return self.client.create(request_data)
            elif option == "update":
                return self.client.update(request_data)
            elif option == "send":
                return self.client.send(request_data)
            elif option == "assign":
                return self.client.assign(request_data)
            elif option == "status":
                return self.client.status(request_data)
            elif option == "assign_status":
                return self.client.assign_status(request_data)
            elif option == "process":
                return self.client.process(request_data)
            else:
                return {"error": f"La opción '{option}' no es válida para la acción '{self.action_name}'"}, 400
                
        except AttributeError:
            return {"error": f"El método '{option}' no está implementado en el modelo de '{self.action_name}'"}, 400
        except Exception as e:
            return {"error": f"Error interno ejecutando '{self.action_name}/{option}': {str(e)}"}, 500


class ContactsInterface(ZoaBaseInterface):
    """
    Interface for Contact management operations.
    """
    def __init__(self, token=None):
        super().__init__(token)
        self.client = ZoaContact(self.token)
        self.action_name = "contacts"

    def search(self, request_data):
        """
        Search for a contact.
        
        Args:
            request_data (dict):
                - phone (str, optional): Contact phone number.
                - mobile (str, optional): Alias for phone.
                - email (str, optional): Contact email.
                - nif (str, optional): Contact NIF/ID document.
                - name (str, optional): Contact name.
                * At least one search criteria is required.
        """
        return self.client.search(request_data)

    def create(self, request_data):
        """
        Create a new contact.
        
        Args:
            request_data (dict):
                - name (str, optional): Contact name.
                - email (str, optional): Contact email.
                - email2 (str, optional): Secondary email.
                - nif (str, optional): NIF/ID document.
                - mobile (str, optional): Phone number.
                - phone (str, optional): Alias for mobile.
                - contact_type (str, optional): 'particular' (default) or 'company'.
                - gender (str, optional): Contact gender.
                - office_ids (list, optional): List of office IDs.
                - manager_name (str, optional): Name of the manager to assign (resolved to ID).
        """
        return self.client.create(request_data)

    def update(self, request_data):
        """
        Update an existing contact.
        
        Args:
            request_data (dict):
                - contact_id (str, optional): ID of the contact to update.
                * If contact_id is missing, it attempts to find the contact using search criteria (phone, email, nif, name).
                
                Fields to update:
                - new_name (str, optional): New name for the contact.
                - new_phone (str, optional): New phone number.
                - email (str, optional): New email.
                - nif (str, optional): New NIF.
                - gender (str, optional): New gender.
                - manager_name (str, optional): New manager name (resolved to ID).
                - new_manager_name (str, optional): Alias for manager_name.
        """
        return self.client.update(request_data)


class UsersInterface(ZoaBaseInterface):
    """
    Interface for User (Agent/Manager) operations.
    """
    def __init__(self, token=None):
        super().__init__(token)
        self.client = ZoaUser(self.token)
        self.action_name = "users"

    def search(self, request_data):
        """
        Search for a user/agent.
        
        Args:
            request_data (dict):
                - id (str, optional): User ID.
                - name (str, optional): User name.
                - manager_name (str, optional): Alias for name.
                * If no criteria provided, returns list of users.
        """
        return self.client.search(request_data)


class CardsInterface(ZoaBaseInterface):
    """
    Interface for Card (Opportunity/Task) operations.
    """
    def __init__(self, token=None):
        super().__init__(token)
        self.client = ZoaCard(self.token)
        self.action_name = "cards"

    def search(self, request_data):
        """
        Search for a card.
        
        Args:
            request_data (dict):
                - title (str, optional): Card title.
                * Or search by contact fields (returns cards for that contact):
                - phone, mobile, email, nif (str, optional).
        """
        return self.client.search(request_data)

    def create(self, request_data):
        """
        Create a new card.
        
        Args:
            request_data (dict):
                - title (str, required): Card title.
                - card_type (str, optional): 'opportunity' (default) or 'task'.
                - pipeline_name (str, optional): Name of the pipeline.
                - stage_name (str, optional): Name of the stage.
                - amount (float, optional): Monetary amount.
                - tags_name (str/list, optional): Tag names to apply.
                
                Contact identification (at least one required):
                - phone, mobile, email, nif.
        """
        return self.client.create(request_data)

    def update(self, request_data):
        """
        Update an existing card.
        
        Args:
            request_data (dict):
                - card_id (str, optional): ID of the card to update.
                - title (str, optional): Title to search for if card_id missing.
                * Or contact search fields to find the card.
                
                Fields to update:
                - new_title (str, optional): New title.
                - new_stage_name (str, optional): Move to this stage.
                - stage_name (str, optional): Alias for new_stage_name.
                - new_pipeline_name (str, optional): Move to this pipeline.
                - pipeline_name (str, optional): Alias for new_pipeline_name.
                - new_tags_name (str/list, optional): Update tags.
                - amount (float, optional): Update amount.
                - description (str, optional): Update description.
        """
        return self.client.update(request_data)


class CardActionsInterface(ZoaBaseInterface):
    """
    Interface for combined Card + Activity operations (orchestration).
    """
    def __init__(self, token=None):
        super().__init__(token)
        self.client = ZoaCardAct(self.token)
        self.action_name = "cardact"

    def create(self, request_data):
        """
        Create a Card and optionally an Activity linked to it.
        
        Args:
            request_data (dict):
                Card fields:
                - title (str, required): Card title.
                - card_type (str, optional): 'opportunity' or 'task'.
                - pipeline_name (str, optional): Target pipeline.
                - stage_name (str, optional): Target stage.
                - amount (float, optional): Amount.
                - tags_name (str/list, optional): Tags (auto-created if missing).
                - description (str, optional): Card description.
                - manager_name (str, optional): Manager name.
                
                Contact identification:
                - phone, mobile, email, nif.
                
                Activity fields (triggers activity creation if 'type_of_activity' present):
                - type_of_activity (str): e.g., 'llamada', 'reunion'.
                - activity_title (str, optional): Defaults to "Actividad: {title}".
                - activity_description (str, optional): Activity notes.
                - date (str, optional): 'YYYY-MM-DD'.
                - start_time (str, optional): 'HH:MM'.
                - duration (str, optional): Duration in minutes.
                - guests_names (str, optional): Comma-separated names of guests (users).
                - manager_name (str, optional): Manager name.
        """
        return self.client.create(request_data)

    def update(self, request_data):
        """
        Update a Card and recreate its Activity.
        
        Args:
            request_data (dict):
                - card_id (str, optional): Target card ID.
                - title (str, optional): Target card title (search).
                
                Card Update fields:
                - new_title (str, optional).
                - amount (float, optional).
                - description (str, optional).
                - manager_name (str, optional).
                - tags_name (str, optional).
                
                Activity Re-creation fields:
                - activity_title, type_of_activity, activity_description.
                - date, start_time, duration.
                - guests_names.
        """
        return self.client.update(request_data)


class ActivitiesInterface(ZoaBaseInterface):
    """
    Interface for Activity management operations.
    """
    def __init__(self, token=None):
        super().__init__(token)
        self.client = ZoaActivity(self.token)
        self.action_name = "activities"

    def search(self, request_data):
        """
        Search activities for a specific contact.
        
        Args:
            request_data (dict):
                Contact identification (one required):
                - phone, mobile, email, nif.
        """
        return self.client.search(request_data)

    def create(self, request_data):
        """
        Create a new activity.
        
        Args:
            request_data (dict):
                - title (str, required): Activity title.
                - type_of_activity (str, optional): 'llamada' (default), 'reunion', etc.
                - date (str, optional): 'YYYY-MM-DD'.
                - start_time (str, optional): 'HH:MM'.
                - duration (str, optional): Minutes (default 30).
                - description (str, optional): Notes.
                - card_name (str, optional): Title of card to link.
                - guests_names (str, optional): Comma-separated guest names.
                
                Contact identification:
                - phone, mobile, email, nif.
        """
        return self.client.create(request_data)

    def update(self, request_data):
        """
        Update an existing activity.
        
        Args:
            request_data (dict):
                - activity_id (str, optional): ID of activity.
                - title (str, optional): Title to search if ID missing.
                * Also requires contact identification if searching by title.
                
                Fields to update:
                - new_title, new_description, completed (status).
                - new_date, new_start_time, new_duration.
                - guests_names.
        """
        return self.client.update(request_data)


class DepartmentsInterface(ZoaBaseInterface):
    """
    Interface for Department/Team lookup operations.
    """
    def __init__(self, token=None):
        super().__init__(token)
        self.client = ZoaDepartment(self.token)
        self.action_name = "departments"

    def search(self, request_data):
        """
        Search department info based on a contact's manager.
        
        Args:
            request_data (dict):
                - phone (str, required): Contact phone number.
                * Or mobile.
        """
        return self.client.search(request_data)


class TagsInterface(ZoaBaseInterface):
    """
    Interface for Tag management operations.
    """
    def __init__(self, token=None):
        super().__init__(token)
        self.client = ZoaTags(self.token)
        self.action_name = "tags"

    def search(self, request_data=None):
        """
        Get all tags.
        
        Args:
            request_data (dict, optional): Unused.
        """
        return self.client.search(request_data)

    def create(self, request_data):
        """
        Create a new tag.
        
        Args:
            request_data (dict):
                - name (str, required): Tag name.
                - type (str, optional): Tag type (default 'sales').
                - color (str, optional): Hex color code.
        """
        return self.client.create(request_data)


class ReadAllInterface(ZoaBaseInterface):
    """
    Interface for Aggregated Data operations.
    """
    def __init__(self, token=None):
        super().__init__(token)
        self.client = ZoaReadAll(self.token)
        self.action_name = "readall"

    def search(self, request_data):
        """
        Get aggregated info (contact + manager + open cards).
        
        Args:
            request_data (dict):
                Contact identification:
                - phone, mobile, email, nif, name.
        """
        return self.client.search(request_data)


class EmailInterface(ZoaBaseInterface):
    """
    Interface for Email operations.
    """
    def __init__(self, token=None):
        super().__init__(token)
        self.client = ZoaEmail(self.token)
        self.action_name = "email_module"

    def send(self, request_data):
        """
        Send an email.
        
        Args:
            request_data (dict):
                - to (str, required): Recipient email.
                - subject (str, required): Email subject.
                - body (str, required): Email content.
                - body_type (str, optional): 'text' or 'html'.
                - cc (str, optional): Carbon copy.
                - bcc (str, optional): Blind carbon copy.
                - reply_to (str, optional).
        """
        return self.client.send(request_data)


class ConversationsInterface(ZoaBaseInterface):
    """
    Interface for WhatsApp Conversation operations.
    """
    def __init__(self, token=None):
        super().__init__(token)
        self.client = ZoaConversation(self.token)
        self.action_name = "conversations"

    def search(self, request_data):
        """
        Retrieve a WABA message by its wamid.
        
        Args:
            request_data (dict):
                - wamid (str, required): WhatsApp message ID.
                - company_id (str, required): Company identifier.
        """
        return self.client.search(request_data)

    def send(self, request_data):
        """
        Send a WhatsApp message.
        
        Args:
            request_data (dict):
                - type (str, required): 'text', 'template', or 'buttons_text'.
                
                For 'text':
                - text (str): Message content.
                - to/phone (str): Recipient phone.
                
                For 'template':
                - template_name (str): Name of the template.
                - to/phone (str): Recipient phone.
                - data (dict): Template parameters (body, header, etc.).
                
                For 'buttons_text':
                - text (str): Body text.
                - bt1, bt2, bt3 (str): Button labels.
        """
        return self.client.send(request_data)

    def assign(self, request_data):
        """
        Assign a conversation to an agent.
        
        Args:
            request_data (dict):
                - conversation_id (str, optional): ID.
                - phone (str, optional): Customer phone (to resolve ID).
                - manager_name (str, required): Name of agent to assign.
        """
        return self.client.assign(request_data)

    def status(self, request_data):
        """
        Update conversation status.
        
        Args:
            request_data (dict):
                - conversation_id (str, optional): ID.
                - phone (str, optional): Customer phone.
                - sales_status (str, required): New status (e.g. 'pending', 'solved').
        """
        return self.client.status(request_data)

    def assign_status(self, request_data):
        """
        Combined Assign + Status update.
        
        Args:
            request_data (dict):
                Same as assign() and status() combined.
        """
        return self.client.assign_status(request_data)


class NotesInterface(ZoaBaseInterface):
    """
    Interface for Note management operations.
    """
    def __init__(self, token=None):
        super().__init__(token)
        self.client = ZoaNote(self.token)
        self.action_name = "notes"

    def search(self, request_data):
        """
        Get notes for a contact.
        
        Args:
            request_data (dict):
                Contact identification:
                - phone, mobile, email, nif, name.
        """
        return self.client.search(request_data)

    def create(self, request_data):
        """
        Create a note.
        
        Args:
            request_data (dict):
                - content (str, required): Note text.
                - manager_name (str, optional): Author name.
                - is_pinned (bool, optional).
                - date (str, optional).
                
                Contact identification:
                - phone, mobile, email, nif, name.
        """
        return self.client.create(request_data)

    def update(self, request_data):
        """
        Update a note.
        
        Args:
            request_data (dict):
                - date (str, required): Date of note to find.
                - old_content (str, optional): To refine search.
                - new_content (str, optional): New text.
                - is_pinned (bool, optional).
                
                Contact identification required.
        """
        return self.client.update(request_data)


class SchedulerInterface(ZoaBaseInterface):
    """
    Interface for Scheduler configuration operations.
    """
    def __init__(self, token=None):
        super().__init__(token)
        self.client = ZoaScheduler(self.token)
        self.action_name = "scheduler"

    def search(self, request_data):
        """
        Get scheduler config.
        
        Args:
            request_data (dict):
                - company_id (str, required): Inherited from execute().
        """
        return self.client.search(request_data)


class AIChatInterface(ZoaBaseInterface):
    """
    Interface for AI Chat Assistant operations.
    """
    def __init__(self, token=None):
        super().__init__(token)
        self.client = ZoaAIChat(self.token)
        self.action_name = "ai_chat"

    def send(self, request_data):
        """
        Send a message to the AI chat assistant.
        
        Args:
            request_data (dict):
                - user_id (str, required): The user ID for the chat session.
                - body (dict, required): The message body. Must be a dict with 'data' key.
                  Format: {"data": "your message text"}
                - body_type (str, optional): Type of body content (default: 'text').
        """
        return self.client.send(request_data)


class InsuranceAgentInterface(ZoaBaseInterface):
    """
    Interface for the Insurance Tarification Agent.

    Receives buffered call transcription messages and automatically classifies
    them as relevant/irrelevant. For relevant messages, extracts insurance data
    and creates or updates tarification sheets (auto_sheet / home_sheet) via
    the AI Chat API.
    """
    def __init__(self, token=None):
        super().__init__(token)
        self.client = ZoaInsuranceAgent(self.token)
        self.action_name = "insurance_agent"

    def process(self, request_data):
        """
        Process a buffered transcription message through the insurance agent pipeline.

        Pipeline: classify (relevant/irrelevant) → extract data → create/update sheet.

        Args:
            request_data (dict):
                - user_id (str, required): User ID for the AI chat session.
                - call_id (str, required): Identifier of the active call.
                - message (str, required): Buffered/concatenated transcription text.
                - memory (dict, optional): Current tarification state. Pass empty dict
                  or null for a new session. The response includes an updated memory
                  that should be passed back in subsequent calls.

        Returns:
            dict with:
                - status: "created" | "updated" | "waiting" | "irrelevant"
                - ramo: "AUTO" | "HOGAR" | null
                - memory: Updated tarification state (pass back in next call).
                - datos_detectados: List of fields extracted in this call.
                - pendientes: List of required fields still missing.
                - api_response: Response from the AI Chat API (only on create/update).
        """
        return self.client.process(request_data)


# Usage example
if __name__ == "__main__":
    # Example: Search for a contact
    # company_id and option must be provided
    interface = ContactsInterface()
    result, status = interface.execute(
        company_id="123", 
        option="search", 
        request_data={"phone": "123456789"}
    )
