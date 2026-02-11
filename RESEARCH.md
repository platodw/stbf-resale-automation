# STBF Resale Clothing Business Automation Research

**Business Context**: Something to be Found (STBF) operated by Katie Plato
- Volume: ~5 items/day, all clothing types
- Current Platforms: eBay and Poshmark  
- Listing Type: Buy It Now + Best Offer (no auctions)
- Photo Source: iPhone photos stored in Google Photos

---

## 1. eBay Seller API

### API Options for Creating Listings

**eBay Inventory API** (Recommended)
- Modern REST-based API designed for inventory management
- Key entities: Location → Inventory Item → Offer → Published Listing
- Process flow:
  1. Create/configure inventory location (warehouse/store)
  2. Create inventory item record (product details, condition, quantity, SKU)
  3. Create offer (associates item with marketplace, category, price, policies)
  4. Publish offer to create live eBay listing

**Key Requirements:**
- Seller must be opted into Business Policies (payment, fulfillment, return policies)
- Each inventory item needs unique seller-defined SKU
- Each offer references business policies and category ID
- Listings created via API can only be edited through API (not Seller Hub)

**eBay Trading API** (Legacy)
- SOAP-based legacy API, still functional but less preferred
- More complex integration compared to REST-based Inventory API

### Authentication Requirements

**OAuth 2.0 Implementation:**
- Must have eBay Developers Program account
- Client credentials flow for app-level access
- Authorization code flow for user-level access (required for seller operations)
- Access tokens required for all API requests

**Required Steps:**
1. Register application in eBay Developer Program
2. Obtain client ID and client secret
3. Implement OAuth flows to get access tokens
4. Include tokens in API request headers

### Searching Completed/Sold Listings for Pricing Comps

**eBay Browse API** (Current)
- Modern REST API for searching active listings
- **Limitation**: Does not provide access to completed/sold listing data
- Only returns active listings (Buy It Now items)
- Provides filtering by category, condition, price range, etc.

**eBay Finding API** (Legacy - Being Deprecated)
- Previously offered `findCompletedItems` call for sold listing data
- API documentation redirects suggest this is being phased out
- Historical sold data access appears to be restricted

**eBay Research Tools (Terapeak Integration):**
- **Product Research**: Free tool available in Seller Hub for all sellers
- Provides access to "real-world sales data for millions of items"
- Shows recent marketplace price trends and performance data
- Includes competitor analysis and pricing optimization suggestions
- **Sourcing Insights**: Available for sellers with Basic+ Store subscriptions
- Identifies high-demand/low-supply categories and seasonal trends

**API Alternative Solutions:**
- **eBay Seller Hub automation**: Browser automation to access Product Research tool
  - Login to Seller Hub programmatically
  - Search for comparable items in Product Research
  - Extract pricing and sales data from results
  - Lower risk than general web scraping (using legitimate seller tools)
- **Third-party services**: WorthPoint, PriceCharting for specific categories
- **Manual integration**: Export CSV data from Seller Hub research tools for analysis

---

## 2. Poshmark Automation

### No Public API Available
Poshmark does not offer a public API for listing creation or management.

### robots.txt Analysis
Poshmark explicitly blocks automation on key endpoints:
```
Disallow: /create-listing
Disallow: /edit-listing/*
Disallow: /api
```

### Browser Automation Options

**Selenium/Puppeteer Approaches:**
- **Selenium WebDriver**: Cross-browser automation, more stable
- **Puppeteer**: Chrome-specific, faster, more modern API
- **Playwright**: Multi-browser support, modern alternative to Selenium

**Implementation Considerations:**
- Need to handle login flow (email/password or OAuth)
- Parse and automate listing form fields
- Handle image uploads from local files
- Manage session persistence and rate limiting

### Known Tools/Services
- **Third-party services**: Some services like "PosherVA" exist but may violate TOS
- **Browser extensions**: Limited functionality, mainly for sharing/bumping
- **Desktop applications**: Often use web scraping techniques

### Account Suspension Risks

**High Risk Factors:**
- Poshmark actively monitors for automated behavior
- Terms of Service explicitly prohibit automated tools
- Pattern detection: Rapid listing creation, identical timing patterns
- IP-based detection for automated requests

