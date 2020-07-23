import argparse
import pandas as pd
from deduce_stream.source import BasicStreamSrc

def main(host, port, dataset_iterator, dataset_src,
         measurement, stats_dir):
    stream_src = BasicStreamSrc(host, port)
    stream_src.set_stats_dir(stats_dir)

    stream_src.set_dataset_iterator(dataset_iterator)
    stream_src.stream(dataset_src, measurement)


###################
# Data stream transformation
def transform_fluxnet_stream(stream_src, measurement=None):
    df = pd.read_csv(stream_src, comment='#', sep=',', na_filter=False, dtype='str')
    df['datetime'] = df['TIMESTAMP_END']

    dataset_len = len(df.index)
    for i in range(1, dataset_len):
        data_points = df.loc[i-1:i, measurement]
        yield data_points.tolist()

def transform_lathuile_stream(stream_src, measurement=None):
    df = pd.read_csv(stream_src, comment='#', sep=',', na_filter=False, dtype='str')
    df['datetime'] = (pd.to_datetime(df['Year'].str[:-2]) + pd.to_timedelta(df['DoY'].str[:-2] + 'days') + \
        pd.to_timedelta('-1 day') + pd.to_timedelta(pd.to_numeric(df['Time']), unit='h'))
    df['datetime'] = df['datetime'].dt.strftime('%Y%m%d%H%M')

    dataset_len = len(df.index)
    for i in range(1, dataset_len):
        data_points = df.loc[i-1:i, measurement]
        yield data_points.tolist()


###################
def _fluxnetSourceParser(subparsers):
    parser_worker = subparsers.add_parser('fluxnet',
                                          formatter_class=argparse.ArgumentDefaultsHelpFormatter,
                                          help=""" Streaming dstream for Fluxnet data """)

    parser_worker.set_defaults(action="fluxnet")
    parser_worker.add_argument(dest='filename', help='input stream file')
    parser_worker.add_argument('-m', '--measurement',
                               choices=['CO2_F_MDS', 'WD', 'TA_F'], type=str,
                               default='CO2_F_MDS', help='measurement')
    parser_worker.add_argument('-r', '--redis_host', type=str, required=True, help='Redis host')
    parser_worker.add_argument('-p', '--redis_port', type=str, required=True, help='Redis port')
    parser_worker.add_argument('-o', '--output_stats_dir', type=str, help='output stats directory')


def _lathuileSourceParser(subparsers):
    parser_worker = subparsers.add_parser('lathuile',
                                          formatter_class=argparse.ArgumentDefaultsHelpFormatter,
                                          help=""" Streaming dstream for La Thuile data """)

    parser_worker.set_defaults(action="lathuile")
    parser_worker.add_argument(dest='filename', help='input stream file')
    parser_worker.add_argument('-m', '--measurement',
                               choices=['CO2', 'WD', 'Ta_f'], type=str,
                               default='CO2', help='measurement')
    parser_worker.add_argument('-r', '--redis_host', type=str, required=True, help='Redis host')
    parser_worker.add_argument('-p', '--redis_port', type=str, required=True, help='Redis port')
    parser_worker.add_argument('-o', '--output_stats_dir', type=str, help='output stats directory')


###################
# Usage with Ameriflux data, for creating tasks with two datablocks
# python source.py fluxnet
#    data/fluxnet2015/FLX_AT-Neu_FLUXNET2015_FULLSET_HH_2002-2012_1-3.csv
#    -r redis-host -p redis-port -o stats_dir
#
# python source.py lathuile data/la_thuile/AT-Neu.2002.synth.hourly.allvars.csv
#    -r redis-host -p redis-port -o stats_dir

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="fluxnet streaming source",
                                     prog="source.py",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    subparsers = parser.add_subparsers()
    _fluxnetSourceParser(subparsers)
    _lathuileSourceParser(subparsers)

    args = parser.parse_args()

    if args.action == 'fluxnet':
        fn = transform_fluxnet_stream
    elif args.action == 'lathuile':
        fn = transform_lathuile_stream
    else:
        raise ValueError("%s is not supported." % args.action +
            "Only fluxnet & lathuile are supported so far")

    main(args.redis_host, args.redis_port, fn, args.filename,
         args.measurement, args.output_stats_dir)