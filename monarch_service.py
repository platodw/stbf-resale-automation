"""
Monarch Money service for fetching financial data via browser relay
Due to Cloudflare blocking direct API calls from WSL, we need to use browser automation
"""
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

async def get_stbf_financial_data():
    """
    Get STBF financial data from Monarch Money
    Returns data for week, month, and YTD comparison
    """
    try:
        # Use browser automation to get data from Monarch
        data = await fetch_monarch_data_via_browser()
        return process_financial_data(data)
    except Exception as e:
        print(f"Error fetching Monarch data: {e}")
        # Return mock data for now
        return get_mock_financial_data()

def process_financial_data(transactions):
    """Process raw transaction data into dashboard format"""
    now = datetime.now()
    
    # Calculate date ranges
    week_start = now - timedelta(days=now.weekday())
    month_start = now.replace(day=1)
    ytd_start = now.replace(month=1, day=1)
    ytd_prior_start = ytd_start.replace(year=ytd_start.year - 1)
    ytd_prior_end = ytd_prior_start.replace(month=now.month, day=now.day)
    
    # Filter transactions by categories and date ranges
    def filter_and_sum(transactions, categories, start_date, end_date=None):
        if end_date is None:
            end_date = now
        
        total = 0
        for txn in transactions:
            txn_date = datetime.fromisoformat(txn.get('date', '').replace('Z', '+00:00'))
            if (start_date <= txn_date <= end_date and 
                txn.get('category', '').lower() in [cat.lower() for cat in categories]):
                total += abs(txn.get('amount', 0))  # Use abs for positive values
        
        return total
    
    # Define categories (these should match Monarch Money categories)
    ebay_categories = ['eBay Income', 'ebay income']
    poshmark_categories = ['Poshmark Income', 'poshmark income'] 
    shipping_categories = ['Shipping Costs', 'shipping costs', 'postage', 'usps', 'fedex', 'ups']
    
    # Calculate week totals
    week_data = {
        'ebay': filter_and_sum(transactions, ebay_categories, week_start),
        'poshmark': filter_and_sum(transactions, poshmark_categories, week_start),
        'shipping': filter_and_sum(transactions, shipping_categories, week_start)
    }
    
    # Calculate month totals  
    month_data = {
        'ebay': filter_and_sum(transactions, ebay_categories, month_start),
        'poshmark': filter_and_sum(transactions, poshmark_categories, month_start),
        'shipping': filter_and_sum(transactions, shipping_categories, month_start)
    }
    
    # Calculate YTD totals
    ytd_current = {
        'ebay': filter_and_sum(transactions, ebay_categories, ytd_start),
        'poshmark': filter_and_sum(transactions, poshmark_categories, ytd_start),
        'shipping': filter_and_sum(transactions, shipping_categories, ytd_start)
    }
    
    ytd_prior = {
        'ebay': filter_and_sum(transactions, ebay_categories, ytd_prior_start, ytd_prior_end),
        'poshmark': filter_and_sum(transactions, poshmark_categories, ytd_prior_start, ytd_prior_end),
        'shipping': filter_and_sum(transactions, shipping_categories, ytd_prior_start, ytd_prior_end)
    }
    
    return {
        'week': week_data,
        'month': month_data,
        'ytd': {
            'current': ytd_current,
            'prior': ytd_prior
        }
    }

async def fetch_monarch_data_via_browser():
    """
    Use OpenClaw browser automation to fetch data from Monarch Money
    This bypasses Cloudflare blocking of direct API calls
    """
    # This is a placeholder - the actual implementation would use OpenClaw's browser tool
    # to navigate to Monarch Money and extract transaction data
    
    # For now, we'll need to integrate this with the OpenClaw browser control
    # via the parent OpenClaw session that spawned this app
    
    return []  # Empty for now - will be implemented with browser automation

def get_mock_financial_data():
    """Return mock data for testing"""
    return {
        'week': {
            'ebay': 125.50,
            'poshmark': 89.25,
            'shipping': 24.75
        },
        'month': {
            'ebay': 456.75,
            'poshmark': 312.50,
            'shipping': 87.25
        },
        'ytd': {
            'current': {
                'ebay': 1234.50,
                'poshmark': 876.25,
                'shipping': 298.75
            },
            'prior': {
                'ebay': 987.50,
                'poshmark': 654.25,
                'shipping': 234.50
            }
        }
    }

def load_monarch_credentials():
    """Load Monarch Money credentials"""
    creds_path = Path.home() / '.openclaw' / 'credentials' / 'monarch' / 'config.json'
    try:
        with open(creds_path) as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Monarch credentials not found at {creds_path}")
        return None