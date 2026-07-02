import os
import glob

html_files = glob.glob(r'C:\Users\ACER\OneDrive\Desktop\hercare_v2\*.html')

for file_path in html_files:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    new_content = content.replace('hercare_', 'hc_')
    new_content = new_content.replace("'daily_'", "'hc_daily_'")

    if new_content != content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f'Updated {file_path}')

print('String replacement done.')
