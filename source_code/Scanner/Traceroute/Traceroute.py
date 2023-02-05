import subprocess
import typing
import jc
from pydantic.dataclasses import dataclass
from DataBaseStuff.MongoengineDocuments.Scanner.TracerouteConfig import TracerouteAnswer, TracerouteConfig
from DataBaseStuff.MongoengineDocuments.Scanner.BaseMongoEngineDocument import BaseScanningRequests
from Scanner.BaseScanner import BaseScanner, Config, BaseScanningRequestForScannerObject


@dataclass(config=Config)
class DomainsIpsTraceroute(BaseScanningRequestForScannerObject):
    pass


class Traceroute(BaseScanner):
    _scanner_document: TracerouteConfig
    @property
    def result_class(self) -> typing.Type[BaseScanningRequests]:
        return TracerouteAnswer

    @property
    def scanner_mongo_document_class(self):
        return TracerouteConfig

    def _do_your_scanning_job(self):
        try:
            cmd_output = subprocess.check_output(['traceroute', '-I', f'{self.next_ooi_obj.ooi}'],
                                                 text=True)
        except Exception as e:
            self.scanning_result.traceroute_exc = f'{e}'
        else:
            result = jc.parse('traceroute', cmd_output)
            hops = []
            for hop in result['hops']:
                if len(hop['probes']) > 0:
                    hops.append(hop)
            self.scanning_result.hops = hops
            self.scanning_result.hops_counter = len(hops)
            self.scanning_result.destination_ip = result['destination_ip']


