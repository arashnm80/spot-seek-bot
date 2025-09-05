count_files=$(ls received_links/ | wc -l)
count_lines=$(cat received_links/* | wc -l)
echo "Files: $count_files"
echo "Lines: $count_lines"
if [ "$count_files" -ne 0 ]; then
    average=$(echo "scale=2; $count_lines / $count_files" | bc)
    echo "Average lines per file: $average"
else
    echo "No files to compute average."
fi

# list mp3 files in output folder
echo $'\nmp3 files:'
find -name "*.mp3"