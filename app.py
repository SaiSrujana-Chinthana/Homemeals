from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from pymongo import MongoClient
from datetime import datetime
import random, json, os, uuid, base64
from bson import ObjectId
from werkzeug.utils import secure_filename
import statistics

# Optional: Pillow for image optimization (pip install Pillow)
try:
    from PIL import Image
    import io
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False

app = Flask(__name__, static_folder='static')
CORS(app, resources={r"/*": {"origins": "*"}})

# Static folder configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_FOLDER = os.path.join(BASE_DIR, 'static')
IMAGES_FOLDER = os.path.join(STATIC_FOLDER, 'images')
PROFILES_FOLDER = os.path.join(STATIC_FOLDER, 'profiles')
FOOD_IMAGES_FOLDER = os.path.join(STATIC_FOLDER, 'food')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp'}

# Create directories
os.makedirs(STATIC_FOLDER, exist_ok=True)
os.makedirs(IMAGES_FOLDER, exist_ok=True)
os.makedirs(PROFILES_FOLDER, exist_ok=True)
os.makedirs(FOOD_IMAGES_FOLDER, exist_ok=True)

app.config['STATIC_FOLDER'] = STATIC_FOLDER
app.config['IMAGES_FOLDER'] = IMAGES_FOLDER
app.config['PROFILES_FOLDER'] = PROFILES_FOLDER
app.config['FOOD_IMAGES_FOLDER'] = FOOD_IMAGES_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024  # 32 MB

print(f"Static folder: {STATIC_FOLDER}")
print(f"Images folder: {IMAGES_FOLDER}")
print(f"Profiles folder: {PROFILES_FOLDER}")
print(f"Food images folder: {FOOD_IMAGES_FOLDER}")

class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        if isinstance(o, datetime):
            return o.isoformat()
        return json.JSONEncoder.default(self, o)

app.json_encoder = JSONEncoder

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_image_url(image_name, image_type='dish'):
    """Generate proper image URL with fallback"""
    if not image_name:
        if image_type == 'profile':
            return 'https://via.placeholder.com/300x300/ff6347/white?text=Cook'
        else:
            return 'https://via.placeholder.com/400x300/ff6347/white?text=Delicious+Food'
    if str(image_name).startswith('http'):
        return image_name

    if image_type == 'profile':
        folder = 'profiles'
    elif image_type == 'food':
        folder = 'food'
    else:
        folder = 'images'

    local_path = os.path.join(STATIC_FOLDER, folder, image_name)
    if os.path.exists(local_path):
        return f'http://localhost:5000/static/{folder}/{image_name}'
    else:
        if image_type == 'profile':
            return 'https://via.placeholder.com/300x300/ff6347/white?text=Cook'
        else:
            return 'https://via.placeholder.com/400x300/ff6347/white?text=Delicious+Food'

def serialize_doc(doc):
    if '_id' in doc:
        doc['_id'] = str(doc['_id'])
    return doc

# MongoDB connection
try:
    client = MongoClient("mongodb://localhost:27017", serverSelectionTimeoutMS=3000)
    client.server_info()
    db = client['homemealsdb']
    users_col = db['users']
    menu_col = db['menu_items']
    orders_col = db['orders']
    ratings_col = db['ratings']
    USE_MONGODB = True
    print("Connected to MongoDB")
except Exception as e:
    print(f"MongoDB connection failed: {e}")
    print("Using in-memory storage instead")
    USE_MONGODB = False
    users_data = []
    menu_data = []
    orders_data = []
    ratings_data = []

# SAMPLE COOKS WITH UPLOADED PROFILE PICTURES
sample_cooks = [
    {
        'name': 'Arjun Singh',
        'email': 'arjun@homemeals.com',
        'phone': '+91-9876543201',
        'address': 'Rajouri Garden, New Delhi',
        'type': 'cook',
        'specialties': 'Punjabi, Tandoor, Street Food, Parathas',
        'experience': 9,
        'description': 'Passionate Punjabi home cook with 9+ years of experience.',
        'averageRating': 4.6,
        'totalOrders': 245,
        'totalRatings': 134,
        'profilePic': 'boy1.jpeg',
        'profilePicUrl': 'http://localhost:5000/static/profiles/boy1.jpg',
        'registrationDate': datetime.utcnow(),
        'isAvailable': True,
        'deliveryRadius': 12,
        'preparationTime': '25-35 mins'
    },
    {
        'name': 'Kavya Reddy',
        'email': 'kavya@homemeals.com',
        'phone': '+91-9876543202',
        'address': 'Hitech City, Hyderabad',
        'type': 'cook',
        'specialties': 'Andhra, Telangana, Spicy Curries, Biryanis',
        'experience': 7,
        'description': 'Andhra home cuisine expert specializing in fiery curries and biryanis.',
        'averageRating': 4.8,
        'totalOrders': 312,
        'totalRatings': 189,
        'profilePic': 'girl 1.jpeg',
        'profilePicUrl': 'http://localhost:5000/static/profiles/girl-1.jpg',
        'registrationDate': datetime.utcnow(),
        'isAvailable': True,
        'deliveryRadius': 10,
        'preparationTime': '35-45 mins'
    },
    {
        'name': 'Rohit Jain',
        'email': 'rohit@homemeals.com',
        'phone': '+91-9876543203',
        'address': 'Andheri East, Mumbai',
        'type': 'cook',
        'specialties': 'Maharashtrian, Gujarati, Jain Food, Thalis',
        'experience': 6,
        'description': 'Pure vegetarian Maharashtrian and Gujarati dishes.',
        'averageRating': 4.4,
        'totalOrders': 198,
        'totalRatings': 112,
        'profilePic': 'boy2.jpeg',
        'profilePicUrl': 'http://localhost:5000/static/profiles/boy2.jpg',
        'registrationDate': datetime.utcnow(),
        'isAvailable': True,
        'deliveryRadius': 8,
        'preparationTime': '30-40 mins'
    },
    {
        'name': 'Sneha Iyer',
        'email': 'sneha@homemeals.com',
        'phone': '+91-9876543204',
        'address': 'Indiranagar, Bangalore',
        'type': 'cook',
        'specialties': 'Tamil, Karnataka, Filter Coffee, Breakfast',
        'experience': 11,
        'description': 'Traditional South Indian home cook.',
        'averageRating': 4.7,
        'totalOrders': 456,
        'totalRatings': 267,
        'profilePic': 'girl2.jpeg',
        'profilePicUrl': 'http://localhost:5000/static/profiles/girl2.jpg',
        'registrationDate': datetime.utcnow(),
        'isAvailable': True,
        'deliveryRadius': 9,
        'preparationTime': '20-30 mins'
    },
    {
        'name': 'Amit Gupta',
        'email': 'amit@homemeals.com',
        'phone': '+91-9876543205',
        'address': 'Park Street, Kolkata',
        'type': 'cook',
        'specialties': 'Bengali, Mughlai, Fish Curry, Sweets',
        'experience': 13,
        'description': 'Bengali home cuisine master.',
        'averageRating': 4.9,
        'totalOrders': 567,
        'totalRatings': 298,
        'profilePic': 'boy3.jpeg',
        'profilePicUrl': 'http://localhost:5000/static/profiles/boy3.jpg',
        'registrationDate': datetime.utcnow(),
        'isAvailable': True,
        'deliveryRadius': 14,
        'preparationTime': '40-50 mins'
    },
    {
        'name': 'Priya Nambiar',
        'email': 'priya@homemeals.com',
        'phone': '+91-9876543206',
        'address': 'Marine Drive, Kochi',
        'type': 'cook',
        'specialties': 'Kerala, Coastal, Coconut Dishes, Seafood',
        'experience': 8,
        'description': 'Kerala home cook bringing authentic flavors.',
        'averageRating': 4.5,
        'totalOrders': 289,
        'totalRatings': 156,
        'profilePic': 'girl3.jpeg',
        'profilePicUrl': 'http://localhost:5000/static/profiles/girl3.jpg',
        'registrationDate': datetime.utcnow(),
        'isAvailable': True,
        'deliveryRadius': 11,
        'preparationTime': '35-45 mins'
    }
]

