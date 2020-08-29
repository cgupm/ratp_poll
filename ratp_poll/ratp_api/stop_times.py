import sys
import asyncio
from aiohttp import (
        ClientSession,
        TCPConnector,
        ClientTimeout,
        client_exceptions
)
import datetime
import json
from filelock import FileLock
import pathlib
import urllib.parse
import logging

logger = logging.getLogger()


def fetch_log(fetch_log=None, *args):
    """Write the passed arguments as CSV to fetch_log if set.

    Arguments:
        fetch_log (str): Path to the fethc log file.
        *args (object): CSV line column values.
    """
    if (fetch_log):
        csv_columns = 'actual_date,transport_type,line_code,stop_code,way,' \
                      'resp_time,resp_status,' \
                      'resp_length,timeout,connection_error,' \
                      'max_connections,timeout_time'
        log_csv = ",".join([str(arg) for arg in args])
        logger.debug("CSV fetch log line: " + log_csv)
        with FileLock(fetch_log + '.lock', timeout=10):
            path_exists = pathlib.Path(fetch_log).exists()
            with open(fetch_log, 'a+') as f:
                if (path_exists):
                    f.write('\n')
                else:
                    f.write(csv_columns + '\n')
                f.write(log_csv)


async def fetch(transport_type,
                line_code,
                station_name,
                way,
                session,
                fetch_conf):
    """Fetch the remaining time for a line to a given stop with a defined way
    reusing a session.

    Passes some additional data to the fetch_log function. The  CSV column
    names are:
    'actual_date,transport_type,line_code,stop_code,way,' \
    'resp_time,resp_status,resp_length,timeout, \
    'connection_error,max_connections,timeout_time'

    Arguments:
        transport_type (str): The transport type (metros, rers, tramways, buses
            or noctiliens).
        line_code (str): The line code (e.g. '187').
        station_name (str): The name of the station (e.g.
            'Division+Leclerc+-+Camille+Desmoulins').
        way (str): Way of the line ('A', 'R' or 'A+R').
        session (ClientSession): The aiohttp ClientSession.
        fetch_conf (dict): Dictionary with configuration parameters for
            fetching the content.

    Returns:
        str: Response text.
    """
    global counter

    actual_time = None
    resp_time = None
    resp_status = None
    resp_length = None
    timeout = None
    connection_error = None

    api_url = 'https://api-ratp.pierre-grimaud.fr/v4/schedules/'
    params = '{transport_type}/' \
             '{line_code}/' \
             '{station_name}/' \
             '{way}'.format(**locals())
    url = api_url+urllib.parse.quote(params)
    actual_time = datetime.datetime.now()
    try:
        async with session.get(url) as response:
            dt_2 = datetime.datetime.now()
            resp_time = (dt_2 - actual_time).total_seconds()
            resp_status = response.status
            resp_text = await response.text()
            resp_length = len(resp_text)
            timeout = False
            connection_error = False
            logger.info("Response time: " + str(resp_time)
                        + " code: " + str(resp_status)
                        + " length: " + str(resp_length))
            fetch_log(fetch_conf['log'], actual_time,
                      transport_type, line_code, station_name, way,
                      resp_time, resp_status,
                      resp_length, timeout, connection_error,
                      fetch_conf['max_connections'], fetch_conf['timeout'])
            return resp_text
    except asyncio.TimeoutError:
        dt_2 = datetime.datetime.now()
        resp_time = (dt_2 - actual_time).total_seconds()
        timeout = True
        connection_error = False
        logger.warning("Timeout")
        fetch_log(fetch_conf['log'], actual_time,
                  transport_type, line_code, station_name, way,
                  resp_time, resp_status,
                  resp_length, timeout, connection_error,
                  fetch_conf['max_connections'], fetch_conf['timeout'])
    except client_exceptions.ClientConnectorError:
        dt_2 = datetime.datetime.now()
        resp_time = (dt_2 - actual_time).total_seconds()
        timeout = False
        connection_error = True
        logger.warning("Connection error")
        fetch_log(fetch_conf['log'], actual_time,
                  transport_type, line_code, station_name, way,
                  resp_time, resp_status,
                  resp_length, timeout, connection_error,
                  fetch_conf['max_connections'], fetch_conf['timeout'])


