import traceback
from pathlib import Path
from argparse import ArgumentParser, Namespace

from src.SessionBase import SessionBase
from src.ConfigManager import ConfigManager
from src.lib.lib_tools import print_plancha_header


def parse_option() -> Namespace:
    parser = ArgumentParser(prog="plancha-workflow", description="Workflow between raw data and Seatizen data")

    parser.add_argument("-csv", default=None, help="Path to csv file for session_name")
    parser.add_argument("-os", "--only-split", action="store_true", help="Only split images from videos")
    parser.add_argument("-ns", "--no-split", action="store_true", help="Don't split images from videos")
    parser.add_argument("-na", "--no_tags", action="store_true", help="Don't tags images")
    parser.add_argument("-nb", "--no_bathy", action="store_true", help="Don't process bathy")
    parser.add_argument("-nc", "--no_clean", default="", help="Specify folder to clean f: FRAMES, m: METADATA, b: BATHY, g: GPS, Ex: -no_clean fm")
    parser.add_argument("-frgp", "--force_use_rgp", action="store_true", help="Force to use RGP station to compute base gps")
    parser.add_argument("-rp", "--root_path", default=None, help="Root path for the session")
    parser.add_argument("-rf", "--remove_frames", default=None, help="Remove frames until meet the number")
    parser.add_argument("-pcn", "--plancha_config_path", default=None, help="Path to the plancha config file to use")


    return parser.parse_args()


def main(opt: Namespace) -> None:
    print_plancha_header()

    session_fails = []

    config_manager = ConfigManager(opt)

    for session_name, filt_exclude_specific_datetimeUTC in config_manager.iterate_over_session():

        session_path = Path(config_manager.get_root_path(), session_name)

        if not session_path.exists(): 
            print(f"[WARNING] Path {session_path} not found")
            continue

        session_base = SessionBase(session_path)

        try:
            print("\n\n-- Launching " + session_base.session.name)

            # Clean folder.
            session_base.prepare_folder(config_manager.get_folder_to_clean())    
            
            session_base.image_manager.setup(config_manager)
            session_base.write_session_info(config_manager)

            ### Image part.
            session_base.split_videos(config_manager)

            if not config_manager.is_only_split():
                session_base.remove_first_frames(config_manager)

            ### GPS part.
            session_base.compute_gps(config_manager)

            ### Bathy part.
            session_base.compute_bathy(config_manager)
            
            session_base.update_filt_exclude_interval(config_manager, filt_exclude_specific_datetimeUTC)

            ### Tags part
            if not config_manager.is_only_split():
                session_base.tags_frames(config_manager)
            
        except Exception:
            # Print error
            print(traceback.format_exc(), end="\n\n")
                
            # Store sessions name
            session_fails.append(session_base.session.name)
        finally:
            print("\n-- Finally, save plancha_config.json\n")
            config_manager.save_cfg_prog(session_base.prog_config_path)


if __name__ == "__main__":
    opt = parse_option()
    main(opt)