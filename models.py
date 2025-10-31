from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Category(db.Model):
    __tablename__ = 'category'
    id = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    products = db.relationship('Product', backref='category', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name
        }

class Product(db.Model):
    __tablename__ = 'product'
    # Dùng MD5 hash của URL làm ID
    id = db.Column(db.String(32), primary_key=True) 
    name = db.Column(db.String(500), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    image_url = db.Column(db.String(1000))
    url = db.Column(db.String(1000), nullable=False)
    platform = db.Column(db.String(50), default='Shopee')
    description = db.Column(db.Text, nullable=True)

    # Khóa ngoại liên kết với Category
    category_id = db.Column(db.String(50), db.ForeignKey('category.id'), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'price': self.price,
            'image_url': self.image_url,
            'url': self.url,
            'platform': self.platform,
            'category_id': self.category_id,
            'description': self.description
        }