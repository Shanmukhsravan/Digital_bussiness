from datetime import datetime, timedelta

class BusinessAnalyzer:
    def __init__(self, db_conn, role, app_type='BuildBasket Construction'):
        self.conn = db_conn
        self.cursor = db_conn.cursor()
        self.role = role
        self.app_type = app_type
        self.today = datetime.now().strftime("%Y-%m-%d")
        self.week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    def query(self, text):
        text = text.lower()
        
        # Determine context (Kirana vs Cement)
        # If user explicitly says 'kirana', use that. Otherwise use app_type.
        context = 'Kirana' if 'kirana' in text else self.app_type
        
        # Security Check
        if ("profit" in text or "revenue" in text or "money" in text or "earned" in text) and self.role != 'admin':
            return "You do not have permission to access financial information. Please contact the Admin."

        if "advice" in text or "tip" in text or "suggest" in text:
            return self._get_business_advice(context)
        
        if "stock" in text or "inventory" in text or "left" in text:
            return self._query_stock(context)
            
        if "sale" in text or "sold" in text:
            return self._query_sales(context, text)
            
        if ("who owes" in text or "pending" in text or "credit" in text) and self.role == 'admin':
            return self._query_pending()

        if "profit" in text or "revenue" in text:
            return self._query_financials(context, text)

        return f"I am currently analyzing your {context} data. I can help with sales, stock, or business advice. Try asking 'What is my {context} profit today?'"

    def _get_business_advice(self, context):
        advices = []
        
        if 'Kirana' in context:
            self.cursor.execute("SELECT name, stock FROM kirana_products WHERE stock < 10")
            low = self.cursor.fetchall()
            if low:
                advices.append(f"Attention: {len(low)} Kirana items are low on stock. Check {low[0][0]} soon.")
            
            # Advice on pricing
            advices.append("Tip: Group similar items like soaps and detergents together for easier selection.")
        else:
            self.cursor.execute("SELECT brand, quantity FROM stock WHERE quantity < 50")
            low = self.cursor.fetchall()
            if low:
                advices.append(f"CRITICAL: Stock for {', '.join([r[0] for r in low])} is low. Restock to avoid missing bags sales.")
            
            self.cursor.execute("SELECT SUM(quantity * price) FROM sales WHERE date >= %s", (self.week_ago,))
            week_rev = float(self.cursor.fetchone()[0] or 0)
            if week_rev > 50000:
                advices.append("Sales are high! Consider a loyalty discount for repeat customers.")

        tips = [
            "Customer Loyalty: Collect phone numbers to build a digital relationship.",
            "Credit Control: Set limits on how much credit each customer can take.",
            "Visual Flow: Keep high-margin items at eye level."
        ]
        
        import random
        return f"**{context} Advice:**\n\n- {advices[0] if advices else 'Your business looks stable today.'}\n- {random.choice(tips)}"

    def _query_stock(self, context):
        if 'Kirana' in context:
            self.cursor.execute("SELECT name, stock, variant FROM kirana_products WHERE stock < 20 LIMIT 10")
            stock = self.cursor.fetchall()
            if not stock: return "Kirana stock is fully replenished."
            prefix = "**Low Kirana Stock:**\n"
            items = [f"- {s[0]} ({s[2]}): {s[1]} units" for s in stock]
        else:
            self.cursor.execute("SELECT brand, quantity FROM stock")
            stock = self.cursor.fetchall()
            prefix = "**Cement Stock Levels:**\n"
            items = [f"- {s[0]}: {s[1]} bags" for s in stock]
        
        return prefix + "\n".join(items)

    def _query_sales(self, context, text):
        date_used = self.today
        label = "today"
        if "week" in text:
            date_used = self.week_ago
            label = "this week"
            
        if 'Kirana' in context:
            self.cursor.execute("SELECT SUM(quantity) FROM kirana_sales WHERE DATE(date_time) >= %s", (date_used,))
            total = self.cursor.fetchone()[0] or 0
            unit = "items"
        else:
            self.cursor.execute("SELECT SUM(quantity) FROM sales WHERE date >= %s", (date_used,))
            total = self.cursor.fetchone()[0] or 0
            unit = "bags"
            
        return f"{context}: You have sold **{total} {unit}** {label}."

    def _query_pending(self):
        self.cursor.execute("SELECT customer_name, SUM(quantity * price - amount_paid) as due FROM sales GROUP BY customer_name HAVING due > 0 ORDER BY due DESC LIMIT 3")
        rows = self.cursor.fetchall()
        if not rows: return "No outstanding payments recorded."
        
        resp = "**Outstanding Cement Balances:**\n"
        for r in rows:
            resp += f"- {r[0]}: ₹{r[1]:,.2f}\n"
        return resp

    def _query_financials(self, context, text):
        if 'Kirana' in context:
            self.cursor.execute("""
                SELECT SUM((p.price - p.cost_price) * s.quantity), SUM(p.price * s.quantity)
                FROM kirana_sales s
                JOIN kirana_products p ON s.product_id = p.id
                WHERE DATE(s.date_time) = %s
            """, (self.today,))
            data = self.cursor.fetchone()
            profit = float(data[0] or 0)
            rev = float(data[1] or 0)
        else:
            self.cursor.execute("SELECT quantity, price, purchase_price FROM sales WHERE date = %s", (self.today,))
            rows = self.cursor.fetchall()
            rev = sum(r[0] * r[1] for r in rows)
            profit = sum((r[1] - r[2]) * r[0] if r[2] > 0 else 40 * r[0] for r in rows)
        
        if "profit" in text:
            return f"{context} profit for today is estimated at **₹{profit:,.2f}**."
        return f"{context} total revenue for today is **₹{rev:,.2f}**."

    def get_analysis(self):
        return self.query("summary")
