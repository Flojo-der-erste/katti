import unittest

from DataBaseStuff.ConnectDisconnect import connect_to_database
from DataBaseStuff.MongoengineDocuments.Scanner.TracerouteConfig import TracerouteConfig

from DataBaseStuff.MongoengineDocuments.Scanner.VirusTotalConfig import VirusTotalConfig

from DataBaseStuff.MongoengineDocuments.Scanner.FarsightDocument import FarsightDocument

from DataBaseStuff.MongoengineDocuments.Scanner.SSLScanner import SSLScannerDB

from DataBaseStuff.MongoengineDocuments.Scanner.Shodan import ShodanScannerDB

from DataBaseStuff.MongoengineDocuments.Scanner.GoogleSafeBrwosingConfig import GoogleSafeBrowserConfig

from DataBaseStuff.MongoengineDocuments.Scanner.DNSServerConfig import DNSConfig

from Scanner.GSB.GoogleSafeBrowsing import URLsForGSBRequest
from Scanner.Farsight.Farsight import FarsightQuerries, FarsightOOI
from Scanner.SSLScanner.SSLScanner import DomainsIPsForSSLScanning
from Scanner.Shodan.Shodan import ShodanScanningRequest
from Scanner.DNS.DNSResolver import DomainsForDNSResolverRequest
from DataBaseStuff.MongoengineDocuments.UserManagement.Tag import Ownership
from Scanner.BaseScanner import OOI
from CeleryApps.ScanningTasks import vt_scanning_task, dns_scanning_task, shodan_api_call_task, ssl_scanning_task, \
    farsight_scanning_task, gsb_scanning_task, traceroute_scanning_task
from Scanner.Traceroute.Traceroute import DomainsIpsTraceroute
from Scanner.VirusTotal.VirusTotal import IOCsForVTRequest, VirusTotal


class TestScanners(unittest.TestCase):
    def test_dns(self):
        x = DomainsForDNSResolverRequest(oois=[OOI(raw_ooi='bsi.de'), OOI(raw_ooi='bsi.de')],
                                         scanner_id=DNSConfig.objects.get(name='google').id,
                                         dig_type='A',
                                         dig_flags=[],
                                         ownership_obj=Ownership(),
                                         time_valid_response=5)
        task = dns_scanning_task.apply_async(args=(x,))
        task.get()
        self.assertEqual(task.status, 'SUCCESS')

    def test_gsb(self):
        x = URLsForGSBRequest(
            oois=[OOI(raw_ooi='https://testsafebrowsing.appspot.com/s/phishing.html'), OOI(raw_ooi='https://bsi.de'),
                  OOI(raw_ooi='testsafebrowsing.appspot.com/s/phishing.html')],
            scanner_id=GoogleSafeBrowserConfig.objects.get(name='gsb').id,
            ownership_obj=Ownership(),
            time_valid_response=5)
        task = gsb_scanning_task.apply_async(args=(x,))
        task.get()
        self.assertEqual(task.status, 'SUCCESS')

    def test_maxmind(self):
        pass

    def test_farsight(self):
        connect_to_database()
        x = FarsightQuerries(oois=[FarsightOOI(raw_ooi='google.de')],
                             scanner_id=FarsightDocument.objects.get(name='farsight').id,
                             ownership_obj=Ownership(),
                             time_valid_response=5,
                             rdata_or_rrset='rrset')
        task = farsight_scanning_task.apply_async(args=(x,))
        self.assertEqual(task.status, 'SUCCESS')

    def test_shodan(self):
        x = ShodanScanningRequest(oois=[OOI(raw_ooi='93.184.216.34')],
                                  scanner_id=ShodanScannerDB.objects.get(name='name'),
                                  ownership_obj=Ownership(),
                                  time_valid_response=60)
        task = shodan_api_call_task.apply_async(args=(x,))
        task.get()
        self.assertEqual(task.status, 'SUCCESS')

    def test_sslscanner(self):
        x = DomainsIPsForSSLScanning(oois=[OOI(raw_ooi='example.com')],
                                     scanner_id=SSLScannerDB.objects.get(name='ssl_scanner'),
                                     ownership_obj=Ownership(),
                                     time_valid_response=5)
        task = ssl_scanning_task.apply_async(args=(x,))
        task.get()
        self.assertEqual(task.status, 'SUCCESS')

    def test_virustotal(self):
        x = IOCsForVTRequest(oois=[OOI(raw_ooi='https://testsafebrowsing.appspot.com/s/phishing.html'),
                                   OOI(raw_ooi='https://ofc-bonn.de')],
                             scanner_id=VirusTotalConfig.objects.get(name='vt'),
                             endpoint=VirusTotal.VT_URL_ENDPOINT,
                             ownership_obj=Ownership(),
                             own_api_key='', # API KEY
                             time_valid_response=0)
        task = vt_scanning_task.apply_async(args=[x])
        task.get()
        self.assertEqual(task.status, 'SUCCESS')

    def test_traceroute(self):
        x = DomainsIpsTraceroute(oois=[OOI(raw_ooi='example.com')],
                                 scanner_id=TracerouteConfig.objects.get(name='traceroute'),
                                 ownership_obj=Ownership(),
                                 time_valid_response=0)
        task = traceroute_scanning_task.apply_async(args=[x])
        task.get()
        self.assertEqual(task.status, 'SUCCESS')


if __name__ == '__main__':
    unittest.main()
