import os
import shutil

def clean_pycache(root_dir="."):
    for root, dirs, files in os.walk(root_dir):
        for dir_name in dirs:
            if dir_name == "__pycache__" or dir_name.endswith(".pytest_cache"):
                shutil.rmtree(os.path.join(root, dir_name))
        for file_name in files:
            if file_name.endswith(".pyc"):
                os.remove(os.path.join(root, file_name))

clean_pycache()