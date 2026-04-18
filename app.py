from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file
import sys
print(">>> APP LOADING AT TOP LEVEL...", flush=True)
from datetime import datetime, timedelta 
from models import init_db, connect 
from werkzeug.security import check_password_hash
from functools import wraps
import os
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter
from ai_engine import BusinessAnalyzer


app = Flask(__name__) 
app.secret_key = os.environ.get('SECRET_KEY', 'default_secret_key_rajanna')
app.permanent_session_lifetime = timedelta(days=7)

@app.route('/health')
def health_check():
    return jsonify({"status": "ok"}), 200

try:
    print(">>> CALLING init_db()...", flush=True)
    init_db() 
    print(">>> init_db() COMPLETED.", flush=True)
except Exception as e:
    print(f">>> CRITICAL ERROR in init_db(): {e}", flush=True)

# Helper to provide current app context
@app.context_processor
def utility_processor():
    return dict(current_app_name=session.get('current_app', 'BuildBasket'))

@app.route('/switch_app')
def switch_app():
    # Toggle between apps
    if session.get('current_app') == 'BuildBasket Daily':
        session['current_app'] = 'BuildBasket Construction'
        return redirect(url_for('dashboard'))
    else:
        session['current_app'] = 'BuildBasket Daily'
        return redirect(url_for('kirana_dashboard'))

# ---------------- AUTH DECORATOR ---------------- 
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ---------------- LOGIN / LOGOUT ---------------- 
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = connect()
        c = conn.cursor()
        c.execute("SELECT id, username, password, role FROM users WHERE username = %s", (username,))
        user = c.fetchone()
        conn.close()
        
        if username == 'admin' and password == '1234': 
            session['role'] = 'admin' 
            session['username'] = 'Admin' 
            if request.form.get('remember'):
                session.permanent = True
            return redirect('/') 
        elif username == 'staff' and password == '1234': 
            session['role'] = 'shopkeep' 
            session['username'] = 'Staff' 
            if request.form.get('remember'):
                session.permanent = True
            return redirect('/') 
        elif user and check_password_hash(user[2], password):
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['role'] = user[3]
            # Set default app on login
            if 'current_app' not in session:
                session['current_app'] = 'BuildBasket Construction'
            return redirect(url_for('dashboard'))
        else:
            return "Invalid Credentials", 401
            
    return render_template("login.html")

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Profit Margin and Price Setting routes removed/refactored

# ---------------- PANEL SWITCH ----------------
@app.route('/switch_panel')
@login_required
def switch_panel():
    """Toggle between admin and staff view for admin users"""
    if session.get('role') != 'admin':
        return redirect(url_for('dashboard'))
    
    current_view = session.get('panel_view', 'admin')
    session['panel_view'] = 'staff' if current_view == 'admin' else 'admin'
    return redirect(url_for('dashboard'))

