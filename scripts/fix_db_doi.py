import sys
from json import dumps
import psycopg2
from invenio_pidstore.providers.datacite import DataCiteProvider
from b2share.modules.records.serializers import datacite_v31

if len(sys.argv) != 5:
    print('This script fixes DOI naming errors in a b2share database', sys.argv[0])
    print('    Usage: {} username password hostname databasename'.format(sys.argv[0]))
    sys.exit(1)

user = sys.argv[1]
password = sys.argv[2]
host = sys.argv[3]
dbname = sys.argv[4]

bad_doi_prefix = '10.5072/b2share.'
good_doi_prefix = '10.23728/b2share.'


def fix_doi_in_pids():
    conn = psycopg2.connect("user='{}' password={} host='{}' dbname='{}'"
                            .format(user, password, host, dbname))
    cursor = conn.cursor()
    cursor.execute("""SELECT id, pid_type, pid_value from pidstore_pid""")
    rows = cursor.fetchall()
    for row in rows:
        [id_, pid_type, pid_value] = row
        if pid_type != 'doi':
            continue
        if bad_doi_prefix not in pid_value:
            continue

        new_pid_value = pid_value.replace(bad_doi_prefix, good_doi_prefix)
        print ('update (id: pid_value): {}: {} with {}'.format(
            id_, pid_value, new_pid_value))
        cursor.execute("UPDATE pidstore_pid SET pid_value=(%s) WHERE id = (%s)",
                       (new_pid_value, id_))
    conn.commit()
    cursor.close()


def fix_doi_in_records():
    conn = psycopg2.connect("user='{}' password={} host='{}' dbname='{}'"
                            .format(user, password, host, dbname))
    cursor = conn.cursor()
    cursor.execute("""SELECT id, json, version_id from records_metadata""")
    rows = cursor.fetchall()
    for row in rows:
        [id_, json, version_id] = row
        if not json or '_pid' not in json:
            continue

        doi = None
        for pid in json['_pid']:
            if pid['type'] == 'DOI' and bad_doi_prefix in pid['value']:
                assert not doi
                doi = pid['value'].replace(bad_doi_prefix, good_doi_prefix)
                pid['value'] = doi

        if not doi:
            continue

        print('\nupdate (id, version_id): ({}, {}) with \n{}'.format(
            id_, version_id, json))
        cursor.execute("UPDATE records_metadata SET json=(%s)"
                       " WHERE id = (%s) AND version_id = (%s)",
                       (dumps(json), id_, version_id))
    conn.commit()
    cursor.close()


fix_doi_in_pids()
fix_doi_in_records()
