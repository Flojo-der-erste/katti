from inspect import isclass
from pkgutil import iter_modules
from pathlib import Path
from importlib import import_module
from DataBaseStuff.MongoengineDocuments.Feeds.BaseFeedEntry import BaseFeedEntry
from DataFeeds.BaseDataFeed import BaseDataFeed


def import_feeds():
    package_dir = Path(__file__).resolve().parent
    for (_, module_name, _) in iter_modules([f'{package_dir}']):
        match module_name:
            case 'import_loader' | 'BaseDataFeed' | 'BaseFeedEntry' | 'DGAEntry' | 'InsertFeed':
                continue
        module = import_module(f"DataFeeds.{module_name}.{module_name}")
        for attribute_name in dir(module):
            attribute = getattr(module, attribute_name)
            if isclass(attribute) and (issubclass(attribute, BaseDataFeed) or issubclass(attribute, BaseFeedEntry)):
                globals()[attribute_name] = attribute