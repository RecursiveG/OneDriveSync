## OneDrive Sync

Sync with OneDrive for Business publicly shared folders.

Get cookie:

    ./odb.py --login\_url 'https://<xxx>-my.sharepoint.com/:f:/g/personal/<yyy>/<zzz>' --cookie\_file cookie.json
    
Fetch full tree metadata:

    ./odb.py --cookie\_file cookie.json --tree '/' -recursive --output tree\_metadata.json --verbose
    
Pretty print the tree:

    ./odb.py --print\_tree tree\_metadata.json
    
Generate aria2c download list, it will print the command need to run:

    ./gen\_aria2c.py --cookie\_file cookie.json --current\_listing tree\_metadata.json --aria2c\_list aria2c.txt --download\_path <some_path>

