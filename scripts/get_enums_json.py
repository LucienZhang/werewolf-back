from pathlib import Path
import sys
import json
from dotenv import load_dotenv
load_dotenv()

sys.path.append(str(Path(__file__).resolve().parents[1]))
from werewolf.utils.enums import GameEnum

data = {}
for e in GameEnum:
    data[e.value] = {'key': e.name, 'label': e.label}
with open('./enums.txt', 'w', encoding='utf8') as f:
    json.dump(data, f, ensure_ascii=False)
