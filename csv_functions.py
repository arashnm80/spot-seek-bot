import csv, datetime
# from variables import users_csv_path, db_time_column, db_sp_track_column, db_tl_audio_column, datetime_format, user_request_wait, ucsv_user_id_column, ucsv_last_time_column
from variables import *
import pandas as pd # for edit_csv function

def csv_read(csv_path):
    # Reading from a CSV file
    with open(csv_path, mode='r') as file:
        reader = csv.reader(file)
        for row in reader:
            print(row)

def db_csv_append(csv_path, spotify_track_id, telegram_audio_id):
    # calculate and format current time
    now = datetime.datetime.now()
    formatted_date = now.strftime(datetime_format)
    # Writing to a CSV file
    with open(csv_path, mode='a', newline='') as file:
        # Create a CSV writer object
        writer = csv.writer(file)
        # Write the new row to the CSV file
        writer.writerow([formatted_date, spotify_track_id, telegram_audio_id])

def get_row_list_csv_search(csv_path, column, value):
    value = str(value) # value should be converted to string to prevent variable type bug
    # Reading from a CSV file
    with open(csv_path, mode='r') as file:
        reader = csv.reader(file)
        for row in reader:
            if row[column] == value:
                return row
        return False

def get_row_index_csv_search(csv_path, column, value):
    value = str(value) # value should be converted to string to prevent variable type bug
    # Reading from a CSV file
    with open(csv_path, mode='r') as file:
        reader = csv.reader(file)
        for index, row in enumerate(reader):
            if row[column] == value:
                return index
        return False

def edit_csv(csv_path, row_index, column_index, new_value):
    # convert variables types
    new_value = str(new_value)
    row_index = int(row_index) - 1 # we decrement it by 1 because apparently in pandas rows are started from second row
    column_index = int(column_index)
    # read the CSV file into a pandas dataframe
    df = pd.read_csv(csv_path)
    # update the value in the dataframe
    df.iloc[row_index, column_index] = new_value
    # write the updated dataframe back to a new CSV file
    new_csv_path = csv_path.rstrip(".csv") + "_new.csv"
    df.to_csv(new_csv_path, index=False)
    # remove old csv rename new one to it (it is optional and we can directly write it to csv_path in df.to_csv)
    os.remove(csv_path)
    os.rename(new_csv_path, csv_path)

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

def users_csv_append(csv_path, telegram_user_id):
    # calculate and format current time
    now = datetime.datetime.now()
    formatted_date = now.strftime(datetime_format)
    # Writing to a CSV file
    with open(csv_path, mode='a', newline='') as file:
        # Create a CSV writer object
        writer = csv.writer(file)
        # Write the new row to the CSV file
        writer.writerow([str(telegram_user_id), formatted_date])

# check for time interval for 2 allowed requests from user (it edits users.csv)
def allow_user(telegram_user_id):
    # convert to string
    telegram_user_id = str(telegram_user_id)
    # calculate and format current time
    now = datetime.datetime.now()
    formatted_date = now.strftime(datetime_format)
    # search between existing users
    row_list = get_row_list_csv_search(users_csv_path, ucsv_user_id_column, telegram_user_id)
    row_index = get_row_index_csv_search(users_csv_path, ucsv_user_id_column, telegram_user_id)
    row_index = int(row_index)
    if row_list:
        last_time = row_list[ucsv_last_time_column]
        # convert it to datetime object
        last_time = datetime.datetime.strptime(last_time, datetime_format)
        # calculate passed time        
        time_difference = now - last_time
        # convert it to seconds and round down to integer
        time_difference = int(time_difference.total_seconds())
        print("user", telegram_user_id, "last use was", time_difference, "seconds ago.")
        if time_difference > user_request_wait:
            print("user " + telegram_user_id + " is allowed to use bot.")
            edit_csv(users_csv_path, row_index, ucsv_last_time_column, formatted_date)
            return True
        else:
            print("user " + telegram_user_id + " is not allowed to use bot.")
            return False
    else:
        users_csv_append(users_csv_path, str(telegram_user_id))
        print("user " + telegram_user_id + " added to users.csv")
        return True

