"""
E-Commerce Shopfront - Comprehensive Tech Demo

A complete end-to-end test of the hierarchical agent system.

This is a REAL project specification that will test:
- Phase 5: Business Analyst requirements refinement
- Phase 4C: Design exploration at all levels
- Phase 4B: Code context during generation
- Phase 6: Automatic linting and quality
- Phase 3: Review loops for quality
- Full pipeline from requirements to working code

Project: Simple Online Store
- Backend: Python FastAPI
- Products: Catalog with search
- Cart: Session-based shopping cart
- Payment: PayPal integration (stubbed)
- Auth: Basic user authentication
- Database: SQLite (simple)
"""

SHOPFRONT_SPECIFICATION = """
# Simple E-Commerce Shopfront

## Overview
Build a simple online store with product catalog, shopping cart, and PayPal payment integration (stubbed for demo).

## Requirements

### 1. Product Catalog
- Display list of products with:
  * Product name
  * Description
  * Price
  * Stock quantity
  * Image URL
- Search products by name
- Filter products by price range
- Sort products by price/name

### 2. Shopping Cart
- Add products to cart
- Update quantities
- Remove products
- View cart total
- Session-based (no login required for cart)

### 3. User Authentication
- User registration (email + password)
- User login/logout
- Password hashing (bcrypt)
- Session management
- Protected routes for checkout

### 4. Checkout & Payment
- Review order summary
- Enter shipping address
- PayPal integration (STUBBED - no real payments)
  * Generate PayPal order
  * Mock approval flow
  * Capture payment (simulated)
- Create order record
- Email confirmation (stubbed)

### 5. Order Management
- View user's order history
- View order details
- Order status tracking (pending/paid/shipped/delivered)

## Technical Stack
- **Backend**: Python 3.12+ with FastAPI
- **Database**: SQLite (simple for demo)
- **ORM**: SQLAlchemy
- **Auth**: JWT tokens
- **Payment**: PayPal REST API (stubbed)
- **Frontend**: Simple HTML/CSS/JavaScript (stub)

## API Endpoints

### Products
- GET /api/products - List all products
- GET /api/products/{id} - Get product details
- GET /api/products/search?q={query} - Search products
- GET /api/products/filter?min={price}&max={price} - Filter by price

### Cart
- POST /api/cart/add - Add item to cart
- PUT /api/cart/update - Update item quantity
- DELETE /api/cart/remove/{product_id} - Remove item
- GET /api/cart - Get cart contents

### Auth
- POST /api/auth/register - Register new user
- POST /api/auth/login - Login user
- POST /api/auth/logout - Logout user
- GET /api/auth/me - Get current user

### Checkout
- POST /api/checkout/create-order - Create order from cart
- POST /api/checkout/paypal/create - Create PayPal order (stubbed)
- POST /api/checkout/paypal/capture - Capture PayPal payment (stubbed)

### Orders
- GET /api/orders - Get user's orders
- GET /api/orders/{id} - Get order details

## Database Models

### User
- id: integer (primary key)
- email: string (unique)
- password_hash: string
- name: string
- created_at: datetime

### Product
- id: integer (primary key)
- name: string
- description: text
- price: decimal
- stock: integer
- image_url: string
- created_at: datetime

### Order
- id: integer (primary key)
- user_id: integer (foreign key)
- total: decimal
- status: string (pending/paid/shipped/delivered)
- shipping_address: text
- paypal_order_id: string (stubbed)
- created_at: datetime

### OrderItem
- id: integer (primary key)
- order_id: integer (foreign key)
- product_id: integer (foreign key)
- quantity: integer
- price: decimal

## Success Criteria
1. All API endpoints return proper responses
2. Authentication works correctly
3. Cart operations function properly
4. PayPal flow completes (stubbed)
5. Orders are created and stored
6. Code is linted and type-safe (Python 3.12+)
7. All code has proper error handling
8. Database schema is correct

## Non-Functional Requirements
- Type hints on all functions
- Docstrings on all public methods
- Proper error handling
- Input validation
- Security (password hashing, SQL injection prevention)
- Clean code (passes ruff linting)

## Out of Scope (For This Demo)
- Real PayPal integration (use stubs)
- Email sending (use stubs)
- Complex frontend (just provide API)
- Admin panel
- Product reviews
- Inventory management beyond stock count
"""


def get_shopfront_request():
    """Get the user request for the shopfront demo"""
    return """Create a simple e-commerce shopfront with the following features:

1. Product catalog with search and filtering
2. Shopping cart functionality
3. User authentication and registration
4. Checkout flow with PayPal integration (stubbed - no real payments)
5. Order history for users

Technical requirements:
- Python 3.12+ with FastAPI
- SQLite database with SQLAlchemy ORM
- JWT authentication
- RESTful API design
- Type hints and docstrings
- Proper error handling

The system should be production-ready with:
- Secure password hashing
- Input validation
- SQL injection prevention
- Clean, linted code

This is a demo, so PayPal and email can be stubbed.
"""


if __name__ == "__main__":
    print("="*80)
    print("SHOPFRONT DEMO SPECIFICATION")
    print("="*80)
    print(SHOPFRONT_SPECIFICATION)
    print("\n" + "="*80)
    print("USER REQUEST")
    print("="*80)
    print(get_shopfront_request())
