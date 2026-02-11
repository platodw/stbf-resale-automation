# STBF (Something to be Found) - Resale Listing Manager

**A mobile-first web application for automating eBay and resale platform listings.**

🎉 **Project Status**: Successfully deployed! First live listing published: *Bugle Boy Vintage Blue Knit Turtleneck Sweater* (eBay listing ID: 267571796008)

## Overview

STBF is a complete resale automation solution that streamlines the clothing resale process from photo upload to live marketplace listings. Originally built for Katie Plato's "Something to be Found" resale business, handling ~5 items/day across eBay and Poshmark.

### Key Features

- **📱 Mobile-First Design**: Optimized for smartphone photography workflow
- **🤖 AI-Powered Grouping**: Claude Vision API groups uploaded photos by clothing item
- **📝 Smart Descriptions**: AI generates compelling titles, descriptions, and pricing suggestions
- **🏷️ eBay Integration**: Direct publishing via eBay Inventory API
- **💰 Price Intelligence**: Market analysis with comparable sold listings
- **📊 Business Policy Management**: Integrated payment, shipping, and return policies

## Tech Stack

- **Backend**: FastAPI + SQLite
- **Frontend**: Vanilla HTML/CSS/JS (mobile-optimized)
- **AI**: Claude Vision API for photo analysis and content generation
- **Marketplace APIs**: eBay Inventory API (with Poshmark support)
- **Image Processing**: Pillow for photo optimization

## Quick Start

```bash
# Clone and setup
git clone [repo-url]
cd stbf
chmod +x start.sh
./start.sh
```

Open http://localhost:8000

## Configuration

### Required Credentials

1. **eBay API Access**:
   - Place `config.json` and `oauth_tokens.json` in `~/.openclaw/credentials/ebay/`
   - Requires eBay Developer Program account with OAuth 2.0 setup

2. **Anthropic API Key** (for AI features):
   - Place API key in `~/.openclaw/credentials/anthropic/api_key`
   - Without this, AI features are stubbed but core functionality works

### eBay Setup Requirements

- Seller must be opted into Business Policies
- Application registered in eBay Developers Program
- OAuth 2.0 authorization completed for seller account
- Inventory API access enabled

## Workflow

### 1. 📸 Upload Photos
- Batch drag-and-drop or direct camera capture
- Mobile-optimized interface for quick photo sessions
- Automatic image optimization and processing

### 2. 🔍 AI Grouping
- Claude Vision API analyzes uploaded photos
- Groups photos by individual clothing items
- Manual adjustment interface for edge cases

### 3. ✏️ Review & Edit
- AI generates draft listings with:
  - SEO-optimized titles
  - Detailed descriptions with measurements
  - Condition assessments
  - Competitive pricing suggestions
- Full editing interface for manual refinements

### 4. 🚀 Publish
- Direct publishing to eBay via Inventory API
- Creates inventory items, offers, and live listings
- Poshmark integration available
- Real-time status tracking

## Success Story

**First Production Listing**: Bugle Boy Vintage Blue Knit Turtleneck Sweater
- **eBay Listing ID**: 267571796008
- Successfully published using the automated workflow
- Demonstrates end-to-end functionality from photo upload to live listing

## API Integrations

### eBay Inventory API
- **Inventory Items**: Product catalog management
- **Offers**: Pricing and policy association
- **Publishing**: Live marketplace listing creation
- **Business Policies**: Automated policy application

### Anthropic Claude Vision
- **Photo Analysis**: Item identification and grouping
- **Content Generation**: Titles, descriptions, and features
- **Market Intelligence**: Pricing recommendations

## Development Features

- **Hot Reload**: Development server with automatic restart
- **SQLite Database**: Local data persistence
- **Static Asset Serving**: Integrated CSS/JS/image serving
- **Mobile Responsive**: Touch-optimized interface
- **Error Handling**: Comprehensive error reporting and recovery

## File Structure

```
stbf/
├── main.py                 # FastAPI application server
├── ebay_service.py         # eBay API integration
├── ai_service.py           # Claude Vision AI processing
├── database.py             # SQLite database models
├── config.py              # Configuration management
├── poshmark_service.py    # Poshmark integration
├── monarch_service.py     # Additional platform support
├── templates/             # HTML templates
├── static/               # CSS, JS, images
├── requirements.txt      # Python dependencies
├── start.sh             # Development startup script
└── README.md           # This file
```

## Business Context

Originally developed for Katie Plato's clothing resale business:
- **Volume**: ~5 items/day
- **Platforms**: eBay (primary) + Poshmark
- **Inventory**: Mixed clothing types and brands
- **Strategy**: Buy It Now + Best Offer (no auctions)
- **Photo Source**: iPhone with Google Photos storage

The system is designed to handle the complete workflow from sourcing through final sale, with particular attention to mobile usability and automation of repetitive tasks.

## Lovable Integration Notes

This project is optimized for continued development in Lovable:

- **Modern Stack**: FastAPI + vanilla JS (no complex build systems)
- **Clear Separation**: API backend with standard REST endpoints
- **Mobile-First**: Responsive design principles throughout
- **Well-Documented**: Comprehensive API and component documentation
- **Environment Ready**: Standard Python project structure

## License

Private project for STBF resale business operations.

---

*Built with ❤️ for efficient resale operations*