import sqlite3

db = sqlite3.connect('firstActivity.db', check_same_thread=False)

def getallprocess(sql: str, params=()) -> list:
    cursor = db.cursor()
    cursor.execute(sql, params)
    data = cursor.fetchall()
    cursor.close()
    return data

def postprocess(sql: str, params=()) -> bool:
    cursor = db.cursor()
    cursor.execute(sql, params)
    db.commit()
    cursor.close()
    return cursor.rowcount > 0

def addprocess(query: str, params) -> dict:
    cursor = db.cursor()
    cursor.execute(query, params)
    result = cursor.fetchone() 
    db.commit()
    cursor.close()
    
    return result