# EXPANDED SAMPLE DISHES WITH FOOD IMAGES
sample_dishes = [
    # Arjun Singh's Punjabi dishes [web:63][web:68]
    {
        '_id': '1',
        'cookEmail': 'arjun@homemeals.com',
        'cookName': 'Arjun Singh',
        'name': 'Amritsari Kulcha',
        'description': 'Authentic Amritsari kulcha stuffed with spiced potatoes, served with chole and pickled onions.',
        'price': 95,
        'category': 'Lunch',
        'cuisine': 'Punjabi',
        'prepTime': 25,
        'spiceLevel': 'Medium',
        'isAvailable': True,
        'image': 'amritsarikulcha.jpeg',
        'imageUrl': 'https://images.unsplash.com/photo-1601050690597-df0568f70950?w=400&h=300&fit=crop',
        'averageRating': 4.7,
        'totalRatings': 68,
        'isVegetarian': True,
        'calories': 380,
        'dateAdded': datetime.utcnow()
    },
    {
        '_id': '2',
        'cookEmail': 'arjun@homemeals.com',
        'cookName': 'Arjun Singh',
        'name': 'Chole Bhature',
        'description': 'Fluffy homemade bhature with spicy chickpea curry, garnished with onions and green chutney.',
        'price': 85,
        'category': 'Breakfast',
        'cuisine': 'Punjabi',
        'prepTime': 20,
        'spiceLevel': 'Medium',
        'isAvailable': True,
        'image': 'CholeBhature.jpeg',
        'imageUrl': 'https://images.unsplash.com/photo-1626082927389-6cd097cdc6ec?w=400&h=300&fit=crop',
        'averageRating': 4.5,
        'totalRatings': 89,
        'isVegetarian': True,
        'calories': 450,
        'dateAdded': datetime.utcnow()
    },
    {
        '_id': '3',
        'cookEmail': 'arjun@homemeals.com',
        'cookName': 'Arjun Singh',
        'name': 'Tandoori Paneer Tikka',
        'description': 'Smoky paneer tikka marinated in yogurt and home-ground spices, grilled with bell peppers.',
        'price': 165,
        'category': 'Snacks',
        'cuisine': 'Punjabi',
        'prepTime': 30,
        'spiceLevel': 'High',
        'isAvailable': True,
        'image': 'paneer_tikka.jpeg',
        'imageUrl': 'https://images.unsplash.com/photo-1599487488170-d11ec9c172f0?w=400&h=300&fit=crop',
        'averageRating': 4.6,
        'totalRatings': 54,
        'isVegetarian': True,
        'calories': 320,
        'dateAdded': datetime.utcnow()
    },
    {
        '_id': '4',
        'cookEmail': 'arjun@homemeals.com',
        'cookName': 'Arjun Singh',
        'name': 'Butter Chicken',
        'description': 'Creamy tomato-based curry with tender chicken pieces, slow-cooked in aromatic spices.',
        'price': 195,
        'category': 'Dinner',
        'cuisine': 'Punjabi',
        'prepTime': 35,
        'spiceLevel': 'Medium',
        'isAvailable': True,
        'image': 'butter_chicken.jpeg',
        'imageUrl': 'https://images.unsplash.com/photo-1588166524941-3bf61a9c41db?w=400&h=300&fit=crop',
        'averageRating': 4.8,
        'totalRatings': 142,
        'isVegetarian': False,
        'calories': 520,
        'dateAdded': datetime.utcnow()
    },
    {
        '_id': '5',
        'cookEmail': 'arjun@homemeals.com',
        'cookName': 'Arjun Singh',
        'name': 'Makki di Roti with Sarson da Saag',
        'description': 'Traditional Punjabi cornmeal flatbread served with mustard greens curry and jaggery.',
        'price': 120,
        'category': 'Lunch',
        'cuisine': 'Punjabi',
        'prepTime': 40,
        'spiceLevel': 'Medium',
        'isAvailable': True,
        'image': 'makki_roti_saag.jpeg',
        'imageUrl': 'https://images.unsplash.com/photo-1596797038530-2c107229654b?w=400&h=300&fit=crop',
        'averageRating': 4.4,
        'totalRatings': 76,
        'isVegetarian': True,
        'calories': 350,
        'dateAdded': datetime.utcnow()
    },

    # Kavya Reddy's Andhra dishes [web:63][web:76]
    {
        '_id': '6',
        'cookEmail': 'kavya@homemeals.com',
        'cookName': 'Kavya Reddy',
        'name': 'Hyderabadi Biryani',
        'description': 'Aromatic basmati rice layered with spiced mutton, cooked in dum style with saffron and mint.',
        'price': 220,
        'category': 'Lunch',
        'cuisine': 'Andhra',
        'prepTime': 55,
        'spiceLevel': 'Medium',
        'isAvailable': True,
        'image': 'biryani.jpeg',
        'imageUrl': 'https://images.unsplash.com/photo-1563379091339-03246963d51a?w=400&h=300&fit=crop',
        'averageRating': 4.9,
        'totalRatings': 123,
        'isVegetarian': False,
        'calories': 580,
        'dateAdded': datetime.utcnow()
    },
    {
        '_id': '7',
        'cookEmail': 'kavya@homemeals.com',
        'cookName': 'Kavya Reddy',
        'name': 'Andhra Chicken Curry',
        'description': 'Spicy Andhra-style chicken curry with traditional spices, coconut, and curry leaves.',
        'price': 180,
        'category': 'Dinner',
        'cuisine': 'Andhra',
        'prepTime': 45,
        'spiceLevel': 'High',
        'isAvailable': True,
        'image': 'chicken.jpeg',
        'imageUrl': 'https://images.unsplash.com/photo-1565557623262-b51c2513a641?w=400&h=300&fit=crop',
        'averageRating': 4.8,
        'totalRatings': 98,
        'isVegetarian': False,
        'calories': 420,
        'dateAdded': datetime.utcnow()
    },
    {
        '_id': '8',
        'cookEmail': 'kavya@homemeals.com',
        'cookName': 'Kavya Reddy',
        'name': 'Gongura Mutton',
        'description': 'Traditional Andhra mutton curry cooked with tangy sorrel leaves and authentic spices.',
        'price': 250,
        'category': 'Dinner',
        'cuisine': 'Andhra',
        'prepTime': 60,
        'spiceLevel': 'High',
        'isAvailable': True,
        'image': 'gongura_mutton.jpeg',
        'imageUrl': 'https://images.unsplash.com/photo-1574653057686-61d6c4b6bb15?w=400&h=300&fit=crop',
        'averageRating': 4.7,
        'totalRatings': 54,
        'isVegetarian': False,
        'calories': 480,
        'dateAdded': datetime.utcnow()
    },
    {
        '_id': '9',
        'cookEmail': 'kavya@homemeals.com',
        'cookName': 'Kavya Reddy',
        'name': 'Pesarattu',
        'description': 'Healthy green gram dosa from Andhra Pradesh, served with ginger chutney and sambar.',
        'price': 75,
        'category': 'Breakfast',
        'cuisine': 'Andhra',
        'prepTime': 20,
        'spiceLevel': 'Low',
        'isAvailable': True,
        'image': 'pesarattu.jpeg',
        'imageUrl': 'https://images.unsplash.com/photo-1567188040759-fb8a883dc6d8?w=400&h=300&fit=crop',
        'averageRating': 4.3,
        'totalRatings': 67,
        'isVegetarian': True,
        'calories': 280,
        'dateAdded': datetime.utcnow()
    },

    # Rohit Jain's Gujarati/Maharashtrian dishes [web:67][web:70]
    {
        '_id': '10',
        'cookEmail': 'rohit@homemeals.com',
        'cookName': 'Rohit Jain',
        'name': 'Gujarati Thali',
        'description': 'Complete traditional Gujarati meal with dal, sabzi, roti, rice, and sweets.',
        'price': 150,
        'category': 'Lunch',
        'cuisine': 'Gujarati',
        'prepTime': 25,
        'spiceLevel': 'Medium',
        'isAvailable': True,
        'image': 'gujarati thali.jpeg',
        'imageUrl': 'https://images.unsplash.com/photo-1571115764595-644a1f56a55c?w=400&h=300&fit=crop',
        'averageRating': 4.6,
        'totalRatings': 89,
        'isVegetarian': True,
        'calories': 650,
        'dateAdded': datetime.utcnow()
    },
    {
        '_id': '11',
        'cookEmail': 'rohit@homemeals.com',
        'cookName': 'Rohit Jain',
        'name': 'Dhokla',
        'description': 'Steamed gram flour cake from Gujarat, light and spongy, served with green chutney.',
        'price': 60,
        'category': 'Snacks',
        'cuisine': 'Gujarati',
        'prepTime': 30,
        'spiceLevel': 'Low',
        'isAvailable': True,
        'image': 'dhokla.jpeg',
        'imageUrl': 'https://images.unsplash.com/photo-1606491956689-2ea866880c84?w=400&h=300&fit=crop',
        'averageRating': 4.4,
        'totalRatings': 112,
        'isVegetarian': True,
        'calories': 180,
        'dateAdded': datetime.utcnow()
    },
    {
        '_id': '12',
        'cookEmail': 'rohit@homemeals.com',
        'cookName': 'Rohit Jain',
        'name': 'Misal Pav',
        'description': 'Spicy Maharashtrian curry made with sprouts, served with pav bread and farsan.',
        'price': 85,
        'category': 'Breakfast',
        'cuisine': 'Maharashtrian',
        'prepTime': 25,
        'spiceLevel': 'High',
        'isAvailable': True,
        'image': 'misal_pav.jpeg',
        'imageUrl': 'https://images.unsplash.com/photo-1630383249896-424e482df921?w=400&h=300&fit=crop',
        'averageRating': 4.5,
        'totalRatings': 78,
        'isVegetarian': True,
        'calories': 320,
        'dateAdded': datetime.utcnow()
    },
    {
        '_id': '13',
        'cookEmail': 'rohit@homemeals.com',
        'cookName': 'Rohit Jain',
        'name': 'Undhiyu',
        'description': 'Mixed vegetable curry from Gujarat with seasonal vegetables and spices.',
        'price': 135,
        'category': 'Lunch',
        'cuisine': 'Gujarati',
        'prepTime': 45,
        'spiceLevel': 'Medium',
        'isAvailable': True,
        'image': 'undhiyu.jpeg',
        'imageUrl': 'https://images.unsplash.com/photo-1505253304499-671c55fb57fe?w=400&h=300&fit=crop',
        'averageRating': 4.2,
        'totalRatings': 45,
        'isVegetarian': True,
        'calories': 290,
        'dateAdded': datetime.utcnow()
    },

    # Sneha Iyer's South Indian dishes [web:76][web:79]
    {
        '_id': '14',
        'cookEmail': 'sneha@homemeals.com',
        'cookName': 'Sneha Iyer',
        'name': 'Masala Dosa',
        'description': 'Crispy fermented rice crepe filled with spiced potato curry, served with sambar and chutney.',
        'price': 80,
        'category': 'Breakfast',
        'cuisine': 'South Indian',
        'prepTime': 20,
        'spiceLevel': 'Medium',
        'isAvailable': True,
        'image': 'masala_dosa.jpeg',
        'imageUrl': 'https://images.unsplash.com/photo-1589301760014-d929f3979dbc?w=400&h=300&fit=crop',
        'averageRating': 4.8,
        'totalRatings': 156,
        'isVegetarian': True,
        'calories': 350,
        'dateAdded': datetime.utcnow()
    },
    {
        '_id': '15',
        'cookEmail': 'sneha@homemeals.com',
        'cookName': 'Sneha Iyer',
        'name': 'Idli Sambar',
        'description': 'Steamed rice cakes served with lentil curry and coconut chutney.',
        'price': 55,
        'category': 'Breakfast',
        'cuisine': 'South Indian',
        'prepTime': 15,
        'spiceLevel': 'Low',
        'isAvailable': True,
        'image': 'idli_sambar.jpeg',
        'imageUrl': 'https://images.unsplash.com/photo-1606491956689-2ea866880c84?w=400&h=300&fit=crop',
        'averageRating': 4.6,
        'totalRatings': 134,
        'isVegetarian': True,
        'calories': 220,
        'dateAdded': datetime.utcnow()
    },
    {
        '_id': '16',
        'cookEmail': 'sneha@homemeals.com',
        'cookName': 'Sneha Iyer',
        'name': 'Chettinad Chicken',
        'description': 'Spicy Tamil Nadu chicken curry with black pepper, star anise, and coconut.',
        'price': 190,
        'category': 'Dinner',
        'cuisine': 'Tamil',
        'prepTime': 40,
        'spiceLevel': 'High',
        'isAvailable': True,
        'image': 'chettinad_chicken.jpeg',
        'imageUrl': 'https://images.unsplash.com/photo-1565299624946-b28f40a0ca4b?w=400&h=300&fit=crop',
        'averageRating': 4.7,
        'totalRatings': 87,
        'isVegetarian': False,
        'calories': 480,
        'dateAdded': datetime.utcnow()
    },
    {
        '_id': '17',
        'cookEmail': 'sneha@homemeals.com',
        'cookName': 'Sneha Iyer',
        'name': 'Vada',
        'description': 'Deep-fried lentil donuts served with sambar and coconut chutney.',
        'price': 45,
        'category': 'Snacks',
        'cuisine': 'South Indian',
        'prepTime': 25,
        'spiceLevel': 'Medium',
        'isAvailable': True,
        'image': 'vada.jpeg',
        'imageUrl': 'https://images.unsplash.com/photo-1567188040759-fb8a883dc6d8?w=400&h=300&fit=crop',
        'averageRating': 4.3,
        'totalRatings': 92,
        'isVegetarian': True,
        'calories': 280,
        'dateAdded': datetime.utcnow()
    },
    {
        '_id': '18',
        'cookEmail': 'sneha@homemeals.com',
        'cookName': 'Sneha Iyer',
        'name': 'Rasam Rice',
        'description': 'Tangy tamarind-based soup with rice, a comfort food from South India.',
        'price': 70,
        'category': 'Lunch',
        'cuisine': 'South Indian',
        'prepTime': 20,
        'spiceLevel': 'Medium',
        'isAvailable': True,
        'image': 'rasam_rice.jpeg',
        'imageUrl': 'https://images.unsplash.com/photo-1596797038530-2c107229654b?w=400&h=300&fit=crop',
        'averageRating': 4.4,
        'totalRatings': 68,
        'isVegetarian': True,
        'calories': 320,
        'dateAdded': datetime.utcnow()
    },

    # Amit Gupta's Bengali dishes [web:63][web:67]
    {
        '_id': '19',
        'cookEmail': 'amit@homemeals.com',
        'cookName': 'Amit Gupta',
        'name': 'Fish Curry (Maach Bhaat)',
        'description': 'Traditional Bengali fish curry with rice, cooked in mustard oil and spices.',
        'price': 160,
        'category': 'Lunch',
        'cuisine': 'Bengali',
        'prepTime': 35,
        'spiceLevel': 'Medium',
        'isAvailable': True,
        'image': 'fish_curry.jpeg',
        'imageUrl': 'https://images.unsplash.com/photo-1565299624946-b28f40a0ca4b?w=400&h=300&fit=crop',
        'averageRating': 4.9,
        'totalRatings': 176,
        'isVegetarian': False,
        'calories': 380,
        'dateAdded': datetime.utcnow()
    },
    {
        '_id': '20',
        'cookEmail': 'amit@homemeals.com',
        'cookName': 'Amit Gupta',
        'name': 'Kosha Mangsho',
        'description': 'Slow-cooked Bengali mutton curry with onions, ginger, and aromatic spices.',
        'price': 240,
        'category': 'Dinner',
        'cuisine': 'Bengali',
        'prepTime': 50,
        'spiceLevel': 'Medium',
        'isAvailable': True,
        'image': 'kosha_mangsho.jpeg',
        'imageUrl': 'https://images.unsplash.com/photo-1574653057686-61d6c4b6bb15?w=400&h=300&fit=crop',
        'averageRating': 4.8,
        'totalRatings': 134,
        'isVegetarian': False,
        'calories': 520,
        'dateAdded': datetime.utcnow()
    },
    {
        '_id': '21',
        'cookEmail': 'amit@homemeals.com',
        'cookName': 'Amit Gupta',
        'name': 'Aloo Posto',
        'description': 'Bengali potato curry cooked with poppy seed paste and green chilies.',
        'price': 90,
        'category': 'Lunch',
        'cuisine': 'Bengali',
        'prepTime': 25,
        'spiceLevel': 'Low',
        'isAvailable': True,
        'image': 'aloo_posto.jpeg',
        'imageUrl': 'https://images.unsplash.com/photo-1505253304499-671c55fb57fe?w=400&h=300&fit=crop',
        'averageRating': 4.5,
        'totalRatings': 89,
        'isVegetarian': True,
        'calories': 250,
        'dateAdded': datetime.utcnow()
    },
    {
        '_id': '22',
        'cookEmail': 'amit@homemeals.com',
        'cookName': 'Amit Gupta',
        'name': 'Mishti Doi',
        'description': 'Sweet yogurt dessert from Bengal, set in earthen pots for authentic flavor.',
        'price': 45,
        'category': 'Dessert',
        'cuisine': 'Bengali',
        'prepTime': 10,
        'spiceLevel': 'None',
        'isAvailable': True,
        'image': 'mishti_doi.jpeg',
        'imageUrl': 'https://images.unsplash.com/photo-1488477181946-6428a0291777?w=400&h=300&fit=crop',
        'averageRating': 4.6,
        'totalRatings': 102,
        'isVegetarian': True,
        'calories': 150,
        'dateAdded': datetime.utcnow()
    },

    # Priya Nambiar's Kerala dishes [web:76][web:79]
    {
        '_id': '23',
        'cookEmail': 'priya@homemeals.com',
        'cookName': 'Priya Nambiar',
        'name': 'Kerala Fish Curry',
        'description': 'Coconut-based fish curry with curry leaves, kokum, and traditional Kerala spices.',
        'price': 175,
        'category': 'Lunch',
        'cuisine': 'Kerala',
        'prepTime': 30,
        'spiceLevel': 'Medium',
        'isAvailable': True,
        'image': 'fish_curry.jpeg',
        'imageUrl': 'https://images.unsplash.com/photo-1565299624946-b28f40a0ca4b?w=400&h=300&fit=crop',
        'averageRating': 4.7,
        'totalRatings': 98,
        'isVegetarian': False,
        'calories': 320,
        'dateAdded': datetime.utcnow()
    },
    {
        '_id': '24',
        'cookEmail': 'priya@homemeals.com',
        'cookName': 'Priya Nambiar',
        'name': 'Appam with Stew',
        'description': 'Fermented rice pancakes served with coconut milk-based vegetable or chicken stew.',
        'price': 120,
        'category': 'Breakfast',
        'cuisine': 'Kerala',
        'prepTime': 25,
        'spiceLevel': 'Low',
        'isAvailable': True,
        'image': 'appam_stew.jpeg',
        'imageUrl': 'https://images.unsplash.com/photo-1589301760014-d929f3979dbc?w=400&h=300&fit=crop',
        'averageRating': 4.5,
        'totalRatings': 76,
        'isVegetarian': True,
        'calories': 290,
        'dateAdded': datetime.utcnow()
    },
    {
        '_id': '25',
        'cookEmail': 'priya@homemeals.com',
        'cookName': 'Priya Nambiar',
        'name': 'Puttu with Kadala Curry',
        'description': 'Steamed rice cakes served with spiced black chickpea curry, a Kerala breakfast staple.',
        'price': 85,
        'category': 'Breakfast',
        'cuisine': 'Kerala',
        'prepTime': 30,
        'spiceLevel': 'Medium',
        'isAvailable': True,
        'image': 'puttu_kadala.jpeg',
        'imageUrl': 'https://images.unsplash.com/photo-1567188040759-fb8a883dc6d8?w=400&h=300&fit=crop',
        'averageRating': 4.4,
        'totalRatings': 67,
        'isVegetarian': True,
        'calories': 310,
        'dateAdded': datetime.utcnow()
    },
    {
        '_id': '26',
        'cookEmail': 'priya@homemeals.com',
        'cookName': 'Priya Nambiar',
        'name': 'Avial',
        'description': 'Mixed vegetable curry with coconut and yogurt, a traditional Kerala sadya dish.',
        'price': 95,
        'category': 'Lunch',
        'cuisine': 'Kerala',
        'prepTime': 35,
        'spiceLevel': 'Low',
        'isAvailable': True,
        'image': 'avial.jpeg',
        'imageUrl': 'https://images.unsplash.com/photo-1505253304499-671c55fb57fe?w=400&h=300&fit=crop',
        'averageRating': 4.3,
        'totalRatings': 54,
        'isVegetarian': True,
        'calories': 240,
        'dateAdded': datetime.utcnow()
    },
    {
        '_id': '27',
        'cookEmail': 'priya@homemeals.com',
        'cookName': 'Priya Nambiar',
        'name': 'Prawn Curry',
        'description': 'Kerala-style prawn curry cooked in coconut milk with aromatic spices.',
        'price': 210,
        'category': 'Dinner',
        'cuisine': 'Kerala',
        'prepTime': 35,
        'spiceLevel': 'Medium',
        'isAvailable': True,
        'image': 'prawn Curry.jpeg',
        'imageUrl': 'https://images.unsplash.com/photo-1565299624946-b28f40a0ca4b?w=400&h=300&fit=crop',
        'averageRating': 4.8,
        'totalRatings': 89,
        'isVegetarian': False,
        'calories': 380,
        'dateAdded': datetime.utcnow()
    }
]

