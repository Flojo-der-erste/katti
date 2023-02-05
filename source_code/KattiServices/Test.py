from mongoengine import connect

from source_code.KattiServices.MongoengineClasses.TestServiceDB import TestServiceDB

if __name__ == '__main__':
    connect()
    test_service = TestServiceDB()
    test_service.save()