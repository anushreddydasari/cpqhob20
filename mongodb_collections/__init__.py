# MongoDB Collections Package
# All MongoDB collection operations in one flat folder

from .email_collection import EmailCollection
from .smtp_collection import SMTPCollection
from .quote_collection import QuoteCollection
from .client_collection import ClientCollection
from .pricing_collection import PricingCollection
from .hubspot_contact_collection import HubSpotContactCollection
from .hubspot_integration_collection import HubSpotIntegrationCollection
from .form_tracking_collection import FormTrackingCollection
from .template_collection import TemplateCollection


__all__ = [
    'EmailCollection',
    'SMTPCollection', 
    'QuoteCollection',
    'ClientCollection',
    'PricingCollection',
    'HubSpotContactCollection',
    'HubSpotIntegrationCollection',
    'FormTrackingCollection',
    'TemplateCollection'
]
