from sqlite3 import connect, Row

database = 'firstActivity.db'

def getallprocess(sql: str, params=()) -> list:
    db = connect(database)
    db.row_factory = Row
    cursor = db.cursor()
    cursor.execute(sql, params)
    data = cursor.fetchall()
    cursor.close()
    db.close()
    return data

def postprocess(sql: str, params=()) -> bool:
    db = connect(database)
    cursor = db.cursor()
    cursor.execute(sql, params)
    db.commit()
    cursor.close()
    db.close()
    return True if cursor.rowcount > 0 else False

def addprocess(table, **kwargs) -> dict:
    keys = list(kwargs.keys())
    values = [f"'{v}'" for v in kwargs.values()]
    
    fld = "`,`".join(keys)
    dta = ",".join(values)
    sql = f"INSERT INTO `{table}` (`{fld}`) VALUES ({ dta })"
    
    return postprocess(sql)

# def getallrecords(table:str)-> list:
    sql:str = f"SELECT * FROM `{table}`"
    return getallprocess(sql)