**Risk Mitigation Strategies:**
- Human-like timing patterns (random delays, breaks)
- Rotate user agents and request patterns  
- Limit daily listing volume
- Use residential proxies if needed
- Consider running during business hours only

**Recommendation**: Poshmark automation carries significant account suspension risk. Consider manual listing or focus primarily on eBay for automated listings.

---

## 3. Google Photos API

### API Overview
Google Photos provides two main APIs:
- **Picker API**: Secure user selection of photos/videos for app use
- **Library API**: Upload, manage, and organize content in user's library

### Required Scopes for Accessing Photos

**For Reading Shared Albums:**
- `https://www.googleapis.com/auth/photoslibrary.readonly` - Read access to all media items and albums
- `https://www.googleapis.com/auth/photoslibrary.sharing` - Access to shared albums

**For Downloading/Managing:**
- `https://www.googleapis.com/auth/photoslibrary` - Full read/write access
- `https://www.googleapis.com/auth/photoslibrary.readonly.appcreateddata` - Read access to app-created content only

### Authentication Requirements
- **OAuth 2.0 required** (service accounts NOT supported)
- Must register application in Google Cloud Console
- Enable Google Photos API in console
- Obtain client ID and client secret
- Request user consent for specific scopes

### Integration with Existing Google OAuth
**Yes, can leverage existing setup:**
- If already using Google OAuth for Gmail/Calendar/Drive, can extend scopes
- Same OAuth 2.0 client credentials can be used
- Add Google Photos API scopes to existing consent flow
- Refresh tokens can be used for both services

### Implementation Steps
1. Add Google Photos API to existing Google Cloud project
2. Update OAuth consent screen with new scopes
3. Modify authentication flow to request additional scopes
4. Use existing refresh tokens to get access tokens with new scopes

---

## 4. AI Image Analysis for Clothing

### General Approach for Clothing Analysis

**Current Vision AI Capabilities:**
- **GPT-4 Vision (GPT-4V)**: Excellent for general image analysis, brand recognition, condition assessment
- **Claude Vision**: Strong analytical capabilities, detailed descriptions, good for brand/text reading
- **Google Vision AI**: Specialized features like text detection, logo recognition
- **Google Vision API**: Label detection, logo recognition, text detection (OCR)
**Custom Models**: Fashion-specific models exist but may be overkill for this use case

### Specific Analysis Requirements

**Brand Detection:**
- **From tags/labels**: OCR-based text extraction from care labels, brand tags
- **Visual brand recognition**: Logo detection and matching
- **Combined approach**: Use general vision AI to locate and read text in images

**Item Classification:**
- **Clothing type**: Dress, shirt, pants, shoes, accessories
- **Style categories**: Casual, formal, athletic, vintage
- **Subcategories**: T-shirt vs. blouse, sneakers vs. dress shoes

**Physical Attributes:**
- **Size detection**: Read size tags when visible in photos
- **Color analysis**: Primary and secondary colors, patterns
- **Material identification**: Cotton, polyester, denim, leather (from visual cues)

**Condition Assessment:**
- **Wear patterns**: Fading, pilling, stretching
- **Damage detection**: Stains, tears, missing buttons
- **Overall condition rating**: New, excellent, good, fair, poor

### Recommended Implementation

**GPT-4 Vision or Claude Vision** are sufficient for most needs:
- Cost-effective compared to specialized models
- Excellent text reading capabilities for brand/size detection
- Strong analytical abilities for condition assessment
- Can provide structured responses in JSON format

**Prompt Engineering Strategy:**
```
Analyze this clothing item photo and provide:
1. Brand (read any visible labels/tags)
2. Item type and category
3. Size (if visible on tags)
4. Primary colors and patterns
5. Condition assessment (rate 1-10 with explanation)
6. Notable features or defects
7. Estimated retail category (designer, mid-range, fast fashion)
```

**Multi-Service Approach (Recommended):**
1. **Google Vision API**: Fast label detection and OCR for tags/brands
2. **GPT-4V/Claude Vision**: Detailed condition analysis and styling descriptions  
3. **Hybrid processing**: Combine structured data from Google Vision with narrative analysis from conversational AI

