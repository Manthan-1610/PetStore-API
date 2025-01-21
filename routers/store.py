from fastapi import APIRouter, HTTPException
from ..models import Order, orderStatus
from ..dependencies import get_db_connection, get_orders_from_db
from mysql.connector import Error

router = APIRouter()

@router.get('/store/inventory', response_model=Order)
async def get_inventory(status: orderStatus):
    my_order = None
    for order in get_orders_from_db():
        if order.status == status:
            my_order = order
    if my_order == None:
        raise HTTPException(status_code=404, detail="No order wit this status found") 
    return my_order

@router.get("/store/order/{orderId}", response_model=Order)
async def get_pets(orderId: int):
    my_order= None
    for order in get_orders_from_db():
        if order.id == orderId:
            my_order = order
            break
    if my_order == None:
        raise HTTPException(status_code=404, detail="Pet not found by orderID") 
    return my_order

@router.post("/store/order", response_model=Order)
async def place_order(order: Order):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM pets WHERE id = %s", (order.petId,))
    pet = cursor.fetchone()

    if not pet:
        cursor.close()
        connection.close()
        raise HTTPException(status_code=404, detail="Pet not found")

    try:
        cursor.execute("""
            INSERT INTO orders (pet_id, quantity, ship_date, status, complete)
            VALUES (%s, %s, %s, %s, %s)
        """, (order.petId, order.quantity, order.shipDate, order.status, order.complete))
        connection.commit()

        order_id = cursor.lastrowid
        
        cursor.execute("SELECT * FROM orders WHERE id = %s", (order_id,))
        new_order = cursor.fetchone()
        cursor.close()
        connection.close()

        return Order(
            id=new_order["id"],
            petId=new_order["pet_id"],
            quantity=new_order["quantity"],
            shipDate=new_order["ship_date"],
            status=new_order["status"],
            complete=new_order["complete"]
        )

    except Error as e:
        cursor.close()
        connection.close()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
@router.delete("/store/order/{orderId}")
async def delete_order(orderId: int):
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM orders WHERE id = %s", (orderId,))
    order = cursor.fetchone()

    if not order:
        cursor.close()
        connection.close()
        raise HTTPException(status_code=404, detail="Order not found")

    try:
        cursor.execute("DELETE FROM orders WHERE id = %s", (orderId,))
        connection.commit()

        cursor.close()
        connection.close()

        return {"message": f"Order with ID {orderId} has been deleted successfully."}

    except Exception as e:
        cursor.close()
        connection.close()
        raise HTTPException(status_code=500, detail=f"Database error: {e}")