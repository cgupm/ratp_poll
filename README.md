# ratp_poll

Python scripts for polling different data from RATP. Using the
[pgrimaud/horaires-ratp-api](https://github.com/pgrimaud/horaires-ratp-api)
REST API.

Based on a similar project for the Madrid intercity buses: [cgupm/crtm_poll](https://github.com/cgupm/crtm_poll).

* [docs](https://ratp-poll.readthedocs.io/en/latest/)
* [docker](https://hub.docker.com/r/cgupm/ratp_poll)

## Features

* RATP:
   * Get the remaining times for the next vehicles of a line to a stop.
   * Get the parsed remaining times for the next vehicles of a line to a stop
      in CSV format.
   * Run a periodic daemon that executes one of the possible functions and
      stores the output a given file.

## Installation

```bash
pip3 install git+git://github.com/cgupm/ratp_poll
```

## Docker

You can use the *Dockerfile* to build a minimal image containing this tool and
its dependencies or directly use the [public
image](https://hub.docker.com/r/cgupm/ratp_poll):

```bash
docker run -it --rm -v "${PWD}:/home/user" -v /etc/localtime:/etc/localtime:ro --user $(id -u):$(id -g) cgupm/ratp_poll
```

## Usage

Once installed, this package provides a command line script that can be run as
follows:

```bash
ratp_poll --help
ratp_poll gst [type] [code] [station] [way]
```

## Testing

Tests can be run executing `pytest` or `make test` within the project's
directory.

## License

GPLv3

## Author Information

* cgupm: c.garcia-maurino (at) alumnos.upm.es
