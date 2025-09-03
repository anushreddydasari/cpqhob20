# Deal Pages Files

This folder contains all the HTML templates and JavaScript files related to HubSpot deal management and integration.

## Files:

### 1. `hubspot-deals.html`
- **Purpose**: Main HubSpot deals management interface
- **Route**: `/hubspot-deals`
- **Features**: 
  - View HubSpot deals
  - Deal management interface
  - Integration with HubSpot API

### 2. `hubspot-cpq-setup.html`
- **Purpose**: HubSpot CPQ setup and configuration page
- **Route**: `/hubspot-cpq-setup`
- **Features**:
  - CPQ setup configuration
  - HubSpot integration settings
  - Setup wizard interface

### 3. `hubspot-data.html`
- **Purpose**: HubSpot data visualization and management
- **Route**: `/hubspot-data`
- **Features**:
  - Data visualization
  - HubSpot data management
  - Data export/import functionality

### 4. `hubspot_deal_integration.js`
- **Purpose**: JavaScript file for HubSpot deal integration
- **Features**:
  - Deal API integration
  - Real-time deal updates
  - JavaScript utilities for deal management

## Integration:

All files are integrated with the main Flask application (`app.py`) and use:
- HubSpot API integration
- MongoDB for data storage
- JavaScript for frontend functionality
- Flask routes for serving pages

## Dependencies:

- HubSpot API
- JavaScript (for frontend functionality)
- Flask (for routing)
- MongoDB (for data storage)
- HubSpot SDK (for API integration)

## Workflow:

1. **Setup**: `hubspot-cpq-setup.html` → Configure HubSpot CPQ integration
2. **Data Management**: `hubspot-data.html` → Manage HubSpot data
3. **Deal Management**: `hubspot-deals.html` → View and manage deals
4. **Integration**: `hubspot_deal_integration.js` → Handle deal API operations

## API Endpoints:

- `/api/hubspot/deals` - Deal management API
- `/api/hubspot/sync` - Data synchronization
- `/api/hubspot/config` - Configuration management
