from fastapi import APIRouter, HTTPException, UploadFile, File
from typing import List
import json
from ..models import Pet, petStatus, Category, Tag
from ..dependencies import get_pets_from_db, get_db_connection, add_tags_to_db, UPLOAD_DIRECTORY, update_pet_image_in_db
from mysql.connector import Error

router = APIRouter()

@router.get("/", response_model=List[Pet])
async def index():
    return get_pets_from_db()

@router.get("/pets/{pet_id}", response_model=Pet)
async def get_pets(pet_id: int):
    my_pet = None
    for pet in get_pets_from_db():
        if pet.id == pet_id:
            my_pet = pet
            break
    if my_pet == None:
        raise HTTPException(status_code=404, detail="Pet not found") 
    return my_pet

@router.get('/pet/findByStatus', response_model=Pet)
async def find_pet_by_status(status: petStatus):
    my_pet = None
    for pet in get_pets_from_db():
        if pet.status == status:
            my_pet = pet
    if my_pet == None:
        raise HTTPException(status_code=404, detail="Pet not found with this status") 
    return my_pet

@router.post("/pet/{petId}/uploadImage")
async def upload_pet_image(petId: int, file: UploadFile = File(...)):
    try:
        if not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="The uploaded file is not an image.")

        file_location = UPLOAD_DIRECTORY / f"{petId}_{file.filename}"

        with open(file_location, "wb") as f:
            f.write(await file.read())

        image_url = f"/uploaded_images/{petId}_{file.filename}"
        update_pet_image_in_db(petId, image_url)

        return {"message": f"Image for pet {petId} uploaded successfully!", "image_url": image_url}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/pet", response_model=Pet)
async def add_pet(pet: Pet):
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        insert_pet_query = """
        INSERT INTO pets (category_id, name, photoUrls, status)
        VALUES (%s, %s, %s, %s)
        """
        
        photo_urls_json = json.dumps(pet.photoUrls)
        
        cursor.execute(insert_pet_query, (
            pet.category.id,  # category_id
            pet.name,  # pet name
            photo_urls_json,  # photoUrls as JSON string
            pet.status,  # pet status
        ))
        
        connection.commit()
        
        pet_id = cursor.lastrowid
        
        add_tags_to_db(pet.tags, pet_id, cursor)

        cursor.execute("SELECT * FROM pets WHERE id = %s", (pet_id,))
        new_pet = cursor.fetchone()

        cursor.execute("SELECT name FROM categories WHERE id = %s", (new_pet['category_id'],))
        category = cursor.fetchone()

        cursor.execute("""
            SELECT t.id, t.name FROM tags t
            JOIN pet_tags pt ON pt.tag_id = t.id
            WHERE pt.pet_id = %s
        """, (pet_id,))
        tags = cursor.fetchall()

        cursor.close()
        connection.close()

        tag_objects = [Tag(id=tag['id'], name=tag['name']) for tag in tags]

        return Pet(
            id=pet_id,
            category=Category(id=new_pet['category_id'], name=category['name']),
            name=new_pet['name'],
            photoUrls=pet.photoUrls,
            tags=tag_objects,
            status=new_pet['status']
        )

    except Error as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Error adding pet to the store")    
    
@router.put("/pet", response_model=Pet)
async def update_pet(pet: Pet):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)  # Use dictionary cursor to access columns by name

    try:
        update_pet_query = """
            UPDATE pets 
            SET category_id = %s, name = %s, status = %s 
            WHERE id = %s
        """
        cursor.execute(update_pet_query, (
            pet.category.id, pet.name, pet.status, pet.id
        ))

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Pet not found")

        if pet.photoUrls:
            photo_urls_json = json.dumps(pet.photoUrls)  # Convert the list to a JSON string

            update_photo_urls_query = """
                UPDATE pets 
                SET photoUrls = %s 
                WHERE id = %s
            """
            cursor.execute(update_photo_urls_query, (photo_urls_json, pet.id))

        delete_tags_query = """
            DELETE FROM pet_tags WHERE pet_id = %s
        """
        cursor.execute(delete_tags_query, (pet.id,))

        if pet.tags:
            insert_tag_query = """
                INSERT INTO pet_tags (pet_id, tag_id) 
                VALUES (%s, %s)
            """
            for tag in pet.tags:
                cursor.execute(insert_tag_query, (pet.id, tag.id))

        connection.commit()

        cursor.execute("SELECT * FROM pets WHERE id = %s", (pet.id,))
        updated_pet_data = cursor.fetchone()

        cursor.execute("SELECT * FROM categories WHERE id = %s", (updated_pet_data['category_id'],))
        category = cursor.fetchone()

        cursor.execute("SELECT t.id, t.name FROM tags t "
                       "JOIN pet_tags pt ON t.id = pt.tag_id "
                       "WHERE pt.pet_id = %s", (pet.id,))
        tags = cursor.fetchall()

        updated_pet = Pet(
            id=updated_pet_data['id'],
            category=Category(id=category['id'], name=category['name']),
            name=updated_pet_data['name'],
            photoUrls=eval(updated_pet_data['photoUrls']) if updated_pet_data['photoUrls'] else [],
            tags=[Tag(id=tag['id'], name=tag['name']) for tag in tags],
            status=updated_pet_data['status']
        )

        cursor.close()
        connection.close()

        return updated_pet

    except Error as e:
        cursor.close()
        connection.close()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
@router.put("/pet/{petId}")
async def update_pet(petId: int, pet: Pet):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM pets WHERE id = %s", (petId,))
    existing_pet = cursor.fetchone()
    
    if not existing_pet:
        cursor.close()
        connection.close()
        raise HTTPException(status_code=404, detail="Pet not found")
    
    try:
        cursor.execute("""
            UPDATE pets
            SET name = %s, status = %s
            WHERE id = %s
        """, (pet.name, pet.status, petId))
        connection.commit()
        
        cursor.close()
        connection.close()
        
        return {"message": "Pet updated successfully", "petId": petId}
    
    except Error as e:
        cursor.close()
        connection.close()
        raise HTTPException(status_code=500, detail=f"Database update error: {str(e)}")
    
@router.delete("/pet/{petId}")
async def delete_pet(petId: int):
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM pets WHERE id = %s", (petId,))
    pet = cursor.fetchone()
    
    if not pet:
        cursor.close()
        connection.close()
        raise HTTPException(status_code=404, detail="Pet not found")

    try:
        cursor.execute("DELETE FROM orders WHERE pet_id = %s", (petId,))

        cursor.execute("DELETE FROM pet_tags WHERE pet_id = %s", (petId,))

        cursor.execute("DELETE FROM pets WHERE id = %s", (petId,))
        connection.commit()

        cursor.close()
        connection.close()

        return {"message": f"Pet with ID {petId} and its associated orders have been deleted successfully."}
    
    except Exception as e:
        cursor.close()
        connection.close()
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
