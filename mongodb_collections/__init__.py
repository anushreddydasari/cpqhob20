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
from .hubspot_quote_collection import HubSpotQuoteCollection
from .signature_collection import SignatureCollection
from .generated_pdf_collection import GeneratedPDFCollection
from .generated_agreement_collection import GeneratedAgreementCollection



__all__ = [
    'EmailCollection',
    'SMTPCollection', 
    'QuoteCollection',
    'ClientCollection',
    'PricingCollection',
    'HubSpotContactCollection',
    'HubSpotIntegrationCollection',
    'FormTrackingCollection',
    'TemplateCollection',
    'HubSpotQuoteCollection',
    'SignatureCollection',
    'GeneratedPDFCollection',
    'GeneratedAgreementCollection',

]
