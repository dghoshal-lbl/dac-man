import os
import sys
from hashlib import blake2b
import redis
import deduce_stream.settings as _settings
import uuid
import socket
import time
import csv

# Cache implementation using Redis
class Cache(object):
    def __init__(self, host, port):
        self._task_q = self._get_entity_name(_settings.TASK_QUEUE_NAME)
        self._task_list = self._get_entity_name(_settings.JOB_ORDERED_LIST)
        self._redis = self._init_redis(host, port)

        # stat vars for streaming source
        self._data_datablock_send_start = {}
        self._data_datablock_send_end = {}
        self._data_task_send_start = {}
        self._data_task_send_end = {}

        # stat vars for workers
        self._data_pull_start = {}
        self._data_pull_end = {}
        self._job_end_processing = {}
        self._job_end_data_put = {}

    def _get_entity_name(self, name):
        hash_digest = blake2b(digest_size=20)
        hash_digest.update(name.encode('utf-8'))
        entity_name = "%s:%s" % (name, hash_digest.hexdigest())
        return entity_name

    def _init_redis(self, host, port):
        r = redis.Redis(
            host=host,
            port=port
        )
        return r

    def set_redis_instance(self, r):
        self._redis = r
        return self._redis

    def worker_ready(self):
        self._redis.set("worker", 1)

    def pull_task(self, br_wait_time=10):
        return self._redis.brpop(self._task_q, br_wait_time)

    def dataid_to_datablock(self, task_uuid, *datablock_ids):
        self._data_pull_start[task_uuid] = time.time()
        datablocks = self._redis.mget(datablock_ids)
        self._data_pull_end[task_uuid] = time.time()

        return datablocks

    def put_results(self, task_uuid, results):
        self._job_end_processing[task_uuid] = time.time()
        self._redis.set(task_uuid, results)
        self._job_end_data_put[task_uuid] = time.time()

    def put_datablock(self, datablock):
        datablock_id = "%s:%s" % (_settings.DATABLOCK_PREFIX, str(uuid.uuid4()))

        self._data_datablock_send_start[datablock_id] = time.time()
        self._redis.set(datablock_id, datablock)
        self._data_datablock_send_end[datablock_id] = time.time()

        return datablock_id

    def put_multi_datablocks(self, datablocks):
        datab_mappings = {}

        datablock_ids = []
        for datab in datablocks:
            datablock_id = "%s:%s" % (_settings.DATABLOCK_PREFIX, str(uuid.uuid4()))
            datablock_ids.append(datablock_id)

            datab_mappings[datablock_id] = datab

        self._data_datablock_send_start[datablock_id] = time.time()
        self._redis.mset(datab_mappings)
        self._data_datablock_send_end[datablock_id] = time.time()

        return datablock_ids

    def get_current_window_size(self, window_key):
        n_objs = self._redis.llen(window_key)
        return n_objs

    def assign_datablocks_to_window(self, window_key, datablock_ids):
        n = self._redis.lpush(window_key, *datablock_ids)
        return n

    # Inserts entries to task-list and task-queue
    def create_task(self, *datablock_ids):
        task_uuid = "%s:%s" % (_settings.TASK_PREFIX, str(uuid.uuid4()))

        sys.stdout.write(str((task_uuid, *datablock_ids)) + "\n")

        task = str((task_uuid, *datablock_ids))

        self._data_task_send_start[task_uuid] = time.time()
        self._redis.rpush(self._task_list, task_uuid)
        self._redis.lpush(self._task_q, task)
        self._data_task_send_end[task_uuid] = time.time()

    # Retrieves datablock-ids within a window
    def get_windowed_datablock_ids(self, window_key, start=0, end=-1):
        return self._redis.lrange(window_key, start, end)

    # Saving streaming source stats to disk
    def write_streaming_source_stats(self, output_dir):
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        ####################################################################
        name = _settings.CSV_SOURCE_DICTS_DIRS[0]
        if not os.path.exists(os.path.join(output_dir, name)):
            os.makedirs(os.path.join(output_dir, name))

        output_full_path = os.path.join(output_dir, name, 
                '%s_%s_%s.csv' % (name, socket.gethostname(), os.getpid()))
        with open(output_full_path, 'w') as csv_file:
            writer = csv.writer(csv_file)
            for key, value in self._data_task_send_start.items():
               writer.writerow([key, value])

        ####################################################################
        name = _settings.CSV_SOURCE_DICTS_DIRS[1]
        if not os.path.exists(os.path.join(output_dir, name)):
            os.makedirs(os.path.join(output_dir, name))

        output_full_path = os.path.join(output_dir, name, 
                '%s_%s_%s.csv' % (name, socket.gethostname(), os.getpid()))
        with open(output_full_path, 'w') as csv_file:
            writer = csv.writer(csv_file)
            for key, value in self._data_task_send_end.items():
               writer.writerow([key, value])

    # Saving streaming source stats to disk
    def write_wroker_stats(self, output_dir):
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        ####################################################################
        name = _settings.CSV_WORKER_DICTS_DIRS[0]
        if not os.path.exists(os.path.join(output_dir, name)):
            os.makedirs(os.path.join(output_dir, name))

        output_full_path = os.path.join(output_dir, name, 
                '%s_%s_%s.csv' % (name, socket.gethostname(), os.getpid()))
        with open(output_full_path, 'w') as csv_file:
            writer = csv.writer(csv_file)
            for key, value in self._data_pull_start.items():
               writer.writerow([key, value])

        ####################################################################
        name = _settings.CSV_WORKER_DICTS_DIRS[1]
        if not os.path.exists(os.path.join(output_dir, name)):
            os.makedirs(os.path.join(output_dir, name))

        output_full_path = os.path.join(output_dir, name, 
                '%s_%s_%s.csv' % (name, socket.gethostname(), os.getpid()))
        with open(output_full_path, 'w') as csv_file:
            writer = csv.writer(csv_file)
            for key, value in self._data_pull_end.items():
               writer.writerow([key, value])

        ####################################################################
        name = _settings.CSV_WORKER_DICTS_DIRS[2]
        if not os.path.exists(os.path.join(output_dir, name)):
            os.makedirs(os.path.join(output_dir, name))

        output_full_path = os.path.join(output_dir, name, 
                '%s_%s_%s.csv' % (name, socket.gethostname(), os.getpid()))
        with open(output_full_path, 'w') as csv_file:
            writer = csv.writer(csv_file)
            for key, value in self._job_end_processing.items():
               writer.writerow([key, value])

        ####################################################################
        name = _settings.CSV_WORKER_DICTS_DIRS[3]
        if not os.path.exists(os.path.join(output_dir, name)):
            os.makedirs(os.path.join(output_dir, name))

        output_full_path = os.path.join(output_dir, name, 
                '%s_%s_%s.csv' % (name, socket.gethostname(), os.getpid()))
        with open(output_full_path, 'w') as csv_file:
            writer = csv.writer(csv_file)
            for key, value in self._job_end_data_put.items():
               writer.writerow([key, value])