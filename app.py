from flask import Flask, render_template, request, redirect, url_for, session, jsonify, send_file
from datetime import datetime, timedelta 
from models import init_db, connect 
from werkzeug.security import check_password_hash
from functools import wraps
import os
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter

app = Flask(__name__) 
app.secret_key = os.environ.get('SECRET_KEY', 'default_secret_key_rajanna')
init_db() 

# Helper to provide current app context
@app.context_processor
def utility_processor():
    return dict(current_app_name=session.get('current_app', 'Cement Pro'))

@app.route('/switch_app')
def switch_app():
    # Toggle between apps
    if session.get('current_app') == 'Smart Kirana':
        session['current_app'] = 'Cement Pro'
        return redirect(url_for('dashboard'))
    else:
        session['current_app'] = 'Smart Kirana'
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
        
        if user and check_password_hash(user[2], password):
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['role'] = user[3]
            # Set default app on login
            if 'current_app' not in session:
                session['current_app'] = 'Cement Pro'
            return redirect(url_for('dashboard'))
        else:
            return "Invalid Credentials", 401
            
    return render_template("login.html")

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ---------------- PROFIT MARGINS ----------------
@app.route('/profit_margin', methods=['GET', 'POST'])
@login_required
def profit_margin():
    if session.get('role') != 'admin':
        return "Access Denied", 403
    
    conn = connect()
    c = conn.cursor()
    
    if request.method == 'POST':
        brand = request.form.get('brand')
        ptype = request.form.get('profit_type')
        pvalue = float(request.form.get('profit_value'))
        
        # Use REPLACE to update or insert
        c.execute("REPLACE INTO margins (brand, profit_type, profit_value) VALUES (%s,%s,%s)", 
                  (brand, ptype, pvalue))
        conn.commit()
        conn.close()
        return redirect(url_for('profit_margin'))
        
    c.execute("SELECT brand, profit_type, profit_value FROM margins")
    margins = {row[0]: {'type': row[1], 'value': row[2]} for row in c.fetchall()}
    
    c.execute("SELECT DISTINCT brand, price FROM stock")
    brands_with_price = c.fetchall()
    brands = [row[0] for row in brands_with_price]
    brand_prices = {row[0]: row[1] for row in brands_with_price}
    conn.close()
    
    return render_template("profit_margin.html", margins=margins, brands=brands, brand_prices=brand_prices)

# ---------------- SET ITEM PRICE (Admin Only) ----------------
@app.route('/set_price', methods=['POST'])
@login_required
def set_price():
    if session.get('role') != 'admin':
        return "Access Denied", 403
    brand = request.form.get('brand')
    price = float(request.form.get('price', 0))
    conn = connect()
    c = conn.cursor()
    c.execute("UPDATE stock SET price = %s WHERE brand = %s", (price, brand))
    conn.commit()
    conn.close()
    return redirect(url_for('profit_margin'))

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
    session['current_app'] = 'Cement Pro'
    conn = connect() 
    c = conn.cursor() 
 
    panel_view = session.get('panel_view', 'admin') if session.get('role') == 'admin' else 'staff'
    c.execute("SELECT brand, SUM(quantity), MAX(price) FROM stock GROUP BY brand") 
    stock = c.fetchall() 
    c.execute("SELECT brand, SUM(quantity), SUM(quantity*price) FROM sales GROUP BY brand") 
    sales = c.fetchall() 
    total_revenue = float(sum(s[2] or 0 for s in sales)) 
    
    c.execute("SELECT profit_type, profit_value, quantity, price FROM sales")
    total_sales_records = c.fetchall()
    total_profit = 0
    for row in total_sales_records:
        ptype, pval, qty, sprice = row
        if ptype == 'rupees':
            total_profit += pval * qty
        else:
            total_profit += (pval / 100) * (sprice * qty)
    
    c.execute("SELECT brand, profit_type, profit_value FROM margins")
    margins_data = c.fetchall()
    today = datetime.now().strftime("%Y-%m-%d") 
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d") 
    month_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d") 
 
    def get_revenue(date): 
        c.execute("SELECT SUM(quantity*price) FROM sales WHERE date >= %s", (date,)) 
        return float(c.fetchone()[0] or 0) 
 
    daily = get_revenue(today) 
    weekly = get_revenue(week_ago) 
    monthly = get_revenue(month_ago) 
 
    c.execute("SELECT profit_type, profit_value, quantity, price FROM sales WHERE date = %s", (today,))
    today_records = c.fetchall()
    daily_profit_val = 0
    for row in today_records:
        ptype, pval, qty, sprice = row
        if ptype == 'rupees':
            daily_profit_val += pval * qty
        else:
            daily_profit_val += (pval / 100) * (sprice * qty)

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

    c.execute("SELECT brand, quantity, date, load_name FROM loads ORDER BY id DESC")
    loads = c.fetchall()
    c.execute("SELECT brand, SUM(quantity) FROM waste GROUP BY brand")
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
            c.execute("SELECT profit_type, profit_value, quantity, price FROM sales WHERE date >= %s AND date <= %s", (month_start, month_end))
            month_profit_records = c.fetchall()
            m_profit = 0
            m_bags = 0
            m_revenue = 0
            for row in month_profit_records:
                pt, pv, q, sp = row
                if pt == 'rupees': m_profit += pv * q
                else: m_profit += (pv / 100) * (sp * q)
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
    for l in loads:
        brand_name = l[0]
        qty = l[1]
        if brand_name == 'JK Super': total_investment += qty * 265
        elif brand_name == 'Nagarjuna': total_investment += qty * 340

    conn.close() 
    return render_template("dashboard.html", stock=stock, sales=sales, total_revenue=total_revenue, total_profit=total_profit, daily=daily, daily_profit=daily_profit_val, daily_bags=daily_bags, weekly_bags=weekly_bags, monthly_bags=monthly_bags, total_bags_sold=total_bags_sold, total_bags_left=total_bags_left, total_bags_loaded=total_bags_loaded, total_waste=total_waste, total_investment=total_investment, loads=loads, waste_summary=waste_summary, recent_sales=recent_sales, weekly=weekly, monthly=monthly, low_stock=low_stock, margins=margins_data, monthly_breakdown=monthly_breakdown, panel_view=panel_view, today_date=today, jk_sold=jk_sold, nagarjuna_sold=nagarjuna_sold) 

