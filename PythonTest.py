from flask import Flask, render_template, request, redirect, jsonify, session, send_file, url_for
import sqlite3
import qrcode
import io
import os
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'restaurant_secret_key_2024'  # For session management
app.config['UPLOAD_FOLDER'] = 'static/images'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
ALLOWED_EXTENSIONS = {
    'png', 'jpg', 'jpeg', 'gif', 'webp', 
    'bmp', 'svg', 'ico', 'tiff', 'tif', 
    'jfif', 'pjpeg', 'pjp', 'avif', 'heic', 'heif'
}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db():
    return sqlite3.connect("database.db")

# ---------- DB INIT ----------
def init_db():
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS menu (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            price INTEGER,
            image TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_date TEXT,
            total_amount REAL,
            status TEXT DEFAULT 'pending'
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            menu_id INTEGER,
            quantity INTEGER,
            price REAL,
            FOREIGN KEY (order_id) REFERENCES orders(id),
            FOREIGN KEY (menu_id) REFERENCES menu(id)
        )
    """)
    db.commit()

init_db()

# ---------- HOME ----------
@app.route("/")
def index():
    db = get_db()
    cur = db.cursor()
    items = cur.execute("SELECT * FROM menu").fetchall()
    db.close()
    return render_template("index.html", items=items)

# ---------- CART PAGE ----------
@app.route("/cart_page")
def cart_page():
    return render_template("cart.html")

# ---------- CHECKOUT PAGE ----------
@app.route("/checkout")
def checkout():
    return render_template("checkout.html")

# ---------- INITIALIZE DEFAULT MENU ITEMS ----------
def init_default_menu():
    db = get_db()
    cur = db.cursor()
    # Check if menu is empty
    count = cur.execute("SELECT COUNT(*) FROM menu").fetchone()[0]
    if count == 0:
        default_items = [
            ("Idly", 30, "/static/images/idly.jpg"),
            ("Puttu", 40, "/static/images/puttu.jpg"),
            ("Poori", 35, "/static/images/poori.jpg"),
            ("Pongal", 45, "/static/images/pongal.jpg"),
            ("Dosai", 50, "/static/images/dosai.jpg"),
            ("Vada", 25, "/static/images/apple.jpg")
        ]
        for name, price, image in default_items:
            cur.execute("INSERT INTO menu (name, price, image) VALUES (?,?,?)",
                      (name, price, image))
        db.commit()
    db.close()

init_default_menu()

# ---------- ADD MENU ----------
@app.route("/add", methods=["POST"])
def add_menu():
    name = request.form["name"]
    price = request.form["price"]
    image = request.form.get("image", "")  # URL input
    
    # Handle file upload
    if 'image_file' in request.files:
        file = request.files['image_file']
        if file and file.filename and allowed_file(file.filename):
            # Create upload directory if it doesn't exist
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            
            # Generate unique filename
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_")
            filename = timestamp + filename
            
            # Save file
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Store relative path for static files
            image = f'images/{filename}'
    
    db = get_db()
    cur = db.cursor()
    cur.execute("INSERT INTO menu (name, price, image) VALUES (?,?,?)",
               (name, price, image))
    db.commit()
    db.close()
    return redirect("/admin")

# ---------- UPDATE MENU ----------
@app.route("/update/<int:id>", methods=["GET", "POST"])
def update_menu(id):
    db = get_db()
    cur = db.cursor()
    if request.method == "POST":
        name = request.form["name"]
        price = request.form["price"]
        image = request.form.get("image", "")  # URL input
        
        # Handle file upload
        if 'image_file' in request.files:
            file = request.files['image_file']
            if file and file.filename and allowed_file(file.filename):
                # Create upload directory if it doesn't exist
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                
                # Generate unique filename
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_")
                filename = timestamp + filename
                
                # Save file
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                
                # Store relative path for static files
                image = f'images/{filename}'
        
        cur.execute("UPDATE menu SET name=?, price=?, image=? WHERE id=?", 
                   (name, price, image, id))
        db.commit()
        db.close()
        return redirect("/admin")
    else:
        item = cur.execute("SELECT * FROM menu WHERE id=?", (id,)).fetchone()
        db.close()
        return jsonify({
            "id": item[0],
            "name": item[1],
            "price": item[2],
            "image": item[3]
        })

# ---------- GET MENU ITEM ----------
@app.route("/menu/<int:id>")
def get_menu_item(id):
    db = get_db()
    cur = db.cursor()
    item = cur.execute("SELECT * FROM menu WHERE id=?", (id,)).fetchone()
    db.close()
    if item:
        return jsonify({
            "id": item[0],
            "name": item[1],
            "price": item[2],
            "image": item[3]
        })
    return jsonify({"error": "Item not found"}), 404

# ---------- DELETE MENU ----------
@app.route("/delete/<int:id>")
def delete_menu(id):
    db = get_db()
    cur = db.cursor()
    cur.execute("DELETE FROM menu WHERE id=?", (id,))
    db.commit()
    db.close()
    return redirect("/admin")

# ---------- CART OPERATIONS ----------
@app.route("/add_to_cart", methods=["POST"])
def add_to_cart():
    data = request.json
    menu_id = data.get("menu_id")
    quantity = data.get("quantity", 1)
    
    if 'cart' not in session:
        session['cart'] = {}
    
    cart = session['cart']
    if str(menu_id) in cart:
        cart[str(menu_id)] += quantity
    else:
        cart[str(menu_id)] = quantity
    
    session['cart'] = cart
    return jsonify({"success": True, "cart": cart})

@app.route("/cart")
def get_cart():
    cart = session.get('cart', {})
    db = get_db()
    cur = db.cursor()
    cart_items = []
    total = 0
    
    for menu_id, quantity in cart.items():
        item = cur.execute("SELECT * FROM menu WHERE id=?", (int(menu_id),)).fetchone()
        if item:
            item_total = item[2] * quantity
            total += item_total
            
            # Convert image path to proper URL
            image_url = item[3] if item[3] else ""
            if image_url and image_url.startswith('images/'):
                image_url = url_for('static', filename=image_url)
            elif image_url and not image_url.startswith('http') and not image_url.startswith('/static/'):
                # Handle legacy paths
                if not image_url.startswith('/'):
                    image_url = url_for('static', filename=f'images/{image_url}')
            
            cart_items.append({
                "id": item[0],
                "name": item[1],
                "price": item[2],
                "image": image_url,
                "quantity": quantity,
                "total": item_total
            })
    
    db.close()
    return jsonify({"items": cart_items, "total": total})

@app.route("/update_cart/<int:menu_id>", methods=["POST"])
def update_cart(menu_id):
    data = request.json
    quantity = data.get("quantity", 1)
    
    if 'cart' not in session:
        session['cart'] = {}
    
    cart = session['cart']
    if quantity > 0:
        cart[str(menu_id)] = quantity
    else:
        cart.pop(str(menu_id), None)
    
    session['cart'] = cart
    return jsonify({"success": True, "cart": cart})

@app.route("/remove_from_cart/<int:menu_id>", methods=["DELETE"])
def remove_from_cart(menu_id):
    if 'cart' in session:
        cart = session['cart']
        cart.pop(str(menu_id), None)
        session['cart'] = cart
    return jsonify({"success": True})

@app.route("/clear_cart", methods=["POST"])
def clear_cart():
    session['cart'] = {}
    return jsonify({"success": True})

# ---------- ORDER OPERATIONS ----------
@app.route("/create_order", methods=["POST"])
def create_order():
    cart = session.get('cart', {})
    if not cart:
        return jsonify({"error": "Cart is empty"}), 400
    
    db = get_db()
    cur = db.cursor()
    total_amount = 0
    
    # Calculate total
    for menu_id, quantity in cart.items():
        item = cur.execute("SELECT price FROM menu WHERE id=?", (int(menu_id),)).fetchone()
        if item:
            total_amount += item[0] * quantity
    
    # Create order
    order_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("INSERT INTO orders (order_date, total_amount, status) VALUES (?, ?, ?)",
                (order_date, total_amount, "pending"))
    order_id = cur.lastrowid
    
    # Add order items
    for menu_id, quantity in cart.items():
        item = cur.execute("SELECT price FROM menu WHERE id=?", (int(menu_id),)).fetchone()
        if item:
            cur.execute("INSERT INTO order_items (order_id, menu_id, quantity, price) VALUES (?, ?, ?, ?)",
                       (order_id, int(menu_id), quantity, item[0]))
    
    db.commit()
    db.close()
    session['cart'] = {}  # Clear cart after order
    
    return jsonify({"success": True, "order_id": order_id, "total": total_amount})

# ---------- QR CODE GENERATION ----------
@app.route("/generate_qr/<float:amount>")
def generate_qr(amount):
    qr_data = f"Payment Amount: ₹{amount:.2f}\nRestaurant Payment"
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(qr_data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    img_io = io.BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    
    return send_file(img_io, mimetype='image/png')

# ---------- BILL PRINT ----------
@app.route("/bill/<int:order_id>")
def bill(order_id):
    db = get_db()
    cur = db.cursor()
    order = cur.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
    if not order:
        db.close()
        return "Order not found", 404
    
    order_items = cur.execute("""
        SELECT m.name, oi.quantity, oi.price, (oi.quantity * oi.price) as total
        FROM order_items oi
        JOIN menu m ON oi.menu_id = m.id
        WHERE oi.order_id = ?
    """, (order_id,)).fetchall()
    
    db.close()
    return render_template("bill.html", order=order, order_items=order_items)

# ---------- SALARY REPORT ----------
@app.route("/salary")
def salary():
    staff = 5
    salary_per_staff = 12000
    total = staff * salary_per_staff
    return jsonify({
        "staff": staff,
        "salary_per_staff": salary_per_staff,
        "total_salary": total
    })

@app.route("/salary_report")
def salary_report():
    staff = 5
    salary_per_staff = 12000
    total = staff * salary_per_staff
    return render_template("salary_report.html", 
                         staff=staff, 
                         salary_per_staff=salary_per_staff, 
                         total=total)

# ---------- ADMIN PANEL ----------
@app.route("/admin")
def admin():
    db = get_db()
    cur = db.cursor()
    items = cur.execute("SELECT * FROM menu").fetchall()
    db.close()
    return render_template("admin.html", items=items)

if __name__ == "__main__":
    app.run(debug=True)