def copy_profile_images():
    """Copy profile images from current directory to profiles folder if present"""
    try:
        image_mappings = {
            'boy1.jpg': 'boy1.jpg',
            'boy2.jpg': 'boy2.jpg',
            'boy3.jpg': 'boy3.jpg',
            'girl-1.jpg': 'girl-1.jpg',
            'girl2.jpg': 'girl2.jpg',
            'girl3.jpg': 'girl3.jpg'
        }
        for original, dest in image_mappings.items():
            src_path = os.path.join(BASE_DIR, original)
            dest_path = os.path.join(PROFILES_FOLDER, dest)
            if os.path.exists(src_path):
                if not os.path.exists(dest_path):
                    import shutil
                    shutil.copy2(src_path, dest_path)
                print(f"Profile image available: {dest}")
            else:
                # Ensure placeholder file exists for route safety
                if not os.path.exists(dest_path):
                    with open(dest_path, 'wb') as f:
                        f.write(b'')
                print(f"Placeholder created: {dest}")
        print("Profile images setup complete")
    except Exception as e:
        print(f"Error setting up profile images: {e}")

def optimize_food_image(image_file, max_size=(800, 600), quality=85):
    """Optimize food images for web display if Pillow available"""
    if not PIL_AVAILABLE:
        return image_file
    try:
        img = Image.open(image_file)
        if img.mode in ('RGBA', 'LA'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        output = io.BytesIO()
        img.save(output, format='JPEG', quality=quality, optimize=True)
        output.seek(0)
        return output
    except Exception as e:
        print(f"Image optimization error: {e}")
        return image_file

def init_sample_data():
    """Initialize sample data"""
    print("Initializing sample data with uploaded images...")
    copy_profile_images()
    if USE_MONGODB:
        users_col.delete_many({'type': 'cook'})
        menu_col.delete_many({})
        users_col.insert_many(sample_cooks.copy())
        menu_col.insert_many(sample_dishes.copy())
        print(f"Added {users_col.count_documents({'type': 'cook'})} home cooks")
        print(f"Added {menu_col.count_documents({})} dishes")
    else:
        global users_data, menu_data
        users_data = [u for u in users_data if u.get('type') != 'cook']
        menu_data = []
        users_data.extend(sample_cooks.copy())
        menu_data.extend(sample_dishes.copy())
        print(f"Added {len(sample_cooks)} home cooks (memory)")
        print(f"Added {len(sample_dishes)} dishes (memory)")

# STATIC FILE SERVING
@app.route('/static/<path:filename>')
def serve_static_file(filename):
    try:
        response = send_from_directory(STATIC_FOLDER, filename)
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Cache-Control'] = 'public, max-age=300'
        return response
    except Exception:
        return jsonify({'error': 'File not found'}), 404

@app.route('/static/profiles/<filename>')
def serve_profile_image(filename):
    try:
        filepath = os.path.join(PROFILES_FOLDER, filename)
        if not os.path.exists(filepath):
            return jsonify({'error': 'Profile image not found'}), 404
        response = send_from_directory(PROFILES_FOLDER, filename)
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Cache-Control'] = 'public, max-age=3600'
        return response
    except Exception:
        return jsonify({'error': 'Profile image error'}), 500

@app.route('/static/food/<filename>')
def serve_food_image(filename):
    try:
        filepath = os.path.join(FOOD_IMAGES_FOLDER, filename)
        if not os.path.exists(filepath):
            return jsonify({'error': 'Food image not found'}), 404
        response = send_from_directory(FOOD_IMAGES_FOLDER, filename)
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Cache-Control'] = 'public, max-age=3600'
        return response
    except Exception:
        return jsonify({'error': 'Food image error'}), 500

# API ROUTES
@app.route('/api/test', methods=['GET'])
def test():
    return jsonify({
        'message': 'Server is running!',
        'timestamp': datetime.utcnow(),
        'storage': 'MongoDB' if USE_MONGODB else 'Memory'
    }), 200

# GET ALL COOKS
@app.route('/api/cooks', methods=['GET'])
def get_cooks():
    try:
        if USE_MONGODB:
            cooks = list(users_col.find({'type': 'cook'}))
            cooks = [serialize_doc(cook) for cook in cooks]
        else:
            cooks = [cook.copy() for cook in users_data if cook.get('type') == 'cook']
        for cook in cooks:
            if cook.get('profilePic') and not str(cook['profilePic']).startswith('http'):
                cook['profilePicUrl'] = f'http://localhost:5000/static/profiles/{cook["profilePic"]}'
        return jsonify({'cooks': cooks, 'count': len(cooks)}), 200
    except Exception as e:
        return jsonify({'error': str(e), 'cooks': [], 'count': 0}), 500

# GET COOK DETAILS BY EMAIL
@app.route('/api/cooks/<cook_email>', methods=['GET'])
def get_cook_details(cook_email):
    try:
        if USE_MONGODB:
            cook = users_col.find_one({'email': cook_email, 'type': 'cook'})
            if cook:
                cook = serialize_doc(cook)
        else:
            cook = next((c for c in users_data if c['email'] == cook_email and c.get('type') == 'cook'), None)
        if not cook:
            return jsonify({'message': 'Cook not found'}), 404
        if cook.get('profilePic') and not str(cook['profilePic']).startswith('http'):
            cook['profilePicUrl'] = f'http://localhost:5000/static/profiles/{cook["profilePic"]}'
        return jsonify({'cook': cook}), 200
    except Exception as e:
        return jsonify({'message': f'Error: {str(e)}'}), 500

# GET DISHES BY COOK
@app.route('/api/cooks/<cook_email>/dishes', methods=['GET'])
def get_cook_dishes(cook_email):
    try:
        if USE_MONGODB:
            dishes = list(menu_col.find({'cookEmail': cook_email}))
            dishes = [serialize_doc(dish) for dish in dishes]
        else:
            dishes = [dish.copy() for dish in menu_data if dish.get('cookEmail') == cook_email]
        for dish in dishes:
            if dish.get('image') and not str(dish['image']).startswith('http'):
                dish['imageUrl'] = f'http://localhost:5000/static/food/{dish["image"]}'
            elif not dish.get('imageUrl'):
                dish['imageUrl'] = 'https://via.placeholder.com/400x300/ff6347/white?text=Delicious+Food'
        return jsonify({'dishes': dishes, 'count': len(dishes)}), 200
    except Exception as e:
        return jsonify({'error': str(e), 'dishes': [], 'count': 0}), 500

# ADD NEW FOOD ITEM (WITH IMAGE UPLOAD)
@app.route('/api/dishes/add', methods=['POST'])
def add_dish():
    try:
        # Handle multipart form data
        data = {
            'cookEmail': request.form.get('cookEmail'),
            'name': request.form.get('name'),
            'description': request.form.get('description'),
            'price': request.form.get('price'),
            'category': request.form.get('category'),
            'cuisine': request.form.get('cuisine'),
            'prepTime': request.form.get('prepTime'),
            'spiceLevel': request.form.get('spiceLevel'),
            'isVegetarian': str(request.form.get('isVegetarian')).lower() == 'true',
            'calories': request.form.get('calories')
        }
        dish_image = request.files.get('dishImage')

        # Validate required fields
        required_fields = ['cookEmail', 'name', 'description', 'price', 'category', 'cuisine', 'prepTime', 'spiceLevel']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'message': f'{field} is required'}), 400

        # Get cook details
        cook_email = data['cookEmail']
        if USE_MONGODB:
            cook = users_col.find_one({'email': cook_email, 'type': 'cook'})
        else:
            cook = next((c for c in users_data if c['email'] == cook_email and c.get('type') == 'cook'), None)
        if not cook:
            return jsonify({'message': 'Cook not found'}), 404

        # Handle dish image upload
        image_filename = None
        image_url = 'https://via.placeholder.com/400x300/ff6347/white?text=Delicious+Food'
        if dish_image and dish_image.filename:
            if allowed_file(dish_image.filename):
                original_filename = secure_filename(dish_image.filename)
                file_extension = original_filename.rsplit('.', 1)[1].lower()
                image_filename = f"dish_{cook_email.split('@')[0]}_{uuid.uuid4().hex[:8]}.{file_extension}"
                save_path = os.path.join(FOOD_IMAGES_FOLDER, image_filename)

                # Optimize if Pillow is available
                if PIL_AVAILABLE:
                    optimized_fileobj = optimize_food_image(dish_image.stream)
                    with open(save_path, 'wb') as out:
                        out.write(optimized_fileobj.read())
                else:
                    dish_image.save(save_path)

                image_url = f'http://localhost:5000/static/food/{image_filename}'
                print(f"Food image saved: {image_filename}")
            else:
                return jsonify({'message': 'Invalid image file type'}), 400

        # Prepare dish data
        dish_data = {
            'cookEmail': cook_email,
            'cookName': cook.get('name', 'Unknown Cook'),
            'name': data['name'],
            'description': data['description'],
            'price': int(float(data['price'])),
            'category': data['category'],
            'cuisine': data['cuisine'],
            'prepTime': int(float(data['prepTime'])),
            'spiceLevel': data['spiceLevel'],
            'isAvailable': True,
            'isVegetarian': data['isVegetarian'],
            'calories': int(float(data.get('calories', 0))) if data.get('calories') else 0,
            'image': image_filename,
            'imageUrl': image_url,
            'averageRating': 0.0,
            'totalRatings': 0,
            'dateAdded': datetime.utcnow()
        }

        # Save dish to database
        if USE_MONGODB:
            result = menu_col.insert_one(dish_data)
            dish_data['_id'] = str(result.inserted_id)
        else:
            dish_data['_id'] = str(uuid.uuid4())
            menu_data.append(dish_data)

        return jsonify({'message': 'Dish added successfully!', 'dish': serialize_doc(dish_data.copy())}), 201
    except Exception as e:
        print(f"Error adding dish: {str(e)}")
        return jsonify({'message': f'Error adding dish: {str(e)}'}), 500