# ---------------- ADD STOCK ---------------- 
@app.route('/add_stock', methods=['GET','POST']) 
@login_required
def add_stock(): 
    if session.get('role') != 'admin':
        return "Access Denied", 403
    if request.method == 'POST': 
        brand = request.form['brand'] 
        qty = int(request.form['quantity']) 
        price = float(request.form['price']) 
        conn = connect() 
        c = conn.cursor() 
        c.execute("INSERT INTO stock (brand, quantity, price) VALUES (%s,%s,%s)", (brand, qty, price)) 
        conn.commit() 
        conn.close() 
        return redirect('/') 
    return render_template("add_stock.html") 
 
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
        c.execute("SELECT profit_type, profit_value FROM margins WHERE brand = %s", (brand,))
        margin = c.fetchone()
        ptype = margin[0] if margin else 'rupees'
        pvalue = margin[1] if margin else 0.0
        c.execute("INSERT INTO sales (brand, quantity, price, date, customer_name, customer_village, customer_phone, payment_method, profit_type, profit_value, load_source) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", (brand, qty, price, datetime.now().strftime("%Y-%m-%d"), customer_name, customer_village, customer_phone, payment_method, ptype, pvalue, "Current Stock")) 
        c.execute("UPDATE stock SET quantity = quantity - %s WHERE brand = %s", (qty, brand)) 
        conn.commit() 
        conn.close() 
        return redirect('/') 
    c.execute("SELECT brand FROM stock WHERE quantity > 0")
    brands = [row[0] for row in c.fetchall()]
    conn.close()
    return render_template("add_sale.html", brands=brands) 

# ---------------- CUSTOMER LEDGER ----------------
@app.route('/customers')
@login_required
def customers():
    search = request.args.get('search', '')
    sort_by = request.args.get('sort', 'date_desc')
    conn = connect()
    c = conn.cursor()
    base_cols = "brand, quantity, date, customer_name, customer_village, payment_method, id, customer_phone, load_source"
    conditions = []
    params = []
    if search:
        conditions.append("(customer_name LIKE %s OR customer_village LIKE %s OR customer_phone LIKE %s)")
        params.extend(['%' + search + '%', '%' + search + '%', '%' + search + '%'])
    if sort_by == 'cash': conditions.append("payment_method = 'Cash'")
    elif sort_by == 'upi': conditions.append("payment_method = 'UPI'")
    elif sort_by == 'credit': conditions.append("payment_method = 'Credit'")
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

# ========================================================
# ================= SMART KIRANA MODULES =================
# ========================================================

# ---------------- KIRANA DASHBOARD ----------------
@app.route("/kirana/")
@login_required
def kirana_dashboard():
    session['current_app'] = 'Smart Kirana'
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
                           today_sales_summary=today_sales_summary)

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
    c.execute("SELECT name, variant, price FROM kirana_products ORDER BY name ASC")
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
    if request.method == "POST":
        glasses = int(request.form["glasses_sold"])
        today = datetime.now().strftime("%Y-%m-%d")
        conn = connect()
        c = conn.cursor()
        c.execute("SELECT id FROM kirana_palm_wine WHERE date = %s", (today,))
        existing = c.fetchone()
        if existing:
            c.execute("UPDATE kirana_palm_wine SET glasses_sold = glasses_sold + %s WHERE date = %s", (glasses, today))
        else:
            c.execute("INSERT INTO kirana_palm_wine (date, money_spent, glasses_sold) VALUES (%s, 0, %s)", (today, glasses))
        conn.commit()
        conn.close()
        return redirect(url_for('kirana_palm_update'))
    return render_template("kirana_palm_update.html")

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

if __name__ == "__main__": 
    app.run(debug=True)