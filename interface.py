from config import TOKEN

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

class ZoaBaseInterface:
    """Base class that handles common validation and dispatch logic."""
    
    def __init__(self, token=None):
        self.token = token or TOKEN
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
            else:
                return {"error": f"La opción '{option}' no es válida para la acción '{self.action_name}'"}, 400
                
        except AttributeError:
            return {"error": f"El método '{option}' no está implementado en el modelo de '{self.action_name}'"}, 400
        except Exception as e:
            return {"error": f"Error interno ejecutando '{self.action_name}/{option}': {str(e)}"}, 500


class ContactsInterface(ZoaBaseInterface):
    def __init__(self, token=None):
        super().__init__(token)
        self.client = ZoaContact(self.token)
        self.action_name = "contacts"

class UsersInterface(ZoaBaseInterface):
    def __init__(self, token=None):
        super().__init__(token)
        self.client = ZoaUser(self.token)
        self.action_name = "users"

class CardsInterface(ZoaBaseInterface):
    def __init__(self, token=None):
        super().__init__(token)
        self.client = ZoaCard(self.token)
        self.action_name = "cards"

class CardActionsInterface(ZoaBaseInterface):
    def __init__(self, token=None):
        super().__init__(token)
        self.client = ZoaCardAct(self.token)
        self.action_name = "cardact"

class ActivitiesInterface(ZoaBaseInterface):
    def __init__(self, token=None):
        super().__init__(token)
        self.client = ZoaActivity(self.token)
        self.action_name = "activities"

class DepartmentsInterface(ZoaBaseInterface):
    def __init__(self, token=None):
        super().__init__(token)
        self.client = ZoaDepartment(self.token)
        self.action_name = "departments"

class TagsInterface(ZoaBaseInterface):
    def __init__(self, token=None):
        super().__init__(token)
        self.client = ZoaTags(self.token)
        self.action_name = "tags"

class ReadAllInterface(ZoaBaseInterface):
    def __init__(self, token=None):
        super().__init__(token)
        self.client = ZoaReadAll(self.token)
        self.action_name = "readall"

class EmailInterface(ZoaBaseInterface):
    def __init__(self, token=None):
        super().__init__(token)
        self.client = ZoaEmail(self.token)
        self.action_name = "email_module"

class ConversationsInterface(ZoaBaseInterface):
    def __init__(self, token=None):
        super().__init__(token)
        self.client = ZoaConversation(self.token)
        self.action_name = "conversations"

class NotesInterface(ZoaBaseInterface):
    def __init__(self, token=None):
        super().__init__(token)
        self.client = ZoaNote(self.token)
        self.action_name = "notes"

class SchedulerInterface(ZoaBaseInterface):
    def __init__(self, token=None):
        super().__init__(token)
        self.client = ZoaScheduler(self.token)
        self.action_name = "scheduler"

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
    print(f"Status: {status}")
    print(f"Result: {result}")
