# Copyright (C) Anton Wahrstätter 2021

# This file is part of python-bitcoin-graph which was forked from python-bitcoin-blockchain-parser.
#
# It is subject to the license terms in the LICENSE file found in the top-level
# directory of this distribution.
#
# No part of python-bitcoin-graph, including this file, may be copied,
# modified, propagated, or distributed except according to the terms contained
# in the LICENSE file.

# File with helper functions


import os
import sys
import psutil
import re
import csv
from datetime import datetime

# Helpers
#
now = datetime.now().strftime("%Y%m%d_%H%M%S")
def _print(s, end=""):
    s = f"  {datetime.now().strftime('%H:%M:%S')}   |  {s}"
    print(s, end=end)


def get_date(folder="./output"):
    try:
        content = [fn for fn in os.listdir(folder)]
        dates = [datetime.strptime(fn, "%Y%m%d_%H%M%S") for fn in content]
        return dates[dates.index(max(dates))].strftime("%Y%m%d_%H%M%S")
    except:
        return 0   

def save_edge_list(parser, uploader=None, location=None):
    rE           = parser.edge_list   # List with edges
    blkfilenr    = parser.fn          # File name
    cblk         = parser.cblk        # Bool if collecting blk file number
    cvalue       = parser.cvalue      # Bool if collecting values
    use_parquet  = parser.use_parquet # Bool if using parquet format
    multi_p      = parser.multi_p
    
    if parser.upload:
        uploader = parser.uploader
    else:
        location = parser.targetpath
    
    # If collecting blk numbers is activated, then append it to every edge
    if cblk:
        rE = list(map(lambda x: (x) + (blkfilenr,), rE))
    
    # Flatten each line of rE
    # if third entry is a tuple then transaction != coinbase transaction
    rE = [(*row[0:2],*row[2],*row[3:]) if type(row[2]) == tuple else (*row[0:3],*row[2:]) for row in rE]
        
    # Direct upload to Google BigQuery without local copy
    if uploader and not use_parquet:
        success = uploader.upload_data(rE, cblk=cblk,cvalue=cvalue)
        if success == "stop":
            _print("Parsing stopped...")
            
    # Using Parquet format
    elif uploader:
        success = uploader.handle_parquet_data(rE=rE,
                                               blkfilenr=blkfilenr,
                                               cblk=cblk,
                                               cvalue=cvalue
                                              )

    # Store locally
    else:
        if not os.path.isdir('{}/output'.format(location)):
            os.makedirs('{}/output'.format(location))
        if not os.path.isdir('{}/output/{}/rawedges/'.format(location,now)):
            os.makedirs('{}/output/{}/rawedges'.format(location,now))
        with open("{}/output/{}/rawedges/raw_blk_{}.csv".format(location, 
                                                                now, 
                                                                blkfilenr),"w",newline="") as f:
            cw = csv.writer(f,delimiter=",")
            cw.writerows(rE)
        success = True
        
    tablestats(parser)
    
    # Reset edge list
    parser.edge_list = []
    return success
                 
def used_ram():
    m = psutil.virtual_memory()
    return m.percent

def handle_time_delta(parser):
    # Add time delta to loop duration
    if parser.t0:
        delta = int((datetime.now()-parser.t0).total_seconds()) 

    # Else, it must be the first blk file that is parsed
    else:
        delta = int((datetime.now()-parser.creationTime).total_seconds())
    parser.loop_duration.append(delta)
    parser.loop_duration = parser.loop_duration[-15:]
    return delta, parser.loop_duration
           
def estimate_end(loopduration, curr_file, total_files):
    avg_loop = int(sum(loopduration[-15:])/len(loopduration[-15:]))
    delta_files = total_files - curr_file
    _estimate = datetime.fromtimestamp(datetime.now().timestamp() \
                                       + delta_files * avg_loop)
    return _estimate.strftime("%d.%m-%H:%M:%S")

def file_number(s):
    match = re.search("([0-9]{5})", s).group()
    if match == "00000":
        return 0
    else:
        return int(match.lstrip("0"))    

