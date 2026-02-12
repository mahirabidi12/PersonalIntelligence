import os
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
import jwt
import bcrypt

load_dotenv()

MONGO_URL = os.environ.get("MONGO_URL")
DB_NAME = os.environ.get("DB_NAME")
JWT_SECRET = os.environ.get("JWT_SECRET")

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

users_col = db["users"]
categories_col = db["categories"]
products_col = db["products"]
cart_col = db["cart"]
orders_col = db["orders"]
addresses_col = db["addresses"]


# ---- Pydantic Models ----
class RegisterReq(BaseModel):
    name: str
    email: str
    password: str
    mobile: str = ""

class LoginReq(BaseModel):
    email: str
    password: str

class AddToCartReq(BaseModel):
    product_id: str

class UpdateCartReq(BaseModel):
    cart_item_id: str
    quantity: int

class RemoveCartReq(BaseModel):
    cart_item_id: str

class AddressReq(BaseModel):
    address_line: str
    city: str
    state: str
    pincode: str
    mobile: str

class PlaceOrderReq(BaseModel):
    address_id: str
    payment_method: str = "cod"


def create_token(user_id: str) -> str:
    return jwt.encode({"user_id": user_id, "exp": datetime.now(timezone.utc) + timedelta(days=7)}, JWT_SECRET, algorithm="HS256")

