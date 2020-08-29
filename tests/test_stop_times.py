#!/usr/bin/env python

"""Test `ratp_api` module."""

from ratp_poll import ratp_api

from aiohttp import ClientSession
from aioresponses import aioresponses
import os
import pytest


class TestAPI:
    def test_can_log_fetch(self, tmpdir):
        fetch_path = 'fetch_log'
        file = tmpdir.join(fetch_path)
        ratp_api.stop_times.fetch_log(file, 'a', 'b', 'c')
        assert file.readlines()[1] == 'a,b,c'

    def test_can_not_log_fetch(self, tmpdir):
        fetch_path = 'fetch_log'
        file = tmpdir.join(fetch_path)
        ratp_api.stop_times.fetch_log(None, 'a', 'b', 'c')
        assert not os.path.isfile(file)

    @pytest.mark.asyncio
    async def test_can_fetch_ok_stop(self):
        with aioresponses() as m:
            m.get('https://api-ratp.pierre-grimaud.fr/v4/schedules/'
                  'buses/187/Division%20Leclerc%20-%20Camille%20Desmoulins/A',
                  status=200, body='test')
            session = ClientSession()
            fetch_conf = {
                    'log': None,
                    'timeout': 10,
                    'max_connections': 1}
            resp_text = await ratp_api.stop_times.fetch('buses', '187',
                                                        'Division Leclerc - '
                                                        'Camille Desmoulins',
                                                        'A',
                                                        session,
                                                        fetch_conf)
            assert 'test' in resp_text
            await session.close()
