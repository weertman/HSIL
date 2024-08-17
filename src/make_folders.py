# Script to create folders 0001, 0002, ..., 0103 in a specified directory.

import os

# Define the directory where folders will be created. Adjust this path as necessary.
directory = "D:\pycno_pics_joey\PWS_2023_JU"

# Loop to create folders
for i in range(35, 104):
    folder_name = f"{i:04d}"  # Format the folder name with leading zeros
    path = os.path.join(directory, folder_name)
    if os.path.exists(path) != True:
        os.makedirs(path, exist_ok=True)  # Create the folder

"Folders created successfully in the specified directory."
