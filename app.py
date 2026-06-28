from flask import Flask, render_template
from models import db
from models import Sale
from flask import request, jsonify
from flask import Flask, render_template, request, redirect
from models import db, Product
from models import Sale
from sqlalchemy import func
from datetime import datetime
import random
import string

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "webpospro"

db.init_app(app)

with app.app_context():

    db.create_all()
#++++++++CATEGORIES++++++

@app.context_processor
def inject_categories():
    categories = db.session.query(Product.category).distinct().all()
    return dict(categories=categories)

#---- Receip View-------

@app.route("/receipt/<transaction_id>")
def receipt_view(transaction_id):

    sales = Sale.query.filter_by(transaction_id=transaction_id).all()

    if not sales:
        return "Receipt not found", 404

    total = sum(s.total for s in sales)

    return render_template(
        "receipt_db.html",
        sales=sales,
        transaction_id=transaction_id,
        total=total
    )

#-----RECEIPT---------

@app.route("/receipt")
def receipt():
    return render_template("receipt.html")
#-------REPORTS--------
@app.route("/reports")
def reports():

    today = datetime.now().date()

    total_sales = db.session.query(
        func.sum(Sale.total)
    ).filter(
        func.date(Sale.date) == today
    ).scalar()

    sales = Sale.query.order_by(Sale.date.desc()).all()

    return render_template(
        "reports.html",
        total_sales=total_sales or 0,
        sales=sales
    )
#----- SAVE SALES-------

@app.route("/save-sale", methods=["POST"])
def save_sale():

    data = request.json
    cart = data.get("cart", [])
    cash = float(data.get("cash", 0))

    txn = "INV-" + ''.join(random.choices(string.digits, k=6))

    sale_items = []
    total = 0

    for item in cart:

        product = Product.query.filter_by(name=item["name"]).first()

        price = float(item["price"])
        total += price

        # STOCK DEDUCTION
        if product:
            product.stock -= 1

            if product.stock < 0:
                product.stock = 0

        sale = Sale(
            transaction_id=txn,
            product_name=item["name"],
            price=price,
            quantity=1,
            total=price
        )

        db.session.add(sale)

        sale_items.append({
            "name": item["name"],
            "price": price
        })

    db.session.commit()

    return jsonify({
        "message": "Saved",
        "items": sale_items,
        "transaction_id": txn,
        "total": total,
        "cash": cash,
        "change": cash - total
    })

#------Products----------

@app.route("/products")
def products():
    products = Product.query.all()
    return render_template("products.html", products=products)
#------Delete Products-------

@app.route("/delete-product/<int:id>")
def delete_product(id):

    product = Product.query.get_or_404(id)

    db.session.delete(product)
    db.session.commit()

    return redirect("/products")

#------POS-----------

@app.route("/pos")
def pos():

    category = request.args.get("category")

    if category:
        products = Product.query.filter_by(category=category).all()
    else:
        products = Product.query.all()

    categories = db.session.query(Product.category).distinct().all()

    return render_template(
        "pos.html",
        products=products,
        categories=categories,
        selected_category=category
    )

#-------Edit Products--------

@app.route("/edit-product/<int:id>", methods=["GET", "POST"])
def edit_product(id):

    product = Product.query.get_or_404(id)

    if request.method == "POST":
        product.barcode = request.form["barcode"]
        product.name = request.form["name"]
        product.category = request.form["category"]
        product.price = float(request.form["price"])
        product.stock = int(request.form["stock"])

        db.session.commit()

        return redirect("/products")

    return render_template("edit_product.html", product=product)


#++++++ DASHBOARD +++++++++++++

@app.route("/")
def dashboard():

    today = datetime.now().date()

    today_sales = db.session.query(func.sum(Sale.total)).filter(
        func.date(Sale.date) == today
    ).scalar()

    total_transactions = db.session.query(func.count(Sale.id)).scalar()

    total_sales = db.session.query(func.sum(Sale.total)).scalar()

    recent_sales = Sale.query.order_by(Sale.date.desc()).limit(10).all()

    return render_template(
        "dashboard.html",
        today_sales=today_sales or 0,
        total_sales=total_sales or 0,
        total_transactions=total_transactions,
        recent_sales=recent_sales
    )

#-------Add Products---------

@app.route("/add-product", methods=["GET", "POST"])
def add_product():

    if request.method == "POST":

        product = Product(
            barcode=request.form["barcode"],
            name=request.form["name"],
            category=request.form["category"],
            price=float(request.form["price"]),
            stock=int(request.form["stock"])
        )

        db.session.add(product)
        db.session.commit()

        return redirect("/products")

    return render_template("add_product.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