# ---------------- DASHBOARD (Cement Pro) ---------------- 
@app.route('/') 
@login_required
def dashboard():
    status = health_check()
    session['current_app'] = 'BuildBasket Construction'
    conn = connect() 
    c = conn.cursor() 
 
    panel_view = session.get('panel_view', 'admin') if session.get('role') == 'admin' else 'staff'
    c.execute("SELECT brand, SUM(quantity), MAX(price) FROM stock GROUP BY brand") 
    stock = c.fetchall() 
    c.execute("SELECT brand, SUM(quantity), SUM(quantity*price) FROM sales GROUP BY brand") 
    sales = c.fetchall() 
    total_revenue = float(sum(s[2] or 0 for s in sales)) 
    
    c.execute("SELECT quantity, price, purchase_price FROM sales")
    total_sales_records = c.fetchall()
    total_profit = 0
    for row in total_sales_records:
        qty, sprice, pprice = row
        if pprice > 0:
            total_profit += (sprice - pprice) * qty
        else:
            total_profit += 40 * qty
    
    # Detailed Brand Stats for Dashboard
    c.execute("SELECT brand FROM stock")
    all_brands = [r[0] for r in c.fetchall()]
    brand_stats_detailed = []
    for b in all_brands:
        c.execute("SELECT SUM(quantity), SUM(quantity*price) FROM sales WHERE brand = %s", (b,))
        s_data = c.fetchone()
        b_sold = int(s_data[0] or 0)
        b_rev = float(s_data[1] or 0)
        
        c.execute("SELECT quantity, price, purchase_price FROM sales WHERE brand = %s", (b,))
        b_records = c.fetchall()
        b_profit = 0
        for r in b_records:
            q, sp, pp = r
            if pp > 0: b_profit += (sp - pp) * q
            else: b_profit += 40 * q
            
        c.execute("SELECT quantity FROM stock WHERE brand = %s", (b,))
        b_left = int(c.fetchone()[0] or 0)
        
        brand_stats_detailed.append({
            'brand': b,
            'sold': b_sold,
            'revenue': b_rev,
            'profit': b_profit,
            'left': b_left
        })


    today = datetime.now().strftime("%Y-%m-%d") 
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d") 
    month_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d") 
 
    def get_revenue(date): 
        c.execute("SELECT SUM(quantity*price) FROM sales WHERE date >= %s", (date,)) 
        return float(c.fetchone()[0] or 0) 
 
    daily = get_revenue(today) 
    weekly = get_revenue(week_ago) 
    monthly = get_revenue(month_ago) 
 
    c.execute("SELECT quantity, price, purchase_price FROM sales WHERE date = %s", (today,))
    today_records = c.fetchall()
    daily_profit_val = 0
    for row in today_records:
        qty, sprice, pprice = row
        if pprice > 0:
            daily_profit_val += (sprice - pprice) * qty
        else:
            daily_profit_val += 40 * qty

    def get_bag_count(date):
        c.execute("SELECT SUM(quantity) FROM sales WHERE date >= %s", (date,))
        return int(c.fetchone()[0] or 0)

    daily_bags = get_bag_count(today)
    weekly_bags = get_bag_count(week_ago)
    monthly_bags = get_bag_count(month_ago)
    
    # Brand-wise bags sold today (for the highlight bar)
    c.execute("SELECT brand, SUM(quantity) FROM sales WHERE date = %s GROUP BY brand", (today,))
    today_brand_sales = {row[0]: row[1] for row in c.fetchall()}
    jk_sold = today_brand_sales.get("JK Super", 0)
    nagarjuna_sold = today_brand_sales.get("Nagarjuna", 0)

    c.execute("SELECT brand, quantity, date, load_name, purchase_price, settled, description, id FROM loads ORDER BY id DESC")
    loads = c.fetchall()
    c.execute("SELECT brand, quantity, id FROM waste ORDER BY id DESC LIMIT 10")
    waste_summary = c.fetchall()
    total_waste = int(sum(w[1] or 0 for w in waste_summary))
    c.execute("SELECT brand, quantity, date, customer_name, customer_village, payment_method FROM sales ORDER BY id DESC LIMIT 5")
    recent_sales = c.fetchall()

    c.execute("SELECT brand, SUM(quantity) FROM loads GROUP BY brand")
    total_loads = {row[0]: float(row[1]) for row in c.fetchall()}
    low_stock = []
    for s in stock:
        brand_name = s[0]
        current_qty = s[1]
        total_loaded = total_loads.get(brand_name, 0)
        if total_loaded > 0 and current_qty < (0.75 * total_loaded):
            low_stock.append(s)
 
    total_bags_sold = int(sum(s[1] or 0 for s in sales))
    total_bags_left = int(sum(s[1] or 0 for s in stock))
    total_bags_loaded = int(sum(total_loads.values()))

    monthly_breakdown = []
    if panel_view == 'admin':
        c.execute("SELECT DISTINCT DATE_FORMAT(date, '%%Y-%%m') as month FROM loads ORDER BY month ASC")
        load_months_raw = c.fetchall()
        c.execute("SELECT DISTINCT DATE_FORMAT(date, '%%Y-%%m') as month FROM sales ORDER BY month ASC")
        sale_months_raw = c.fetchall()
        all_months = sorted(set([m[0] for m in load_months_raw] + [m[0] for m in sale_months_raw]))
        for month in all_months:
            month_start = month + "-01"
            month_end = month + "-31"
            c.execute("SELECT brand, SUM(quantity) FROM loads WHERE date >= %s AND date <= %s GROUP BY brand", (month_start, month_end))
            month_loads = c.fetchall()
            c.execute("SELECT brand, SUM(quantity), SUM(quantity*price) FROM sales WHERE date >= %s AND date <= %s GROUP BY brand", (month_start, month_end))
            month_sales = c.fetchall()
            c.execute("SELECT quantity, price, purchase_price FROM sales WHERE date >= %s AND date <= %s", (month_start, month_end))
            month_profit_records = c.fetchall()
            m_profit = 0
            m_bags = 0
            m_revenue = 0
            for row in month_profit_records:
                q, sp, pprice = row
                if pprice > 0: m_profit += (sp - pprice) * q
                else: m_profit += 40 * q
                m_bags += q
                m_revenue += sp * q
            c.execute("SELECT SUM(quantity) FROM waste WHERE date >= %s AND date <= %s", (month_start, month_end))
            m_waste = int(c.fetchone()[0] or 0)
            try:
                dt = datetime.strptime(month + "-01", "%Y-%m-%d")
                month_label = dt.strftime("%B %Y")
            except: month_label = month
            monthly_breakdown.append({'month': month_label, 'loads': month_loads, 'sales': month_sales, 'bags_sold': m_bags, 'revenue': m_revenue, 'profit': m_profit, 'waste': m_waste})

    total_investment = 0
    c.execute("SELECT quantity, purchase_price FROM loads")
    all_loads = c.fetchall()
    for row in all_loads:
        total_investment += row[0] * row[1]

    conn.close() 
    return render_template("dashboard.html", stock=stock, sales=sales, total_revenue=total_revenue, total_profit=total_profit, daily=daily, daily_profit=daily_profit_val, daily_bags=daily_bags, weekly_bags=weekly_bags, monthly_bags=monthly_bags, total_bags_sold=total_bags_sold, total_bags_left=total_bags_left, total_bags_loaded=total_bags_loaded, total_waste=total_waste, total_investment=total_investment, loads=loads, waste_summary=waste_summary, recent_sales=recent_sales, weekly=weekly, monthly=monthly, low_stock=low_stock, monthly_breakdown=monthly_breakdown, panel_view=panel_view, today_date=today, jk_sold=jk_sold, nagarjuna_sold=nagarjuna_sold, brand_stats=brand_stats_detailed) 

