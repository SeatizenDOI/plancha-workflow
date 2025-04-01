import traceback
from argparse import ArgumentParser, Namespace

from src.SessionBase import SessionBase

def parse_option() -> Namespace:
    parser = ArgumentParser(prog="plancha-workflow", description="Workflow between raw data and Seatizen data")

    parser.add_argument("-csv", default=None, help="Path to csv file for session_name")
    parser.add_argument("-os", "--only-split", action="store_true", help="Only split images from videos")
    parser.add_argument("-ns", "--no-split", action="store_true", help="Don't split images from videos")
    parser.add_argument("-na", "--no_annotate", action="store_true", help="Don't annotate images")
    parser.add_argument("-nb", "--no_bathy", action="store_true", help="Don't process bathy")
    parser.add_argument("-nc", "--no_clean", default="", help="Specify folder to clean f: FRAMES, m: METADATA, b: BATHY, g: GPS, Ex: -no_clean fm")
    parser.add_argument("-frgp", "--force_use_rgp", action="store_true", help="Force to use RGP station to compute base gps")
    parser.add_argument("-rp", "--root_path", default=None, help="Root path for the session")
    parser.add_argument("-rf", "--remove_frames", default=None, help="Remove frames until meet the number")
    parser.add_argument("-pcn", "--plancha_config_path", default=None, help="Path to the plancha config file to use")


    return parser.parse_args()


def main(opt: Namespace) -> None:

    print(opt)
    session_fails = []

    session = SessionBase(opt)


    try:
        pass
    except Exception:
        # Print error
        print(traceback.format_exc(), end="\n\n")
            
        # Store sessions name
        session_fails.append("")
    finally:
        pass




if __name__ == "__main__":
    opt = parse_option()
    main(opt)