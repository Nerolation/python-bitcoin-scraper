from bitcoin_graph import starting_info
from bitcoin_graph.btcTxParser import *
from bitcoin_graph.bqUploader import *
import argparse
import os



parser = argparse.ArgumentParser(formatter_class=lambda prog: argparse.HelpFormatter(prog,max_help_position=60))
parser.add_argument('-sf', '--startfile', help=".blk start file (included) - default: blk00000.dat", default="blk00000.dat")
parser.add_argument('-ef', '--endfile', help=".blk end file (excluded) - default: None", default=None)
parser.add_argument('-st', '--starttx', help="start transaction (included) - default: None", default=None)
parser.add_argument('-et', '--endtx', help="end transaction (excluded) - default: None", default=None)
parser.add_argument('-ets', '--endts', help="end timestamp of block - default: None", default=None)
parser.add_argument('-loc', '--blklocation', help=".blk|.csv file location - default: ~/.bitcoin/blocks", default="~/.bitcoin/blocks")
parser.add_argument('-utxo', '--utxos', help="path to existing Utxos file - default: None", default=None)
parser.add_argument('-lm', '--lowmemory', help="low memory mode (collecting raw tx inputs) - default: False", default=None)


# Raw edge-list
parser.add_argument('-lp', '--localpath', help="path to store raw edges - default: ./", default="./")
parser.add_argument('-wts', '--withts', help="collect list of edges with timestamps - default: No", default=None)
parser.add_argument('-wv', '--withvalue', help="collect output values - default: No", default=None)

# Uploader
if os.path.isdir(".gcpkey") and len(os.listdir(".gcpkey")) > 0:
    creds = [".gcpkey/"+fn for fn in os.listdir(".gcpkey") if fn.endswith(".json")][0]
else:
    creds = None

# Direct upload
parser.add_argument('-up', '--directupload', help="upload edges directly(!) to google bigquery - default: False", default=None)

# Upload existing raw_blk files
parser.add_argument('-gbq', '--googlebigquery', help="upload edges to google bigquery - default: False", default=None)

# Upload configurations
parser.add_argument('-c', '--credentials', help="path to google credentials (.*json)- default: ./.gcpkey/.*json", default=creds)
parser.add_argument('-tid', '--tableid', help="bigquery table id - default: btc", default="btc")
parser.add_argument('-ds', '--dataset', help="bigquery data set name - default: bitcoin_transactions", default="bitcoin_transactions")

# Handle parameters
_args = parser.parse_args()

# Print some env info
starting_info(vars(_args))

# Static variables
startFile = _args.startfile
endFile   = _args.endfile
startTx   = _args.starttx
endTx     = _args.endtx
endTS     = _args.endts
file_loc  = _args.blklocation
utxos     = _args.utxos
lowMemory = _args.lowmemory
localpath = _args.localpath
withTS    = _args.withts
withvalue = _args.withvalue
gbq       = _args.googlebigquery
upload    = _args.directupload
creds     = _args.credentials
table_id  = _args.tableid
dataset   = _args.dataset
# -----------------------------------------------

if not gbq:
    # Initialize btc graph object
    # `blk_loc` for the location where the blk files are stored
    # `raw Edges` to additionally save graph in edgeList format
    btc_graph = BtcTxParser(dl=file_loc, Utxos=utxos, endTS=endTS,
                            lowMemory=lowMemory, withTS=withTS, upload=upload, 
                            collectValue =withvalue, localpath=localpath,
                            credentials=creds, table_id=table_id, dataset=dataset)

    # Start building graph
    btc_graph.parse(startFile,endFile,startTx,endTx)
    
else:
    # Initialize Big Query Uploader
    bq = bqUpLoader(credentials=creds, path=file_loc, table_id=table_id, dataset=dataset)
    
    # Upload raw edges csv files to google cloud/big-query
    bq.upload_data()
    
print("-----------------------------------------")