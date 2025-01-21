from fastapi import APIRouter, HTTPException
from typing import List
from ..models import User
from ..dependencies import get_db_connection, get_users_from_db
from mysql.connector import Error

router = APIRouter()

@router.get("/user/{username}", response_model=User)
async def get_pets(username: str):
    my_user= None
    for user in get_users_from_db():
        if user.username == username:
            my_user = user
            break
    if my_user == None:
        raise HTTPException(status_code=404, detail="User not found by this username") 
    return my_user

@router.post("/user/createWithList", response_model=List[User])
async def create_users_with_list(users: List[User]):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    insert_query = """
        INSERT INTO users (username, firstName, lastName, email, password, phone, userStatus)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """

    try:
        for user in users:
            cursor.execute(insert_query, (
                user.username, user.firstName, user.lastName,
                user.email, user.password, user.phone, user.userStatus
            ))

        connection.commit()

        cursor.execute("SELECT * FROM users WHERE username IN (%s)" % ",".join([f"'{user.username}'" for user in users]))
        new_users = cursor.fetchall()

        cursor.close()
        connection.close()

        return [User(**user) for user in new_users]

    except Error as e:
        cursor.close()
        connection.close()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
@router.post("/user", response_model=User)
async def create_user(user: User):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    insert_query = """
        INSERT INTO users (username, firstName, lastName, email, password, phone, userStatus)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """

    try:
        cursor.execute(insert_query, (
            user.username, user.firstName, user.lastName,
            user.email, user.password, user.phone, user.userStatus
        ))

        connection.commit()

        new_user_id = cursor.lastrowid

        cursor.execute("SELECT * FROM users WHERE id = %s", (new_user_id,))
        new_user = cursor.fetchone()

        cursor.close()
        connection.close()

        return User(**new_user)

    except Error as e:
        cursor.close()
        connection.close()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
@router.put("/user/{username}", response_model=User)
async def update_user(username: str, updated_user: User):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    existing_user = cursor.fetchone()
    
    if not existing_user:
        cursor.close()
        connection.close()
        raise HTTPException(status_code=404, detail="User not found")

    try:
        cursor.execute("""
            UPDATE users 
            SET firstName = %s, lastName = %s, email = %s, password = %s, phone = %s, userStatus = %s 
            WHERE username = %s
        """, (
            updated_user.firstName,
            updated_user.lastName,
            updated_user.email,
            updated_user.password,
            updated_user.phone,
            updated_user.userStatus,
            username
        ))

        connection.commit()

        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        updated_user_from_db = cursor.fetchone()
        cursor.close()
        connection.close()

        return User(
            id=updated_user_from_db['id'],
            username=updated_user_from_db['username'],
            firstName=updated_user_from_db['firstName'],
            lastName=updated_user_from_db['lastName'],
            email=updated_user_from_db['email'],
            password=updated_user_from_db['password'],
            phone=updated_user_from_db['phone'],
            userStatus=updated_user_from_db['userStatus']
        )
    
    except Exception as e:
        cursor.close()
        connection.close()
        raise HTTPException(status_code=500, detail=f"Database update failed: {e}")
    
@router.delete("/user/{username}")
async def delete_user(username: str):
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()

    if not user:
        cursor.close()
        connection.close()
        raise HTTPException(status_code=404, detail="User not found")

    try:
        cursor.execute("DELETE FROM users WHERE username = %s", (username,))
        connection.commit()

        cursor.close()
        connection.close()

        return {"message": f"User with username {username} has been deleted successfully."}

    except Exception as e:
        cursor.close()
        connection.close()
        raise HTTPException(status_code=500, detail=f"Database error: {e}")