# Lovable Integration Guide

This document outlines how to continue STBF development in Lovable.

## Project Overview for Lovable

**STBF** is a FastAPI-based resale automation platform with the following architecture:

### Backend (FastAPI)
- **main.py**: Primary application server with all API endpoints
- **ebay_service.py**: eBay Inventory API integration
- **ai_service.py**: Claude Vision API for photo analysis and content generation
- **database.py**: SQLite database models and operations
- **config.py**: Configuration and credential management

### Frontend (Vanilla JS)
- **templates/**: HTML templates with embedded JavaScript
- **static/**: CSS, JavaScript, and image assets
- Mobile-first responsive design
- No build system required

## Key Features to Maintain

1. **Mobile Photo Upload**: Drag-drop and camera capture
2. **AI Photo Grouping**: Claude Vision API integration
3. **eBay Publishing**: Direct API integration with listing creation
4. **Price Intelligence**: Comparable sales analysis
5. **Inventory Management**: SQLite-based item tracking

## Environment Variables Needed

```env
# eBay API (required for publishing)
EBAY_CLIENT_ID=your_ebay_client_id
EBAY_CLIENT_SECRET=your_ebay_client_secret
EBAY_REDIRECT_URI=your_redirect_uri

# Anthropic (required for AI features)
ANTHROPIC_API_KEY=your_anthropic_api_key

# Database
DATABASE_URL=sqlite:///./stbf.db
```

## API Endpoints

### Core Endpoints
- `GET /`: Main application interface
- `POST /upload`: Photo upload handling
- `POST /group-photos`: AI-powered photo grouping
- `GET /items/{item_id}`: Item details
- `POST /items/{item_id}/publish`: eBay publishing
- `GET /api/sold-listings`: Price comparison data

### Authentication
- eBay OAuth flow endpoints for seller authorization
- Credential management for API access tokens

## Dependencies

All Python dependencies are listed in `requirements.txt`:
- FastAPI + Uvicorn (web framework)
- httpx (HTTP client for API calls)  
- Pillow (image processing)
- aiofiles (async file handling)
- Jinja2 (HTML templating)

## Database Schema

SQLite database with core tables:
- **items**: Product information and metadata
- **photos**: Image data and grouping associations  
- **listings**: Published listing tracking
- **business_policies**: eBay policy configurations

## Development Setup

1. Install Python dependencies: `pip install -r requirements.txt`
2. Configure environment variables
3. Run with: `uvicorn main:app --reload --port 8000`

## Mobile Considerations

The app is specifically designed for mobile-first usage:
- Touch-optimized UI components
- Camera integration for photo capture
- Responsive grid layouts for photo organization
- Swipe gestures for item review

## Success Metrics

The system has successfully published live eBay listings:
- **Proof of Concept**: Bugle Boy Vintage Blue Knit Turtleneck Sweater
- **eBay Listing ID**: 267571796008
- Complete workflow from photo upload to live listing

## Next Development Priorities

1. **UI/UX Improvements**: Enhanced mobile interface
2. **Batch Processing**: Multiple item handling
3. **Analytics Dashboard**: Sales and performance tracking  
4. **Multi-Platform Publishing**: Enhanced Poshmark integration
5. **Inventory Management**: Stock tracking and reorder alerts

## Technical Debt & Opportunities

- **Authentication**: Implement proper user management
- **Error Handling**: Enhanced error recovery and user feedback
- **Testing**: Unit and integration test coverage
- **Documentation**: API documentation with OpenAPI/Swagger
- **Performance**: Image optimization and caching strategies

## Lovable-Specific Notes

- The vanilla JS approach makes it easy to iterate in Lovable
- No complex build pipeline to maintain
- Clear API boundaries for frontend/backend separation
- SQLite can be easily migrated to cloud database when ready
- Mobile-first design aligns with modern development practices

---

This codebase is production-ready and actively generates revenue through automated eBay listings.