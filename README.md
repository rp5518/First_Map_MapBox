The first thing you must do is create your “Completed_Walk_Lists” which are store in the directory "C:\Users\wjg\Python_Stuff\Completed_Walk_Lists"
The “Completed_Walk_Lists” are generated from the Python File: "C:\Users\wjg\Python_Stuff\make_walk_lists.py"
Example Excel files for the input of make_walk_lists.py are: "C:\Users\wjg\Python_Stuff\Excel_Files\LD12_Hard_REP_EXAMPLE.xlsx" "C:\Users\wjg\Python_Stuff\Excel_Files\Thunderhill_Rep_VS_2024_EXAMPLE.csv"

You must populate the "C:\Users\wjg\Python_Stuff\First_Map_MapBox\markers.json" by running the Python file: "C:\Users\wjg\Python_Stuff\First_Map_MapBox\Address2LngLat.py"
  
The Address2LngLat.py will request a Completed_Walk_List as input.  The Completed_Walk_Lists are located at:
"C:\Users\wjg\Python_Stuff\Completed_Walk_Lists”
Once the markers.json is updated you can run the index.html file to generate a new map. "C:\Users\wjg\Python_Stuff\First_Map_MapBox\index.html"

The latest versions of "C:\Users\wjg\Python_Stuff\First_Map_MapBox\Address2LngLat.py" and "C:\Users\wjg\Python_Stuff\First_Map_MapBox\markers.json" are stored in GitHub at: https://github.com/rp5518/First_Map_MapBox
The marker’s data is stored at: https://console.firebase.google.com
The final map can be accessed at: https://map2canvass.com
My map2canvass name domain is saved in Cloudflare. I do not have a password. I just login with Google.

## Understanding Domain Name Assignments
    CNAME Type (Cononical Name) = www
    "A" Name Type (address Name) = map2canvass.com
    www.map2canvass.com maps to: rp5518.github.io
    map2canvass.com inside of Github maps to one of four servers: 185.199.108.153 or 185.199.109.153 or 185.199.110.153 or 185.199.111.153
    The apex domain (also called a "root domain" or "naked domain") is your domain name without any subdomain prefix
    apex domain = map2canvass.com