**Enhanced Workflow:**
1. Process images through Google Vision API for quick categorization and text extraction
2. Use GPT-4V/Claude for detailed condition assessment and brand verification
3. Cross-reference detected brands with database for category/pricing guidance
4. Generate structured product data combining all AI outputs
5. Manual review for final listing optimization

---

## 5. eBay Listing Best Practices

### Title Optimization

**Key Principles:**
- Use all 80 characters available
- Include brand, size, color, style, condition
- Front-load most important keywords
- Avoid special characters and excessive capitalization
- Include relevant style descriptors (vintage, boho, preppy, etc.)

**Example Format:**
`[BRAND] [SIZE] [COLOR] [ITEM TYPE] [STYLE/CONDITION] [KEY FEATURES]`
`LULULEMON Size 8 Black Align Leggings High-Waisted 25" Excellent Condition`

**Research Tools:**
- eBay's search suggestions for popular keywords
- Competitor title analysis for similar items
- Category-specific keyword research

### Description Format

**Structured Template:**
1. **Opening Hook**: Brief compelling description
2. **Brand and Details**: Size, material, care instructions
3. **Condition Statement**: Honest assessment with specifics
4. **Measurements**: Chest, waist, length, inseam as relevant
5. **Styling Suggestions**: How to wear, occasions
6. **Policies**: Return policy, shipping timeline
7. **Call to Action**: Encourage offers, bundle deals

**Key Elements:**
- Use HTML formatting for readability
- Include specific measurements (not just tagged size)
- Be honest about condition and flaws
- Add care instructions and material details
- Include relevant lifestyle/styling context

### Category Selection

**Importance:**
- Affects search visibility and suggested pricing
- Determines available item specifics
- Influences buyer browsing behavior

**Best Practices:**
- Use most specific category available
- Leverage eBay's category suggestions API
- Research competitor listings in same category
- Consider seasonal category adjustments

### Pricing Strategy for Buy It Now + Best Offer

**Research Process:**
1. **Sold Comps Analysis**: Use eBay Product Research tool in Seller Hub (free access to sales data)
2. **Active Listing Survey**: Check current competition via Browse API or manual research
3. **Brand/Condition Adjustment**: Premium for better condition/desirable brands  
4. **Seasonal Factors**: Use Sourcing Insights for seasonal trend data
5. **Automated Integration**: Consider browser automation to extract Seller Hub research data

**Pricing Formula:**
- **List Price**: 25-40% above target selling price
- **Auto-Accept**: 15-25% above target (for quick sales)
- **Auto-Decline**: Below minimum acceptable price
- **Target Range**: Based on comps with condition/brand adjustments

**Implementation Strategy:**
- Start with higher BIN price to gauge interest
- Use "watchers" as demand indicator
- Adjust pricing weekly based on engagement
- Consider promoted listings for competitive items

**Best Offer Settings:**
- Enable auto-accept at reasonable threshold
- Set auto-decline to avoid lowball offers
- Respond to mid-range offers within 24 hours
- Counter-offer with slight discount to encourage acceptance

---

## Implementation Recommendations

### Phase 1: Foundation (Weeks 1-2)
1. **Set up eBay Developer Account** and implement OAuth authentication
2. **Extend Google OAuth** to include Google Photos API scopes
3. **Create basic image analysis workflow** using GPT-4V or Claude Vision
4. **Develop eBay listing creation** via Inventory API

### Phase 2: Automation Pipeline (Weeks 3-4)
1. **Build Google Photos integration** to fetch and download product images
2. **Implement AI image analysis** for brand, condition, and categorization
3. **Create eBay listing templates** with optimized titles and descriptions
4. **Integrate eBay research tools** via Seller Hub automation for pricing data
5. **Build pricing algorithm** combining research data with brand/condition factors

### Phase 3: Poshmark Strategy (Weeks 5-6)
1. **Evaluate risk tolerance** for Poshmark automation
2. **If proceeding**: Implement careful browser automation with human-like patterns
3. **Alternative**: Focus on eBay optimization and manual Poshmark listings