# BigQuery Table schema
def get_table_schema(cls, cblk, cvalue):

    # Default table schema
    c = [ {'name': '{}'.format(cls[0]), 'type': 'INTEGER'},
          {'name': '{}'.format(cls[1]), 'type': 'STRING'},
          {'name': '{}'.format(cls[2]), 'type': 'STRING'},
          {'name': '{}'.format(cls[3]), 'type': 'INTEGER'},
          {'name': '{}'.format(cls[4]), 'type': 'STRING'},
          {'name': '{}'.format(cls[5]), 'type': 'INTEGER'}
        ]
    if cvalue:
        c.append({'name': '{}'.format("value"), 'type': 'INTEGER'})
        c.append({'name': '{}'.format("script_type"), 'type': 'STRING'})
    if cblk:
        c.append({'name': '{}'.format("blk_file_nr"), 'type': 'INTEGER'})
        
    return c

def print_output_header(parser):
    print("{:-^13}|{:-^9}|{:-^23}|{:-^14}|{:->7}|"\
          "{:-^7}|{:-^10}|{:-^16}|{:-^21}|".format("","","","","","","","","")) 
    print("{:^13}|{:^9}| {:^21} | {:^12} | {:>5} |"\
          "{:^6} | {:^8} | {:^14} | {:^19} |".format("",
                                                     "",
                                                     "",
                                                     "",
                                                     "cum.",
                                                     " \u0394",
                                                     "avg. \u0394",
                                                     "estimated",
                                                     "RAM stats")) 
    print("{:^13}|{:^9}| {:^21} | {:^12} | {:>5} |"\
          "{:^6} | {:^8} | {:^14} | {:^19} |".format("timestamp",
                                                     "blk nr.",
                                                     "date range",
                                                     "edges/blk",
                                                     "edges",
                                                     " time",
                                                     "time",
                                                     "end",
                                                     "(used)")) 
    print("{:-^13}|{:-^9}|{:-^23}|{:-^14}|{:->7}|{:-^7}"\
          "|{:-^10}|{:-^16}|{:-^21}|".format("","","","","","","","","")) 

# Ugly stats-printing function
def tablestats(parser):
    rE            = parser.edge_list     # List with edges
    blkfilenr     = parser.fn            # File nr.
    re_len        = len(rE)              # Nr. of edges
    total_files   = parser.l             # Total blk files
    
    parser.cum_edges += re_len           # Cumulated edges
    
    # Storage/RAM stats
    csize = sys.getsizeof(parser.edge_list)
    m = psutil.virtual_memory()
    used_ram = m.total/(1024**3)-m.available/(1024**3)
    process = psutil.Process(os.getpid())
    col = "red" if m.total*0.75 < m.used else None
    
    # Time stats
    timestamp = datetime.now().strftime('%H:%M:%S')
    
    delta, loop_duration = handle_time_delta(parser)

    # Get timestamps of first and last entry in edge list
    t_0 = datetime.fromtimestamp(int(rE[0][0])).strftime("%d.%m.%Y")
    t_1 = datetime.fromtimestamp(int(rE[-1][0])).strftime("%d.%m.%Y")
    
    # Estimate end of parsing
    estimated_end = estimate_end(loop_duration, blkfilenr, total_files)
    
    # Avg iteration duration
    avg_loop      = int(sum(loop_duration)/len(loop_duration))
    
    # Print table
    sys.stdout.write("\r{:^13}|{:>4}/{:<4}| {:>10}-{:>10} | {:^12,} | "\
                     "{:>4}M | {:^4}s | {:^7}s | {:>14} | {:>3}/{:<3} "\
                     "GiB ({:<4}%) |\n".format(timestamp, 
                                               blkfilenr, 
                                               total_files, 
                                               t_0, 
                                               t_1, 
                                               re_len, 
                                               int(round(parser.cum_edges/int(1e6),0)),
                                               delta,
                                               avg_loop,
                                               estimated_end,
                                               int(used_ram),
                                               int(m.total/(1024**3)),
                                               m.percent))
    sys.stdout.flush()
