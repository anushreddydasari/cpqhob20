// HubSpot Deal Integration JavaScript
// This code should be embedded in your HubSpot deal page

(function() {
    'use strict';
    
    // Function to get current deal data from HubSpot
    function getCurrentDealData() {
        // Get deal data from HubSpot page context
        // This will need to be customized based on your HubSpot setup
        
        // For now, we'll use a placeholder approach
        // You'll need to replace this with actual HubSpot data extraction
        
        const dealData = {
            dealId: window.hubspot?.deal?.id || getDealIdFromPage(),
            dealName: window.hubspot?.deal?.properties?.dealname || getDealNameFromPage(),
            amount: window.hubspot?.deal?.properties?.amount || getAmountFromPage(),
            closeDate: window.hubspot?.deal?.properties?.closedate || getCloseDateFromPage(),
            stage: window.hubspot?.deal?.properties?.dealstage || getStageFromPage(),
            ownerId: window.hubspot?.deal?.properties?.hubspot_owner_id || getOwnerIdFromPage(),
            company: window.hubspot?.deal?.properties?.company || getCompanyFromPage()
        };
        
        return dealData;
    }
    
    // Helper functions to extract deal data from page elements
    function getDealIdFromPage() {
        // Try to get deal ID from URL or page elements
        const urlParams = new URLSearchParams(window.location.search);
        return urlParams.get('dealId') || '';
    }
    
    function getDealNameFromPage() {
        // Look for deal name in page elements
        const dealNameElement = document.querySelector('[data-test-id="deal-name"]') || 
                               document.querySelector('.deal-name') ||
                               document.querySelector('h1');
        return dealNameElement ? dealNameElement.textContent.trim() : '';
    }
    
    function getAmountFromPage() {
        // Look for amount in page elements
        const amountElement = document.querySelector('[data-test-id="deal-amount"]') || 
                             document.querySelector('.deal-amount') ||
                             document.querySelector('.amount');
        return amountElement ? amountElement.textContent.trim() : '';
    }
    
    function getCloseDateFromPage() {
        // Look for close date in page elements
        const closeDateElement = document.querySelector('[data-test-id="deal-close-date"]') || 
                                document.querySelector('.deal-close-date') ||
                                document.querySelector('.close-date');
        return closeDateElement ? closeDateElement.textContent.trim() : '';
    }
    
    function getStageFromPage() {
        // Look for stage in page elements
        const stageElement = document.querySelector('[data-test-id="deal-stage"]') || 
                            document.querySelector('.deal-stage') ||
                            document.querySelector('.stage');
        return stageElement ? stageElement.textContent.trim() : '';
    }
    
    function getOwnerIdFromPage() {
        // Look for owner ID in page elements
        const ownerElement = document.querySelector('[data-test-id="deal-owner"]') || 
                            document.querySelector('.deal-owner') ||
                            document.querySelector('.owner');
        return ownerElement ? ownerElement.getAttribute('data-owner-id') || '' : '';
    }
    
    function getCompanyFromPage() {
        // Look for company in page elements
        const companyElement = document.querySelector('[data-test-id="deal-company"]') || 
                              document.querySelector('.deal-company') ||
                              document.querySelector('.company');
        return companyElement ? companyElement.textContent.trim() : '';
    }
    
    // Function to open CPQ tool with deal data
    function openCPQTool(dealData) {
        // Build URL with deal parameters
        const cpqUrl = new URL('https://your-cpq-website.com/hubspot-cpq-setup');
        
        // Add deal data as URL parameters
        Object.keys(dealData).forEach(key => {
            if (dealData[key]) {
                cpqUrl.searchParams.append(key, dealData[key]);
            }
        });
        
        // Open CPQ tool in new tab
        window.open(cpqUrl.toString(), '_blank');
    }
    
    // Function to update the "Open Anush's Tool" button
    function updateCPQButton() {
        // Find the CPQ tool button
        const cpqButton = document.querySelector('button[onclick*="Open Anush\'s Tool"]') ||
                         document.querySelector('button:contains("Open Anush\'s Tool")') ||
                         document.querySelector('[data-test-id="cpq-tool-button"]');
        
        if (cpqButton) {
            // Remove existing onclick and add new functionality
            cpqButton.removeAttribute('onclick');
            cpqButton.addEventListener('click', function(e) {
                e.preventDefault();
                
                // Get current deal data
                const dealData = getCurrentDealData();
                
                // Validate required data
                if (!dealData.dealId || !dealData.dealName) {
                    alert('Unable to get deal information. Please try refreshing the page.');
                    return;
                }
                
                // Open CPQ tool
                openCPQTool(dealData);
            });
            
            console.log('✅ CPQ Tool button updated successfully!');
        } else {
            console.log('⚠️ CPQ Tool button not found. You may need to customize the selector.');
        }
    }
    
    // Function to create a custom CPQ button if the original is not found
    function createCustomCPQButton() {
        // Look for a container to add the button
        const container = document.querySelector('.deal-actions') || 
                         document.querySelector('.deal-header') ||
                         document.querySelector('.deal-properties');
        
        if (container) {
            const customButton = document.createElement('button');
            customButton.textContent = '🚀 Open Anush\'s CPQ Tool';
            customButton.className = 'btn btn-primary';
            customButton.style.cssText = `
                background: #28a745;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                cursor: pointer;
                font-size: 14px;
                margin: 10px;
            `;
            
            customButton.addEventListener('click', function() {
                const dealData = getCurrentDealData();
                
                if (!dealData.dealId || !dealData.dealName) {
                    alert('Unable to get deal information. Please try refreshing the page.');
                    return;
                }
                
                openCPQTool(dealData);
            });
            
            container.appendChild(customButton);
            console.log('✅ Custom CPQ Tool button created!');
        }
    }
    
    // Initialize when page is ready
    function init() {
        console.log('🚀 Initializing HubSpot Deal Integration...');
        
        // Wait for page to be fully loaded
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', init);
            return;
        }
        
        // Try to update existing button first
        updateCPQButton();
        
        // If no button found, create a custom one
        setTimeout(() => {
            if (!document.querySelector('button[onclick*="Open Anush\'s Tool"]')) {
                createCustomCPQButton();
            }
        }, 2000);
        
        console.log('✅ HubSpot Deal Integration initialized!');
    }
    
    // Start initialization
    init();
    
    // Export functions for external use
    window.HubSpotDealIntegration = {
        getCurrentDealData: getCurrentDealData,
        openCPQTool: openCPQTool,
        updateCPQButton: updateCPQButton,
        createCustomCPQButton: createCustomCPQButton
    };
    
})();
