import json
import os
import subprocess
import sys
import urllib.request

PROJECT_ID = "13602521216895540527"
SCREENS = {
    "70b9eeb5a7e14f49bf19a719e417dc30": "1_Generated_Screen",
    "f8884f4c2a4e4f28ac55be8d8651dbb5": "2_Theme_Switcher_Interface",
    "e95ba240acb34915a6a1c9118a9a30da": "3_Operator_ForceAtlas2_Topology",
    "6694e5c34aa147b1bf6b222dba59ce81": "4_Holographic_ForceAtlas2_Topology",
    "db03099f28824e49a3214155dddc6e0d": "5_Operator_Project_Tree_Map",
    "6c9c66cbe02a46c193f2df13b8816ebc": "6_Holographic_Project_Tree_Map",
    "ea43930a19eb40d9a88526a9d8590612": "7_Operator_TUI_CRUD_Console",
    "ffdfa8795aa04204a2bea7a2cdcc620e": "8_Holographic_CRUD_Interface",
    "087b546ee9734e5ba2b43e9cd5cddf06": "9_Session_Output_Focus_Mode",
    "137a4a6ad3624611b805c17f0cd260b1": "10_The_Operator_System_PRD",
    "155927ea64304b088630b58b93be0884": "11_Holographic_Flow_Interface_PRD",
    "21b93c1261cd41b187a46b12677a759c": "12_Deep_Storage_Backlog",
    "54a6faab3c12479c8582a5706cda3a1f": "13_The_Graph_Network_View",
    "5b32bfcbae9d4db592acd62ecb9cd754": "14_The_Void_Home",
    "c981ca419c444119a76b5bf356718889": "15_Deep_Dive_Project_View",
    "ea4b9f2634cd4c90939bbf003d1055b4": "16_The_Stream_Inbox",
    "fdbf0b689c7343fba1a28f5636e81118": "17_Tactical_Overview_Dashboard",
    "ff7dc756d6624ea4aa80ab6576b0bb0b": "18_Surface_Layer_Task_Mode"
}

target_dir = "/Users/suzor/src/academicOps/overwhelm-dashboard/static/assets/stitch"
os.makedirs(target_dir, exist_ok=True)

try:
    token = subprocess.check_output(["gcloud", "auth", "print-access-token"], text=True).strip()
    gcp_project = subprocess.check_output(["gcloud", "config", "get-value", "project"], text=True).strip()
except Exception as e:
    print(f"Error getting gcloud credentials: {e}")
    sys.exit(1)

for screen_id, name in SCREENS.items():
    print(f"Fetching metadata for {name} ({screen_id})...")
    req = urllib.request.Request(f"https://stitch.googleapis.com/v1/projects/{PROJECT_ID}/screens/{screen_id}")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("X-Goog-User-Project", gcp_project)

    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))

            html_url = data.get("htmlCode", {}).get("downloadUrl")
            img_url = data.get("screenshot", {}).get("downloadUrl")

            if html_url:
                urllib.request.urlretrieve(html_url, os.path.join(target_dir, f"{name}.html"))
            if img_url:
                width = data.get("width", "1024")
                # Append =w{width} if it doesn't already have query params like this
                if "=" not in img_url.split("/")[-1]:
                    img_url += f"=w{width}"
                urllib.request.urlretrieve(img_url, os.path.join(target_dir, f"{name}.png"))

            print(f"Downloaded {name}")
    except Exception as e:
        print(f"Failed to fetch {name}: {e}")

print("Done.")
