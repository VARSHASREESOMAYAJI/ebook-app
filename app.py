from flask import Flask, render_template, request, redirect, url_for, session
import os
import json
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv
from pymongo import MongoClient
import certifi

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "secret")

# === MongoDB Setup (optional if not using users anymore) ===
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client["ebook_app"]

# === Email Settings ===
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
OWNER_EMAIL = os.getenv("OWNER_EMAIL")

# === PDF Directory (inside /static) ===
PDF_DIR = os.path.join("static", "pdfs")

# === Email with PDF Attachment ===
def send_email_with_pdf(name, user_email, product):
    product_title = product['title']
    filename = product.get("file", None)
    pdf_path = os.path.join(PDF_DIR, filename) if filename else None

    owner_msg = EmailMessage()
    owner_msg['Subject'] = f'🛒 New Purchase: {product_title}'
    owner_msg['From'] = EMAIL_ADDRESS
    owner_msg['To'] = OWNER_EMAIL
    owner_msg.set_content(f"New purchase from {name} ({user_email}) for {product_title}")

    user_msg = EmailMessage()
    user_msg['Subject'] = f'✅ Your {product_title} eBook'
    user_msg['From'] = EMAIL_ADDRESS
    user_msg['To'] = user_email
    user_msg.set_content(f"""
Hi {name},

Thanks for purchasing **{product_title}**!

✅ Your eBook is attached with this email as a PDF.
If you face any issue, just reply to this email.

– Team VARSHA
    """)

    # Attach PDF
    if pdf_path and os.path.exists(pdf_path):
        with open(pdf_path, "rb") as f:
            user_msg.add_attachment(f.read(), maintype="application", subtype="pdf", filename=filename)
    else:
        print(f"❌ PDF file not found for: {filename}")

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(owner_msg)
            smtp.send_message(user_msg)
        print("✅ Emails sent.")
    except Exception as e:
        print("❌ Email error:", e)


# === Landing Page ===
@app.route('/')
def landing():
    return render_template('landing.html')

# === Home Page ===
@app.route('/home')
def home():
    try:
        with open('products.json', 'r', encoding='utf-8') as f:
            ebooks = json.load(f)
    except Exception as e:
        print("❌ Could not load products.json:", e)
        ebooks = []

    return render_template('home.html', ebooks=ebooks)

# === Buy Page ===
@app.route('/buy/<slug>', methods=['GET', 'POST'])
def buy(slug):
    with open('products.json', 'r', encoding='utf-8') as f:
        ebooks = json.load(f)

    product = next((p for p in ebooks if p['slug'] == slug), None)
    if not product:
        return "404 – Product not found", 404

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        send_email_with_pdf(name, email, product)
        return redirect(url_for('thank_you', username=name, product=product['title']))

    return render_template('index.html', product=product)

# === Thank You Page ===
@app.route('/thank-you')
def thank_you():
    username = request.args.get('username', 'User')
    product = request.args.get('product', 'your purchase')
    return render_template('thankyou.html', username=username, product=product)

# === Skip Login (Optional) ===
@app.route('/skip')
def skip():
    session.clear()
    return redirect(url_for('home'))

# === Logout (Optional) ===
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('landing'))

# === Run App ===
if __name__ == '__main__':
    app.run(debug=True)
