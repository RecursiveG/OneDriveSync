## OneDrive Sync

Sync with OneDrive for Business publicly shared folders.

Get cookie:

    ./odb.py --login_url 'https://<xxx>-my.sharepoint.com/:f:/g/personal/<yyy>/<zzz>' --cookie_file cookie.json
    
Fetch full tree metadata:

    ./odb.py --cookie_file cookie.json --tree '/' -recursive --output tree_metadata.json --verbose
    
Pretty print the tree:

    ./odb.py --print_tree tree_metadata.json
    
Generate aria2c download list, it will print the command need to run:

    ./gen_aria2c.py --cookie_file cookie.json --current_listing tree_metadata.json --aria2c_list aria2c.txt --download_path <some_path>