def verify_token(token: str) -> str:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])["user_id"]
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_current_user(authorization: str = None):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing auth")
    token = authorization.replace("Bearer ", "")
    user_id = verify_token(token)
    user = await users_col.find_one({"user_id": user_id}, {"_id": 0, "password": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# ---- Seed Data ----
CATEGORIES = [
    {"name": "Fruits & Vegetables", "image": "https://images.unsplash.com/photo-1610832958506-aa56368176cf?w=200&q=80", "icon": "🥬"},
    {"name": "Dairy & Bread", "image": "https://images.unsplash.com/photo-1628088062854-d1870b4553da?w=200&q=80", "icon": "🥛"},
    {"name": "Snacks & Munchies", "image": "https://images.unsplash.com/photo-1621939514649-280e2ee25f60?w=200&q=80", "icon": "🍿"},
    {"name": "Cold Drinks & Juices", "image": "https://images.unsplash.com/photo-1534353473418-4cfa6c56fd38?w=200&q=80", "icon": "🥤"},
    {"name": "Instant & Frozen Food", "image": "https://images.unsplash.com/photo-1612929633738-8fe44f7ec841?w=200&q=80", "icon": "🍜"},
    {"name": "Tea, Coffee & Health Drinks", "image": "https://images.unsplash.com/photo-1556679343-c7306c1976bc?w=200&q=80", "icon": "☕"},
    {"name": "Atta, Rice & Dal", "image": "https://images.unsplash.com/photo-1586201375761-83865001e31c?w=200&q=80", "icon": "🌾"},
    {"name": "Masala, Oil & More", "image": "https://images.unsplash.com/photo-1596040033229-a9821ebd058d?w=200&q=80", "icon": "🫙"},
    {"name": "Sweet Tooth", "image": "https://images.unsplash.com/photo-1551024506-0bccd828d307?w=200&q=80", "icon": "🍫"},
    {"name": "Baby Care", "image": "https://images.unsplash.com/photo-1515488042361-ee00e0ddd4e4?w=200&q=80", "icon": "👶"},
    {"name": "Cleaning Essentials", "image": "https://images.unsplash.com/photo-1585421514738-01798e348b17?w=200&q=80", "icon": "🧹"},
    {"name": "Personal Care", "image": "https://images.unsplash.com/photo-1556228578-0d85b1a4d571?w=200&q=80", "icon": "🧴"},
]

PRODUCTS_DATA = [
    # Fruits & Vegetables
    {"name": "Fresh Banana", "category_idx": 0, "price": 45, "discount": 10, "unit": "1 dozen", "stock": 100, "description": "Fresh yellow bananas, perfect for breakfast", "image": "https://images.unsplash.com/photo-1571771894821-ce9b6c11b08e?w=400&q=80"},
    {"name": "Red Apple", "category_idx": 0, "price": 180, "discount": 5, "unit": "1 kg", "stock": 80, "description": "Crisp and juicy Shimla apples", "image": "https://images.unsplash.com/photo-1560806887-1e4cd0b6cbd6?w=400&q=80"},
    {"name": "Fresh Tomato", "category_idx": 0, "price": 35, "discount": 0, "unit": "500 g", "stock": 150, "description": "Farm fresh red tomatoes", "image": "https://images.unsplash.com/photo-1546470427-0d4db154ceb8?w=400&q=80"},
    {"name": "Onion", "category_idx": 0, "price": 40, "discount": 0, "unit": "1 kg", "stock": 200, "description": "Premium quality onions", "image": "https://images.unsplash.com/photo-1618512496248-a07fe83aa8cb?w=400&q=80"},
    {"name": "Potato", "category_idx": 0, "price": 30, "discount": 0, "unit": "1 kg", "stock": 200, "description": "Fresh potatoes for everyday cooking", "image": "https://images.unsplash.com/photo-1518977676601-b53f82ber40d?w=400&q=80"},
    {"name": "Green Capsicum", "category_idx": 0, "price": 60, "discount": 15, "unit": "500 g", "stock": 60, "description": "Crunchy green bell peppers", "image": "https://images.unsplash.com/photo-1563565375-f3fdfdbefa83?w=400&q=80"},
    {"name": "Fresh Spinach", "category_idx": 0, "price": 25, "discount": 0, "unit": "1 bunch", "stock": 100, "description": "Organic farm fresh palak", "image": "https://images.unsplash.com/photo-1576045057995-568f588f82fb?w=400&q=80"},
    {"name": "Mango (Alphonso)", "category_idx": 0, "price": 350, "discount": 10, "unit": "1 kg", "stock": 40, "description": "Premium Ratnagiri Alphonso mangoes", "image": "https://images.unsplash.com/photo-1553279768-865429fa0078?w=400&q=80"},
    # Dairy & Bread
    {"name": "Amul Toned Milk", "category_idx": 1, "price": 30, "discount": 0, "unit": "500 ml", "stock": 200, "description": "Amul Taaza toned milk", "image": "https://images.unsplash.com/photo-1563636619-e9143da7973b?w=400&q=80"},
    {"name": "Amul Butter", "category_idx": 1, "price": 56, "discount": 5, "unit": "100 g", "stock": 120, "description": "Utterly butterly delicious", "image": "https://images.unsplash.com/photo-1589985270826-4b7bb135bc9d?w=400&q=80"},
    {"name": "White Bread", "category_idx": 1, "price": 40, "discount": 0, "unit": "400 g", "stock": 80, "description": "Soft & fresh white bread", "image": "https://images.unsplash.com/photo-1509440159596-0249088772ff?w=400&q=80"},
    {"name": "Paneer (Fresh)", "category_idx": 1, "price": 90, "discount": 10, "unit": "200 g", "stock": 60, "description": "Fresh cottage cheese", "image": "https://images.unsplash.com/photo-1631452180519-c014fe946bc7?w=400&q=80"},
    {"name": "Curd (Dahi)", "category_idx": 1, "price": 35, "discount": 0, "unit": "400 g", "stock": 100, "description": "Thick and creamy curd", "image": "https://images.unsplash.com/photo-1488477181946-6428a0291777?w=400&q=80"},
    {"name": "Cheese Slices", "category_idx": 1, "price": 120, "discount": 8, "unit": "200 g", "stock": 50, "description": "Processed cheese slices", "image": "https://images.unsplash.com/photo-1486297678162-eb2a19b0a32d?w=400&q=80"},
    {"name": "Eggs (Pack of 6)", "category_idx": 1, "price": 48, "discount": 0, "unit": "6 pcs", "stock": 150, "description": "Farm fresh eggs", "image": "https://images.unsplash.com/photo-1582722872445-44dc5f7e3c8f?w=400&q=80"},
    # Snacks & Munchies
    {"name": "Lay's Classic Salted", "category_idx": 2, "price": 20, "discount": 0, "unit": "52 g", "stock": 200, "description": "Crispy potato chips", "image": "https://images.unsplash.com/photo-1566478989037-eec170784d0b?w=400&q=80"},
    {"name": "Kurkure Masala Munch", "category_idx": 2, "price": 20, "discount": 0, "unit": "75 g", "stock": 180, "description": "Tedha hai par mera hai", "image": "https://images.unsplash.com/photo-1604335399105-a0c585fd81a1?w=400&q=80"},
    {"name": "Haldiram's Aloo Bhujia", "category_idx": 2, "price": 85, "discount": 10, "unit": "200 g", "stock": 100, "description": "Traditional namkeen snack", "image": "https://images.unsplash.com/photo-1599490659213-e2b9527bd087?w=400&q=80"},
    {"name": "Oreo Chocolate Cookies", "category_idx": 2, "price": 30, "discount": 0, "unit": "120 g", "stock": 150, "description": "Twist, lick, dunk!", "image": "https://images.unsplash.com/photo-1558961363-fa8fdf82db35?w=400&q=80"},
    {"name": "Pringles Original", "category_idx": 2, "price": 149, "discount": 12, "unit": "165 g", "stock": 60, "description": "Once you pop you can't stop", "image": "https://images.unsplash.com/photo-1621447504864-d8686e12698c?w=400&q=80"},
    {"name": "Dark Fantasy Choco Fills", "category_idx": 2, "price": 40, "discount": 0, "unit": "75 g", "stock": 120, "description": "Premium chocolate cookies", "image": "https://images.unsplash.com/photo-1499636136210-6f4ee915583e?w=400&q=80"},
    # Cold Drinks & Juices
    {"name": "Coca-Cola", "category_idx": 3, "price": 40, "discount": 0, "unit": "750 ml", "stock": 200, "description": "Thanda matlab Coca-Cola", "image": "https://images.unsplash.com/photo-1554866585-cd94860890b7?w=400&q=80"},
    {"name": "Pepsi", "category_idx": 3, "price": 40, "discount": 0, "unit": "750 ml", "stock": 180, "description": "Yeh Dil Maange More", "image": "https://images.unsplash.com/photo-1629203851122-3726ecdf080e?w=400&q=80"},
    {"name": "Real Mango Juice", "category_idx": 3, "price": 99, "discount": 10, "unit": "1 L", "stock": 80, "description": "100% fruit juice", "image": "https://images.unsplash.com/photo-1546173159-315724a31696?w=400&q=80"},
    {"name": "Sprite", "category_idx": 3, "price": 40, "discount": 0, "unit": "750 ml", "stock": 150, "description": "Clear hai!", "image": "https://images.unsplash.com/photo-1625772299848-391b6a87d7b3?w=400&q=80"},
    {"name": "Frooti Mango", "category_idx": 3, "price": 15, "discount": 0, "unit": "200 ml", "stock": 250, "description": "Mango Frooti, fresh n juicy", "image": "https://images.unsplash.com/photo-1600271886742-f049cd451bba?w=400&q=80"},
    {"name": "Red Bull Energy", "category_idx": 3, "price": 115, "discount": 5, "unit": "250 ml", "stock": 60, "description": "Gives you wings", "image": "https://images.unsplash.com/photo-1613481205692-85ae1ebeb3a5?w=400&q=80"},
    # Instant & Frozen Food
    {"name": "Maggi 2-Minute Noodles", "category_idx": 4, "price": 14, "discount": 0, "unit": "70 g", "stock": 300, "description": "2-Minute Masala Noodles", "image": "https://images.unsplash.com/photo-1612929633738-8fe44f7ec841?w=400&q=80"},
    {"name": "Top Ramen Curry Noodles", "category_idx": 4, "price": 15, "discount": 0, "unit": "70 g", "stock": 200, "description": "Smoodles with curry flavor", "image": "https://images.unsplash.com/photo-1569718212165-3a8278d5f624?w=400&q=80"},
    {"name": "MTR Ready to Eat Poha", "category_idx": 4, "price": 65, "discount": 8, "unit": "180 g", "stock": 80, "description": "Just heat and eat", "image": "https://images.unsplash.com/photo-1567337710282-00832b415979?w=400&q=80"},
    {"name": "McCain French Fries", "category_idx": 4, "price": 130, "discount": 15, "unit": "420 g", "stock": 50, "description": "Crispy golden french fries", "image": "https://images.unsplash.com/photo-1573080496219-bb080dd4f877?w=400&q=80"},
    {"name": "Cup Noodles (Mazedaar Masala)", "category_idx": 4, "price": 45, "discount": 0, "unit": "70 g", "stock": 120, "description": "On-the-go noodles", "image": "https://images.unsplash.com/photo-1626700051175-6818013e1d4f?w=400&q=80"},
    # Tea, Coffee & Health Drinks
    {"name": "Tata Tea Gold", "category_idx": 5, "price": 160, "discount": 5, "unit": "250 g", "stock": 100, "description": "Desh ki chai", "image": "https://images.unsplash.com/photo-1556679343-c7306c1976bc?w=400&q=80"},
    {"name": "Nescafe Classic Coffee", "category_idx": 5, "price": 195, "discount": 8, "unit": "100 g", "stock": 80, "description": "It all starts with a Nescafe", "image": "https://images.unsplash.com/photo-1559056199-641a0ac8b55e?w=400&q=80"},
    {"name": "Bournvita", "category_idx": 5, "price": 220, "discount": 10, "unit": "500 g", "stock": 70, "description": "Taiyari jeet ki", "image": "https://images.unsplash.com/photo-1517578239113-b03992dcdd25?w=400&q=80"},
    {"name": "Green Tea (Lipton)", "category_idx": 5, "price": 145, "discount": 12, "unit": "25 bags", "stock": 60, "description": "Pure & light green tea", "image": "https://images.unsplash.com/photo-1556881286-fc6915169721?w=400&q=80"},
    {"name": "Horlicks Classic Malt", "category_idx": 5, "price": 280, "discount": 8, "unit": "500 g", "stock": 50, "description": "Taller, stronger, sharper", "image": "https://images.unsplash.com/photo-1544787219-7f47ccb76574?w=400&q=80"},
    # Atta, Rice & Dal
    {"name": "Aashirvaad Atta", "category_idx": 6, "price": 280, "discount": 5, "unit": "5 kg", "stock": 60, "description": "100% whole wheat atta", "image": "https://images.unsplash.com/photo-1574323347407-f5e1ad6d020b?w=400&q=80"},
    {"name": "India Gate Basmati Rice", "category_idx": 6, "price": 450, "discount": 10, "unit": "5 kg", "stock": 40, "description": "Premium aged basmati rice", "image": "https://images.unsplash.com/photo-1586201375761-83865001e31c?w=400&q=80"},
    {"name": "Toor Dal", "category_idx": 6, "price": 150, "discount": 8, "unit": "1 kg", "stock": 80, "description": "Premium arhar dal", "image": "https://images.unsplash.com/photo-1585996746418-7f563f10aabc?w=400&q=80"},
    {"name": "Moong Dal", "category_idx": 6, "price": 130, "discount": 5, "unit": "1 kg", "stock": 70, "description": "Split green gram", "image": "https://images.unsplash.com/photo-1613743983303-b3e89f8a2b80?w=400&q=80"},
    {"name": "Chana Dal", "category_idx": 6, "price": 110, "discount": 0, "unit": "1 kg", "stock": 90, "description": "Split chickpeas", "image": "https://images.unsplash.com/photo-1515543904851-00d9a23ebe3c?w=400&q=80"},
    {"name": "Sooji (Semolina)", "category_idx": 6, "price": 45, "discount": 0, "unit": "500 g", "stock": 100, "description": "Fine rava for upma & halwa", "image": "https://images.unsplash.com/photo-1574323347407-f5e1ad6d020b?w=400&q=80"},
    # Masala, Oil & More
    {"name": "MDH Garam Masala", "category_idx": 7, "price": 78, "discount": 5, "unit": "100 g", "stock": 100, "description": "Asli masale sach sach", "image": "https://images.unsplash.com/photo-1596040033229-a9821ebd058d?w=400&q=80"},
    {"name": "Fortune Sunflower Oil", "category_idx": 7, "price": 160, "discount": 10, "unit": "1 L", "stock": 80, "description": "Refined sunflower oil", "image": "https://images.unsplash.com/photo-1474979266404-7eaacbcd87c5?w=400&q=80"},
    {"name": "Tata Salt", "category_idx": 7, "price": 22, "discount": 0, "unit": "1 kg", "stock": 200, "description": "Desh ka namak", "image": "https://images.unsplash.com/photo-1518110925495-5fe2c8f2be87?w=400&q=80"},
    {"name": "Haldi Powder", "category_idx": 7, "price": 55, "discount": 0, "unit": "100 g", "stock": 120, "description": "Pure turmeric powder", "image": "https://images.unsplash.com/photo-1615485500704-8e990f9900f7?w=400&q=80"},
    {"name": "Red Chilli Powder", "category_idx": 7, "price": 65, "discount": 5, "unit": "100 g", "stock": 100, "description": "Premium lal mirch powder", "image": "https://images.unsplash.com/photo-1599909533408-00c7eb444a60?w=400&q=80"},
    {"name": "Mustard Oil", "category_idx": 7, "price": 180, "discount": 8, "unit": "1 L", "stock": 60, "description": "Pure kachi ghani mustard oil", "image": "https://images.unsplash.com/photo-1474979266404-7eaacbcd87c5?w=400&q=80"},
    # Sweet Tooth
    {"name": "Cadbury Dairy Milk", "category_idx": 8, "price": 50, "discount": 0, "unit": "50 g", "stock": 200, "description": "Kuch meetha ho jaaye", "image": "https://images.unsplash.com/photo-1587132137056-bfbf0166836e?w=400&q=80"},
    {"name": "KitKat", "category_idx": 8, "price": 30, "discount": 0, "unit": "37.3 g", "stock": 180, "description": "Have a break, have a KitKat", "image": "https://images.unsplash.com/photo-1582176604856-e824b4736522?w=400&q=80"},
    {"name": "Gulab Jamun (Haldiram's)", "category_idx": 8, "price": 99, "discount": 10, "unit": "500 g", "stock": 60, "description": "Ready to eat gulab jamun", "image": "https://images.unsplash.com/photo-1666190059674-796c4fa2ab09?w=400&q=80"},
    {"name": "Rasgulla (Bikaji)", "category_idx": 8, "price": 120, "discount": 5, "unit": "500 g", "stock": 50, "description": "Soft spongy rasgulla", "image": "https://images.unsplash.com/photo-1643364054688-4e4a25a0d399?w=400&q=80"},
    {"name": "5 Star Chocolate", "category_idx": 8, "price": 20, "discount": 0, "unit": "40 g", "stock": 200, "description": "Jo khaye kho jaaye", "image": "https://images.unsplash.com/photo-1575377427642-087cf684f29d?w=400&q=80"},
    # Baby Care
    {"name": "Pampers Diapers (S)", "category_idx": 9, "price": 399, "discount": 15, "unit": "Pack of 22", "stock": 30, "description": "All night dryness", "image": "https://images.unsplash.com/photo-1544367567-0f2fcb009e0b?w=400&q=80"},
    {"name": "Cerelac Baby Food", "category_idx": 9, "price": 255, "discount": 10, "unit": "300 g", "stock": 40, "description": "Stage 1 wheat apple", "image": "https://images.unsplash.com/photo-1515488042361-ee00e0ddd4e4?w=400&q=80"},
    {"name": "Johnson's Baby Soap", "category_idx": 9, "price": 65, "discount": 0, "unit": "100 g", "stock": 80, "description": "Gentle for baby skin", "image": "https://images.unsplash.com/photo-1585232004423-244e0e6904e3?w=400&q=80"},
    # Cleaning Essentials
    {"name": "Vim Dishwash Gel", "category_idx": 10, "price": 99, "discount": 10, "unit": "500 ml", "stock": 100, "description": "99.9% germ kill", "image": "https://images.unsplash.com/photo-1585232004423-244e0e6904e3?w=400&q=80"},
    {"name": "Harpic Toilet Cleaner", "category_idx": 10, "price": 85, "discount": 5, "unit": "500 ml", "stock": 80, "description": "10x better cleaning", "image": "https://images.unsplash.com/photo-1585421514738-01798e348b17?w=400&q=80"},
    {"name": "Surf Excel Matic", "category_idx": 10, "price": 245, "discount": 12, "unit": "1 kg", "stock": 60, "description": "Tough stain removal", "image": "https://images.unsplash.com/photo-1610557892470-55d9e80c0bce?w=400&q=80"},
    # Personal Care
    {"name": "Dove Soap", "category_idx": 11, "price": 55, "discount": 0, "unit": "100 g", "stock": 120, "description": "1/4 moisturising cream", "image": "https://images.unsplash.com/photo-1556228578-0d85b1a4d571?w=400&q=80"},
    {"name": "Colgate MaxFresh", "category_idx": 11, "price": 95, "discount": 8, "unit": "150 g", "stock": 100, "description": "Cooling crystal toothpaste", "image": "https://images.unsplash.com/photo-1559304787-e8b067e0b0c4?w=400&q=80"},
    {"name": "Head & Shoulders Shampoo", "category_idx": 11, "price": 190, "discount": 10, "unit": "340 ml", "stock": 70, "description": "Anti-dandruff shampoo", "image": "https://images.unsplash.com/photo-1631729371254-42c2892f0e6e?w=400&q=80"},
    {"name": "Nivea Body Lotion", "category_idx": 11, "price": 220, "discount": 12, "unit": "400 ml", "stock": 50, "description": "48H moisture care", "image": "https://images.unsplash.com/photo-1556228578-0d85b1a4d571?w=400&q=80"},
]


async def seed_database():
    existing = await categories_col.count_documents({})
    if existing > 0:
        return

    cat_ids = []
    for cat_data in CATEGORIES:
        cat_id = str(uuid.uuid4())
        await categories_col.insert_one({
            "category_id": cat_id,
            "name": cat_data["name"],
            "image": cat_data["image"],
            "icon": cat_data["icon"],
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        cat_ids.append(cat_id)

    for prod_data in PRODUCTS_DATA:
        prod_id = str(uuid.uuid4())
        cat_idx = prod_data["category_idx"]
        await products_col.insert_one({
            "product_id": prod_id,
            "name": prod_data["name"],
            "category_id": cat_ids[cat_idx],
            "category_name": CATEGORIES[cat_idx]["name"],
            "price": prod_data["price"],
            "discount": prod_data["discount"],
            "unit": prod_data["unit"],
            "stock": prod_data["stock"],
            "description": prod_data["description"],
            "image": prod_data["image"],
            "publish": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

    # Seed a demo user
    hashed = bcrypt.hashpw("password123".encode(), bcrypt.gensalt()).decode()
    await users_col.insert_one({
        "user_id": str(uuid.uuid4()),
        "name": "Demo User",
        "email": "demo@blinkit2.com",
        "password": hashed,
        "mobile": "9876543210",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    await users_col.create_index("user_id", unique=True)
    await users_col.create_index("email", unique=True)
    await products_col.create_index("product_id", unique=True)
    await products_col.create_index("category_id")
    await products_col.create_index([("name", "text"), ("description", "text")])
    await categories_col.create_index("category_id", unique=True)
    await cart_col.create_index("user_id")
    await orders_col.create_index("user_id")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await seed_database()
    yield

app = FastAPI(title="Blinkit2 API", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


# ---- Auth ----
@app.post("/api/auth/register")
async def register(req: RegisterReq):
    existing = await users_col.find_one({"email": req.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user_id = str(uuid.uuid4())
    hashed = bcrypt.hashpw(req.password.encode(), bcrypt.gensalt()).decode()
    await users_col.insert_one({
        "user_id": user_id, "name": req.name, "email": req.email,
        "password": hashed, "mobile": req.mobile,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    token = create_token(user_id)
    return {"token": token, "user_id": user_id, "name": req.name}

@app.post("/api/auth/login")
async def login(req: LoginReq):
    user = await users_col.find_one({"email": req.email})
    if not user or not bcrypt.checkpw(req.password.encode(), user["password"].encode()):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token(user["user_id"])
    return {"token": token, "user_id": user["user_id"], "name": user["name"], "email": user["email"]}

@app.get("/api/auth/me")
async def get_me(authorization: str = Query(None)):
    return await get_current_user(authorization)


# ---- Categories ----
@app.get("/api/categories")
async def get_categories():
    cats = await categories_col.find({}, {"_id": 0}).to_list(100)
    return {"data": cats}


# ---- Products ----
@app.get("/api/products")
async def get_products(category_id: str = None, search: str = None, page: int = 1, limit: int = 20):
    query = {"publish": True}
    if category_id:
        query["category_id"] = category_id
    if search:
        query["$text"] = {"$search": search}
    skip = (page - 1) * limit
    products = await products_col.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    total = await products_col.count_documents(query)
    return {"data": products, "total": total, "page": page, "pages": -(-total // limit)}

@app.get("/api/products/{product_id}")
async def get_product(product_id: str):
    prod = await products_col.find_one({"product_id": product_id}, {"_id": 0})
    if not prod:
        raise HTTPException(status_code=404, detail="Product not found")
    return prod

@app.get("/api/products/category/{category_id}")
async def get_products_by_category(category_id: str, limit: int = 15):
    products = await products_col.find({"category_id": category_id, "publish": True}, {"_id": 0}).limit(limit).to_list(limit)
    return {"data": products}


# ---- Cart ----
@app.get("/api/cart")
async def get_cart(authorization: str = Query(None)):
    user = await get_current_user(authorization)
    items = await cart_col.find({"user_id": user["user_id"]}, {"_id": 0}).to_list(100)
    enriched = []
    for item in items:
        product = await products_col.find_one({"product_id": item["product_id"]}, {"_id": 0})
        if product:
            enriched.append({**item, "product": product})
    return {"data": enriched}

@app.post("/api/cart/add")
async def add_to_cart(req: AddToCartReq, authorization: str = Query(None)):
    user = await get_current_user(authorization)
    existing = await cart_col.find_one({"user_id": user["user_id"], "product_id": req.product_id})
    if existing:
        await cart_col.update_one(
            {"user_id": user["user_id"], "product_id": req.product_id},
            {"$inc": {"quantity": 1}}
        )
        return {"message": "Quantity updated"}
    cart_item_id = str(uuid.uuid4())
    await cart_col.insert_one({
        "cart_item_id": cart_item_id,
        "user_id": user["user_id"],
        "product_id": req.product_id,
        "quantity": 1,
    })
    return {"message": "Added to cart", "cart_item_id": cart_item_id}

@app.put("/api/cart/update")
async def update_cart(req: UpdateCartReq, authorization: str = Query(None)):
    user = await get_current_user(authorization)
    if req.quantity <= 0:
        await cart_col.delete_one({"cart_item_id": req.cart_item_id, "user_id": user["user_id"]})
        return {"message": "Item removed"}
    await cart_col.update_one(
        {"cart_item_id": req.cart_item_id, "user_id": user["user_id"]},
        {"$set": {"quantity": req.quantity}}
    )
    return {"message": "Cart updated"}

@app.delete("/api/cart/remove")
async def remove_from_cart(req: RemoveCartReq, authorization: str = Query(None)):
    user = await get_current_user(authorization)
    await cart_col.delete_one({"cart_item_id": req.cart_item_id, "user_id": user["user_id"]})
    return {"message": "Removed from cart"}

@app.delete("/api/cart/clear")
async def clear_cart(authorization: str = Query(None)):
    user = await get_current_user(authorization)
    await cart_col.delete_many({"user_id": user["user_id"]})
    return {"message": "Cart cleared"}


# ---- Address ----
@app.get("/api/addresses")
async def get_addresses(authorization: str = Query(None)):
    user = await get_current_user(authorization)
    addrs = await addresses_col.find({"user_id": user["user_id"]}, {"_id": 0}).to_list(20)
    return {"data": addrs}

@app.post("/api/addresses")
async def add_address(req: AddressReq, authorization: str = Query(None)):
    user = await get_current_user(authorization)
    addr_id = str(uuid.uuid4())
    await addresses_col.insert_one({
        "address_id": addr_id,
        "user_id": user["user_id"],
        "address_line": req.address_line,
        "city": req.city,
        "state": req.state,
        "pincode": req.pincode,
        "mobile": req.mobile,
    })
    return {"message": "Address added", "address_id": addr_id}


# ---- Orders ----
@app.post("/api/orders")
async def place_order(req: PlaceOrderReq, authorization: str = Query(None)):
    user = await get_current_user(authorization)
    user_id = user["user_id"]

    cart_items = await cart_col.find({"user_id": user_id}).to_list(100)
    if not cart_items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    items = []
    subtotal = 0
    for ci in cart_items:
        prod = await products_col.find_one({"product_id": ci["product_id"]}, {"_id": 0})
        if prod:
            price = prod["price"]
            if prod.get("discount"):
                price = round(price * (1 - prod["discount"] / 100))
            item_total = price * ci["quantity"]
            subtotal += item_total
            items.append({
                "product_id": prod["product_id"],
                "name": prod["name"],
                "image": prod["image"],
                "price": price,
                "quantity": ci["quantity"],
                "unit": prod["unit"],
                "total": item_total,
            })

    delivery_fee = 0 if subtotal >= 199 else 25
    total = subtotal + delivery_fee
    order_id = f"BK2-{str(uuid.uuid4())[:8].upper()}"

    await orders_col.insert_one({
        "order_id": order_id,
        "user_id": user_id,
        "items": items,
        "address_id": req.address_id,
        "payment_method": req.payment_method,
        "subtotal": subtotal,
        "delivery_fee": delivery_fee,
        "total": total,
        "status": "confirmed",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "estimated_delivery": "10 minutes",
    })

    await cart_col.delete_many({"user_id": user_id})

    return {
        "message": "Order placed successfully!",
        "order_id": order_id,
        "total": total,
        "estimated_delivery": "10 minutes",
    }

@app.get("/api/orders")
async def get_orders(authorization: str = Query(None)):
    user = await get_current_user(authorization)
    ords = await orders_col.find({"user_id": user["user_id"]}, {"_id": 0}).sort("created_at", -1).to_list(50)
    return {"data": ords}


@app.get("/api/health")
async def health():
    return {"status": "ok", "app": "Blinkit2"}
