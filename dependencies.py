from pathlib import Path
import json
from typing import List
from fastapi import HTTPException
from mysql.connector import Error
import mysql.connector
from .models import Tag, Pet, Order, User

UPLOAD_DIRECTORY = Path("./uploaded_images")
UPLOAD_DIRECTORY.mkdir(parents=True, exist_ok=True)

def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="root",
            database="pet_store_db"
        )
        if connection.is_connected():
            return connection
    except Error as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Database connection error")


def get_categories_from_db():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM categories")
    categories = cursor.fetchall()
    cursor.close()
    connection.close()
    return {category["id"]: category for category in categories}

def get_tags_from_db():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM tags")
    tags = cursor.fetchall()
    cursor.close()
    connection.close()
    return {tag["id"]: tag for tag in tags}

def get_pets_from_db():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM pets")
    pets = cursor.fetchall()

    categories = get_categories_from_db()
    tags = get_tags_from_db()

    cursor.execute("SELECT * FROM pet_tags")
    pet_tags = cursor.fetchall()

    cursor.close()
    connection.close()

    pet_tags_mapping = {}
    for pet_tag in pet_tags:
        pet_id = pet_tag['pet_id']
        tag_id = pet_tag['tag_id']
        if pet_id not in pet_tags_mapping:
            pet_tags_mapping[pet_id] = []
        pet_tags_mapping[pet_id].append(tags[tag_id])

    pets_db = []
    for pet in pets:
        photo_urls = pet["photoUrls"]
        if photo_urls:
            photo_urls = eval(photo_urls)

        pet_obj = Pet(
            id=pet["id"],
            category=categories[pet["category_id"]],
            name=pet["name"],
            photoUrls=photo_urls if photo_urls else [],
            tags=pet_tags_mapping.get(pet["id"], []),
            status=pet["status"]
        )
        pets_db.append(pet_obj)

    return pets_db

def get_users_from_db():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    cursor.close()
    connection.close()

    mapped_users = []
    for user in users:
        mapped_user = User(
            id = user['id'],
            username = user['username'],
            firstName = user['firstName'],
            lastName = user['lastName'],
            email = user['email'],
            password = user['password'],
            phone = user['phone'],
            userStatus = user['userStatus'],
        )
        mapped_users.append(mapped_user)
    
    return mapped_users


def get_orders_from_db():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM orders")
    orders = cursor.fetchall()
    cursor.close()
    connection.close()
    
    # Map the raw dictionary fields to the Pydantic model fields
    mapped_orders = []
    for order in orders:
        mapped_order = Order(
            id=order["id"],
            petId=order["pet_id"],  # Map 'pet_id' from DB to 'petId' in the model
            quantity=order["quantity"],
            shipDate=order["ship_date"],  # Map 'ship_date' from DB to 'shipDate' in the model
            status=order["status"],
            complete=bool(order["complete"])  # Ensure complete is a boolean
        )
        mapped_orders.append(mapped_order)
    
    return mapped_orders

def update_pet_image_in_db(pet_id: int, image_url: str):
    try:
        # Get the existing pet data
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Fetch the current photoUrls for the pet
        cursor.execute("SELECT photoUrls FROM pets WHERE id = %s", (pet_id,))
        result = cursor.fetchone()
        
        if result is None:
            raise HTTPException(status_code=404, detail="Pet not found")
        
        current_photo_urls = result['photoUrls']

        if current_photo_urls:
            current_urls_list = json.loads(current_photo_urls)  # Load the existing JSON array
        else:
            current_urls_list = []  # Initialize as an empty list if it's empty or NULL

        current_urls_list.append(image_url)
        updated_photo_urls = json.dumps(current_urls_list)
        cursor.execute(
            "UPDATE pets SET photoUrls = %s WHERE id = %s",
            (updated_photo_urls, pet_id)
        )
        connection.commit()
        cursor.close()
        connection.close()
    except Error as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Database update failed")

def add_tags_to_db(tags: List[Tag], pet_id: int, cursor):
    tag_ids = []
    for tag in tags:
        cursor.execute("SELECT id FROM tags WHERE name = %s", (tag.name,))
        result = cursor.fetchone()
        if result:
            tag_ids.append(result['id'])
        else:
            cursor.execute("INSERT INTO tags (name) VALUES (%s)", (tag.name,))
            cursor.execute("SELECT id FROM tags WHERE name = %s", (tag.name,))
            new_tag = cursor.fetchone()
            tag_ids.append(new_tag['id'])
        
        cursor.execute("INSERT INTO pet_tags (pet_id, tag_id) VALUES (%s, %s)", (pet_id, tag_ids[-1]))
    
    return tag_ids