# f"{{'$match': {{'_id': {request_object_id} }} }}, {{'$lookup': {{'from': 'dns_results','localField': 'queries.dns_response','foreignField': '_id',  'as': 'dns_results' }} }}"
get_complete_dns_request = lambda request_object_ids: [{'$match': {'_id': {'$in': request_object_ids}}},
                                                       {'$lookup': {'from': 'dns_results',
                                                                    'localField': 'queries.dns_response',
                                                                    'foreignField': '_id',
                                                                    'as': 'queries.dns_response'}}]


get_complete_ssl_request = lambda request_object_ids: [{'$match': {'_id': {'$in': request_object_ids}}},
                                                       {'$lookup': {'from': 'ssl_scanner_cipher_suites',
                                                                    'localField': 'tls_ssl_scan_results.accepted_cipher_suites'}}]