# BULK UPLOAD FOOD IMAGES
@app.route('/api/dishes/bulk-upload-images', methods=['POST'])
def bulk_upload_food_images():
    try:
        cook_email = request.form.get('cookEmail')
        dish_names = request.form.getlist('dishNames[]') or request.form.getlist('dishNames')
        uploaded_files = request.files.getlist('foodImages[]') or request.files.getlist('foodImages')

        if not cook_email or not uploaded_files:
            return jsonify({'error': 'Cook email and images are required'}), 400

        # Validate cook
        if USE_MONGODB:
            cook = users_col.find_one({'email': cook_email, 'type': 'cook'})
        else:
            cook = next((c for c in users_data if c['email'] == cook_email and c.get('type') == 'cook'), None)
        if not cook:
            return jsonify({'error': 'Cook not found'}), 404

        uploaded_images = []
        for i, file in enumerate(uploaded_files):
            if not file or not file.filename or not allowed_file(file.filename):
                continue
            ext = secure_filename(file.filename).rsplit('.', 1)[1].lower()
            dish_name = dish_names[i] if i < len(dish_names) else f'dish_{i+1}'
            safe_dish = "_".join(dish_name.lower().split())
            fname = f"food_{cook_email.split('@')[0]}_{safe_dish}_{uuid.uuid4().hex[:8]}.{ext}"
            fpath = os.path.join(FOOD_IMAGES_FOLDER, fname)

            if PIL_AVAILABLE:
                optimized = optimize_food_image(file.stream)
                with open(fpath, 'wb') as out:
                    out.write(optimized.read())
            else:
                file.save(fpath)

            uploaded_images.append({
                'filename': fname,
                'url': f'http://localhost:5000/static/food/{fname}',
                'dishName': dish_name
            })

        return jsonify({'message': f'Successfully uploaded {len(uploaded_images)} food images', 'images': uploaded_images}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# REGISTRATION WITH PROFILE PICTURE SUPPORT
@app.route('/api/auth/register', methods=['POST'])
def register():
    try:
        # Handle multipart form data (with file upload)
        if request.content_type and 'multipart/form-data' in request.content_type:
            data = {
                'name': request.form.get('name'),
                'email': request.form.get('email'),
                'phone': request.form.get('phone'),
                'address': request.form.get('address'),
                'type': request.form.get('type'),
                'specialties': request.form.get('specialties'),
                'experience': request.form.get('experience')
            }
            profile_image = request.files.get('profileImage')
        else:
            # Handle JSON data (without file upload)
            data = request.get_json() or {}
            profile_image = None

        # Validate required fields
        required_fields = ['name', 'email', 'phone', 'address', 'type']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'message': f'{field} is required'}), 400

        email = data['email'].lower().strip()
        user_type = data['type'].lower().strip()

        # Check if user already exists
        if USE_MONGODB:
            existing = users_col.find_one({'email': email})
        else:
            existing = next((u for u in users_data if u['email'] == email), None)
        if existing:
            return jsonify({'message': 'Email already registered'}), 400

        # Prepare user data
        user_data = {
            'name': data['name'].strip(),
            'email': email,
            'phone': str(data['phone']).strip(),
            'address': data['address'].strip(),
            'type': user_type,
            'registrationDate': datetime.utcnow(),
            'isAvailable': True
        }

        # Handle cook-specific data
        if user_type == 'cook':
            specialties = (data.get('specialties') or '').strip()
            experience = data.get('experience')
            if not specialties or not experience:
                return jsonify({'message': 'Specialties and experience are required for cooks'}), 400
            user_data.update({
                'specialties': specialties,
                'experience': int(float(experience)),
                'description': f"Home cook specializing in {specialties}.",
                'averageRating': 0.0,
                'totalOrders': 0,
                'totalRatings': 0,
                'deliveryRadius': 10,
                'preparationTime': '30-45 mins'
            })
            # Handle profile image upload
            if profile_image and profile_image.filename:
                if allowed_file(profile_image.filename):
                    file_extension = secure_filename(profile_image.filename).rsplit('.', 1)[1].lower()
                    filename = f"profile_{email.split('@')[0]}_{uuid.uuid4().hex[:8]}.{file_extension}"
                    filepath = os.path.join(PROFILES_FOLDER, filename)
                    profile_image.save(filepath)
                    user_data['profilePic'] = filename
                    user_data['profilePicUrl'] = f'http://localhost:5000/static/profiles/{filename}'
                    print(f"Profile image saved: {filename}")
                else:
                    return jsonify({'message': 'Invalid image file type'}), 400
            else:
                # Use default placeholder
                initial = data["name"][0].upper() if data.get("name") else "C"
                user_data['profilePicUrl'] = f'https://via.placeholder.com/300x300/ff6347/white?text={initial}'

        # Save user to database
        if USE_MONGODB:
            result = users_col.insert_one(user_data)
            user_data['_id'] = str(result.inserted_id)
        else:
            users_data.append(user_data)

        return jsonify({'message': f"Welcome to HomeMeals Connect, {data['name']}!", 'user': serialize_doc(user_data.copy())}), 201
    except Exception as e:
        return jsonify({'message': f'Registration error: {str(e)}'}), 500

