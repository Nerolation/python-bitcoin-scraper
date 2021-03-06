# Copyright (C) Anton Wahrstätter 2021

# This file is part of python-bitcoin-graph which was forked from python-bitcoin-blockchain-parser.
#
# It is subject to the license terms in the LICENSE file found in the top-level
# directory of this distribution.
#
# No part of python-bitcoin-graph, including this file, may be copied,
# modified, propagated, or distributed except according to the terms contained
# in the LICENSE file.


# Command line interface to either start parsing or upload already parsed edges to BigQuery

import os
import argparse
import numpy as np
from datetime import datetime
from multiprocessing import Process, cpu_count, connection

from bitcoin_graph import starting_info
from bitcoin_graph.btcTxParser import *
from bitcoin_graph.uploader import Uploader
from bitcoin_graph.logger import BlkLogger
from bitcoin_graph.helpers import file_number


parser = argparse.ArgumentParser(formatter_class=lambda prog: argparse.HelpFormatter(prog,max_help_position=60))
parser.add_argument('-sf', '--startfile', help=".blk start file (included) - default: blk00000.dat", default="blk00000.dat")
parser.add_argument('-ef', '--endfile', help=".blk end file (included) - default: None", default=None)
parser.add_argument('-st', '--starttx', help="start transaction id (included) - default: None", default=None)
parser.add_argument('-et', '--endtx', help="end transaction id (excluded) - default: None", default=None)
parser.add_argument('-ets', '--endts', help="end timestamp of block - default: None", default=None)
parser.add_argument('-loc', '--blklocation', help=".blk|.csv file location - default: ~/.bitcoin/blocks", default="~/.bitcoin/blocks")

# Raw edge-list
parser.add_argument('-path', '--targetpath', help="path to store raw edges locally - default: ./", default="./")
parser.add_argument('-cv', '--collectvalue', help="collect output values - default: No", action='store_true')
parser.add_argument('-cb', '--collectblk', help="collect blk file numbers with every edge - default: No", action='store_true')

# Uploader
if os.path.isdir(".gcpkey") and len(os.listdir(".gcpkey")) > 0:
    creds = [".gcpkey/"+fn for fn in os.listdir(".gcpkey") if fn.endswith(".json")][0]
else:
    creds = None

# Direct upload
parser.add_argument('-up', '--upload', help="upload edges to google bigquery - default: False",  action='store_true')

# Use Parquet format
parser.add_argument('-parq', '--parquet', help="use parquet format - default: False",  action='store_true')

# Use Multiprocessing
parser.add_argument('-mp', '--multiprocessing', help="use multiprocessing - default: False",  action='store_true')

# Parquet file upload threshold
parser.add_argument('-ut', '--uploadthreshold', help="uploading threshold for parquet files - default: 5",  default=5)

# Bucket name
parser.add_argument('-b', '--bucket', help="bucket name to store parquet files - default: btc_<timestamp>",  default="btc_{}".format(int(datetime.now().timestamp())))

# Upload configurations (if direct upload or uploading existing files)
parser.add_argument('-c', '--credentials', help="path to google credentials (.*json)- default: ./.gcpkey/.*json", default=creds)
parser.add_argument('-p', '--project', help="google cloud project name - default: btcgraph", default="btcgraph")
parser.add_argument('-ds', '--dataset', help="bigquery data set name - default: btc", default="btc")
parser.add_argument('-tid', '--tableid', help="bigquery table id - default: bitcoin_transactions", default="bitcoin_transactions")


# Handle parameters
_args = parser.parse_args()

# Print some env info
starting_info(vars(_args))

# Static variables
startFile    = _args.startfile
endFile      = _args.endfile
startTx      = _args.starttx
endTx        = _args.endtx
endTS        = _args.endts
file_loc     = _args.blklocation
targetpath   = _args.targetpath
collectvalue = _args.collectvalue
cblk         = _args.collectblk
upload       = _args.upload
use_parquet  = _args.parquet
up_thres     = _args.uploadthreshold
bucket       = _args.bucket
creds        = _args.credentials
project      = _args.project
table_id     = _args.tableid
dataset      = _args.dataset
multi_p      = _args.multiprocessing
# -----------------------------------------------


    
# Start Parser

# Initialize btc graph object
# `blk_loc` for the location where the blk files are stored
# `raw Edges` to additionally save graph in edgeList format
btc_graph = BtcTxParser(dl=file_loc, endTS=endTS, upload=upload, use_parquet=use_parquet, 
                        upload_threshold=up_thres, bucket=bucket, cvalue=collectvalue, cblk=cblk, 
                        targetpath=targetpath, credentials=creds, table_id=table_id, dataset=dataset, 
                        project=project, multi_p=multi_p)

# Start building graph
if __name__ == '__main__':
    try:
        if not multi_p:

                btc_graph.parse(startFile,endFile,startTx,endTx)

        else:
            cpus = cpu_count()
            sF = file_number(startFile)
            eF = file_number(endFile)
            r = list(range(sF, eF+1))
            
            processes = []
            
            if upload:  
                cpu_u = 1
                cpu_p = cpus - cpu_u
                uploader = Uploader(credentials=creds, table_id=table_id, dataset=dataset, 
                                    project=project, logger=BlkLogger(), bucket=bucket, 
                                    multi_p=multi_p, cores=cpu_p, loc=file_loc)
                processes.append(Process(target = uploader.upload_parquet_data))
                
            else:
                cpu_p = cpus
            
            d  = round((eF - sF)/cpu_p)
            pack = {}
            for i in range(cpu_p):
                if i+1 == cpu_p:
                    pack[i] = r[d*i:]
                else:
                    pack[i] = r[d*i:d*(1+i)]
           
            for i in list(pack):
                if len(pack[i]) < 1:
                    continue
                start = "blk{}.dat".format(str(list(pack[i])[0]).zfill(5))
                end   = "blk{}.dat".format(str(list(pack[i])[-1]).zfill(5))
                processes.append(Process(target = btc_graph.parse, args=(start,end,startTx,endTx, i)))



            for p in processes:
                p.start()
                print("Starting process at PID {:>5}".format(p.pid))
 
            connection.wait(p.sentinel for p in processes)
    # Crtl + C to end execution
    except KeyboardInterrupt:
        if multi_p:
            if len(processes) > 0:
                for p in processes:
                    print("Ending process at PID {:>5}".format(p.pid))
                    p.terminate()
        print("\nKEYBOARD WAS INTERRUPTED")
        print("-----------------------------------------")
