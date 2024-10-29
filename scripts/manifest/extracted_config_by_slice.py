"""Test and Trial code to build a new config from slices in an exiting config"""
import argparse
import json
import copy
from replay_configuration import ReplayConfigManager

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='build a new config from slices in existing config')
    parser.add_argument('--config', type=str, help='path to config file used in run')
    parser.add_argument('--sliceid', nargs='+', type=int, help='A list of integer slice IDs')
    parser.add_argument('--spring-version', nargs='+', type=str,
        help='Optional list of leap versions to use')
    new_config = []

    args = parser.parse_args()
    replay_config_manager = ReplayConfigManager(args.config)
    for oldid in args.sliceid:
        block = replay_config_manager.get(oldid)
        block_as_dict = block.as_dict(True)
        # args.spring_version may be empty
        if args.spring_version:
            for version in args.spring_version:
                new_record = copy.deepcopy(block_as_dict)
                new_record['spring_version'] = version
                new_config.append(new_record)
        # if it was empty add entry
        else:
            new_config.append(block_as_dict)
    print (json.dumps(new_config, indent=4))