# LOGIN
@app.route('/api/auth/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        email = data.get('email', '').lower().strip()
        user_type = data.get('userType', '').lower().strip()

        if not email or not user_type:
            return jsonify({'message': 'Email and user type are required'}), 400

        if USE_MONGODB:
            user = users_col.find_one({'email': email, 'type': user_type})
            if user:
                user = serialize_doc(user)
        else:
            user = next((u for u in users_data if u['email'] == email and u['type'] == user_type), None)

        if user:
            if user.get('profilePic') and not str(user['profilePic']).startswith('http'):
                user['profilePicUrl'] = f'http://localhost:5000/static/profiles/{user["profilePic"]}'
            return jsonify({'message': f"Welcome back, {user['name']}!", 'user': user}), 200
        else:
            return jsonify({'message': 'User not found. Please register first.'}), 404
    except Exception as e:
        return jsonify({'message': f'Login error: {str(e)}'}), 500

if __name__ == '__main__':
    init_sample_data()
    print("\nHomeMeals Connect Backend Starting with UPLOADED IMAGES")
    print("PROFILE PICTURES ROUTE: /static/profiles/<filename>")
    print("FOOD PICTURES ROUTE: /static/food/<filename>")
    print("ADD DISH: POST /api/dishes/add (multipart/form-data)")
    print("BULK FOOD IMAGES: POST /api/dishes/bulk-upload-images (multipart/form-data)")
    app.run(debug=True, port=5000, host='0.0.0.0')
