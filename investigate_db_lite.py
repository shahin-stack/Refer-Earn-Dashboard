import sqlite3

def check_db():
    conn = sqlite3.connect('detailed_split.db')
    cursor = conn.cursor()
    
    print("Checking Detailed_split_1...")
    cursor.execute("SELECT count(*), count(distinct [Customer Mobile]) FROM Detailed_split_1")
    count1, unique1 = cursor.fetchone()
    print(f"Total rows in Split 1: {count1}")
    print(f"Unique mobiles in Split 1: {unique1}")
    
    print("\nChecking Detailed_split_2...")
    cursor.execute("SELECT count(*), count(distinct [Customer Mobile]) FROM Detailed_split_2")
    count2, unique2 = cursor.fetchone()
    print(f"Total rows in Split 2: {count2}")
    print(f"Unique mobiles in Split 2: {unique2}")
    
    conn.close()

if __name__ == "__main__":
    check_db()
