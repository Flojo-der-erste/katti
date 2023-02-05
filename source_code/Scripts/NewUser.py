import datetime
import hashlib
from argparse import ArgumentParser
from DataBaseStuff.ConnectDisconnect import connect_to_database, disconnect_to_database
from DataBaseStuff.MongoengineDocuments.UserManagement.KattiUser import TimeLord


def args():
    parser = ArgumentParser()
    parser.add_argument('-email', dest='email', default='system@bsi.bund.de')
    parser.add_argument('-pw', dest='pw',default='test12345678')
    parser.add_argument('-f_name', dest='f_name', default='system')
    parser.add_argument('-l_name', dest='l_name', default='system')
    parser.add_argument('-dep', dest='dep', default='oc-16')
    return parser.parse_args()


if __name__ == '__main__':
    connect_to_database()
    arg = args()
    new_user = TimeLord()

    new_user.email = arg.email
    new_user.pw_hash = hashlib.sha256(arg.pw.encode()).hexdigest()

    new_user.last_name = arg.l_name
    new_user.first_name = arg.f_name
    new_user.department = arg.dep

    new_user.created = datetime.datetime.now()
    new_user.updated = datetime.datetime.now()
    try:
        new_user.save()
    except Exception as e:
        print(e)
    else:
        print('New user added')
    finally:
        disconnect_to_database()