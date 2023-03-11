import csv, datetime
from variables import db_csv_path, users_csv_path, db_time_column, db_sp_track_column, db_tl_audio_column

def csv_read(csv_path):
    # Reading from a CSV file
    with open(csv_path, mode='r') as file:
        reader = csv.reader(file)
        for row in reader:
            print(row)

def csv_append(csv_path, spotify_track_id, telegram_audio_id):
    # calculate and format current time
    now = datetime.datetime.now()
    formatted_date = now.strftime("%Y/%m/%d-%H:%M:%S")
    # Writing to a CSV file
    with open(csv_path, mode='a', newline='') as file:
        # Create a CSV writer object
        writer = csv.writer(file)
        # Write the new row to the CSV file
        writer.writerow([formatted_date, spotify_track_id, telegram_audio_id])

def csv_search(csv_path, column, value):
    # Reading from a CSV file
    with open(csv_path, mode='r') as file:
        reader = csv.reader(file)
        for row in reader:
            if row[column] == value:
                return row
        return False

def csv_sort(csv_path, by_column):
    # read csv and hold sorted version of it in memory
    with open(csv_path, 'r') as file:
        reader = csv.reader(file)
        header = next(reader)  # save the header row
        rows = sorted(reader, key=lambda row: row[by_column])  # sort by passed arguement as column index
    # write sorted csv to new file
    new_csv_path = csv_path.rstrip(".csv") + "_sorted.csv"
    with open(new_csv_path, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(header)
        writer.writerows(rows)