# ---------------- ADD STOCK ---------------- 
@app.route('/add_stock', methods=['GET','POST']) 
@login_required
def add_stock(): 
    if session.get('role') != 'admin':
        return "Access Denied", 403
    if request.method == 'POST': 
        brand = request.form['brand'] 
        qty = int(request.form['quantity']) 
        p_price = float(request.form['purchase_price']) 
        date = request.form['date']
        settled = request.form['settled']
        desc = request.form['description']
        
        conn = connect() 
        c = conn.cursor() 
        
        # 1. Update/Insert current Selling Price in stock
        # Note: We keep the old 'price' as selling price here if not provided, but form doesn't have it anymore.
        # User wants to set selling price in 'margins' usually.
        # Let's check if the brand exists in stock
        c.execute("SELECT id FROM stock WHERE brand = %s", (brand,))
        existing = c.fetchone()
        if existing:
            c.execute("UPDATE stock SET quantity = quantity + %s WHERE id = %s", (qty, existing[0]))
        else:
            c.execute("INSERT INTO stock (brand, quantity, price) VALUES (%s,%s,%s)", (brand, qty, p_price + 40)) # Default +40 margin
            
        # 2. Add to Loads History
        load_name = f"Load {datetime.now().strftime('%d%b')}"
        c.execute("INSERT INTO loads (brand, quantity, date, load_name, purchase_price, settled, description) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                  (brand, qty, date, load_name, p_price, settled, desc))
        
        conn.commit() 
        conn.close() 
        return redirect('/') 
    return render_template("add_stock.html", today_date=datetime.now().strftime("%Y-%m-%d")) 
 
# ---------------- ADD SALE ---------------- 
@app.route('/add_sale', methods=['GET','POST']) 
@login_required
def add_sale(): 
    conn = connect() 
    c = conn.cursor()
    if request.method == 'POST': 
        brand = request.form['brand'] 
        qty = int(request.form['quantity']) 
        price = float(request.form['price']) 
        customer_name = request.form.get('customer_name', '')
        customer_village = request.form.get('customer_village', '')
        customer_phone = request.form.get('customer_phone', '')
        payment_method = request.form.get('payment_method', 'Cash')
        amount_paid = float(request.form.get('amount_paid', 0) or 0)
        # Get latest purchase price for profit tracking (Strict Buy Price Logic)
        c.execute("SELECT purchase_price FROM loads WHERE brand = %s ORDER BY id DESC LIMIT 1", (brand,))
        lp = c.fetchone()
        pprice = lp[0] if lp else 0.0
        
        c.execute("INSERT INTO sales (brand, quantity, price, date, customer_name, customer_village, customer_phone, payment_method, profit_type, profit_value, load_source, purchase_price, amount_paid) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", (brand, qty, price, datetime.now().strftime("%Y-%m-%d"), customer_name, customer_village, customer_phone, payment_method, 'rupees', 0.0, "Current Stock", pprice, amount_paid)) 
        c.execute("UPDATE stock SET quantity = quantity - %s WHERE brand = %s", (qty, brand)) 
        
        # Notify Admin
        c.execute("INSERT INTO app_alerts (message, recipient_role, type) VALUES (%s, %s, %s)", 
                  (f"Staff recorded a sale of {qty} bags of {brand} to {customer_name or 'Guest'}", "admin", "sale"))
        
        conn.commit() 
        conn.close() 
        return redirect('/') 
    c.execute("SELECT brand FROM stock WHERE quantity > 0")
    brands = [row[0] for row in c.fetchall()]
    conn.close()
    return render_template("add_sale.html", brands=brands) 

# ---------------- UNDO SALE ----------------
@app.route('/undo_sale/<int:sale_id>')
@login_required
def undo_sale(sale_id):
    if session.get('role') != 'admin':
        return "Access Denied", 403
    
    conn = connect()
    c = conn.cursor()
    
    # 1. Get sale details
    c.execute("SELECT brand, quantity FROM sales WHERE id = %s", (sale_id,))
    sale = c.fetchone()
    
    if sale:
        brand, qty = sale
        # 2. Restore stock
        c.execute("UPDATE stock SET quantity = quantity + %s WHERE brand = %s", (qty, brand))
        # 3. Delete sale
        c.execute("DELETE FROM sales WHERE id = %s", (sale_id,))
        conn.commit()
    
    conn.close()
    return redirect(url_for('customers'))

@app.route('/undo_last_sale')
@login_required
def undo_last_sale():
    if session.get('role') != 'admin':
        return "Access Denied", 403
    
    conn = connect()
    c = conn.cursor()
    c.execute("SELECT id FROM sales ORDER BY id DESC LIMIT 1")
    last_sale = c.fetchone()
    conn.close()
    
    if last_sale:
        return redirect(url_for('undo_sale', sale_id=last_sale[0]))
    return redirect(url_for('dashboard'))
# ---------------- NOTIFICATION SYSTEM ----------------
@app.route('/api/notifications')
@login_required
def get_notifications():
    role = session.get('role')
    conn = connect()
    c = conn.cursor()
    c.execute("SELECT id, message, type, created_at FROM app_alerts WHERE recipient_role = %s AND is_read = FALSE ORDER BY created_at DESC", (role,))
    alerts = [{'id': r[0], 'message': r[1], 'type': r[2], 'time': r[3].strftime("%H:%M")} for r in c.fetchall()]
    conn.close()
    return jsonify(alerts)

@app.route('/api/notifications/read', methods=['POST'])
@login_required
def mark_notifications_read():
    role = session.get('role')
    conn = connect()
    c = conn.cursor()
    c.execute("UPDATE app_alerts SET is_read = TRUE WHERE recipient_role = %s", (role,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})

@app.route('/send_admin_alert', methods=['GET', 'POST'])
@login_required
def send_admin_alert():
    if session.get('role') != 'admin':
        return "Access Denied", 403
    
    if request.method == 'POST':
        message = request.form.get('message')
        conn = connect()
        c = conn.cursor()
        c.execute("INSERT INTO app_alerts (message, recipient_role, type) VALUES (%s, %s, %s)", 
                  (message, "shopkeep", "alert"))
        conn.commit()
        conn.close()
        return redirect(url_for('dashboard'))
    
    return render_template("send_alert.html")


# ---------------- AI ASSISTANT API ----------------
@app.route('/api/ai/analyze', methods=['GET', 'POST'])
@login_required
def ai_analyze():
    app_type = session.get('current_app', 'Cement Pro')
    role = session.get('role', 'shopkeep')
    
    conn = connect()
    try:
        analyzer = BusinessAnalyzer(conn, role, app_type)
        if request.method == 'POST':
            user_query = request.json.get('query', '')
            response = analyzer.query(user_query)
            return jsonify({"response": response})
        else:
            # Traditional summary fallback
            analysis = analyzer.get_analysis()
            return jsonify({"response": analysis})
    except Exception as e:
        print(f"AI Analysis Error: {e}")
        return jsonify({"error": "Analysis temporarily unavailable"}), 500
    finally:
        conn.close()

# ---------------- CUSTOMER LEDGER ----------------
@app.route('/customers')
@login_required
def customers():
    search = request.args.get('search', '')
    sort_by = request.args.get('sort', 'date_desc')
    conn = connect()
    c = conn.cursor()
    base_cols = "brand, quantity, date, customer_name, customer_village, payment_method, id, customer_phone, load_source, price, purchase_price, amount_paid"
    conditions = []
    params = []
    if search:
        conditions.append("(customer_name LIKE %s OR customer_village LIKE %s OR customer_phone LIKE %s)")
        params.extend(['%' + search + '%', '%' + search + '%', '%' + search + '%'])
    if sort_by == 'cash': conditions.append("payment_method = 'Cash'")
    elif sort_by == 'upi': conditions.append("payment_method = 'UPI'")
    elif sort_by == 'credit': conditions.append("payment_method = 'Credit'")
    elif sort_by == 'pending': conditions.append("payment_method IN ('Credit', 'Not Paid')")
    where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
    if sort_by == 'date_asc':
        order = " ORDER BY date ASC, id ASC"
    else:
        order = " ORDER BY date DESC, id DESC"
    query = f"SELECT {base_cols} FROM sales{where_clause}{order}"
    c.execute(query, params)
    all_customers = c.fetchall()
    c.execute("SELECT DISTINCT brand FROM stock")
    brands = [row[0] for row in c.fetchall()]
    c.execute("SELECT DISTINCT load_name FROM loads")
    loads = [row[0] for row in c.fetchall()]
    conn.close()
    return render_template("customers.html", customers=all_customers, search=search, sort_by=sort_by, brands=brands, loads=loads)

# ---------------- EDIT SALE / CUSTOMER ----------------
@app.route('/edit_customer/<int:sale_id>', methods=['GET', 'POST'])
@login_required
def edit_customer(sale_id):
    if session.get('role') != 'admin':
        return "Access Denied", 403
    
    conn = connect()
    c = conn.cursor()
    
    if request.method == 'POST':
        brand = request.form['brand']
        new_qty = int(request.form['quantity'])
        price = float(request.form['price'])
        date = request.form['date']
        c_name = request.form['customer_name']
        c_village = request.form['customer_village']
        c_phone = request.form['customer_phone']
        pay_method = request.form['payment_method']
        l_source = request.form['load_source']
        p_price = float(request.form.get('purchase_price', 0) or 0)
        a_paid = float(request.form.get('amount_paid', 0) or 0)
        
        # Get old qty to adjust stock
        c.execute("SELECT brand, quantity FROM sales WHERE id = %s", (sale_id,))
        old_sale = c.fetchone()
        if old_sale:
            old_brand, old_qty = old_sale
            # Put back old qty, subtract new qty
            c.execute("UPDATE stock SET quantity = quantity + %s WHERE brand = %s", (old_qty, old_brand))
            c.execute("UPDATE stock SET quantity = quantity - %s WHERE brand = %s", (new_qty, brand))
        
        c.execute("""UPDATE sales SET 
                  brand=%s, quantity=%s, price=%s, date=%s, 
                  customer_name=%s, customer_village=%s, customer_phone=%s, 
                  payment_method=%s, load_source=%s, purchase_price=%s, amount_paid=%s
                  WHERE id=%s""", 
                  (brand, new_qty, price, date, c_name, c_village, c_phone, pay_method, l_source, p_price, a_paid, sale_id))
        
        conn.commit()
        conn.close()
        return redirect(url_for('customers'))
    
    c.execute("SELECT * FROM sales WHERE id = %s", (sale_id,))
    sale = c.fetchone()
    c.execute("SELECT brand FROM stock")
    brands = [r[0] for r in c.fetchall()]
    c.execute("SELECT load_name FROM loads")
    loads = [r[0] for r in c.fetchall()]
    conn.close()
    return render_template("edit_customer.html", sale=sale, brands=brands, loads=loads)

# ---------------- EDIT WASTE ----------------
@app.route('/edit_waste/<int:waste_id>', methods=['GET', 'POST'])
@login_required
def edit_waste(waste_id):
    if session.get('role') != 'admin':
        return "Access Denied", 403
    
    conn = connect()
    c = conn.cursor()
    
    if request.method == 'POST':
        brand = request.form['brand']
        new_qty = int(request.form['quantity'])
        date = request.form['date']
        reason = request.form['reason']
        
        # Adjust stock
        c.execute("SELECT brand, quantity FROM waste WHERE id = %s", (waste_id,))
        old_waste = c.fetchone()
        if old_waste:
            old_brand, old_qty = old_waste
            c.execute("UPDATE stock SET quantity = quantity + %s WHERE brand = %s", (old_qty, old_brand))
            c.execute("UPDATE stock SET quantity = quantity - %s WHERE brand = %s", (new_qty, brand))
            
        c.execute("UPDATE waste SET brand=%s, quantity=%s, date=%s, reason=%s WHERE id=%s",
                  (brand, new_qty, date, reason, waste_id))
        conn.commit()
        conn.close()
        return redirect(url_for('dashboard'))
    
    c.execute("SELECT * FROM waste WHERE id = %s", (waste_id,))
    waste = c.fetchone()
    c.execute("SELECT brand FROM stock")
    brands = [r[0] for r in c.fetchall()]
    conn.close()
    return render_template("edit_waste.html", waste=waste, brands=brands)

# ---------------- EDIT LOAD ----------------
@app.route('/edit_load/<int:load_id>', methods=['GET', 'POST'])
@login_required
def edit_load(load_id):
    if session.get('role') != 'admin':
        return "Access Denied", 403
    
    conn = connect()
    c = conn.cursor()
    
    if request.method == 'POST':
        brand = request.form['brand']
        new_qty = int(request.form['quantity'])
        date = request.form['date']
        l_name = request.form['load_name']
        p_price = float(request.form['purchase_price'])
        settled = request.form['settled']
        desc = request.form['description']
        
        # Adjust stock
        c.execute("SELECT brand, quantity FROM loads WHERE id = %s", (load_id,))
        old_load = c.fetchone()
        if old_load:
            old_brand, old_qty = old_load
            c.execute("UPDATE stock SET quantity = quantity - %s WHERE brand = %s", (old_qty, old_brand))
            c.execute("UPDATE stock SET quantity = quantity + %s WHERE brand = %s", (new_qty, brand))
            
        c.execute("""UPDATE loads SET 
                  brand=%s, quantity=%s, date=%s, load_name=%s, 
                  purchase_price=%s, settled=%s, description=%s 
                  WHERE id=%s""",
                  (brand, new_qty, date, l_name, p_price, settled, desc, load_id))
        conn.commit()
        conn.close()
        return redirect(url_for('dashboard'))
    
    c.execute("SELECT * FROM loads WHERE id = %s", (load_id,))
    load = c.fetchone()
    c.execute("SELECT brand FROM stock")
    brands = [r[0] for r in c.fetchall()]
    conn.close()
    return render_template("edit_load.html", load=load, brands=brands)

# ---------------- MARK PAID ----------------
@app.route('/mark_paid/<int:sale_id>')
@login_required
def mark_paid(sale_id):
    if session.get('role') != 'admin':
        return "Access Denied", 403
    
    conn = connect()
    c = conn.cursor()
    c.execute("UPDATE sales SET payment_method = 'Paid' WHERE id = %s", (sale_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('customers'))

# ---------------- PENDING CUSTOMERS ----------------
@app.route('/pending_customers')
@login_required
def pending_customers():
    conn = connect()
    c = conn.cursor()
    # Group by customer and village to show total pending
    c.execute("""SELECT customer_name, customer_village, customer_phone, 
              SUM(quantity * price) as total_pending, 
              COUNT(id) as record_count 
              FROM sales 
              WHERE payment_method IN ('Credit', 'Not Paid') 
              GROUP BY customer_name, customer_village, customer_phone 
              ORDER BY total_pending DESC""")
    pending_list = c.fetchall()
    conn.close()
    return render_template("pending_customers.html", pending_list=pending_list)

# ========================================================
# ================= SMART KIRANA MODULES =================
# ========================================================

# ---------------- KIRANA DASHBOARD ----------------
@app.route("/kirana/")
@login_required
def kirana_dashboard():
    session['current_app'] = 'BuildBasket Daily'
    if session.get('role') != 'admin':
        return redirect(url_for('kirana_add_sale'))

    conn = connect()
    c = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")

    # 1. TODAY PROFIT
    c.execute("""
        SELECT SUM((p.price - p.cost_price) * s.quantity)
        FROM kirana_sales s
        JOIN kirana_products p ON s.product_id = p.id
        WHERE DATE(s.date_time) = %s
    """, (today,))
    result = c.fetchone()
    today_sales_profit = float(result[0] or 0)

    c.execute("SELECT money_spent, glasses_sold FROM kirana_palm_wine WHERE date = %s", (today,))
    palm_data = c.fetchone()
    today_palm_profit = float((palm_data[1] * 20 - palm_data[0]) if palm_data else 0)
    today_total_profit = today_sales_profit + today_palm_profit

    # 2. WEEK PROFIT
    c.execute("""
        SELECT SUM((p.price - p.cost_price) * s.quantity)
        FROM kirana_sales s
        JOIN kirana_products p ON s.product_id = p.id
        WHERE YEARWEEK(s.date_time, 1) = YEARWEEK(NOW(), 1)
    """)
    result_week = c.fetchone()
    week_sales_profit = float(result_week[0] or 0)
    c.execute("""
        SELECT SUM((glasses_sold * 20) - money_spent)
        FROM kirana_palm_wine
        WHERE YEARWEEK(date, 1) = YEARWEEK(NOW(), 1)
    """)
    result_week_palm = c.fetchone()
    week_palm_profit = float(result_week_palm[0] or 0)
    week_total_profit = week_sales_profit + week_palm_profit

    # 3. MONTH PROFIT
    c.execute("""
        SELECT SUM((p.price - p.cost_price) * s.quantity)
        FROM kirana_sales s
        JOIN kirana_products p ON s.product_id = p.id
        WHERE DATE_FORMAT(s.date_time, '%%Y-%%m') = DATE_FORMAT(NOW(), '%%Y-%%m')
    """)
    result_month = c.fetchone()
    month_sales_profit = float(result_month[0] or 0)
    c.execute("""
        SELECT SUM((glasses_sold * 20) - money_spent)
        FROM kirana_palm_wine
        WHERE DATE_FORMAT(date, '%%Y-%%m') = DATE_FORMAT(NOW(), '%%Y-%%m')
    """)
    result_month_palm = c.fetchone()
    month_palm_profit = float(result_month_palm[0] or 0)
    month_total_profit = month_sales_profit + month_palm_profit

    # Low Stock Alert
    c.execute("SELECT name, stock FROM kirana_products WHERE stock < 5")
    low_stock = c.fetchall()

    # Generic stats
    c.execute("SELECT SUM(quantity) FROM kirana_sales WHERE DATE(date_time) = %s", (today,))
    total_items = c.fetchone()[0] or 0
    c.execute("""
        SELECT SUM(p.price * s.quantity) 
        FROM kirana_sales s 
        JOIN kirana_products p ON s.product_id = p.id 
        WHERE DATE(s.date_time) = %s
    """, (today,))
    result_rev = c.fetchone()
    total_revenues = float(result_rev[0] or 0)

    c.execute("""
        SELECT p.name, p.variant, SUM(s.quantity) 
        FROM kirana_sales s 
        JOIN kirana_products p ON s.product_id = p.id 
        WHERE DATE(s.date_time) = %s 
        GROUP BY p.id
    """, (today,))
    today_sales_summary = c.fetchall()

    # Recent Individual Sales (for Undo)
    c.execute("""
        SELECT s.id, p.name, p.variant, s.quantity, DATE_FORMAT(s.date_time, '%%h:%%i %%p')
        FROM kirana_sales s
        JOIN kirana_products p ON s.product_id = p.id
        WHERE DATE(s.date_time) = %s
        ORDER BY s.id DESC LIMIT 10
    """, (today,))
    recent_individual_sales = c.fetchall()

    # Today's Palm Record (for Undo)
    c.execute("SELECT id, glasses_sold FROM kirana_palm_wine WHERE date = %s", (today,))
    palm_record = c.fetchone()

    conn.close()
    return render_template("kirana_dashboard.html",
                           today_total_profit=today_total_profit,
                           week_total_profit=week_total_profit,
                           month_total_profit=month_total_profit,
                           palm_profit=today_palm_profit,
                           total_profit=today_sales_profit,
                           total_items=total_items,
                           total_revenue=total_revenues,
                           low_stock_products=low_stock,
                           today_sales_summary=today_sales_summary,
                           recent_sales=recent_individual_sales,
                           palm_record=palm_record)

# ---------------- KIRANA REPORT ----------------
@app.route("/kirana/report", methods=["GET", "POST"])
@login_required
def kirana_report():
    selected_date = request.form.get("date") or datetime.now().strftime("%Y-%m-%d")
    conn = connect()
    c = conn.cursor()
    c.execute("""
        SELECT p.name, SUM(s.quantity) as total_sold, p.stock,
               SUM((p.price - p.cost_price) * s.quantity) as profit
        FROM kirana_sales s
        JOIN kirana_products p ON s.product_id = p.id
        WHERE DATE(s.date_time) = %s
        GROUP BY p.id
    """, (selected_date,))
    report_data = c.fetchall()

    c.execute("SELECT SUM(quantity) FROM kirana_sales WHERE DATE(date_time) = %s", (selected_date,))
    total_items = c.fetchone()[0] or 0
    c.execute("""
        SELECT SUM((p.price - p.cost_price) * s.quantity)
        FROM kirana_sales s
        JOIN kirana_products p ON s.product_id = p.id
        WHERE DATE(s.date_time) = %s
    """, (selected_date,))
    result_prof = c.fetchone()
    total_profit = float(result_prof[0] or 0)

    c.execute("SELECT money_spent, glasses_sold FROM kirana_palm_wine WHERE date = %s", (selected_date,))
    palm_data = c.fetchone()
    palm_profit = float((palm_data[1] * 20 - palm_data[0]) if palm_data else 0)
    total_combined_profit = total_profit + palm_profit
    conn.close()
    return render_template("kirana_report.html",
                           report_data=report_data,
                           total_items=total_items,
                           total_profit=total_profit,
                           palm_profit=palm_profit,
                           total_combined_profit=total_combined_profit,
                           selected_date=selected_date)

# ---------------- KIRANA ITEMS PRICE LIST ----------------
@app.route("/kirana/items")
@login_required
def kirana_items():
    conn = connect()
    c = conn.cursor()
    c.execute("SELECT name, variant, price, stock FROM kirana_products ORDER BY name ASC")
    items = c.fetchall()
    conn.close()
    return render_template("kirana_items.html", items=items)

# ---------------- KIRANA ADD SALE ----------------
@app.route("/kirana/add_sale", methods=["GET", "POST"])
@login_required
def kirana_add_sale():
    conn = connect()
    c = conn.cursor()
    if request.method == "POST":
        p_id = request.form.get("product_id")
        qty = int(request.form.get("quantity", 0))
        c.execute("INSERT INTO kirana_sales (product_id, quantity, date_time) VALUES (%s, %s, %s)", (p_id, qty, datetime.now()))
        c.execute("UPDATE kirana_products SET stock = stock - %s WHERE id = %s", (qty, p_id))
        
        # Notify Admin
        c.execute("SELECT name FROM kirana_products WHERE id = %s", (p_id,))
        p_name = c.fetchone()[0]
        c.execute("INSERT INTO app_alerts (message, recipient_role, type) VALUES (%s, %s, %s)", 
                  (f"Staff sold {qty} units of {p_name} in Kirana shop", "admin", "sale"))
        
        conn.commit()
        conn.close()
        return redirect(url_for('kirana_add_sale'))
    c.execute("SELECT id, name, variant, price FROM kirana_products")
    products = c.fetchall()

    today = datetime.now().strftime("%Y-%m-%d")
    c.execute("""
        SELECT p.name, p.variant, SUM(s.quantity) 
        FROM kirana_sales s 
        JOIN kirana_products p ON s.product_id = p.id 
        WHERE DATE(s.date_time) = %s 
        GROUP BY p.id
    """, (today,))
    today_sales_summary = c.fetchall()

    conn.close()
    return render_template("kirana_add_sale.html", products=products, today_sales_summary=today_sales_summary)

# ---------------- KIRANA PALM UPDATE STAFF ----------------
@app.route("/kirana/palm_update", methods=["GET", "POST"])
@login_required
def kirana_palm_update():
    today = datetime.now().strftime("%Y-%m-%d")
    conn = connect()
    c = conn.cursor()

    if request.method == "POST":
        glasses = int(request.form["glasses_sold"])
        c.execute("SELECT id FROM kirana_palm_wine WHERE date = %s", (today,))
        existing = c.fetchone()
        if existing:
            c.execute("UPDATE kirana_palm_wine SET glasses_sold = glasses_sold + %s WHERE date = %s", (glasses, today))
        else:
            c.execute("INSERT INTO kirana_palm_wine (date, money_spent, glasses_sold) VALUES (%s, 0, %s)", (today, glasses))
        conn.commit()
        conn.close()
        return redirect(url_for('kirana_palm_update'))
    
    c.execute("SELECT glasses_sold FROM kirana_palm_wine WHERE date = %s", (today,))
    row = c.fetchone()
    total_glasses_today = row[0] if row else 0
    conn.close()
    return render_template("kirana_palm_update.html", total_glasses_today=total_glasses_today)

# ---------------- KIRANA UPDATE STOCK ----------------
@app.route("/kirana/update_stock", methods=["GET", "POST"])
@login_required
def kirana_update_stock():
    conn = connect()
    c = conn.cursor()
    if request.method == "POST":
        p_id = request.form.get("product_id")
        added = int(request.form.get("added_stock", 0))
        c.execute("UPDATE kirana_products SET stock = stock + %s WHERE id = %s", (added, p_id))
        c.execute("SELECT name FROM kirana_products WHERE id = %s", (p_id,))
        p_name = c.fetchone()[0]
        c.execute("INSERT INTO kirana_notifications (message, date_time) VALUES (%s, %s)", (f"Staff added {added} stock to {p_name}", datetime.now()))
        conn.commit()
        conn.close()
        return redirect(url_for('kirana_update_stock'))
    c.execute("SELECT id, name, variant, stock FROM kirana_products")
    products = c.fetchall()
    conn.close()
    return render_template("kirana_update_stock.html", products=products)

# ---------------- KIRANA ADD PRODUCT ----------------
@app.route("/kirana/add_product", methods=["GET", "POST"])
@login_required
def kirana_add_product():
    if session.get('role') != 'admin':
        return redirect(url_for('kirana_add_sale'))
    if request.method == "POST":
        name = request.form["name"]
        variant = request.form["variant"]
        cost = float(request.form["cost_price"])
        price = float(request.form["price"])
        stock = int(request.form["stock"])
        conn = connect()
        c = conn.cursor()
        c.execute("SELECT id FROM kirana_products WHERE LOWER(name)=LOWER(%s) AND LOWER(variant)=LOWER(%s)", (name, variant))
        existing = c.fetchone()
        if existing:
            c.execute("UPDATE kirana_products SET stock = stock + %s, cost_price = %s, price = %s WHERE id = %s", (stock, cost, price, existing[0]))
        else:
            c.execute("INSERT INTO kirana_products (name, variant, cost_price, price, stock) VALUES (%s,%s,%s,%s,%s)", (name, variant, cost, price, stock))
        conn.commit()
        conn.close()
        return redirect(url_for('kirana_dashboard'))
    return render_template("kirana_add_product.html")

# ---------------- KIRANA PALM ADMIN ----------------
@app.route("/kirana/palm_wine", methods=["GET", "POST"])
@login_required
def kirana_palm_wine():
    if session.get('role') != 'admin':
        return redirect(url_for('kirana_add_sale'))
    today = datetime.now().strftime("%Y-%m-%d")
    conn = connect()
    c = conn.cursor()
    if request.method == "POST":
        money_spent = float(request.form["money_spent"])
        c.execute("SELECT id FROM kirana_palm_wine WHERE date = %s", (today,))
        existing = c.fetchone()
        if existing: c.execute("UPDATE kirana_palm_wine SET money_spent = %s WHERE date = %s", (money_spent, today))
        else: c.execute("INSERT INTO kirana_palm_wine (date, money_spent, glasses_sold) VALUES (%s, %s, 0)", (today, money_spent))
        conn.commit()
    c.execute("SELECT money_spent, glasses_sold FROM kirana_palm_wine WHERE date = %s", (today,))
    data = c.fetchone()
    if data:
        money_spent, glasses_sold = data
        revenues = glasses_sold * 20
        profit_loss = revenues - money_spent
    else: money_spent = glasses_sold = revenues = profit_loss = 0
    conn.close()
    return render_template("kirana_palm_wine.html", money_spent=money_spent, glasses_sold=glasses_sold, revenue=revenues, profit_loss=profit_loss)

# ---------------- PDF REPORT ----------------
@app.route("/kirana/monthly_report")
@login_required
def kirana_monthly_report():
    if session.get('role') != 'admin': return redirect(url_for('kirana_add_sale'))
    conn = connect()
    c = conn.cursor()
    c.execute("SELECT p.name, SUM(s.quantity) FROM kirana_sales s JOIN kirana_products p ON s.product_id = p.id WHERE DATE_FORMAT(s.date_time, '%%Y-%%m') = DATE_FORMAT(NOW(), '%%Y-%%m') GROUP BY p.name")
    data = c.fetchall()
    f_path = "kirana_monthly_report.pdf"
    doc = SimpleDocTemplate(f_path, pagesize=letter)
    elements = []
    style = getSampleStyleSheet()
    elements.append(Paragraph("Smart Kirana - Monthly Sales Report", style['Heading1']))
    elements.append(Spacer(1, 12))
    table_data = [["Product", "Total Sold"]]
    for row in data: table_data.append([row[0], str(row[1])])
    elements.append(Table(table_data))
    doc.build(elements)
    conn.close()
    return send_file(f_path, as_attachment=True)

# ---------------- KIRANA UNDO FEATURES ----------------
@app.route("/kirana/undo_sale/<int:sale_id>")
@login_required
def kirana_undo_sale(sale_id):
    if session.get('role') != 'admin':
        return "Access Denied", 403
    
    conn = connect()
    c = conn.cursor()
    
    # Get sale details
    c.execute("SELECT product_id, quantity FROM kirana_sales WHERE id = %s", (sale_id,))
    sale = c.fetchone()
    
    if sale:
        p_id, qty = sale
        # Restore stock
        c.execute("UPDATE kirana_products SET stock = stock + %s WHERE id = %s", (qty, p_id))
        # Delete sale
        c.execute("DELETE FROM kirana_sales WHERE id = %s", (sale_id,))
        conn.commit()
    
    conn.close()
    return redirect(url_for('kirana_dashboard'))

@app.route("/kirana/undo_palm/<int:palm_id>")
@login_required
def kirana_undo_palm(palm_id):
    if session.get('role') != 'admin':
        return "Access Denied", 403
    
    conn = connect()
    c = conn.cursor()
    # For simplicity, we'll just delete the daily record or decrement if we had timestamps.
    # Current schema is daily. Let's just allow deleting a daily record if needed.
    c.execute("DELETE FROM kirana_palm_wine WHERE id = %s", (palm_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('kirana_dashboard'))

if __name__ == "__main__": 
    app.run(debug=True)