import json

# Read data from the machine_data_complete.json file
with open("machine_data_complete.json", "r", encoding="utf-8") as file:
    data = json.load(file)

# Number of questions per small JSON file
questions_per_file = 50000

# Split data into smaller JSON files
for i in range(0, len(data), questions_per_file):
    chunk = data[i:i + questions_per_file]
    filename = f"output_{i // questions_per_file + 1}.json"
    
    with open(filename, "w") as file:
        json.dump(chunk, file, indent=4)

print("JSON files created successfully.")