async def run(queries, fetch_conf):
    """Async function that generates a aiohttp ClientSession and fetches the
    given queries.

    Arguments:
        queries (list): List of tuples with the query details (transport_type,
            line_code, station_name, way).
        fetch_conf (dict): Dictionary with configuration parameters for
            fetching the content.

    Returns:
        list: The responses.
    """
    tasks = []

    # Fetch all responses within one Client session,
    # keep connection alive for all requests.
    connector = TCPConnector(limit=fetch_conf['max_connections'])
    timeout = ClientTimeout(total=fetch_conf['timeout'])
    async with ClientSession(connector=connector, timeout=timeout) as session:
        for query in queries:
            task = asyncio.ensure_future(fetch(*query, session, fetch_conf))
            tasks.append(task)

        responses = await asyncio.gather(*tasks)
        # you now have all response bodies in this variable
        return responses


def get_stop_times_batch(queries, fetch_conf):
    """Get the remaining times for a line to a given stop with a defined way
        of several queries.

    Arguments:
        queries (list): List of tuples with the query details (transport_type,
            line_code, station_name, way).
        fetch_conf (dict): Dictionary with configuration parameters for
            fetching the content.

    Returns:
        (list): List containing the API answers in JSON format.
        (float): Total spent time in seconds.
    """

    dt_1 = datetime.datetime.now()
    loop = asyncio.get_event_loop()
    future = asyncio.ensure_future(run(queries, fetch_conf))
    loop.run_until_complete(future)
    dt_2 = datetime.datetime.now()

    json_array = list(filter(None, future.result()))
    total_time = (dt_2 - dt_1).total_seconds()

    return json_array, total_time


def get_stop_times(query, fetch_conf):
    """Get the stop times for all the bus lines in a given stop.

    Arguments:
        query (tuple): Tuple with the query details (transport_type,
            line_code, station_name, way).
        fetch_conf (dict): Dictionary with configuration parameters for
            fetching the content.

    Returns:
        json: API answer in JSON format.
        float: Request time in seconds.
    """
    json_array, total_time = get_stop_times_batch([(query)], fetch_conf)

    try:
        json = json_array[0]
        time = total_time

        return json, time
    except IndexError:
        logger.error("Empty answer")
        sys.exit(1)


gstbp_csv_columns = 'actual_date,query,remaining_minutes,destination_stop'


def get_stop_times_batch_parsed(queries, fetch_conf):
    """Get the remaining times for a line to a given stop with a defined way
        of several queries in CSV format.

    The CSV column names are: 'actual_date,transport_type,line_code,
    station_name,way,remaining_minutes,destination_stop'

    Arguments:
        queries (list): List of tuples with the query details (transport_type,
            line_code, station_name, way).
        fetch_conf (dict): Dictionary with configuration parameters for
            fetching the content.

    Returns:
        list: Parsed API answers in CSV format.
        float: Total spent time in seconds.
    """

    json_array, total_time = get_stop_times_batch(queries, fetch_conf)

    csv_array = []

    for stop in json_array:
        try:
            split_stop = stop.split('{', 1)
        except AttributeError:
            logger.warning("Empty answer")
            continue

        if (len(split_stop) > 1):
            stop = '{' + split_stop[1]

        try:
            stop_json = json.loads(stop)
        except ValueError:
            logger.warning("json error")
            continue

        try:
            schedules = stop_json['result']['schedules']
            metadata = stop_json['_metadata']
            for schedule in schedules:
                selected_fields = [
                        metadata['date'],
                        metadata['call'],
                        schedule['message'].replace(' mn', ''),
                        schedule['destination'],
                        ]
                row = ','.join(selected_fields)
                csv_array.append(row)
        except (KeyError, TypeError):
            logger.warning("Answer without times")
            continue
        except Exception as e:
            logger.warning("Unknown error: " + str(e))
            continue

    return csv_array, total_time
