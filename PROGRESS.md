# Honey Shop - Project Progress

Last updated: 2026-11-23
Last confirmed commit: 3a69f67 (138 tests passing)

## 1. Goal

A professional website for selling natural honey, in Persian and English.

1. Online sales: products, cart, orders, online payment through a reputable
   gateway, and order management for the administrator.
2. Brand and product presentation: a page per product (description, images,
   honey specifications), brand and company history, benefits of the products,
   educational articles, and customer reviews.

Client requirements: login by phone number with SMS code, SMS notifications,
Persian and English with careful RTL layout, images, an easy admin, fully
responsive, dark mode. The business, brand and products are already registered.
Customers are in Iran. Expected size: 30-200 products, many orders per day.

## 2. How to work on this project (rules from the owner)

- Explain the reasoning (why, basis, expected result) BEFORE proposing or taking
  any action.
- Do not write or change files or run code without discussion and approval.
  Routine research and installing dependencies are fine.
- The owner runs all commands on their own machine and pastes the output back.
- Use current, up-to-date knowledge. Ask before pinning a specific old version.
- The owner's first language is Persian. Use simple English. If something is
  unclear, ask instead of guessing.
- Small commits, one logical change each, format "type: short description" in
  the imperative (feat, fix, chore, build, docs, test, refactor).
- Never commit secrets. .env is ignored by Git.
- Tests are part of every change. If a test fails, do not commit; send the
  exact output.

## 3. Environment

- Ubuntu 26.04, Python 3.14, PostgreSQL 18 (port 5432), project in
  ~/projects/honey-shop, virtual environment in .venv.
- PostgreSQL once stopped by itself. Fix: sudo systemctl start postgresql
- Run: source .venv/bin/activate, then python manage.py runserver
- Test: python manage.py test
- Database user: honey_user, database: honey_shop (password only in .env).
- An old PostgreSQL 16 cluster (port 5433) exists and is unused. Leave it.

## 4. Stack and versions

| Part | Choice |
|---|---|
| Framework | Django 5.2 LTS (>=5.2,<5.3). Upgrade to 6.2 LTS after its release in April 2027 |
| Database | PostgreSQL 18 with psycopg[binary] |
| Settings | django-environ, values in .env (see .env.example) |
| Images | Pillow >=13.0,<14 (security fixes in 13.0.0; keep it updated) |
| Frontend | Plain CSS, small JavaScript, Django templates. No Node, no Tailwind |
| Font | Vazirmatn variable font, self-hosted (static/fonts) |

## 5. Key decisions

| Decision | Reason |
|---|---|
| Custom Django site, not a ready platform | Full control of Persian layout and Iranian payments |
| Django 5.2 LTS first, 6.2 LTS later | 6.2 does not exist before April 2027. No site avoids security patches |
| Language in the URL (/fa/, /en/), Persian default | Stable pages, good for Google, shareable links |
| "/" goes to the language cookie, else Persian | New visitors always get Persian, whatever the browser says |
| Plain CSS with CSS variables and logical properties | No build tool; one stylesheet works in both directions |
| Dark mode: system, light, dark; choice saved in the browser | data-theme attribute on the html element |
| Phone login with one-time SMS code | Client requirement; customers have no password |
| OTP: 6 digits, 2 minutes, 5 attempts, HMAC hash, cooldown 60 s, 5 per hour per phone, 20 per hour per IP | Security and SMS cost control |
| SMS behind a backend interface (console, memory, real provider later) | Provider not chosen yet; console backend refuses to run when DEBUG is off |
| Own code for login, not a ready package | Packages found were tied to REST/JWT; security code should be small and tested |
| Explicit name_fa and name_en fields with a translated() property | No translation package; falls back to the other language when empty |
| Prices stored in Rial, shown in Toman | Gateways use Rial; one formatter for the whole site |
| Prices must be whole Toman (multiple of 10 Rial) | The page must never show a different amount than is charged. Enforced in form and database |
| Variants (sizes) are what customers buy | Each size has its own SKU, price, old price, stock |
| Products are deactivated, not deleted | Order history stays intact |
| Descriptions are plain text, escaped | No HTML from the database reaches pages |
| Images: only JPEG, PNG, WebP, max 10 MB and 25 megapixels, resized to WebP 480/960/1600, EXIF/GPS removed, random names | Security, speed, privacy |
| FileField with own validator, not ImageField | Only our code opens uploaded images, with formats restricted |
| Search understands Arabic letters and Persian digits | Customers on Arabic keyboards would find nothing otherwise |
| Logout is POST only | A link could be triggered from another website |
| Font preload removed | Firefox warned it was unused; text shows at once with font-display: swap |

## 6. What is built (committed)

- accounts: custom User (phone is the login), OTPRequest, phone normalization
  (Persian digits, +98, spaces), forms, services (request_code, verify_code),
  login and verify pages, logout, admin with phone-based forms.
- notifications: SMS backend interface, console backend (development),
  memory backend (tests).
- common: translated() property, price and digit formatting (Toman, Persian
  digits), Persian text normalization.
