import requests
from pprint import pprint
import re
from collections import defaultdict
from collections import Counter
from collections import OrderedDict
from tabulate import tabulate
from terminaltables import AsciiTable, DoubleTable
import yaml
from fabric import red, green, yellow

def config():
    """ loads our config """
    import yaml
    with open('es_hosts.yml', 'r') as f:
        doc = yaml.load(f)
    return doc


def bytesto(bytes, to, bsize=1024):
    """convert bytes to megabytes, etc.
       sample code:
           print('mb= ' + str(bytesto(314575262000000, 'm')))
       sample output: 
           mb= 300002347.946
    """

    a = {'k' : 1, 'm': 2, 'g' : 3, 't' : 4, 'p' : 5, 'e' : 6 }
    r = float(bytes)
    for i in range(a[to]):
        r = r / bsize
    return(r)


def get_color(str):
    if 'red' in str:
        return red(str)
    elif 'green' in str:
        return green(str)
    elif 'yellow' in str:
        return yellow(str)

def main():
    conf = config()
    _CLUSTER_ADDRESS = conf['cluster_address']

    print("Getting stats from cluster...")
    r = requests.get('{}/_stats'.format(_CLUSTER_ADDRESS))
    cl = requests.get('{}/_cluster/stats'.format(_CLUSTER_ADDRESS))
    print("Done getting stats from cluster...")
    clstatsd = cl.json()

    statsd = r.json()

    print("making formatted stats...")
    total_used = statsd['_all']['total']['store']['size_in_bytes']

    total_size = clstatsd['nodes']['fs']['total_in_bytes']
    total_available = clstatsd['nodes']['fs']['available_in_bytes']
    total_free = clstatsd['nodes']['fs']['available_in_bytes']

    jvm_max_mem = clstatsd['nodes']['jvm']['mem']['heap_max_in_bytes']
    jvm_used_mem = clstatsd['nodes']['jvm']['mem']['heap_used_in_bytes']
    jvm_free_mem = jvm_max_mem - jvm_used_mem

    indexes_formatted = [ re.sub('(\d{1,4}.\d{1,2}.\d{1,2})', '', x) for x in statsd['indices'] ]
    #indexes_formatted.sort()
    indexes = [ x for x in statsd['indices'] ]

    indexd = { k:0 for k in indexes_formatted }
    indexd = Counter(indexd)

    for index in indexes:
        time_based = None
        if re.match('.*(\d{1,4}).*$', index):
            time_based = True

        formatted_index = re.sub('(\d{1,4}.\d{1,2}.\d{1,2})', '', index)
        total = statsd['indices'][index]['total']['store']['size_in_bytes']
        indexd += Counter({formatted_index: total})

    day_count = Counter()
    for i in indexes:
        day_count[re.sub('(\d{1,4}.\d{1,2}.\d{1,2})', '', i)] += 1

    print (indexd)
    print("\n")

    print ("Cluster Status: {}".format(get_color(clstatsd.get('status'))))
    print ('\n')

    cstats = []
    cstats.append(['Storage Size (GB)', 'Storage Used (GB)', 'Storage Available (GB)'])
    cstats.append(['%.2f' % (bytesto(total_size, 'g')), '%.2f' % (bytesto(total_used, 'g')), '%.2f' % (bytesto(total_available, 'g'))])
    table = AsciiTable(cstats, 'Cluster Sizing')
    print (table.table)
    print ('\n')

    cusage = []
    cusage.append(['JVM Total Mem (GB)', 'JVM Used/Free Mem (GB)'])
    cusage.append(['%.2f' % (bytesto(jvm_max_mem, 'g')), '%.2f/%.2f' % (bytesto(jvm_used_mem, 'g'), bytesto(jvm_free_mem, 'g'))])
    table = AsciiTable(cusage, 'Cluster JVM Usage')
    print (table.table ('\n'))
    

    # Sort the indexd
    indexd = OrderedDict(sorted(indexd.items()))
    istats = []
    istats.append(["Index Name", "Size (GB)", "Instance Count", "Percentage Of Use", "Avg Daily (GB)"])
    for i, size in indexd.iteritems():
        percentage = float(size) / float(total_size) * 100
        avg_daily = bytesto(size,'g') / day_count.get(i,1)
        istats.append([i, "%.2f" % bytesto(size,'g'), str(day_count.get(i, 1)), "%2.f" % percentage, "%2.f" % avg_daily])

    table = AsciiTable(istats, 'Index Usage Stats')
    print (table.table )
    print ('\n')
   
if __name__ == "__main__":
    main()
