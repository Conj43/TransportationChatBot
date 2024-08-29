from sandbox import AICodeSandbox


import os

query_code = """
import sqlite3

# Connect to the database file
connection = sqlite3.connect('/test.db')  # Ensure the path is correct
cursor = connection.cursor()

# Check the tables in the database
cursor.execute('SELECT name FROM sqlite_master WHERE type="table";')
tables = cursor.fetchall()

# Print the tables in the database
print("Tables in the database:")
for table in tables:
    print(table[0])

# Execute a query to check contents
cursor.execute('SELECT * FROM sample LIMIT 5')
rows = cursor.fetchall()

# Close the connection
connection.close()

# Print results
print("Query Results:")
for row in rows:
    print(row)

"""


sandbox=AICodeSandbox()

def get_database_content(file_path):
    """Read the content of the database file into binary."""
    with open(file_path, 'rb') as file:
        return file.read()

# Example usage
db_file_path = 'hawaii_congestion.db'  # Path to your local database file
container_file_path = '/test.db'  # Path where you want to write the file in the container

# Get the binary content of the database file
db_content = get_database_content(db_file_path)

# print(db_content)


try:
    sandbox.write_file(container_file_path, str(db_content))
    files = sandbox.list_files(directory='/')
    print(files)
    result = sandbox.run_code(query_code)
    print(result)
finally:
    sandbox.close()


# sandbox = AICodeSandbox()
# try:
#     sandbox.write_file('/sandbox/test.txt', 'Hello, World!')
#     print(sandbox.read_file('/sandbox/test.txt'))
#     result = sandbox.run_code('print(24+12)')
#     print(result)
# finally:
#     print("hi")
#     sandbox.close()
#     print("end")