- pages: home placeholder and the root redirect.
- templates and static: base layout with RTL/LTR, header (brand, login/logout,
  language switcher, theme button), footer, color tokens with dark mode,
  components stylesheet, theme.js, font.
- catalog: Category, Product, Variant, ProductImage, ProductSpec; image checks
  and resizing with file cleanup; admin with inlines, previews, stock warning,
  Toman column; whole-Toman price rule; visible() rules and Persian-aware
  search; helpers (from_variant, is_available, main_image, discount_percent).

## 7. Sent but not yet confirmed

- Fix: ignore NUL characters in product search (one line plus a test).
- Product list page: /products/ and /products/category/<slug>/, search,
  pagination (12 per page), product cards, query-count test. Files:
  catalog/urls.py, views.py, templatetags/catalog_extras.py, templates
  product_list.html, _product_card.html, _pagination.html, test_views.py,
  and new rules in static/css/components.css. Expected about 161 tests.

## 8. File structure

    honey-shop/
      manage.py
      requirements.txt            Django, psycopg, django-environ, Pillow
      README.md
      PROGRESS.md                 this file
      .env                        secrets (not in Git)   .env.example
      config/                     settings.py, urls.py, wsgi.py, asgi.py
      accounts/                   models.py (User, UserManager, OTPRequest)
                                  phone.py, forms.py, services.py, views.py,
                                  urls.py, admin.py, migrations/
                                  templates/accounts/ login, verify, _field
                                  tests: tests.py, test_phone.py,
                                  test_forms.py, test_services.py, test_views.py
      notifications/              backends.py, tests.py
      common/                     translated.py, formatting.py, text.py
                                  tests: test_translated.py,
                                  test_formatting.py, test_text.py
      pages/                      urls.py, views.py, tests.py, test_root.py
                                  templates/pages/home.html
      catalog/                    models.py, images.py, validators.py,
                                  admin.py, migrations/ (0001 to 0003)
                                  tests: tests.py, test_images.py,
                                  test_product_images.py, test_admin.py,
                                  test_queries.py
                                  (pending: urls.py, views.py, templatetags/,
                                  templates/catalog/, test_views.py)
      templates/                  base.html, partials/header.html, footer.html
      static/                     css/ fonts.css, tokens.css, base.css,
                                  components.css; js/theme.js;
                                  fonts/Vazirmatn-Variable.woff2
      media/                      uploaded images (not in Git)

## 9. URLs

    /                           redirect to /fa/ or /en/
    /i18n/setlang/              language switch (POST)
    /<lang>/                    home
    /<lang>/admin/              admin
    /<lang>/accounts/login/     phone login
    /<lang>/accounts/verify/    code entry
    /<lang>/accounts/logout/    logout (POST)
    /<lang>/products/           product list (pending)
    /<lang>/products/category/<slug>/   category (pending)

## 10. Remaining tasks (in order)

1. Confirm the NUL fix and the product list page.
2. Product detail page: gallery, sizes table with prices and stock, specification
   table, breadcrumbs, related products. Links from cards. "Products" link in
   the header.
3. Command that creates sample honey data for development.
4. Persian translation stage: makemigrations/makemessages with gettext, all
   texts, admin labels (for example "ACCOUNTS", "PHONE NUMBER"), Jalali dates.
5. Cart, checkout, orders (copy name and price at purchase time), shipping,
   stock reduced only after successful payment.
6. Payment gateway (Zarinpal or Zibal) with sandbox tests.
7. Real SMS provider and order notifications (templates are usually required).
8. Brand and history pages, benefits of products, educational articles
   (safe formatting), customer reviews with admin approval.
9. SEO (titles, descriptions, structured data, sitemap), favicon and logo.
10. Deployment: Nginx, HTTPS, Gunicorn, serving /media/ and /static/, backups,
    monitoring, DEBUG off, security headers.
11. Upgrade to Django 6.2 LTS after its release.

## 11. Before-launch checklist

- Client's brand name and logo (the title still says "Honey Shop").
- Real SMS backend; console backend must not be used (it refuses when DEBUG off).
- Client IP behind Nginx: configure carefully (the per-IP OTP limit depends on it).
- Serve /media/ from the web server; limit upload size there too.
- Add the Vazirmatn license file (Open Font License) next to the font.
- Command to remove orphan media files (rare leftovers after rolled-back saves).
- Merge the duplicated digit tables (accounts/phone.py and common/text.py).
- Check session and cookie security settings, ALLOWED_HOSTS, SECRET_KEY.
- Favicon (the browser asks for /favicon.ico).
- Decide how to show dates (Jalali calendar) in Persian.
- Run a dependency security check; keep Pillow updated.

## 12. Open questions for the client

- Brand name and logo.
- Honey types, sizes, packaging and prices.
- Are prices shown with VAT?
- How are orders shipped (post, courier, by city)?
- Which SMS provider?
- Current status of Iran's currency redenomination (prices live in one place).

## 13. Known notes

- Persian pages show English text until translations exist; punctuation at the
  start of English sentences in RTL pages is expected.
- A Chrome/Firefox console warning about the admin file RelatedObjectLookups.js
  comes from Django itself.
- Django admin dates are still Gregorian.
