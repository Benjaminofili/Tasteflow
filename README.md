# 🍽️ TasteFlow - Premium Food Ordering System

[![Python Support](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/Framework-Flask-red.svg)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**TasteFlow** is a state-of-the-art, full-stack food ordering and delivery platform designed for high performance and premium aesthetics. It bridges the gap between hungry customers, local restaurant owners, and system administrators through a seamless, role-based digital experience.

---

## 🚀 Key Features

### 👤 Customer Experience
-   **Dynamic Discovery**: Browse restaurants and dishes with category-based filtering.
-   **Seamless Checkout**: Integrated cart management and secure order processing.
-   **Live Tracking**: Real-time updates on order status (Pending → Preparing → Out for Delivery).
-   **Favorites & Wishlist**: Save your preferred dishes for quick access later.
-   **Personalized Profile**: Manage your addresses, order history, and account settings.

### 🏪 Restaurant Owner Dashboard
-   **Storefront Management**: Full control over restaurant details, logos, and contact info.
-   **Menu Engineering**: Add, edit, and categorize dishes with high-quality media integration.
-   **Order Fulfillment**: Real-time notifications and streamlined status management for incoming orders.
-   **Promotions**: Create and manage customizable discount coupons.

### 🛡️ Administrative Oversight
-   **Unified Control Panel**: Global management of users, categories, and food types.
-   **Audit Logs**: Comprehensive tracking of system activities for security and transparency.
-   **System Stability**: Built-in rate limiting and robust error handling.

---

## 🛠️ Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Backend** | Python 3.8+, Flask, SQLAlchemy (ORM) |
| **Frontend** | Vanilla JavaScript (ES6+), CSS3 (Modern Hooks), Jinja2 |
| **Database** | PostgreSQL (Production), SQLite (Development) |
| **Media** | Cloudinary API for high-performance image hosting |
| **Security** | Flask-WTF (CSRF), Bcrypt (Hashing), Flask-Limiter |

---

## 🔧 Getting Started

### Prerequisites
- Python 3.8 or higher
- `pip` (Python package manager)
- A Cloudinary account (for media storage)

### Installation

1.  **Clone the Repository**:
    ```bash
    git clone https://github.com/Benjaminofili/tasteflow.git
    cd tasteflow
    ```

2.  **Set Up Virtual Environment**:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment**:
    Create a `.env` file in the root directory and populate it:
    ```env
    SECRET_KEY=your_secure_random_string
    DATABASE_URL=sqlite:///instance/app.db
    CLOUDINARY_URL=cloudinary://api_key:api_secret@cloud_name
    MAIL_SERVER=smtp.gmail.com
    MAIL_PORT=587
    MAIL_USERNAME=your_email@gmail.com
    MAIL_PASSWORD=your_app_password
    ```

### Database Initialization & Seeding

```bash
# Initialize the database schema
python -m flask init-db

# (Optional) Seed the database with sample restaurants and dishes
python run_seeder.py
```

### Running the Application

```bash
python run.py
```
The application will be accessible at `http://127.0.0.1:5000`.

---

## 📂 Project Structure

```text
├── app/                  # Main application package
│   ├── routes/           # Blueprints (auth, customer, owner, admin)
│   ├── static/           # CSS, JS, and local assets
│   ├── templates/        # Jinja2 HTML templates
│   ├── models.py         # Database schema (SQLAlchemy)
│   └── utils.py          # Helper functions and business logic
├── docs/                 # Project documentation and reports
├── instance/             # Local database file (SQLite)
├── tests/                # Unit and integration tests
├── config.py             # Application configuration
└── run.py                # Entry point script
```

---

## 📸 Visual Overview

Detailed screenshots of the Customer Dashboard, Owner Panel, and Admin Interface are available in the [Project Report](docs/report/report.md#screen-shots).

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.