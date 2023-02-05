import importlib
from pydoc import locate

from KattiServices.SourceToScannerService.DomainDGAScannerService import DomainDGAScannerService

SERVICE_CLS = {'dga_domain_scanner': DomainDGAScannerService}

def load_service_cls(name):
    return SERVICE_CLS[name]


if __name__ == '__main__':
    my_module = importlib.import_module('KattiServices.DomainDGAScannerService.DomainDGAScannerService')
    print(my_module.DomainDGAScannerService)