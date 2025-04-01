import json
from pathlib import Path
from argparse import Namespace


class ConfigManager:

    def __init__(self, opt: Namespace):


        print(opt.root_path)
        self.cfg_prog = ""
        pass



    def get_session_path(self) -> Path:
        return Path("l")





    def save(self, prog_congig_path: Path) -> None:
        print("\n-- Finally, save plancha_config.json\n")
        with open(prog_congig_path, 'w') as fp:
            json.dump(self.cfg_prog, fp,indent=3)