### Phase 4: Optimization (Ongoing)
1. **A/B testing** of titles, descriptions, and pricing strategies
2. **Performance analytics** tracking conversion rates and profit margins
3. **Inventory management** integration with existing business processes
4. **Scaling considerations** for increased volume

### Technical Architecture Recommendations

**Backend Stack:**
- **Python**: Excellent library support for eBay API, Google APIs, image analysis
- **Node.js**: Good alternative with strong API integration capabilities
- **Database**: PostgreSQL for inventory tracking, sales history, analytics

**Key Libraries/Services:**
- **eBay SDK**: Official or community Python/Node.js SDK
- **Google Photos API Client**: Official Google client libraries
- **OpenAI API / Anthropic API**: For image analysis
- **Selenium/Playwright**: For Poshmark automation (if pursued)

**Infrastructure:**
- **Cloud hosting**: AWS/GCP/Azure for API integrations and image processing
- **Image storage**: Cloud storage for processed product images
- **Task queue**: For processing images and creating listings asynchronously
- **Monitoring**: Error tracking and API usage monitoring

### Risk Management

**API Rate Limits:**
- Implement proper rate limiting and queuing
- Monitor API usage quotas
- Build retry mechanisms with exponential backoff

**Account Security:**
- Store API credentials securely
- Implement proper OAuth token refresh
- Monitor for unusual account activity

**Business Continuity:**
- Manual fallback procedures
- Regular data backups
- Test recovery procedures

**Compliance:**
- Review platform Terms of Service regularly
- Maintain audit trail of automated actions
- Consider legal review of automation practices

### Cost Optimization Strategies

**API Usage Management:**
- **eBay APIs**: Most seller APIs are free, monitor rate limits carefully
- **Google Photos API**: Free tier sufficient for typical usage (~5 items/day)
- **Vision AI costs**: Google Vision ~$1-3/1000 images, GPT-4V ~$0.01/image
- **Combined approach**: Use cheaper Google Vision for initial processing, expensive models for detailed analysis only when needed

**Infrastructure Scaling:**
- Start with serverless functions (AWS Lambda, Google Cloud Functions)
- Scale to dedicated servers only if processing volume increases significantly
- Use image caching to avoid reprocessing

---

## Conclusion and Recommendations

### Immediate Priority: eBay Automation
- **Highest ROI**: eBay has robust APIs and seller tools for automation
- **Lower risk**: Official APIs reduce account suspension concerns  
- **Rich data access**: Seller Hub research tools provide comprehensive sold data

### Medium Priority: Google Photos Integration
- **Streamlined workflow**: Automatic photo retrieval from shared albums
- **Existing OAuth**: Can extend current Google integration
- **Quality improvement**: Automated image processing and optimization

### Lower Priority: Poshmark Automation
- **High risk/reward**: Potential for automation but significant suspension risk
- **Alternative approach**: Focus on eBay optimization, manual Poshmark posting
- **Future consideration**: Monitor for API availability or policy changes

### Recommended Implementation Sequence
1. **Month 1**: eBay API integration and basic listing automation
2. **Month 2**: Google Photos integration and AI image analysis
3. **Month 3**: eBay research tool integration for pricing optimization
4. **Month 4**: Performance analytics and listing optimization algorithms
5. **Month 5+**: Consider Poshmark automation if eBay automation proves successful

### Success Metrics
- **Time savings**: Reduce listing creation time from manual to 2-3 minutes per item
- **Price optimization**: Improve sell-through rates with data-driven pricing
- **Quality consistency**: Standardized descriptions and categorization
- **Scale potential**: Support for increased inventory volume as business grows

### Key Success Factors
- **Start simple**: Implement basic automation before advanced features
- **Data-driven decisions**: Use eBay's research tools for pricing and category insights
- **Quality over quantity**: Focus on optimizing conversion rates rather than just volume
- **Platform compliance**: Maintain good standing with automated activity patterns
- **Continuous monitoring**: Track performance metrics and adjust strategies accordingly

*This research provides a comprehensive roadmap for automating STBF's resale clothing business while managing platform-specific risks and technical constraints. The phased approach allows for learning and optimization at each stage, ensuring sustainable growth and profitability.*