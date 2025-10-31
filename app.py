from flask import Flask, render_template, jsonify, request
from models import db, Product, Category
from sqlalchemy import or_

# Khởi tạo App
app = Flask(__name__)

# Cấu hình CSDL (dùng SQLite)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Gắn CSDL vào app
db.init_app(app)

# --- Các hàm Helper ---
def serialize_list(items):
    return [item.to_dict() for item in items]

# --- Các Route phục vụ trang (HTML) ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/product.html')
def product_page():
    return render_template('product.html')

# --- Các Route API (trả về JSON) ---

@app.route('/api/categories', methods=['GET'])
def get_categories():
    """API trả về danh sách các danh mục"""
    try:
        categories = Category.query.all()
        return jsonify(serialize_list(categories))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/products/search', methods=['GET'])
def search_products():
    """
    API chính để tìm kiếm và lọc sản phẩm
    Params:
    - q: Từ khóa tìm kiếm (search term)
    - category_id: Lọc theo ID danh mục
    - sort_by: 'price_asc' hoặc 'price_desc'
    """
    try:
        q = request.args.get('q')
        category_id = request.args.get('category_id')
        sort_by = request.args.get('sort_by')

        # Bắt đầu query
        query = Product.query

        if category_id:
            query = query.filter_by(category_id=category_id)
        elif q:
            # Tìm kiếm 'ilike' (không phân biệt hoa thường)
            query = query.filter(Product.name.ilike(f'%{q}%'))
        else:
            # Nếu không tìm kiếm hay lọc, trả về mảng rỗng
             return jsonify({"products": []})

        # Sắp xếp
        if sort_by == 'price_asc':
            query = query.order_by(Product.price.asc())
        elif sort_by == 'price_desc':
            query = query.order_by(Product.price.desc())

        products = query.all()
        
        return jsonify({"products": serialize_list(products)})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/product/<string:product_id>', methods=['GET'])
def get_product_detail(product_id):
    """API lấy chi tiết 1 sản phẩm và các sản phẩm liên quan"""
    try:
        product = Product.query.get_or_404(product_id)
        
        # Tìm sản phẩm liên quan (cùng danh mục, trừ chính nó)
        related_products = Product.query.filter_by(category_id=product.category_id) \
                                        .filter(Product.id != product_id) \
                                        .limit(5) \
                                        .all()
        
        return jsonify({
            "product": product.to_dict(),
            "related_products": serialize_list(related_products)
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Chạy App
if __name__ == '__main__':
    # Tạo CSDL một lần khi chạy (nếu bạn không chạy scraper.py trước)
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)