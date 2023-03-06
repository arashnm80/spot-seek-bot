import csv, datetime

def csv_read():
    # Reading from a CSV file
    with open('database.csv', mode='r') as file:
        reader = csv.reader(file)
        for row in reader:
            print(row)

def csv_append(spotify_song_id, telegram_audio_id):
    # calculate and format current time
    now = datetime.datetime.now()
    formatted_date = now.strftime("%Y/%m/%d-%H:%M:%S")
    # Writing to a CSV file
    with open('database.csv', mode='a', newline='') as file:
        # Create a CSV writer object
        writer = csv.writer(file)
        # Write the new row to the CSV file
        repetition = 0
        writer.writerow([formatted_date, spotify_song_id, telegram_audio_id, repetition])

def csv_search(spotify_song_id):
    # Reading from a CSV file
    with open('database.csv', mode='r') as file:
        reader = csv.reader(file)
        for row in reader:
            if row[1] == spotify_song_id:
                return row
        return False

def csv_sort(by_column):
    # read csv and hold sorted version of it in memory
    with open('database.csv', 'r') as file:
        reader = csv.reader(file)
        header = next(reader)  # save the header row
        rows = sorted(reader, key=lambda row: row[by_column])  # sort by passed arguement as column index
    # write sorted csv to new file
    with open('database_sorted.csv', 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(header)
        writer.writerows(rows)

################################################################################################

