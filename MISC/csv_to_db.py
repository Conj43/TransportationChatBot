import sqlite3
import pandas as pd
import os

# Function to create SQLite database and import CSV files
def create_sqlite_db(db_file, csv_folder):
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    # Get list of CSV files in the folder
    csv_files = [f for f in os.listdir(csv_folder) if f.endswith('.csv')]

    for csv_file in csv_files:
        table_name = os.path.splitext(csv_file)[0]  # Table name will be same as CSV file name without extension

        # Read CSV file into pandas DataFrame
        df = pd.read_csv(os.path.join(csv_folder, csv_file))

        # Replace spaces in column names with underscores (optional)
        df.columns = df.columns.str.replace(' ', '_')

        # Create table and insert data
        df.to_sql(table_name, conn, if_exists='replace', index=False)

        print(f"Table '{table_name}' created and data inserted.")

    conn.commit()
    conn.close()
    print("SQLite database created successfully!")

# Example usage:
db_file = 'accident_dataset.db'  # Name of SQLite database file
csv_folder = 'New DB'  # Folder containing CSV files

create_sqlite_db(db_file, csv_folder)