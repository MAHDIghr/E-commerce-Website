Directory structure:
└── mahdighr-e-commerce-website/
    ├── manage.py
    ├── requirements.txt
    ├── .env.example
    ├── checkout/
    │   ├── __init__.py
    │   ├── admin.py
    │   ├── apps.py
    │   ├── models.py
    │   ├── tests.py
    │   ├── urls.py
    │   ├── views.py
    │   ├── migrations/
    │   │   └── __init__.py
    │   ├── static/
    │   │   ├── css/
    │   │   │   └── checkout.css
    │   │   └── js/
    │   │       └── checkout.js
    │   └── templates/
    │       └── checkout.html
    ├── config/
    │   ├── __init__.py
    │   ├── asgi.py
    │   ├── urls.py
    │   ├── wsgi.py
    │   └── settings/
    │       ├── __init__.py
    │       ├── base.py
    │       ├── development.py
    │       └── production.py
    ├── home/
    │   ├── __init__.py
    │   ├── admin.py
    │   ├── apps.py
    │   ├── models.py
    │   ├── tests.py
    │   ├── urls.py
    │   ├── views.py
    │   ├── migrations/
    │   │   └── __init__.py
    │   ├── static/
    │   │   ├── css/
    │   │   │   └── home.css
    │   │   └── js/
    │   │       └── home.js
    │   └── templates/
    │       └── home.html
    ├── product/
    │   ├── __init__.py
    │   ├── admin.py
    │   ├── apps.py
    │   ├── models.py
    │   ├── tests.py
    │   ├── urls.py
    │   ├── views.py
    │   ├── migrations/
    │   │   └── __init__.py
    │   ├── static/
    │   │   ├── css/
    │   │   │   └── product.css
    │   │   └── js/
    │   │       └── product.js
    │   └── templates/
    │       └── product.html
    ├── shop/
    │   ├── __init__.py
    │   ├── admin.py
    │   ├── apps.py
    │   ├── models.py
    │   ├── tests.py
    │   ├── urls.py
    │   ├── views.py
    │   ├── migrations/
    │   │   └── __init__.py
    │   ├── static/
    │   │   ├── css/
    │   │   │   └── shop.css
    │   │   └── js/
    │   │       └── shop.js
    │   └── templates/
    │       └── catalog.html
    ├── static/
    │   ├── css/
    │   │   └── base.css
    │   └── js/
    │       └── base.js
    └── templates/
        ├── base.html
        └── partials/
            ├── _cart_drawer.html
            ├── _footer.html
            ├── _header.html
            ├── _promo_bar.html
            └── _search_overlay.html
