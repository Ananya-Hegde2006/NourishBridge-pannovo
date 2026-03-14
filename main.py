import fastapi
import fastapi.middleware.cors
from pydantic import BaseModel, EmailStr
from typing import Optional
import json
import os
import uuid
from datetime import datetime

app = fastapi.FastAPI(title="NourishBridge API")

# CORS middleware
app.add_middleware(
    fastapi.middleware.cors.CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data file paths
DATA_DIR = os.path.dirname(os.path.abspath(__file__))
USERS_FILE = os.path.join(DATA_DIR, "users.json")
FOOD_FILE = os.path.join(DATA_DIR, "food_data.json")

# Initialize data files if they don't exist
def init_data_files():
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w") as f:
            json.dump([], f)
    if not os.path.exists(FOOD_FILE):
        with open(FOOD_FILE, "w") as f:
            json.dump([], f)

init_data_files()

# Helper functions
def load_users():
    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

def load_donations():
    try:
        with open(FOOD_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_donations(donations):
    with open(FOOD_FILE, "w") as f:
        json.dump(donations, f, indent=2)

# Pydantic models
class Address(BaseModel):
    street: str
    area: str
    city: str = "Mangalore"
    state: str = "Karnataka"
    pincode: str

class RestaurantRegister(BaseModel):
    type: str = "restaurant"
    restaurantName: str
    ownerName: str
    email: str
    phone: str
    password: str
    address: Address

class CentreRegister(BaseModel):
    type: str = "centre"
    centreName: str
    contactPerson: str
    email: str
    phone: str
    password: str
    address: Address

class LoginRequest(BaseModel):
    email: str
    password: str
    type: str

class FoodDonation(BaseModel):
    restaurantName: str
    restaurantEmail: str
    foodItem: str
    quantity: str
    preparedTime: str
    pickupDeadline: str
    phone: str
    address: str
    status: str = "Available"

class FoodRequest(BaseModel):
    centreEmail: str
    centreName: str

# API Endpoints

@app.get("/health")
async def health():
    return {"status": "ok", "service": "NourishBridge API"}

@app.post("/register")
async def register(data: dict):
    users = load_users()
    
    # Check if email already exists
    email = data.get("email", "").lower()
    if any(u.get("email", "").lower() == email for u in users):
        raise fastapi.HTTPException(status_code=400, detail="Email already registered")
    
    # Validate phone
    phone = data.get("phone", "")
    if len(phone) != 10 or not phone.isdigit():
        raise fastapi.HTTPException(status_code=400, detail="Phone number must be 10 digits")
    
    # Validate password
    password = data.get("password", "")
    if len(password) < 8:
        raise fastapi.HTTPException(status_code=400, detail="Password must be at least 8 characters")
    
    # Add user ID and created timestamp
    data["id"] = str(uuid.uuid4())
    data["email"] = email
    data["createdAt"] = datetime.now().isoformat()
    
    users.append(data)
    save_users(users)
    
    return {"message": "Registration successful", "userId": data["id"]}

@app.post("/login")
async def login(request: LoginRequest):
    users = load_users()
    
    email = request.email.lower()
    user = None
    
    for u in users:
        if u.get("email", "").lower() == email and u.get("password") == request.password:
            if u.get("type") == request.type:
                user = u
                break
    
    if not user:
        raise fastapi.HTTPException(status_code=401, detail="Invalid email or password")
    
    # Return user data (without password)
    user_data = {k: v for k, v in user.items() if k != "password"}
    
    return {"message": "Login successful", "user": user_data}

@app.post("/add_food")
async def add_food(donation: FoodDonation):
    donations = load_donations()
    
    donation_data = donation.model_dump()
    donation_data["id"] = str(uuid.uuid4())
    donation_data["createdAt"] = datetime.now().isoformat()
    donation_data["requestedBy"] = None
    donation_data["requestedByName"] = None
    
    donations.append(donation_data)
    save_donations(donations)
    
    return {"message": "Food donation added successfully", "donationId": donation_data["id"]}

@app.get("/donations")
async def get_donations():
    donations = load_donations()
    # Sort by created date (newest first)
    donations.sort(key=lambda x: x.get("createdAt", ""), reverse=True)
    return donations

@app.get("/donations/{donation_id}")
async def get_donation(donation_id: str):
    donations = load_donations()
    
    for donation in donations:
        if donation.get("id") == donation_id:
            return donation
    
    raise fastapi.HTTPException(status_code=404, detail="Donation not found")

@app.post("/request_food/{donation_id}")
async def request_food(donation_id: str, request: FoodRequest):
    donations = load_donations()
    
    for donation in donations:
        if donation.get("id") == donation_id:
            if donation.get("status") != "Available":
                raise fastapi.HTTPException(status_code=400, detail="This food is no longer available")
            
            donation["status"] = "Picked"
            donation["requestedBy"] = request.centreEmail
            donation["requestedByName"] = request.centreName
            donation["requestedAt"] = datetime.now().isoformat()
            
            save_donations(donations)
            return {"message": "Food requested successfully"}
    
    raise fastapi.HTTPException(status_code=404, detail="Donation not found")

@app.post("/mark_delivered/{donation_id}")
async def mark_delivered(donation_id: str):
    donations = load_donations()
    
    for donation in donations:
        if donation.get("id") == donation_id:
            if donation.get("status") != "Picked":
                raise fastapi.HTTPException(status_code=400, detail="Cannot mark as delivered")
            
            donation["status"] = "Delivered"
            donation["deliveredAt"] = datetime.now().isoformat()
            
            save_donations(donations)
            return {"message": "Marked as delivered successfully"}
    
    raise fastapi.HTTPException(status_code=404, detail="Donation not found")

@app.get("/stats")
async def get_stats():
    donations = load_donations()
    
    total_meals = sum(1 for d in donations if d.get("status") == "Delivered")
    # Estimate food weight (rough estimate based on quantity strings)
    food_rescued_kg = len([d for d in donations if d.get("status") in ["Picked", "Delivered"]]) * 5
    
    users = load_users()
    centres_supported = len([u for u in users if u.get("type") == "centre"])
    
    return {
        "mealsServed": 1250 + (total_meals * 10),  # Base + actual
        "foodRescuedKg": 380 + food_rescued_kg,
        "centresSupported": max(3, centres_supported)
    }

@app.get("/users")
async def get_users():
    users = load_users()
    # Return without passwords
    return [{k: v for k, v in u.items() if k != "password"} for u in users]
